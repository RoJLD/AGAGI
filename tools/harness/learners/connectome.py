"""
tools/harness/learners/connectome.py — ConnectomeLearner : l'adaptateur UNIQUE vers make_population(backend="torch")
(frontière population, ADR-003). Il rejoue EXACTEMENT la séquence de tools/bilinear_composition_probe._train_eval_one
(np.random.seed(seed) AVANT les MambaAgent() ; torch.manual_seed(seed) AVANT make_population ; drapeaux de classe
posés AVANT ; Adam sur [W] + [U, V, W_bl] présents ; rng des opérandes seed+1 tenu par le runner) : c'est ce qui rend
la cellule A bit-identique à results bilinear_composition.json.

Piège E5 : type(self).BILINEAR est relu à CHAQUE _step (backend_torch.py:128) — les drapeaux restent posés tant
qu'une instance est ouverte ; close() de la DERNIÈRE instance restaure l'état d'origine ; ouvrir une instance à
drapeaux DIFFÉRENTS d'une instance ouverte est refusé.

Décision contrôleur (tâche 9, 2026-09-16) — les drapeaux comparés/restaurés sont un TUPLE EXPLICITE de CINQ
éléments (CONDITION_GATE, GATE_TARGET, BILINEAR, BILINEAR_RANK, BILINEAR_SHAM) : `BILINEAR_SHAM` (P4.12) est
lu par `_step` au même titre que `BILINEAR`, donc doit être épinglé/restauré exactement comme les quatre autres
— un flag de classe non couvert par la comparaison "drapeaux différents" laisserait deux instances partager un
process avec un SHAM actif sur l'une et pas l'autre, invisible à `_flags`.

Revue contrôleur, fix round 1 (2026-09-16) — deux défauts réels :
CRITICAL 1 (fuite de drapeaux sur un `build` qui ÉCHOUE, PERMANENTE) : toute validation qui peut lever
(`credit`, `hyper["lr"]`, cohérence `bilinear_sham`/`bilinear`) est désormais faite AVANT la moindre
écriture d'un drapeau de classe -- un échec pur (avant mutation) ne touche jamais l'état global. Ce qui
reste APRÈS l'écriture des drapeaux (seed, `make_population`, construction d'Adam) est enveloppé dans un
`try/except` : un échec y restaure `_ORIGINAL` SI `_OPEN` est vide (aucune autre instance légitime ne
dépend des drapeaux qu'on vient de poser), puis relève -- sinon (une autre instance est déjà ouverte avec
CES MÊMES drapeaux) on relève sans rien toucher, les drapeaux restant ceux, corrects, de l'instance
ouverte. Avant ce correctif : `build(..., credit="reinforce")` levait APRÈS avoir déjà écrit `BILINEAR`
etc. sur la classe, avec `self` jamais ajouté à `_OPEN` -- la fuite devenait PERMANENTE dès le build
suivant, qui capturait l'état fuité comme `_ORIGINAL`.
IMPORTANT 2 : `bilinear_sham=True` avec `bilinear=False` était accepté et silencieusement INERTE (la
branche sham de `_step` est sous le garde `BILINEAR` ; `U`/`V`/`W_bl` sont `None`) -- refusé désormais
par `ValueError`, avant tout drapeau.
IMPORTANT 3 (ruling contrôleur) : la variante « sans recurrent_state » (`without={"feedforward": True}`)
est un learner ENTRAÎNÉ SANS ÉTAT PORTÉ, pas une lésion à l'évaluation seule -- `learn` n'imite plus la
séquence entière sous ce régime, seulement le SEUL pas noté (le pas réponse), rejoué depuis H=0 : un
`opt.step` par épisode, dose appariée à l'intact (mêmes `calls`/`updates`). `act` continue de zéroer
l'état AVANT chaque `forward` (comportement inchangé côté éval) ; sous `feedforward`, `act` renvoie
désormais un état explicitement nul (auto-descriptif : aucune information n'y est jamais portée) plutôt
que le `H` réel (qui serait de toute façon écrasé par des zéros à l'appel suivant).
"""
import copy
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.harness_learner import Dose  # noqa: E402
from src.seed_ai.harness_pieces import PIECES  # noqa: E402

_OPEN = []            # instances ouvertes (état global du process)
_ORIGINAL = {"flags": None}


