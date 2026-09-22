"""
tools/harness/seal_r1.py — Scelle HARNESS-R1 à partir du SMOKE (jamais de chiffre importé d'un autre régime, E8).
Usage : PYTHONIOENCODING=utf-8 python -m tools.harness.seal_r1 [chemin du smoke]

Décisions contrôleur (tâche 10, 2026-09-16) appliquées ici :
(1) `matched_sham` de chaque cellule est LU depuis `PIECES[piece].matched_sham` (registre, tâche 9),
    jamais tapé en dur — c'est le maillon manquant relevé à la tâche 7 : rien n'alignait le
    `matched_sham` d'une règle avec le registre des pièces.
(2) Chaque sous-règle de cellule (`rule["cellules"][c]`) est construite pour passer `validate_rule`
    ET les vérifications en tête de `run_harness_cell` (sweep = EXACTEMENT les deux dicts que
    `ConnectomeLearner(lrs=..., n_classes=...).sweep()` produirait ; ablations = exactement celles de
    la tâche visée ; `bayes_floors` restreint aux ablations `must_bite` de cette tâche).
(3) `discrimination` couvre les 15 branches de `BRANCHES` (dont `DEMAND_INCONCLUSIVE` et `AUTRE`).
(4) Les prédictions chiffrées sont scellées AVANT tout run ; chaque nombre y est soit une réponse
    connue déjà publiée, soit une mesure du présent smoke (jamais un chiffre importé d'un autre
    régime, E8) — annoté comme tel dans le texte.
(7) Ce module SCELLE une règle (`preregister`) : gate 11 (`check_control_family.py`) exige donc un
    `declare_design(...)` dans le même fichier (ici, dans `build_rule_r1`, sous la clé `design` de la
    règle) et un tampon de provenance (`provenance(` ou `stamp(`) APRÈS le scellement, dans `main`.
"""
import json
import os
import statistics
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.paths import results_file  # noqa: E402
from src.seed_ai.harness_pieces import PIECES  # noqa: E402
from src.seed_ai.harness_verdict import BRANCHES  # noqa: E402
from tools.experiment_preflight import assert_control_family, declare_design  # noqa: E402
from tools.preregister import preregister, provenance  # noqa: E402

N_SEEDS, N_ARMS = 12, 5


def _hyper(lr, n_classes):
    return {"lr": lr, "rank": 16, "n_classes": n_classes, "credit": "supervised"}


