"""
tools/harness/tasks/composition.py — CompositionTask : (q + key) % K, portée SANS COPIE depuis
tools/bilinear_composition_probe.py (_make_seq / _slot restent la réponse connue de la cellule A).

Slots : key dans [0:K), q dans [K:2K), distracteur dans [2K:3K) — VIDE dans l'episode intact (bit-identite avec
_make_seq), REMPLI d'un one-hot aleatoire par l'ablation `inject_distractor_slot` (REVIEW-01 R1 : un controle qui
permute des zeros ne peut pas echouer, classe E1 ; celui-ci peut : un learner sensible aux noeuds 2K..3K y perd). same_tick=True -> T = 1 ; sinon T = 2
(key au pas 0, q au pas 1, masque [0, 1]). kind="recall" : cible = key. split="control" (2-pas) : key
RE-PRÉSENTÉE au pas de réponse -> une politique qui lit l'entrée n'a pas besoin de l'état porté : c'est le bras
CONTROL de alias_guard_verdict pour `state_reset`. Sous ablation la VÉRITÉ (target) ne change pas ; `meta` porte
ce qui reste OBSERVABLE, c'est ce que l'oracle lit — et ce qui le fait tomber au plancher de Bayes.
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.harness_task import Ablation, DemandDeclaration, Episode  # noqa: E402
from tools.bilinear_composition_probe import _make_seq, _slot  # noqa: E402
from tools.plain_substrate_ceiling import PLAIN_COMPOSITION_CEILING, PLAIN_COMPOSITION_PROVENANCE  # noqa: E402


class CompositionTask:
    version = "1"

    def __init__(self, K=6, same_tick=True, kind="composition", obs_dim=59, name=None):
        if kind not in ("composition", "recall"):
            raise ValueError(f"kind inconnu : {kind!r}")
        if 3 * K > obs_dim:
            raise ValueError(f"3K={3*K} slots ne tiennent pas dans obs_dim={obs_dim}")
        self.K, self.same_tick, self.kind, self.obs_dim = int(K), bool(same_tick), kind, int(obs_dim)
        self.T = 1 if same_tick else 2
        self.name = name or f"{kind}_{'same_tick' if same_tick else 'two_step'}_K{K}"
        floor = 1.0 / self.K
        abls = [Ablation("permute_key", "input", True, apply=self._permute_key, bayes_floor=floor),
                Ablation("permute_query", "input", kind == "composition", apply=self._permute_query,
                         bayes_floor=(floor if kind == "composition" else None)),
                Ablation("inject_distractor_slot", "input", False, apply=self._inject_distractor)]
        if not same_tick:
            abls.append(Ablation("state_reset", "state", True, bayes_floor=floor))
        ceiling = None
        if kind == "composition" and same_tick:
            ceiling = (float(PLAIN_COMPOSITION_CEILING), PLAIN_COMPOSITION_PROVENANCE + " MINORANT, jamais PROUVE.", False)
        self.demand = DemandDeclaration(kind, tuple(abls), incapable_ceiling=ceiling)

    def _build(self, key, q, split, target=None):
        n = key.shape[0]
        seq, mask = _make_seq(key, q, self.kind, self.K, self.obs_dim, n, self.same_tick)
        if split == "control":
            if self.same_tick:
                raise ValueError("split control : seulement en 2-pas")
            seq = [seq[0], seq[1] + _slot(key, self.K, 0, self.obs_dim, n)]   # key re-présentée au pas de réponse
        if target is None:
            target = ((q + key) % self.K) if self.kind == "composition" else key
        return Episode(tuple(np.ascontiguousarray(x, dtype=np.float32) for x in seq),
                       np.asarray(target).astype(np.int64), (None if mask is None else tuple(mask)),
                       {"key": np.asarray(key), "q": np.asarray(q), "split": split})

    def episodes(self, rng, n, split="train"):
        key = rng.randint(0, self.K, size=n)       # ORDRE de _train_eval_one:133-134 : key PUIS q
        q = rng.randint(0, self.K, size=n)
        return self._build(key, q, split)

    def _permute_key(self, ep, rng):
        return self._build(ep.meta["key"][rng.permutation(ep.n)], ep.meta["q"], ep.meta["split"], target=ep.target)

    def _permute_query(self, ep, rng):
        q2 = ep.meta["q"][rng.permutation(ep.n)]
        ep2 = self._build(ep.meta["key"], q2, ep.meta["split"], target=ep.target)
        if self.kind == "composition":
            return ep2
        # kind == "recall" : _make_seq n'encode JAMAIS q (la tache l'ignore par construction), donc
        # permuter q laisserait l'observation bit-identique -- un controle qui ne peut pas echouer ne
        # prouve rien (REVIEW-01 R1, E1). Ecrire le slot q explicitement, au pas de reponse, sur une
        # COPIE : meme convention que la ou "composition" le placerait ; l'oracle recall (= key) et la
        # cible en restent independants.
        seq = [np.array(x, copy=True) for x in ep2.obs_seq]
        seq[-1] = seq[-1] + _slot(q2, self.K, self.K, self.obs_dim, ep.n)
        return Episode(tuple(seq), ep2.target, ep2.mask_seq, ep2.meta)

    def _inject_distractor(self, ep, rng):
        """Controle de SPECIFICITE : ecrit un one-hot aleatoire dans le slot distracteur [2K:3K) du DERNIER pas de
        la copie ablatee. L'observation CHANGE (le contrat (c) l'exige : un controle qui ne change rien ne peut pas
        echouer, E1), l'information utile a la cible ne change pas (oracle 1,0), et un learner dont le readout est
        sensible a ces noeuds d'entree PEUT y perdre — c'est ce qui rend l'issue DECOY informative."""
        seq = [np.array(x, copy=True) for x in ep.obs_seq]
        d = rng.randint(0, self.K, size=ep.n)
        seq[-1][np.arange(ep.n), 2 * self.K + d] = 1.0
        return Episode(tuple(seq), ep.target.copy(), ep.mask_seq, dict(ep.meta, distractor=d))

    def score(self, actions, ep):
        if ep.n == 0:
            raise ValueError("CompositionTask.score : lot vide (porte 14)")
        return (np.asarray(actions).reshape(-1) == np.asarray(ep.target)).astype(np.float32)

    def oracle(self, ep):
        key, q = ep.meta["key"], ep.meta["q"]
        return ((q + key) % self.K) if self.kind == "composition" else np.asarray(key)

    def enumerate_states(self):
        return self.K * self.K

    def regime(self):
        return {"task": self.name, "K": self.K, "T": self.T, "same_tick": self.same_tick, "kind": self.kind,
                "obs_dim": self.obs_dim, "slots": {"key": [0, self.K], "q": [self.K, 2 * self.K],
                                                    "distractor": [2 * self.K, 3 * self.K]}}
