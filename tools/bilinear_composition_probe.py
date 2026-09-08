"""Calibration : le terme BILINÉAIRE du substrat débloque-t-il la composition (q+key)%K ?

Étalon connu (finding LANG-MEMORY, `tools/language_memory_demand_probe.py`) : le substrat PLAIN est NUL
sur (q+key)%K (médianes 0.15-0.33 sur un large balayage d'hyperparamètres/méthodes de crédit, floor=1/K).
On entraîne la MÊME tâche avec `TorchPopulationModel.BILINEAR` off puis on, et on compare : `unlocked`
ssi plain reste nul (<= 1/K+0.15) ET bilinéaire apprend (> 1/K+0.15). Contrôle NO-OP : task='recall'
(pur-rappel, one-shot key->key, que le plain apprend déjà) doit ENCORE marcher en bilinéaire (pas de
régression du canal que le substrat maîtrisait avant l'ajout du terme). Le nom `run_*probe` trippe le
cliquet -> calibré dans `tests/sandbox/test_instrument_calibration.py`. Pur torch CPU, aucun bail.

⚠️ Vérifié contre le code réel (`src/agents/backend_torch.py`, Task 1 `7747b1e`) :
- `TorchPopulationModel.BILINEAR`/`BILINEAR_RANK` sont des flags de CLASSE lus au constructeur
  (`make_population` doit être appelé APRÈS les avoir positionnés) ; `agent.U`/`agent.V`/`agent.W_bl`
  ne sont créés (non-None) QUE si `BILINEAR=True` au moment du `__init__`.
- `forward(x) -> (logits, 0)` : le 2e élément est un PLACEHOLDER entier, PAS l'état — `forward` met déjà
  à jour `self.H` EN INTERNE. Ne PAS réassigner `agent.H` depuis ce retour.
- `learn_episode(obs_seq, actions_seq, rewards, gate_last_only=True)` rejoue depuis un H LOCAL tronqué
  (indépendant de `agent.H` externe) et backprop via `self._step`, qui inclut le terme bilinéaire quand
  `BILINEAR=True` et `self.W_bl is not None` — le gradient REMONTE jusqu'à U/V/W_bl (vérifié : leurs
  valeurs changent après un `learn_episode`, cf. smoke/calibration).
- REINFORCE crédite le GUESS ÉCHANTILLONNÉ (pas la cible), motif déjà calibré dans les sondes sœurs
  (`language_memory_demand_probe.py`, `memory_perception_demand_probe.py`) — l'avantage centré
  `(guess==tgt)-mean` pousse la probabilité du guess RÉEL vers le haut/bas selon qu'il a marché.

Tâche 3 (diagnostic des 2 confonds identifiés par la revue adversariale du nul de la Tâche 2) — deux
leviers OPTIONNELS, défauts = comportement Tâche 2 INCHANGÉ :
- `same_tick=True` : key ET q dans la MÊME observation (un seul pas), au lieu de encode(key) puis
  usage(query) sur 2 pas. Supprime la RÉTENTION (le bilinéaire n'a plus besoin de porter key à travers
  un tick de récurrence pour le multiplier avec q — les deux sont présents simultanément).
- `credit_mode="supervised"` : `agent.imitate_episode_bptt` (cross-entropy supervisée, BPTT NON tronqué
  entre pas) au lieu de `agent.learn_episode` (REINFORCE, qui détache H à CHAQUE pas — `H=H.detach()`
  dans `_step` de `learn_episode` — donc sévère le gradient à la frontière encode->usage). Supprime le
  confond de CRÉDIT (variance REINFORCE + coupure de gradient), indépendamment de `same_tick`.
Le test décisif combine `same_tick=True, credit_mode="supervised"` : lève les DEUX confonds à la fois,
isolant la question purement REPRÉSENTATIONNELLE (le bilinéaire peut-il représenter le produit ?).

Usage : python tools/bilinear_composition_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.experiment_preflight import assert_bar_separates_the_incapable
from tools.plain_substrate_ceiling import PLAIN_COMPOSITION_CEILING, PLAIN_COMPOSITION_PROVENANCE


def _slot(idx, K, offset, I, n):
    m = np.zeros((n, I), dtype=np.float32)
    m[np.arange(n), offset + (idx % K)] = 1.0
    return m


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sample(preds, K, rng, n):
    p = _softmax(np.asarray(preds)[:, :K])
    return np.array([rng.choice(K, p=pi) for pi in p])


def _make_seq(key, q, task, K, I, n, same_tick):
    """Construit obs_seq (+ mask_seq) pour un batch (key, q). `same_tick=False` (défaut) : 2 pas,
    encode(key) puis usage(query) — RETENTION requise (le crédit doit porter key du pas 0 au pas 1).
    `same_tick=True` : 1 SEUL pas, key ET q dans la MÊME observation (slots disjoints [0:K]/[K:2K]) —
    supprime la RETENTION (le bilinéaire ((H·U)⊙(H·V))·W_bl peut multiplier deux entrées PRÉSENTES au
    même tick, sans devoir porter key à travers un tick de récurrence). mask_seq (pour le crédit
    supervisé) marque le pas RÉPONSE (1.0) vs le pas encode (0.0, non supervisé) ; None si un seul pas."""
    if same_tick:
        obs = np.zeros((n, I), dtype=np.float32)
        obs[np.arange(n), key % K] = 1.0
        if task == "composition":
            obs[np.arange(n), K + (q % K)] = 1.0
        return [obs], None
    enc = _slot(key, K, 0, I, n)
    use = _slot(q, K, K, I, n) if task == "composition" else np.zeros((n, I), np.float32)
    mask_seq = [np.zeros(n, dtype=np.float32), np.ones(n, dtype=np.float32)]
    return [enc, use], mask_seq


def _train_eval_one(seed, bilinear, task, episodes, n_agents, K, lr, rank, eval_batches=40,
                     same_tick=False, credit_mode="reinforce"):
    """Entraîne la tâche (composition (q+key)%K OU recall=key) avec BILINEAR on/off ; renvoie l'accuracy éval.

    `same_tick` (défaut False = comportement Tâche 2 inchangé) : lève le confond de RÉTENTION (cf.
    `_make_seq`). `credit_mode` (défaut "reinforce" = comportement Tâche 2 inchangé, `agent.learn_episode`,
    H détaché à CHAQUE pas -> le crédit ne traverse PAS la frontière encode->usage) | "supervised" (BPTT
    via `agent.imitate_episode_bptt` — cross-entropy sur la cible au pas RÉPONSE, gradient NON tronqué
    entre pas -> lève le confond de CRÉDIT). Les deux défauts préservent EXACTEMENT le chemin de calibration
    de la Tâche 2 (mêmes seeds -> mêmes résultats)."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
             TorchPopulationModel.BILINEAR, TorchPopulationModel.BILINEAR_RANK)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    TorchPopulationModel.BILINEAR = bool(bilinear)
    TorchPopulationModel.BILINEAR_RANK = int(rank)
    try:
        agent = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I = agent.I
        rng = np.random.RandomState(seed + 1)
        params = [agent.W]
        if bilinear:
            params += [agent.U, agent.V, agent.W_bl]           # inclure les params bilinéaires
        agent.opt = torch.optim.Adam(params, lr=lr)

        def _target(key, q):
            return (q + key) % K if task == "composition" else key   # recall = key seul (no-op)

        for _ in range(episodes):
            key = rng.randint(0, K, size=n_agents)
            q = rng.randint(0, K, size=n_agents)
            seq, mask_seq = _make_seq(key, q, task, K, I, n_agents, same_tick)
            tgt = _target(key, q)

            if credit_mode == "supervised":
                if same_tick:
                    target_moves_seq = [tgt]
                else:
                    target_moves_seq = [np.zeros(n_agents, dtype=np.int64), tgt]
                agent.imitate_episode_bptt(seq, target_moves_seq, mask_seq=mask_seq)
            else:
                agent.H = torch.zeros((n_agents, agent.N))
                logits = None
                for x in seq:
                    logits, _ = agent.forward(x)
                guess = _sample(logits, K, rng, n_agents)
                adv = (guess == tgt).astype(np.float32)
                adv = adv - adv.mean()
                if same_tick:
                    acts = [[{"move": int(g)} for g in guess]]
                else:
                    acts = [[{"move": 0} for _ in range(n_agents)], [{"move": int(g)} for g in guess]]
                agent.learn_episode(seq, acts, adv, gate_last_only=True)

        hits = []
        for _ in range(eval_batches):
            key = rng.randint(0, K, size=n_agents)
            q = rng.randint(0, K, size=n_agents)
            seq, _ = _make_seq(key, q, task, K, I, n_agents, same_tick)
            agent.H = torch.zeros((n_agents, agent.N))
            logits = None
            for x in seq:
                logits, _ = agent.forward(x)
            g = np.asarray(logits)[:, :K].argmax(axis=1)
            hits.append((g == _target(key, q)).astype(np.float32))
        return float(np.mean(np.concatenate(hits)))
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
         TorchPopulationModel.BILINEAR, TorchPopulationModel.BILINEAR_RANK) = saved


