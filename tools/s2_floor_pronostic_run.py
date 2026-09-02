"""S2-FLOOR-PRONOSTIC — le pronostic gravé au câblage E14 (2026-09-02) passe au banc.

Pronostic scellé (docs/preregistrations/S2-FLOOR-PRONOSTIC.json, AVANT ce run) : au régime GRAVÉ de
S2-002 (12 agents, 200 ticks, K=12, seed 2026), la médiane intacte du champion sur `soup` (~22-29
d'après S2-003/S2-012) est SOUS le plancher no-perception mesuré sur SES CLONES (32.0) → l'instrument
doit rendre INDETERMINE_DEGENERATE — et le fait mesuré serait : la politique du champion vaut MOINS
que le hasard à corps égal sur soup. Les 4 autres mondes se lisent au même banc (règle continue :
l'écart intact−plancher se rapporte en absolu pour les 5, jamais de suppression).

    PYTHONPATH=. python -u tools/s2_floor_pronostic_run.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.jobs.run import hold
from tools.preregister import verify

SEED, K, AGENTS, TICKS = 2026, 12, 12, 200          # le régime GRAVÉ de S2-002, rien d'autre


def main():
    rule = verify("S2-FLOOR-PRONOSTIC")
    print("règle SCELLÉE vérifiée |", rule["dv_primaire"][:80], "\n")

    with hold("kuzu", owner="s2-floor-pronostic", ttl_s=1800):
        from tools.s2_demand_ablation import run_ablation_map, PLANCHER_NOPERC
        m = run_ablation_map(seed=SEED, K=K, num_agents=AGENTS, max_ticks=TICKS)

    print(f"=== S2-FLOOR-PRONOSTIC (seed={SEED}, K={K}, {AGENTS} agents, {TICKS} ticks) ===")
    print(f"{'monde':<14} {'intact':>7} {'plancher':>9} {'écart':>7} {'within':>7}  verdict")
    degeneres = []
    for w, r in m.items():
        im, fl = r["intact_median"], PLANCHER_NOPERC[w]
        ecart = im - fl
        if "DEGENERATE" in r["verdict"]:
            degeneres.append(w)
        print(f"{w:<14} {im:>7.2f} {fl:>9.2f} {ecart:>+7.2f} {r['within_ratio']:>7.2f}  {r['verdict']}")

    print(f"\nmondes dégénérés : {len(degeneres)}/5 {degeneres or ''}")
    soup = m["soup"]
    if soup["intact_median"] < PLANCHER_NOPERC["soup"]:
        print("\n→ branche scellée « soup_sous_son_plancher » : PRONOSTIC CONFIRMÉ.")
        print("  soup est ILLISIBLE pour le within à ce régime, ET fait mesuré : la politique du")
        print("  champion vaut MOINS que le hasard à corps égal sur soup → annoter EDR-S2-002")
        print("  (son argument de lisibilité reposait sur l'ancien plancher 9.0 de WARM-010).")
    else:
        print("\n→ branche scellée « soup_au_dessus_de_son_plancher » : PRONOSTIC RÉFUTÉ.")
        print("  La ligne soup de S2-002 se lit normalement ; documenter l'écart avec la médiane")
        print("  historique 22-29 (variabilité inter-seed 2026 vs 3026).")
    return m


if __name__ == "__main__":
    main()
