"""
tools/robust_eval.py — Validation biosphère d'EDR 078 : l'évaluation ROBUSTE lève-t-elle le plateau ? (EDR 079)

EDR 078 (banc) : le plateau de compétence est du bruit de fitness ; nettoyer le signal -> ×3. On le
valide ici sur la VRAIE biosphère : la sélection HoF d'EDR 076 évalue un candidat sur 1 ère (bruitée).
On compare au régime ROBUSTE : le top candidat de chaque ère est ré-évalué sur K ères et MOYENNÉ avant
de concourir pour le cliquet best-ever. Métrique finale : compétence VRAIE du champion (survie moyenne
sur n ères propres). Robuste > bruité valide le levier sur le vivant.

Usage : HEADLESS=1 python -m tools.robust_eval
"""
import time

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.persistence import load_hall_of_fame
from src.agents.mamba_agent import MambaAgent
from src.graph_rag.async_logger import logger as async_logger
from tools.evolve_competence import run_era, _reproduce
from tools.progress import Progress


def _load_champions():
    champs = []
    try:
        _, hof = load_hall_of_fame()
        for e in hof:
            if isinstance(e, tuple):
                champs.append(e[1])
            elif hasattr(e, "genome"):
                champs.append(e.genome)
        champs = [g for g in champs if g is not None][:5]
    except Exception:
        champs = []
    return champs or [MambaAgent().genome for _ in range(5)]


def _robust_score(cfg, g, K, num_agents):
    """Compétence robuste d'un génome : moyenne du life_score sur K ères de clones (de-bruite)."""
    vals = []
    for _ in range(K):
        _, m = run_era(cfg, [g] * num_agents)
        vals.append(m["score"])
    return float(np.mean(vals))


def _true_competence(cfg, g, n, num_agents):
    """Compétence VRAIE (mesure propre) : survie moyenne sur n ères indépendantes."""
    return float(np.mean([run_era(cfg, [g] * num_agents)[1]["ticks"] for _ in range(n)]))


def evolve(cfg, robust_K, eras, num_agents, mc, prog):
    champions = _load_champions()
    best_ever = [(0.0, g) for g in champions]
    for _ in range(eras):
        genomes = _reproduce([g for _s, g in best_ever], num_agents, mc)
        scored, _ = run_era(cfg, genomes)
        if scored:
            if robust_K > 1:                              # ROBUSTE : ré-évaluer le top candidat avant le cliquet
                top_g = scored[0][1]
                scored[0] = (_robust_score(cfg, top_g, robust_K, num_agents), top_g)
            best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
        prog.update()
    return best_ever[0][1]


def main(eras=15, num_agents=30, robust_K=3, n_final=15):
    async_logger.start()
    for _ in range(50):
        if async_logger.get_db():
            break
        time.sleep(0.1)
    cfg = WorldConfig()
    mc = MutationConfig(weight_init_std=2.0)
    print(f"VALIDATION BIOSPHERE d'EDR 078 : selection BRUITEE (K=1) vs ROBUSTE (K={robust_K}). {eras} eres.")

    pn = Progress(eras, label="BRUITEE (K=1)")
    champ_noisy = evolve(cfg, 1, eras, num_agents, mc, pn)
    pr = Progress(eras, label=f"ROBUSTE (K={robust_K})")
    champ_robust = evolve(cfg, robust_K, eras, num_agents, mc, pr)

    pf = Progress(2, label="mesure competence vraie")
    tn = _true_competence(cfg, champ_noisy, n_final, num_agents); pf.update()
    tr = _true_competence(cfg, champ_robust, n_final, num_agents); pf.update()

    print(f"\n=== COMPETENCE VRAIE du champion (survie moyenne / {n_final} eres propres) ===")
    print(f"  selection BRUITEE  (K=1)        : {tn:5.1f} ticks")
    print(f"  selection ROBUSTE  (K={robust_K})        : {tr:5.1f} ticks")
    print("\n=== VERDICT ===")
    if tr > tn * 1.15:
        print(f"  -> l'evaluation ROBUSTE leve le plateau : {tn:.0f} -> {tr:.0f} ticks (+{(tr/tn-1)*100:.0f}%).")
        print(f"     EDR 078 valide sur le VIVANT : de-bruiter la fitness forge une vraie competence.")
    elif tr > tn:
        print(f"  -> robuste > bruitee ({tr:.0f} vs {tn:.0f}) ; effet present, a amplifier (K plus grand).")
    else:
        print(f"  -> pas d'effet net sur le vivant ({tr:.0f} vs {tn:.0f}) : la fitness de GROUPE domine le bruit.")
    async_logger.stop()


if __name__ == "__main__":
    main()