def _resolve_ceiling(incapable_ceiling, ceiling_provenance, task, same_tick, K,
                     ceiling_is_proven=False):
    """Plafond du bras PROUVABLEMENT INCAPABLE (ici : le substrat plain), et d'où il vient.

    ⚠️ P2.15 — c'est le cœur de la dette. `"auto"` ne résout QUE le régime où la forme close est EXACTE :
    `task="composition"` ET `same_tick=True`, un seul `_step` depuis `H_in=0`, donc
    `logit_j = σ(W[j,j])·tanh(W[key,j] + W[K+q,j])` — un score SÉPARABLE en key et q dont le plafond est
    mesuré par `tools/plain_substrate_ceiling.py` avec son contrôle positif apparié. Hors de ce régime
    (2 pas : l'état porte key, la forme n'est plus close ; `task="recall"` : la tâche est séparable donc
    le plain n'est pas incapable), AUCUN plafond n'est établi et on rend `None` : la sonde REFUSE alors
    de rendre `unlocked` plutôt que de deviner. Ne pas proxifier ce qu'on ne sait pas mesurer."""
    if incapable_ceiling == "auto":
        # ⛔ 2026-09-08 — `"auto"` ne résout PLUS rien, et c'est la conséquence logique de la
        # RÉFUTATION. Ce mode rendait `PLAIN_COMPOSITION_CEILING` en le nommant « plafond de
        # l'INCAPABLE ». Or le plain n'est PAS incapable : sa forme close compose PARFAITEMENT
        # (9/9 à K=3, 16/16 à K=4, vérifiés in situ — `results/plain_ceiling_witness_K{3,4}.json`).
        # Un « plafond de l'incapable » pour un bras qui atteint le maximum n'existe pas. La sonde
        # refuse donc de certifier, sauf si l'appelant DÉCLARE un plafond et le prouve.
        return None, None, False
    if incapable_ceiling is None:
        return None, None, False
    return float(incapable_ceiling), ceiling_provenance, bool(ceiling_is_proven)


