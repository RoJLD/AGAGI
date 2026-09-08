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

    # ---- GARDE E23 (porte 11) : la FAMILLE de contrôles est DÉCLARÉE, AVANT toute mesure ---------
    # COMBIEN de cellules ? CINQ — le garde-fou de dégénérescence de `ablation_verdict` (plancher
    # `PLANCHER_NOPERC[w]` / plafond `max_ticks`) est appliqué une fois PAR MONDE, et le runner le
    # relit ligne à ligne (`if "DEGENERATE" in r["verdict"]`). C'est la seule forme de la famille ici :
    # 5 mondes × 1 contrôle. Chaque cellule porte sur la médiane des K=12 ères appariées de SON monde.
    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.s2_demand_ablation import WORLDS

    famille = assert_control_family(
        cells=len(WORLDS), alpha_family=0.05, method="none",
        reason="Multiplicité SANS OBJET ici, et la raison est dans la règle scellée elle-même : les "
               "5 cellules sont RAPPORTÉES (« le nombre de mondes dégénérés (0-5) se rapporte tel "
               "quel », lecture CONTINUE, jamais de suppression de ligne) et ne sont JAMAIS agrégées "
               "en un « au moins une cellule hors bande » — c'est précisément l'agrégation qui "
               "fabriquait 0,216 de fausse alarme sur EVO-011. La branche discriminante scellée "
               "porte sur UN monde NOMMÉ D'AVANCE (soup vs son plancher 32.0), donc sur une seule "
               "cellule pré-désignée : la multiplicité ne peut pas la gonfler. Et aucune de ces "
               "comparaisons n'est un test à p-value (médiane vs constante mesurée hors run) : il "
               "n'y a pas d'alpha à corriger, une Bonferroni serait DÉCORATIVE.")
    design = declare_design(
        question=rule["question"],
        replication_unit=rule["unite_de_replication"],
        n_independent=K,
        links={"champion INTACT -> survie médiane par monde (K ères appariées)": "measured",
               "clones du champion sans perception -> plancher PLANCHER_NOPERC": "measured",
               "intact vs SON plancher -> verdict de dégénérescence par monde": "measured"},
        control_family=famille,
        cost_estimate=rule.get("cout"))
    print(f"[design] unité = {design['replication_unit']} | famille = {famille['cells']} cellules "
          f"(1 par monde), method={famille['method']} — raison publiée dans le design\n")

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