class _ConnectomeInstance:
    def __init__(self, seed, n, K, hyper, without, reference):
        import torch
        from src.agents.backend import make_population
        from src.agents.backend_torch import TorchPopulationModel
        from src.agents.mamba_agent import MambaAgent
        cfg = {"bilinear": True, "feedforward": False, "truncate": False,
               "bilinear_sham": bool(hyper.get("bilinear_sham", False))}
        cfg.update(without or {})
        # --- Zone PURE (fix CRITICAL 1) : tout ce qui peut lever DOIT lever ICI, avant la moindre
        # écriture d'un drapeau de classe -- sinon un échec laisse le process avec des drapeaux MUTÉS
        # et `self` jamais dans `_OPEN`, donc plus aucune instance pour les restaurer à la fermeture.
        if cfg["bilinear_sham"] and not cfg["bilinear"]:
            raise ValueError(
                "bilinear_sham=True sans bilinear=True : le sham est sous le garde BILINEAR de _step "
                "(U/V/W_bl sont None si BILINEAR est faux) -- silencieusement INERTE, refusé (IMPORTANT 2)")
        credit = hyper.get("credit", "supervised")
        if credit != "supervised":
            raise NotImplementedError("crédit REINFORCE : pièce optionnelle, hors R1")
        lr = 0.0 if reference else float(hyper["lr"])          # KeyError pur si absent -- avant tout drapeau
        rank = int(hyper.get("rank", 16))
        flags = (False, None, bool(cfg["bilinear"]), rank, bool(cfg["bilinear_sham"]))
        for other in _OPEN:
            if other._flags != flags:
                raise RuntimeError(
                    f"une instance connectome ouverte porte d'autres drapeaux {other._flags} != {flags} "
                    "(drapeaux de classe, état global E5) : close() d'abord")
        # --- Zone de MUTATION : à partir d'ici, toute levée doit restaurer avant de se propager. ---
        if not _OPEN:
            _ORIGINAL["flags"] = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
                                  TorchPopulationModel.BILINEAR, TorchPopulationModel.BILINEAR_RANK,
                                  TorchPopulationModel.BILINEAR_SHAM)
        TorchPopulationModel.CONDITION_GATE = False
        TorchPopulationModel.GATE_TARGET = None
        TorchPopulationModel.BILINEAR = flags[2]
        TorchPopulationModel.BILINEAR_RANK = flags[3]
        TorchPopulationModel.BILINEAR_SHAM = flags[4]
        try:
            np.random.seed(int(seed))                 # MambaAgent() tire W sur le rng GLOBAL (29 584 tirages/agent)
            torch.manual_seed(int(seed))               # U, V, W_bl dans cet ordre, ssi BILINEAR
            pop = make_population([MambaAgent() for _ in range(int(n))], backend="torch")
            params = [pop.W] + [p for p in (pop.U, pop.V, pop.W_bl) if p is not None]
            pop.opt = torch.optim.Adam([pop.W] + [p for p in (pop.U, pop.V, pop.W_bl) if p is not None], lr=lr)
        except Exception:
            if not _OPEN and _ORIGINAL["flags"] is not None:
                (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
                 TorchPopulationModel.BILINEAR, TorchPopulationModel.BILINEAR_RANK,
                 TorchPopulationModel.BILINEAR_SHAM) = _ORIGINAL["flags"]
                _ORIGINAL["flags"] = None
            raise
        self.pop, self._params = pop, params
        self._flags, self._TPM, self._torch = flags, TorchPopulationModel, torch
        self.K, self.n = int(K), int(n)
        self.feedforward, self.truncate = bool(cfg["feedforward"]), bool(cfg["truncate"])
        self.n_classes, self.credit = hyper.get("n_classes"), credit
        self._dose = Dose(unit="gradient_updates")
        _OPEN.append(self)

    def init_state(self):
        return self._torch.zeros((self.n, self.pop.N))

    def act(self, obs_t, state):
        if self.feedforward:
            state = self._torch.zeros_like(state)
        self.pop.H = state
        logits, _ = self.pop.forward(obs_t)           # met à jour pop.H ; logits = VUE de H -> copie
        # Sous feedforward, l'état sortant est explicitement nul (auto-descriptif : aucune information
        # n'y est JAMAIS portée sous ce régime -- l'appel suivant le zéroerait de toute façon en tête ;
        # renvoyer le vrai H, qui provient d'un forward dont l'entrée était déjà zéro, ajouterait un
        # clone inutile d'un tenseur qui ne sert jamais).
        new_state = self._torch.zeros_like(self.pop.H) if self.feedforward else self.pop.H.detach().clone()
        return np.array(np.asarray(logits)[:, :self.K], copy=True), new_state

    def learn(self, ep, actions, hits):
        self._dose.calls += 1
        self._dose.episodes_seen += ep.n
        before = [p.detach().clone() for p in self._params]
        tgt = np.asarray(ep.target, dtype=np.int64)
        if self.feedforward:
            # Ruling contrôleur (fix round 1, 2026-09-16) : la variante « sans recurrent_state » doit
            # être un learner ENTRAÎNÉ sans état porté, pas une lésion à la seule évaluation -- imiter
            # la séquence ENTIÈRE ici entraînerait un W qui compte sur l'état carrié entre les pas
            # (imitate_episode_bptt démarre à H=0 en interne et laisse H évoluer À TRAVERS les pas),
            # exactement la capacité que cette variante est censée retirer. On ne rejoue donc que le
            # SEUL pas noté (le pas réponse), depuis H=0 : un opt.step par épisode, dose appariée à
            # l'intact (mêmes calls/updates).
            t_last = ep.T - 1
            targets = [tgt]
            mask = None if ep.mask_seq is None else [np.asarray(ep.mask_seq[t_last], dtype=np.float32)]
            self.pop.imitate_episode_bptt([ep.obs_seq[t_last]], targets, mask_seq=mask,
                                          n_classes=self.n_classes, truncate_window=None)
        else:
            targets = [tgt] if ep.T == 1 else [np.zeros(ep.n, dtype=np.int64)] * (ep.T - 1) + [tgt]
            mask = None if ep.mask_seq is None else [np.asarray(m, dtype=np.float32) for m in ep.mask_seq]
            self.pop.imitate_episode_bptt(list(ep.obs_seq), targets, mask_seq=mask, n_classes=self.n_classes,
                                          truncate_window=(1 if self.truncate else None))
        d = float(sum((p.detach() - b).abs().sum().item() for p, b in zip(self._params, before)))
        self._dose.updates += int(d > 0.0)
        self._dose.dparam_abs_sum = (self._dose.dparam_abs_sum or 0.0) + d
        return self._dose

    def ablate_state(self, state, name):
        if name != "state_reset":
            raise KeyError(f"ablation d'état inconnue : {name!r}")
        return self._torch.zeros_like(state)

    def state_dict(self):
        return {"W": self.pop.W.detach().cpu().numpy(),
                "U": None if self.pop.U is None else self.pop.U.detach().cpu().numpy(),
                "V": None if self.pop.V is None else self.pop.V.detach().cpu().numpy(),
                "W_bl": None if self.pop.W_bl is None else self.pop.W_bl.detach().cpu().numpy(),
                "opt": copy.deepcopy(self.pop.opt.state_dict())}   # ne doit pas aliaser l'état live d'Adam

    def dose(self):
        return self._dose

    def close(self):
        if self in _OPEN:
            _OPEN.remove(self)
        if not _OPEN and _ORIGINAL["flags"] is not None:
            (self._TPM.CONDITION_GATE, self._TPM.GATE_TARGET, self._TPM.BILINEAR, self._TPM.BILINEAR_RANK,
             self._TPM.BILINEAR_SHAM) = _ORIGINAL["flags"]
            _ORIGINAL["flags"] = None


class ConnectomeLearner:
    name, family, max_K = "connectome_torch", "connectome_torch", 8
    entry_task = "composition_same_tick_K6 -- billet PAYE : bilinear_composition.json (results), 0,932 vs 0,271, n=12"
    supported_state_ablations = frozenset({"state_reset"})

    def __init__(self, credit="supervised", rank=16, lrs=(0.02, 0.002), n_classes=None):
        self.pieces = (PIECES["bilinear"], PIECES["recurrent_state"], PIECES["bptt_credit"])
        self.credit, self.rank, self.lrs, self.n_classes = credit, int(rank), tuple(float(x) for x in lrs), n_classes

    def sweep(self):
        return [{"lr": lr, "rank": self.rank, "n_classes": self.n_classes, "credit": self.credit} for lr in self.lrs]

    def build(self, seed, n, obs_dim, K, hyper, *, without=None, reference=False):
        if int(obs_dim) != 59:
            raise ValueError(f"obs_dim={obs_dim} : le connectome par défaut a I=59 entrées (MambaAgent)")
        if int(K) > self.max_K:
            raise ValueError(f"K={K} > max_K={self.max_K} (_MOVE_LOGITS)")
        return _ConnectomeInstance(seed, n, K, hyper, without or {}, reference)