def run_bilinear_composition_probe(seeds, episodes=1500, n_agents=16, K=6, lr=0.02, rank=16, task="composition",
                                    same_tick=False, credit_mode="reinforce",
                                    incapable_ceiling="auto", ceiling_provenance=None, bar=None,
                                    ceiling_is_proven=False):
    """Compare le substrat PLAIN vs BILINÉAIRE sur la tâche. `same_tick`/`credit_mode` (Tâche 3, cf.
    `_train_eval_one`) : les deux DÉFAUTS reproduisent bit-pour-bit le chemin de calibration de la Tâche 2.

    ⚠️ **`unlocked` N'EST PLUS RENDU CONTRE `1/K + 0.15`** (dette P2.15, corrigée le 2026-09-07). Cette
    barre est SOUS le plafond du substrat que le premier terme du critère déclare nul : un plain qui la
    franchit ne prouvait donc rien, et `unlocked` mélangeait une affirmation de CAPACITÉ avec une
    affirmation de BUDGET. La barre est désormais dérivée du PLAFOND DE L'INCAPABLE — invariant au pas
    ET au budget, là où un seuil absolu ne l'est ni l'un ni l'autre.
      * plafond résolu (cf. `_resolve_ceiling`) -> `bar = plafond + marge`, validé EN TÊTE de fonction
        par `assert_bar_separates_the_incapable` (refus INSTANTANÉ, zéro simulation), `bar_status
        = "SEPARATES"`, et `unlocked` a le sens qu'il annonce : le bilinéaire fait ce que le plain ne
        PEUT pas faire, pas seulement ce qu'il n'a pas eu le budget de faire ;
      * aucun plafond établi -> `unlocked=None` et `bar_status="UNVALIDATED"`. La sonde MESURE toujours
        (les médianes et le per-seed restent rendus, et c'est là que vit la séparation observable) mais
        elle ne CERTIFIE pas. Un verdict deviné vaut moins qu'un verdict refusé.

    `marge` : erreur-type d'échantillonnage à `n_eval = 40 × n_agents`, même convention que
    `assert_bar_is_reachable`. ⚠️ Le plafond est un MINORANT (le meilleur trouvé par recherche, contrôle
    positif apparié à 1.000) : franchir la barre établit « au-dessus de ce que l'incapable atteint de
    façon démontrée », pas « au-dessus de tout ce que l'incapable pourrait atteindre »."""
    ceil, prov, prouve = _resolve_ceiling(incapable_ceiling, ceiling_provenance, task, same_tick, K,
                                          ceiling_is_proven=ceiling_is_proven)
    if bar is None:
        bar = (1.0 / K + 0.15) if ceil is None else ceil + float(np.sqrt(
            max(ceil * (1.0 - ceil), 0.0) / max(40 * n_agents, 1)))
    bar = float(bar)
    # GARDE EN TÊTE, avant toute construction de population : un refus doit être INSTANTANÉ, sinon on
    # paie les seeds avant d'apprendre que le verdict ne voulait rien dire (technique du dépôt, mesurée).
    if ceil is not None:
        assert_bar_separates_the_incapable(bar, ceil, prov, label="barre `unlocked` de la composition")

    plain, bil = [], []
    for s in seeds:
        plain.append(_train_eval_one(s, False, task, episodes, n_agents, K, lr, rank,
                                      same_tick=same_tick, credit_mode=credit_mode))
        bil.append(_train_eval_one(s, True, task, episodes, n_agents, K, lr, rank,
                                    same_tick=same_tick, credit_mode=credit_mode))
    pm, bm = float(np.median(plain)), float(np.median(bil))
    # ⚠️ Un MINORANT ne peut pas certifier une séparation — il ne peut que MONTER. Mesuré le 2026-09-07 :
    # trois recherches indépendantes sur la MÊME forme close ont rendu 29/36, 34/36 et 36/36, par ordre
    # d'effort croissant. Un « plafond » qui bouge avec l'effort n'est pas un plafond.
    unlocked = ((pm <= bar) and (bm > bar)) if prouve else None
    return {"plain_median": pm, "bilinear_median": bm, "unlocked": unlocked,
            "bar": bar, "bar_status": ("SEPARATES_PROVEN" if prouve else
                                       ("CEILING_IS_MINORANT" if ceil is not None else "UNVALIDATED")),
            "incapable_ceiling": ceil, "ceiling_is_proven": bool(prouve),
            "per_seed": {"plain": plain, "bilinear": bil}, "task": task, "n": len(seeds),
            "same_tick": same_tick, "credit_mode": credit_mode}


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("BL_SEEDS", "12"))))
    r = run_bilinear_composition_probe(seeds, episodes=int(os.environ.get("BL_EPISODES", "1500")))
    print(json.dumps({k: v for k, v in r.items() if k != "per_seed"}, ensure_ascii=False, indent=2))