def build_rule_r1(smoke: dict) -> dict:
    """Pure : choisit le second lr de B = le meilleur des lr ≠ 0,002 dont la médiane dépasse la barre
    (référence + 0,05) ; lève s'il n'y en a aucun (la cellule B ne serait pas scellable). Construit les
    trois sous-règles de cellule (A, A', B) validables individuellement par `validate_rule`, déclare le
    design de la famille entière (`declare_design`, classe E23/E10 — gate 11) et scelle les
    prédictions chiffrées AVANT tout run."""
    ref_b = statistics.median(float(v) for v in smoke["B_ref"].values())
    bar_b = ref_b + 0.05
    cands = {float(lr): statistics.median(float(v) for v in col.values()) for lr, col in smoke["B"].items() if float(lr) != 0.002}
    ok = {lr: m for lr, m in cands.items() if m > bar_b}
    if not ok:
        raise ValueError(f"aucun second pas de B ne franchit la barre {bar_b:.3f} : {cands}")
    lr2 = max(ok, key=ok.get)
    unit = smoke["unit_s"]
    budget = 3.0 * (float(unit["A"]) + float(unit["Aprime"]) + float(unit["B"])) * N_SEEDS * N_ARMS

    # (1) Décision contrôleur : LU du registre, jamais tapé en dur.
    sham_bilinear = PIECES["bilinear"].matched_sham
    sham_recurrent = PIECES["recurrent_state"].matched_sham

    common = {"n_floor": N_SEEDS, "min_sep": 0.05, "prior_max": 0.5, "oracle_min": 0.9, "collapse_factor": 1.5,
              "alive_margin": 0.05}
    ceiling = {"value": 34 / 36, "provenance": "forme close plain 34/36, tools/plain_substrate_ceiling.py:155, MINORANT jamais PROUVE", "proven": False}

    abl_A = [{"name": "permute_key", "site": "input", "must_bite": True},
             {"name": "permute_query", "site": "input", "must_bite": True},
             {"name": "inject_distractor_slot", "site": "input", "must_bite": False}]
    abl_Aprime = [dict(abl_A[0]), {"name": "permute_query", "site": "input", "must_bite": False}, dict(abl_A[2])]
    abl_B = [dict(a) for a in abl_A] + [{"name": "state_reset", "site": "state", "must_bite": True}]

    # (2) bayes_floors restreint aux ablations must_bite de CHAQUE tâche (jamais une union importée
    # d'une autre cellule -- une clé absente de la tâche fait lever `run_harness_cell` en tête).
    floors_A = {"permute_key": 1 / 6, "permute_query": 1 / 6}
    floors_Aprime = {"permute_key": 1 / 6}
    floors_B = {"permute_key": 1 / 6, "permute_query": 1 / 6, "state_reset": 1 / 6}

    cells = {
        "A": dict(common, task="composition_same_tick_K6", learner="connectome_torch", piece="bilinear", episodes=300,
                  sweep=[_hyper(0.02, None), _hyper(0.002, None)], ablations=abl_A, bayes_floors=floors_A,
                  incapable_ceiling=ceiling, matched_sham=sham_bilinear),
        "Aprime": dict(common, task="recall_same_tick_K6", learner="connectome_torch", piece="bilinear", episodes=150,
                       sweep=[_hyper(0.02, None), _hyper(0.002, None)], ablations=abl_Aprime, bayes_floors=floors_Aprime,
                       incapable_ceiling=None, matched_sham=sham_bilinear),
        "B": dict(common, task="composition_two_step_K6", learner="connectome_torch", piece="recurrent_state", episodes=600,
                  sweep=[_hyper(0.002, 6), _hyper(lr2, 6)], ablations=abl_B, bayes_floors=floors_B,
                  incapable_ceiling=None, matched_sham=sham_recurrent),
    }

    # (7) declare_design : mêmes maillons que ceux déclarés par `run_harness_cell` lui-même
    # (tools/harness/cell.py) -- la famille de contrôles porte les TROIS cellules x DEUX pas de sweep
    # chacune (une ablation "à must_bite" par pas, comparée au bras intact), donc cells=3*2=6.
    design = declare_design(
        question="Le harnais à trois conditions rend-il, sur les trois cellules PORTÉES à réponse "
                 "connue, PARTIAL (A), NOT_NECESSARY (A') et NECESSARY (B) ?",
        replication_unit="seed", n_independent=N_SEEDS,
        links={"ablation->chute": "measured", "dose->acquisition": "measured", "sans_piece->chute": "measured",
               "analogue_bio": "inferred"},
        allow_inferred_reason="l'analogue biologique d'une pièce est une hypothèse portée par le registre "
                              "(spec §2.6), jamais mesurée ici",
        control_family=assert_control_family(cells=3 * 2))

    return {
        "question": design["question"],
        "design": design,
        "design_note": "unite = seed, n = 12 (seeds 0-11), 5 bras apparies par seed (A, A0, A2, D, D2), "
                       "eval du meme sujet, plancher de bruit par second rng",
        "cellules": cells,
        "dv_primaire": "`hits` par seed et par bras ; `ratio_within` par ablation ; `sep_ref` (mediane A - mediane A0) ; `dose.updates` par bras ; `noise_band` ; `closure` (E19)",
        "discrimination": {b: "voir src/seed_ai/harness_verdict.py::BRANCHES, ordre impose" for b in BRANCHES},
        "regle_de_lecture_continue": "ORDRE IMPOSE : " + " -> ".join(BRANCHES),
        "predictions_chiffrees_AVANT_le_run": {
            "A": "PIECE_PARTIAL : chute >= 3x hors bande, plain ~0,27 > barre ~0,22 (billet publié, "
                 "results/bilinear_composition.json) ; bit-identite seed 0 (0,9328125 / 0,2703125, connu "
                 "publié) ; bar_status CEILING_ABOVE_BAR (0,944 = 34/36 forme close, publiée > barre "
                 "ref+0,05) ; sham DECLARED ({\"bilinear_sham\": True}, registre PIECES) ; e19 ROBUST attendu",
            "Aprime": "PIECE_NOT_NECESSARY : plain = bilineaire = 1,0 (same_tick supervise 150 ep., "
                      "MESURE seeds 0-2 au present smoke, cf. Aprime/Aprime_plain) ; acquisition ACQUIRED",
            "B": f"DEMANDED_ACQUIRED_NECESSARY : intact ~0,92 a lr 0,002 (MESURE au present smoke) ; "
                 "state_reset -> ~1/6 (plancher de Bayes K=6, connu) ; sans recurrent_state (feedforward, "
                 "entraine sans etat porte) -> ~1/6 (meme plancher) ; second pas de lr "
                 f"{lr2} (mediane MESUREE au present smoke {ok[lr2]:.3f}) ; e19 ROBUST attendu"},
        "clause_E19": "toute cellule non NECESSARY passe assert_verdict_invariant_to_optimizer sur les deux pas du sweep ; closure > 2/3 = LR_ARTIFACT, pas un verdict",
        "smoke": {"B_medians_by_lr": {str(k): v for k, v in cands.items()}, "B_ref_median": ref_b, "unit_s": unit},
        "budget_s": budget,
        "cout": f"unites mesurees au smoke (s/bras) : {unit} ; budget = 3 x somme x 12 seeds x 5 bras = {budget/60:.0f} min ; sans bail kuzu",
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    path = results_file("harness_r1_smoke_0.json")
    if argv:
        path = argv[0]
    with open(path, encoding="utf-8") as f:
        smoke = json.load(f)["data"]
    rule = build_rule_r1(smoke)
    p = preregister("HARNESS-R1", rule)
    prov = provenance("HARNESS-R1")          # (7) tampon de provenance APRES le scellement (gate 11 / test_every_sealed_runner_carries_the_provenance_stamp)
    print("->", p)
    print("-> provenance :", prov)


if __name__ == "__main__":
    main()
