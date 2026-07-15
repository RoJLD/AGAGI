"""S2-003 — Sonde ladder open-loop : localise la compétence du champion au-dessus de S2-002.
S2-002 tranche "la perception est-elle causalement porteuse ?" via UNE ablation (permutation
inter-agents). Cette sonde ajoute une ÉCHELLE de sévérité within-subject : permuted (dans-
distribution, décorrélée) -> noise (hors-distribution, échelle appariée) -> zero (hors-
distribution, dégénérée). Si les 3 barreaux sont plats (decoy), le champion est OPEN_LOOP
(il ignore l'entrée, quelle que soit sa forme) ; si un barreau s'effondre, il est
INPUT_SENSITIVE (la perception porte, au moins sous une forme d'ablation).

N'importe PAS en modifiant s2_demand/s2_demand_ablation/demand_marker (déjà livrés, réutilisés
tels quels via le seam batch_model_cls). Ajoute deux nouvelles classes d'ablation (bruit gaussien
à échelle appariée, obs zéro) et une échelle world-agnostic au-dessus.

Usage : python tools/s2_openloop_probe.py   (env: S2OL_SEED, S2OL_K, S2OL_AGENTS, S2OL_TICKS,
S2OL_WORLDS="soup,stoneage,...").
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
from tools.s2_demand_ablation import PerceptionAblatedMamba


class NoiseObsMamba(MambaBatchModel):
    """Champion à génome INTACT mais perception remplacée par du bruit gaussien à échelle
    APPARIÉE (même moyenne/écart-type que l'obs réelle) : hors-distribution mais pas dégénérée.
    Tire du flux GLOBAL np.random (pairing Harness) ; ne mute jamais batch_obs."""

    def forward(self, batch_obs, env_surprise_batch=None):
        scale = float(batch_obs.std()) + 1e-9
        noise = (np.random.randn(*batch_obs.shape) * scale + float(batch_obs.mean())).astype(batch_obs.dtype)
        return super().forward(noise, env_surprise_batch)


class ZeroObsMamba(MambaBatchModel):
    """Champion à génome INTACT mais perception ZÉRO (obs dégénérée) : barreau le plus sévère
    de la ladder. Ne mute jamais batch_obs."""

    def forward(self, batch_obs, env_surprise_batch=None):
        return super().forward(np.zeros_like(batch_obs), env_surprise_batch)


def run_openloop_ladder(worlds=None, seed=2026, K=12, num_agents=12, max_ticks=200):
    """Pour chaque monde : champion INTACT vs 3 barreaux d'ablation croissante (permuted -> noise
    -> zero), toutes within-subject, appariées par ère (n_eras=K). Renvoie
    {world: {intact_med, permuted, noise, zero, verdict}} où chaque barreau porte le dict complet
    ablation_verdict (ratio/n/collapse/decoy/verdict) et verdict = lecture world-level :
    OPEN_LOOP (les 3 barreaux sont des leurres) / INPUT_SENSITIVE (au moins un s'effondre) / MIXED."""
    worlds = worlds if worlds is not None else ["soup", "stoneage", "famine"]
    champion = load_champion_genome()
    out = {}
    for w in worlds:
        wcls = WORLDS[w]
        intact = run_condition(wcls, None, champion, seed, num_agents=num_agents,
                               max_ticks=max_ticks, n_eras=K)
        permuted = run_condition(wcls, PerceptionAblatedMamba, champion, seed, num_agents=num_agents,
                                 max_ticks=max_ticks, n_eras=K)
        noise = run_condition(wcls, NoiseObsMamba, champion, seed, num_agents=num_agents,
                              max_ticks=max_ticks, n_eras=K)
        zero = run_condition(wcls, ZeroObsMamba, champion, seed, num_agents=num_agents,
                             max_ticks=max_ticks, n_eras=K)

        permuted_v = ablation_verdict(intact["era_survival"], permuted["era_survival"])
        noise_v = ablation_verdict(intact["era_survival"], noise["era_survival"])
        zero_v = ablation_verdict(intact["era_survival"], zero["era_survival"])
        rungs = (permuted_v, noise_v, zero_v)

        if all(r["decoy"] for r in rungs):
            verdict = "OPEN_LOOP"
        elif any(r["collapse"] for r in rungs):
            verdict = "INPUT_SENSITIVE"
        else:
            verdict = "MIXED"

        era = intact.get("era_survival") or []
        out[w] = {
            "intact_med": float(np.median(era)) if era else 0.0,
            "permuted": permuted_v,
            "noise": noise_v,
            "zero": zero_v,
            "verdict": verdict,
        }
    return out


def main():
    seed = int(os.environ.get("S2OL_SEED", "2026"))
    K = int(os.environ.get("S2OL_K", "12"))
    num_agents = int(os.environ.get("S2OL_AGENTS", "12"))
    max_ticks = int(os.environ.get("S2OL_TICKS", "200"))
    worlds_env = os.environ.get("S2OL_WORLDS")
    worlds = worlds_env.split(",") if worlds_env else None

    m = run_openloop_ladder(worlds, seed=seed, K=K, num_agents=num_agents, max_ticks=max_ticks)
    print(f"\n=== S2-003 — ladder open-loop within-subject (seed={seed}, K={K}) ===")
    print(f"{'monde':12s} {'intact_med':>10s} {'permuted':>9s} {'noise':>9s} {'zero':>9s}  verdict")
    for w, r in m.items():
        print(f"{w:12s} {r['intact_med']:10.1f} {r['permuted']['ratio']:9.2f} "
              f"{r['noise']['ratio']:9.2f} {r['zero']['ratio']:9.2f}  {r['verdict']}")
    open_loop = [w for w, r in m.items() if r["verdict"] == "OPEN_LOOP"]
    input_sensitive = [w for w, r in m.items() if r["verdict"] == "INPUT_SENSITIVE"]
    print(f"\nOPEN_LOOP (champion ignore l'entrée, tous barreaux leurres) : {open_loop or 'aucun'}")
    print(f"INPUT_SENSITIVE (au moins un barreau s'effondre) : {input_sensitive or 'aucun'}")
    print("-> Rédiger EDR-S2-003 à partir de cette échelle.")
    return m


if __name__ == "__main__":
    main()
