"""P4.13 (a) (ADR-005 item 3, 2026-09-16) — la distribution de la « constante de temps » δ_j = σ(clip(W_jj, ±10)) sur
chaque génome des Hall of Fame PRÉSENTS (principal, famine, famine_s43), à 0 simulation.

Pourquoi : l'« hormone » d'ADR-005 est un facteur sur δ — avant de poser un levier sur une grandeur, on publie sa
distribution telle qu'elle est (E8 : mesurée, jamais raisonnée). Un HoF absent n'est pas une mesure ; un HoF présent
mais illisible est RAPPORTÉ dans `illisibles`, jamais compté 0 ; un génome à diagonale non finie est compté
(`n_non_fini`), jamais avalé. Résultats : `results/delta_distribution_hof.json` (tampon de provenance).
Usage : python tools/delta_distribution_hof.py
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.agents.mamba_agent import DELTA_GELE, DELTA_INSTANTANE, delta_distribution
from tools.preregister import stamp
from src.paths import results_file   # noqa: E402  (porte 12)

_HOF_VARIANTES = (None, "famine", "famine_s43")


def scan_hof_deltas(variantes=_HOF_VARIANTES):
    """Une entrée par génome de chaque HoF PRÉSENT : `hall_of_fame.pkl#<rang>` -> distribution de δ (+ `score` si
    l'entrée en porte un). Rend (genomes, illisibles, variantes_presentes)."""
    from src.paths import hall_of_fame
    from src.seed_ai.persistence import load_hall_of_fame
    import src.seed_ai.persistence as P
    genomes, illisibles, presentes = {}, [], []
    for v in variantes:
        p = str(hall_of_fame(v))
        if not os.path.exists(p):
            continue
        nom = os.path.basename(p)
        presentes.append(nom)
        ancien = P.HALL_OF_FAME_PATH
        try:
            P.HALL_OF_FAME_PATH = p          # module-level, lu par load_hall_of_fame
            _version, entries = load_hall_of_fame()
        except Exception as exc:                        # noqa: BLE001 — rapporté, jamais compté comme 0
            illisibles.append(f"{nom} ({type(exc).__name__})")
            continue
        finally:
            P.HALL_OF_FAME_PATH = ancien
        for i, e in enumerate(entries):
            d = delta_distribution(e.genome)
            sc = getattr(e, "score", None)                   # AgentSnapshot : genome, score, state_path, stats
            d["score"] = float(sc) if isinstance(sc, (int, float, np.floating)) else None
            genomes[f"{nom}#{i}"] = d
    return genomes, illisibles, presentes


def agrege(genomes):
    """Médiane, sur les génomes à statistiques PRÉSENTES, de chaque statistique ; `n_genomes` et `n_sans_stat`
    publiés à côté. Aucun génome lisible -> None partout, pas 0."""
    avec = [g for g in genomes.values() if g.get("mediane") is not None]
    out = {"n_genomes": len(genomes), "n_sans_stat": len(genomes) - len(avec),
           "n_non_fini_total": int(sum(g["n_non_fini"] for g in genomes.values()))}
    for k in ("min", "mediane", "max", "part_gele", "part_instantane", "part_diag_nulle"):
        out[f"{k}_mediane_des_genomes"] = float(np.median([g[k] for g in avec])) if avec else None
    return out


def main(argv=None):
    out_path = str(results_file("delta_distribution_hof.json"))
    genomes, illisibles, presentes = scan_hof_deltas()
    db = {"_regime": {"variantes_presentes": presentes, "bornes": {"gele": DELTA_GELE, "instantane": DELTA_INSTANTANE},
                      "clip": 10.0, "formule": "delta_j = sigmoid(clip(W_jj, -10, 10))"},
          "genomes": genomes, "illisibles": illisibles, "_agrege": agrege(genomes)}
    json.dump(stamp(db), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps({"presentes": presentes, "illisibles": illisibles, **db["_agrege"]}, indent=1, ensure_ascii=False))
    print("->", out_path)
    return db


if __name__ == "__main__":
    main()
