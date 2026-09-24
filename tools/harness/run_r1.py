"""
tools/harness/run_r1.py — Exécute les trois cellules de HARNESS-R1 (n = 12) sous une règle SCELLÉE
(`--rule`, défaut `HARNESS-R1-ter`), via run_harness_cell, et imprime les verdicts. Usage :

    PYTHONIOENCODING=utf-8 python -m tools.harness.run_r1 [--rule NOM] [A|Aprime|B ...]

sans argument de cellule -> les trois cellules, dans l'ordre A, Aprime, B.

Chaîne de règles (chacune SUPERSEDED par la suivante, aucune n'est réécrite -- `tools/preregister.py`) :
  * `HARNESS-R1` — R1, revue tâche 10 : unités non comparables, référence A' non mesurée, plancher de
    bruit absent, issue négative non nommée, famille de contrôles sous-déclarée (E2/E8/E23).
  * `HARNESS-R1-bis` — corrige R1 ; PREMIER run réel (2026-09-22, 13 processus python vus par
    `tasklist` au lancement) : cellule A INCONCLUSIVE_N (CostGuard par seed = 15x l'unité scellée,
    abandons sous 9 processus python DU PROJET concurrents -- classe E12, cf. `tools/harness/seal_r1.py
    ::RAISON_TER`), Aprime LR_ARTIFACT, B INCONCLUSIVE_N (1 seed abandonné) -- résultats CONSERVÉS sous
    `results/harness_r1_{A,Aprime,B}_0_bis_E12.json`, jamais gravés dans le record HARNESS-R1.
  * `HARNESS-R1-ter` — MÊME règle que -bis (relue depuis son sceau, jamais du smoke), budget_s de
    chaque cellule x3 (CostGuard par seed = 45x l'unité scellée, marge de charge EXPLICITE ; le budget
    est une GARDE DE COÛT, jamais une grandeur LUE par `harness_verdict_lecture` -- la relever ne
    change AUCUNE lecture). `predictions_chiffrees_AVANT_le_run` INCHANGÉES (scellées dans -bis avant
    tout run, re-portées telles quelles).

Coût : `rule.cellules.<clé>.budget_s` EST DÉJÀ la projection exacte de
`project_cost(unit_s, n_units=60, safety=3.0)` (cf. `rule.cout`) -- passer l'unité SCELLÉE
(`rule.smoke.unit_s`) EN MÊME TEMPS que ce budget ne fait donc PAS doubler la marge : c'est le
`CostGuard` PAR SEED (`budget_s / 12`) qui porte le reste de la marge. Le temps mur imprimé est un
MAJORANT mesuré SOUS LA CHARGE observée juste AVANT CHAQUE CELLULE (E12, `CLAUDE.md` §Protocole
expérimental point 4 -- la charge peut changer d'une cellule à l'autre, jamais une constante du
dispositif) : `tools.jobs.doctor.project_processes()` (processus python DU PROJET, hors moi-même et mes
ancêtres), pas un compte aveugle de tout `python.exe` système.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.experiment_preflight import assert_control_family, declare_design  # noqa: E402
from tools.harness.cell import run_harness_cell  # noqa: E402
from tools.harness.learners.connectome import ConnectomeLearner  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402
from tools.jobs.doctor import project_processes  # noqa: E402
from tools.preregister import provenance, verify  # noqa: E402

DEFAULT_RULE = "HARNESS-R1-ter"
SEEDS = tuple(range(12))

# Une lambda par cellule -- construire la tâche puis vérifier `task.name == rule.cellules[clé]["task"]`
# EN TÊTE (avant tout run) est ce qui distingue une erreur de câblage d'un résultat scientifique : la
# tâche est PORTÉE (tools/bilinear_composition_probe.py), jamais reconstruite de mémoire.
_TASKS = {"A": lambda: CompositionTask(K=6, same_tick=True),
          "Aprime": lambda: CompositionTask(K=6, same_tick=True, kind="recall"),
          "B": lambda: CompositionTask(K=6, same_tick=False)}


def _machine_load_note():
    """Processus python DU PROJET (hors moi-même et mes ancêtres), lus par
    `tools.jobs.doctor.project_processes()` -- ligne de commande/cwd DANS le dépôt, PAS un compte
    aveugle de tout `python.exe` système (une première version de ce module utilisait `tasklist`, qui
    comptait aussi des éditeurs/extensions sans lien avec la charge de CALCUL réelle -- ruling
    contrôleur E12, 2026-09-22 : la mesure qui compte est celle du PROJET). Appelé au DÉPART de CHAQUE
    cellule, pas une seule fois pour tout le run : la charge observée AVANT la cellule A (2026-09-22,
    premier run -bis) a produit des abandons de coût que la charge d'UNE lecture globale n'aurait pas
    datés correctement pour B, minutes plus tard."""
    try:
        procs = project_processes()
    except Exception as exc:                                # noqa: BLE001 -- charge non mesurable, jamais inventée
        return f"tools.jobs.doctor indisponible ({exc!r}) -- charge machine NON mesurée", []
    detail = "; ".join(f"pid={p['pid']} age={p['age_min']:.1f}min {p['cmd'][:70]}" for p in procs[:6])
    more = f" (+{len(procs) - 6} autres)" if len(procs) > 6 else ""
    note = (f"{len(procs)} processus python DU PROJET vus (tools.jobs.doctor, hors moi-même) avant "
           f"cette cellule -- E12, tout wall-clock qui suit est un MAJORANT sous cette charge"
           + (f" : {detail}{more}" if procs else ""))
    return note, procs


def main(argv=None):
    argv = list(argv) if argv is not None else sys.argv[1:]
    rule_name = DEFAULT_RULE
    if "--rule" in argv:
        i = argv.index("--rule")
        if i + 1 >= len(argv):
            raise ValueError("--rule requiert un argument (le nom de la regle scellee) : aucun fourni "
                             "apres --rule sur la ligne de commande")
        rule_name = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    cells = argv or ["A", "Aprime", "B"]

    rule = verify(rule_name)                     # sceau vérifié sur la règle ENTIÈRE (les trois cellules)
    prov = provenance(rule_name)
    print(f"[règle] {rule_name}")
    print(f"[provenance] {prov}")

    # declare_design du LANCEUR (les 20 cellules de contrôle de la FAMILLE ENTIÈRE, rule.design) --
    # DISTINCT du declare_design PAR CELLULE que run_harness_cell appelle déjà en interne (6/6/8
    # cellules par cellule A/Aprime/B) : celui-ci couvre le design du run_r1 lui-même, exigé par
    # check_control_family.py dès qu'un module importe tools.preregister et y appelle verify(...).
    design = declare_design(
        question=rule["design"]["question"], replication_unit=rule["design"]["replication_unit"],
        n_independent=int(rule["design"]["n_independent"]), links=dict(rule["design"]["links"]),
        allow_inferred_reason=rule["design"]["inferred_reason"],
        control_family=assert_control_family(cells=int(rule["design"]["control_family"]["cells"])))
    print(f"[design du lanceur] {design}")

    results = {}
    for key in cells:
        c = rule["cellules"][key]
        task = _TASKS[key]()
        if task.name != c["task"]:
            raise ValueError(f"cellule {key} : task.name={task.name!r} != rule.cellules.{key}.task={c['task']!r}")
        learner = ConnectomeLearner(lrs=(float(c["sweep"][0]["lr"]), float(c["sweep"][1]["lr"])),
                                    n_classes=c["sweep"][0]["n_classes"])
        load_note, load_procs = _machine_load_note()
        print(f"[{key}] charge machine, AVANT cette cellule : {load_note}")
        out = run_harness_cell(task, learner, rule_name, seeds=SEEDS, episodes=int(c["episodes"]),
                               out_name=f"harness_r1_{key}", n_agents=int(c["n_agents"]),
                               eval_batches=int(c["eval_batches"]), budget_s=float(c["budget_s"]),
                               unit_s=float(rule["smoke"]["unit_s"][key]), rule_path=["cellules", key],
                               machine_load_note=load_note)   # C3 : la charge MESURÉE, plus la constante
        v, cost = out["verdict"], out["cost"]
        observed_unit_s = cost["actual_s"] / 60.0     # 60 = len(seeds) x len(ARMS) -- même dénominateur
        # que le `n_units` de project_cost : moyenne observée par (seed, bras), comparable à l'unité
        # scellée (ruling contrôleur E12 : "cost.actual_s / 60 par bras en moyenne", comme d7 le publie).
        print(f"[{key}] verdict={v['verdict']}  branch={v['branch']}")
        print(f"      why : {v['why']}")
        print(f"      -> {out['path']}")
        print(f"      cout : unite_scellee(smoke)={cost['unit_s_given']:.3f}s  "
              f"unite_observee(actual_s/60)={observed_unit_s:.3f}s  projete={cost['projected_s']:.1f}s  "
              f"reel={cost['actual_s']:.1f}s ({cost['actual_s'] / 60.0:.1f} min)")
        out["load_note"], out["load_procs"], out["observed_unit_s"] = load_note, load_procs, observed_unit_s
        results[key] = out
    return results


if __name__ == "__main__":
    main()
