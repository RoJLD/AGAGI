"""S2-002 — Pont proxy→in-world du demand-marker : bras d'ablation-perception WITHIN-subject sur les
5 mondes réels. Le champion HoF joue INTACT vs perception PERMUTÉE (chaque agent reçoit l'obs d'un
pair -> décorrélée de SA réalité, mais dans-distribution). Si la survie s'effondre, la perception est
causalement porteuse (PERCEPTION_DEMANDED) ; sinon c'est un leurre pour CE champion (PERCEPTION_DECOY).
Contraste avec le between (champion vs réflexe) = rend visible in-world le faux-positif de S2-001.

N'importe PAS en modifiant s2_demand (benchmark pré-enregistré) : réutilise run_condition/WORLDS/
load_champion_genome. Ablation injectée via le seam batch_model_cls.

Usage : python tools/s2_demand_ablation.py   (env: S2ABL_SEED, S2ABL_K, S2ABL_AGENTS, S2ABL_TICKS,
S2ABL_WORLDS="soup,stoneage,...").
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.mamba_agent import MambaBatchModel
from tools.demand_marker import ablation_verdict
from tools.s2_demand import run_condition, WORLDS, load_champion_genome
from src.agents.baseline_models import ReflexBatchModel


def derange_rows(batch_obs, rng=None):
    """Permute les LIGNES de batch_obs entre agents. B>=2 : dérangement (aucun point fixe) -> chaque
    agent voit l'obs d'un PAIR (décorrélée de sa réalité, dans-distribution). B<2 : copie inchangée
    (near-death ; fuite négligeable et CONSERVATRICE). Ne mute jamais l'entrée. RNG = flux global
    np.random par défaut (seedé aux frontières par le Harness -> appariement préservé)."""
    B = batch_obs.shape[0]
    if B < 2:
        return batch_obs.copy()
    draw = (rng or np.random)
    perm = np.arange(B)
    while np.any(perm == np.arange(B)):        # rejet jusqu'à obtenir un dérangement
        perm = draw.permutation(B)
    return batch_obs[perm].copy()


class PerceptionAblatedMamba(MambaBatchModel):
    """Champion à génome INTACT mais perception décorrélée : permute batch_obs avant le forward normal.
    Sous-classe MambaBatchModel -> réutilise entièrement le moteur/poids ; seule l'ENTRÉE change."""

    def forward(self, batch_obs, env_surprise_batch=None):
        return super().forward(derange_rows(batch_obs), env_surprise_batch)


def _median_survival(cond):
    """Survie médiane globale d'une condition run_condition (liste 'survival')."""
    s = cond.get("survival") or []
    return float(np.median(s)) if s else 0.0


def run_ablation_map(worlds=None, seed=2026, K=12, num_agents=20, max_ticks=400):
    """Pour chaque monde : champion INTACT vs champion ABLATÉ (within) + réflexe (between). Renvoie
    {world: {within_ratio, between_ratio, verdict, n}}. n = K ères (unité d'appariement)."""
    worlds = worlds or list(WORLDS)
    champion = load_champion_genome()
    out = {}
    for w in worlds:
        wcls = WORLDS[w]
        intact = run_condition(wcls, None, champion, seed, num_agents=num_agents,
                               max_ticks=max_ticks, n_eras=K)
        ablated = run_condition(wcls, PerceptionAblatedMamba, champion, seed, num_agents=num_agents,
                                max_ticks=max_ticks, n_eras=K)
        reflex = run_condition(wcls, ReflexBatchModel, None, seed, num_agents=num_agents,
                               max_ticks=max_ticks, n_eras=K)
        # appariement par ère (même seed_at(seed, i)) : era_survival est la médiane par ère
        wv = ablation_verdict(intact["era_survival"], ablated["era_survival"])
        between_ratio = _median_survival(intact) / max(_median_survival(reflex), 1e-9)
        verdict = wv["verdict"].replace("X_", "PERCEPTION_")
        out[w] = {"within_ratio": wv["ratio"], "between_ratio": between_ratio,
                  "verdict": verdict, "n": wv["n"]}
    return out


def main():
    seed = int(os.environ.get("S2ABL_SEED", "2026"))
    K = int(os.environ.get("S2ABL_K", "12"))
    num_agents = int(os.environ.get("S2ABL_AGENTS", "20"))
    max_ticks = int(os.environ.get("S2ABL_TICKS", "400"))
    worlds_env = os.environ.get("S2ABL_WORLDS")
    worlds = worlds_env.split(",") if worlds_env else None

    m = run_ablation_map(worlds, seed=seed, K=K, num_agents=num_agents, max_ticks=max_ticks)
    print(f"\n=== S2-002 — ablation-perception within-subject in-world (seed={seed}, K={K}) ===")
    print(f"{'monde':12s} {'within':>8s} {'between':>8s}  verdict")
    for w, r in m.items():
        print(f"{w:12s} {r['within_ratio']:8.2f} {r['between_ratio']:8.2f}  {r['verdict']} (n={r['n']})")
    # lecture : within>>1 = perception causalement porteuse ; within~1 & between>>1 = between
    # FAUX-POSITIVE (survivant existe mais perception = leurre) -> le finding S2-001 rendu in-world.
    disagree = [w for w, r in m.items() if r["between_ratio"] >= 1.5 and r["within_ratio"] <= 1.3]
    print(f"\nDésaccords between/within (between crie demande, within dit leurre) : {disagree or 'aucun'}")
    print("-> Rédiger EDR-S2-002 à partir de cette carte.")
    return m


if __name__ == "__main__":
    main()
