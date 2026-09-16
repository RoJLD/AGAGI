# tests/sandbox/test_harness_verdict.py
"""Lecture pure du harnais : chaque branche de l'ORDRE 2.3-b est atteinte par UNE db factice, et rien d'autre.
Aucune constante sur collection vide : listes vides et nan LÈVENT.

Fix round 1/5 (revue contrôleur, 2026-09-16) : trois défauts réels du composé d'instruments, corrigés
dans `src/seed_ai/harness_verdict.py` -- CRITICAL 1 (les INCONCLUSIVE* de `ablation_verdict` devenaient
une affirmation NÉGATIVE), CRITICAL 2 (l'E19 de nécessité lisait du bruit sous-résolution comme un
artefact de pas), IMPORTANT 1/2/3 (intervention_verified câblée, défauts de RÈGLE lus comme verdict,
demande publiée sur un sujet qui n'a rien acquis). Les cas de calibration correspondants sont ajoutés
ci-dessous plutôt que réécrits en place -- la suite croît de façon monotone (règle « Auto-amélioration »)."""
import dataclasses
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_verdict import (  # noqa: E402
    BRANCHES, harness_verdict_lecture, measure_ablated_bayes_ceiling, measure_noise_floor)

SEEDS = list(range(12))


def _col(values):
    return {str(s): float(v) for s, v in zip(SEEDS, values)}


def _dose(updates):
    return {str(s): {"calls": 300, "updates": updates, "dparam_abs_sum": float(updates), "episodes_seen": 4800,
                     "unit": "gradient_updates"} for s in SEEDS}


def _rule(piece="bilinear"):
    return {"n_floor": 12, "piece": piece, "sweep": [{"lr": 0.02}, {"lr": 0.002}],
            "ablations": [{"name": "permute_key", "site": "input", "must_bite": True},
                          {"name": "inject_distractor_slot", "site": "input", "must_bite": False}],
            "bayes_floors": {"permute_key": 1 / 6},
            "incapable_ceiling": {"value": 34 / 36, "provenance": "forme close plain 34/36, MINORANT (plain_substrate_ceiling.py)", "proven": False},
            "min_sep": 0.05, "prior_max": 0.5, "oracle_min": 0.9, "collapse_factor": 1.5, "alive_margin": 0.05,
            "matched_sham": None}


def _db(A=0.93, A0=0.17, A2=0.90, D=0.27, D2=0.30, noop=None, abl_key=0.17, abl_dist=None, oracle=1.0, first=0.20):
    rng = np.random.RandomState(0)
    j = lambda v, w=0.01: [v + w * x for x in rng.uniform(-1, 1, 12)]   # noqa: E731
    noop = j(A) if noop is None else noop
    abl_dist = j(A) if abl_dist is None else abl_dist
    return {"seeds": SEEDS,
            "arms": {"A": {"first": _col(j(first)), "mid": _col(j((first + A) / 2)), "last": _col(j(A)), "dose": _dose(300)},
                     "A0": {"last": _col(j(A0)), "dose": _dose(0)},
                     "A2": {"last": _col(j(A2)), "dose": _dose(300)},
                     "D": {"last": _col(j(D)), "dose": _dose(300)},
                     "D2": {"last": _col(j(D2)), "dose": _dose(300)}},
            "eval": {"noop": {"A": _col(noop), "A0": _col(j(A0)), "A2": _col(j(A2)), "D": _col(j(D)), "D2": _col(j(D2))},
                     "oracle": _col([oracle] * 12),
                     "ablated": {"permute_key": _col(j(abl_key)), "inject_distractor_slot": _col(abl_dist)},
                     "control": {}},
            "abandoned": {k: [] for k in ("A", "A0", "A2", "D", "D2")},
            # IMPORTANT 1 (fix round 1) : `piece_removed_verified` publié par défaut (le runner de la
            # tâche 6 le publiera depuis `assert_learner_contract(pieces=[piece])`) -- préserve le
            # comportement de toutes les db factices précédentes (`intervention_verified=True`).
            "regime": {"piece_removed_verified": True}}


def test_branch_order_is_the_sealed_one():
    assert BRANCHES == ("INCOMPLET", "INCONCLUSIVE_N", "INDETERMINE_HARNAIS", "LR_ARTIFACT", "NOT_ACQUIRED",
                        "NOT_DEMANDED", "DEMAND_WITHIN_NOISE", "DEMAND_INCONCLUSIVE", "INCONCLUSIVE_SPECIFICITY",
                        "INCONCLUSIVE_ALIAS", "PIECE_NOT_NECESSARY", "PIECE_INCONCLUSIVE", "PIECE_PARTIAL",
                        "DEMANDED_ACQUIRED_NECESSARY", "AUTRE")


def test_cell_A_known_answer_is_PARTIAL_with_ceiling_above_bar():
    out = harness_verdict_lecture(_db(), _rule())
    assert out["verdict"] == "PIECE_PARTIAL"
    assert out["demand"]["permute_key"]["verdict"] == "X_DEMANDED"
    assert out["demand"]["inject_distractor_slot"]["verdict"] == "X_DECOY"
    assert out["acquisition"]["verdict"] == "ACQUIRED" and out["acquisition"]["per_seed_above_ref"] == "12/12"
    assert out["acquisition"]["representational_ceiling_above_bar"] is True
    assert out["acquisition"]["bar_status"] == "CEILING_ABOVE_BAR"
    assert out["necessity"]["bilinear"]["verdict"] == "PIECE_PARTIAL"
    assert out["necessity"]["bilinear"]["sham"] == "PARAMS_NON_APPARIES"
    assert out["necessity"]["bilinear"]["without_clears_bar"] is True   # deliberately-not-applied ruling
    assert 0.0 <= out["e19"]["closure"] <= 2 / 3
    assert out["e19"]["condition"] == "necessity"


def test_cell_B_known_answer_is_NECESSARY():
    out = harness_verdict_lecture(_db(D=0.18, D2=0.19), _rule("recurrent_state"))
    assert out["verdict"] == "DEMANDED_ACQUIRED_NECESSARY"
    assert out["necessity"]["recurrent_state"]["verdict"] == "NECESSARY"
    assert out["necessity"]["recurrent_state"]["without_clears_bar"] is False
    assert out["e19"]["status"] == "SKIPPED_NECESSARY"   # CRITICAL 2 : NECESSARY ne teste jamais la robustesse


def test_ablated_equal_to_intact_is_NOT_DEMANDED():
    # abl_key=0.93 (== A) tombe DANS la bande de bruit mesurée (ratio ~1,0 +- le même bruit que le noop
    # de A) : la branche atteinte est alors DEMAND_WITHIN_NOISE, plus sévère dans l'ORDRE 2.3-b -- ce
    # n'est pas le cas visé ici. 0,80 rend un ratio ~1,15, hors bande mais toujours dans la zone DECOY
    # (< 1,3) : un vrai « n'a pas mordu », distinct du cas « indiscernable du bruit ».
    assert harness_verdict_lecture(_db(abl_key=0.80), _rule())["verdict"] == "NOT_DEMANDED"


def test_ratio_inside_the_measured_noise_band_is_DEMAND_WITHIN_NOISE_never_decoy():
    db = _db(abl_key=0.88, noop=[0.93 / r for r in np.linspace(0.92, 1.08, 12)])   # bande [0.92 ; 1.08] mesurée
    out = harness_verdict_lecture(db, _rule())
    assert out["verdict"] == "DEMAND_WITHIN_NOISE"
    assert out["demand"]["permute_key"]["in_noise_band"] is True


def test_grey_zone_ratio_is_DEMAND_INCONCLUSIVE_not_a_claim():
    """CRITICAL 1 (fix round 1) : ratio 1,39 -- ni collapse (>=1,5, decoy_ceiling par défaut) ni decoy
    ([1/1,3 ; 1,3]) -- `ablation_verdict` rend INCONCLUSIVE. Le harnais ne doit JAMAIS relire ça comme
    NOT_DEMANDED ou DEMAND_WITHIN_NOISE : un instrument qui refuse de conclure n'affirme rien."""
    db = _db(abl_key=0.93 / 1.39)
    out = harness_verdict_lecture(db, _rule())
    assert out["demand"]["permute_key"]["verdict"] == "INCONCLUSIVE"
    assert out["verdict"] == "DEMAND_INCONCLUSIVE"
    assert "INCONCLUSIVE" in out["why"]


def test_ablation_that_improves_the_arm_is_DEMAND_INCONCLUSIVE_not_a_claim():
    """CRITICAL 1 : l'ablation AMÉLIORE le bras de 1,55x (ratio ~0,645 < 1/1,3) -- `ablation_verdict`
    rend INCONCLUSIVE_INVERTED (effet de signe inverse), jamais un decoy ni une demande."""
    db = _db(A=0.50, abl_key=0.775)
    out = harness_verdict_lecture(db, _rule())
    assert out["demand"]["permute_key"]["verdict"] == "INCONCLUSIVE_INVERTED"
    assert out["verdict"] == "DEMAND_INCONCLUSIVE"


def test_intact_at_the_bayes_floor_is_DEMAND_INCONCLUSIVE_never_a_negative_claim():
    """CRITICAL 1 : le bras intact est LUI-MÊME au plancher de Bayes déclaré (permute_key, 1/6) -- la
    garde de dégénérescence de `ablation_verdict` s'arme (bras au PLANCHER) ; le harnais doit lire
    DEMAND_INCONCLUSIVE, jamais un DEMAND_WITHIN_NOISE qui prétendrait avoir mesuré quelque chose."""
    db = _db(A=0.15, A0=0.05, A2=0.15, D=0.12, D2=0.12, first=0.05, abl_key=0.17)
    out = harness_verdict_lecture(db, _rule())
    assert out["acquisition"]["verdict"] == "ACQUIRED"
    assert out["demand"]["permute_key"]["verdict"] == "INCONCLUSIVE_DEGENERATE"
    assert out["verdict"] == "DEMAND_INCONCLUSIVE"


def test_a_biting_control_is_INCONCLUSIVE_SPECIFICITY():
    assert harness_verdict_lecture(_db(abl_dist=[0.40] * 12), _rule())["verdict"] == "INCONCLUSIVE_SPECIFICITY"


def test_learner_at_reference_is_NOT_ACQUIRED_with_dose_and_saturation():
    # IMPORTANT 3 (fix round 1) : `abl_key` reste à sa valeur par défaut (chance, ~1/6) -- avant le fix,
    # la demande pouvait ENCORE écraser NOT_ACQUIRED (d'où le 0,10 forcé dans la version précédente) ;
    # maintenant la demande est publiée mais jamais lue quand le sujet n'a rien acquis, donc même un
    # abl_key « à chance » ne change plus le verdict final.
    out = harness_verdict_lecture(_db(A=0.18, A2=0.18, D=0.17, D2=0.17, first=0.17), _rule())
    assert out["verdict"] == "NOT_ACQUIRED"
    # `dose` est publié PAR SEED (db["arms"][arm]["dose"] est déjà indexé seed -> dose.as_dict(), jamais
    # aplati par harness_verdict_lecture) : indexer par un seed pour lire le champ, pas directement.
    assert out["acquisition"]["dose"]["A"]["0"]["updates"] == 300
    assert out["acquisition"]["saturation"] in ("TENDANCE", "PLATEAU")
    assert out["demand"] is not None   # publiée pour information...
    assert out["verdict"] == "NOT_ACQUIRED"   # ...mais jamais lue comme verdict final


def test_reference_above_prior_max_is_INDETERMINE_HARNAIS_PRIOR_SOLVES():
    out = harness_verdict_lecture(_db(A0=0.60), _rule())
    assert out["verdict"] == "INDETERMINE_HARNAIS" and "PRIOR_SOLVES" in out["why"]


def test_oracle_below_min_is_INDETERMINE_HARNAIS():
    assert harness_verdict_lecture(_db(oracle=0.85), _rule())["verdict"] == "INDETERMINE_HARNAIS"


def test_piece_gap_that_closes_at_the_second_lr_is_LR_ARTIFACT():
    assert harness_verdict_lecture(_db(D=0.27, D2=0.88, A2=0.90), _rule())["verdict"] == "LR_ARTIFACT"


def test_intact_collapsed_at_the_second_lr_is_INDETERMINE_HARNAIS():
    # acquis à sweep[0] (0,93) mais l'intact tombe SOUS la barre au second pas (0,18) : la closure E19 n'a plus de référence
    assert harness_verdict_lecture(_db(A2=0.18, D2=0.17), _rule())["verdict"] == "INDETERMINE_HARNAIS"


def test_acquisition_null_that_vanishes_at_the_second_lr_is_LR_ARTIFACT():
    # inerte à sweep[0] (0,18 ~ référence) mais acquiert au second pas (0,90 sur 12/12) : nul d'acquisition NON robuste au pas
    assert harness_verdict_lecture(_db(A=0.18, A2=0.90, D=0.17, D2=0.30, first=0.17), _rule())["verdict"] == "LR_ARTIFACT"


def test_gap_below_resolution_floor_is_PIECE_NOT_NECESSARY_not_LR_ARTIFACT():
    """CRITICAL 2 (fix round 1) : deux écarts MINUSCULES (0,0111 puis 0,0036), tous deux < min_sep=0,05 --
    le plancher de résolution (`max(min_sep, med_A*(band_AD[1]-1))`) absorbe la fluctuation ; jamais lue
    comme une fermeture d'artefact par `assert_verdict_invariant_to_optimizer`."""
    db = _db(A=0.90, A2=0.88, D=0.8889, D2=0.8764)
    for s in SEEDS:
        db["arms"]["A"]["last"][str(s)] = 0.90
        db["arms"]["A2"]["last"][str(s)] = 0.88
        db["arms"]["D"]["last"][str(s)] = 0.90 - 0.0111
        db["arms"]["D2"]["last"][str(s)] = 0.88 - 0.0036
    out = harness_verdict_lecture(db, _rule())
    assert out["verdict"] == "PIECE_NOT_NECESSARY"
    assert out["e19"]["status"] == "GAP_BELOW_RESOLUTION"
    assert out["e19"]["condition"] == "necessity"


def test_D_equal_to_A_is_PIECE_NOT_NECESSARY_and_both_at_ceiling_is_not_degenerate():
    """CRITICAL 2 (fix round 1) : jitter INDÉPENDANT restauré (D/D2 tirés séparément de A/A2, comme dans
    la brief d'origine) -- avant le fix, ce bruit sous-résolution (~1e-3) fermait la closure de l'E19 de
    NÉCESSITÉ de >2/3 « par hasard » et rendait LR_ARTIFACT (mesuré : 119/200 seeds synthétiques). Le
    plancher de résolution absorbe maintenant ce bruit ; ce test peut donc À NOUVEAU échouer si la
    résolution disparaissait (c'est tout l'intérêt de restaurer le jitter indépendant)."""
    db = _db(A=1.0, A2=1.0, D=1.0, D2=1.0, noop=[1.0] * 12, abl_dist=[1.0] * 12)
    db["eval"]["noop"]["D"] = _col([1.0] * 12)
    out = harness_verdict_lecture(db, _rule())
    assert out["verdict"] == "PIECE_NOT_NECESSARY"


def test_missing_intervention_flag_with_D_equal_to_A_is_PIECE_INCONCLUSIVE_not_NOT_NECESSARY():
    """IMPORTANT 1 (fix round 1) : `regime.piece_removed_verified` ABSENT + D bit-identique à A --
    `intervention_verified=False` laisse le garde-fou d'identité de `ablation_verdict` armé : le verdict
    est INCONCLUSIVE_DEGENERATE (« l'ablation ne s'est peut-être pas appliquée »), jamais NOT_NECESSARY,
    qui affirmerait à tort que la pièce a été retirée sans effet."""
    db = _db()
    db["regime"] = {}   # flag absent -> intervention_verified=False
    db["arms"]["D"]["last"] = dict(db["arms"]["A"]["last"])
    db["arms"]["D2"]["last"] = dict(db["arms"]["A2"]["last"])
    out = harness_verdict_lecture(db, _rule())
    assert out["necessity"]["bilinear"]["intervention_verified"] is False
    assert out["necessity"]["bilinear"]["verdict"] == "INCONCLUSIVE"
    assert out["verdict"] == "PIECE_INCONCLUSIVE"


def test_missing_arm_is_INCOMPLET_and_n11_is_INCONCLUSIVE_N():
    db = _db()
    del db["arms"]["D2"]
    assert harness_verdict_lecture(db, _rule())["verdict"] == "INCOMPLET"
    db = _db()
    db["abandoned"]["D"] = [3]
    del db["arms"]["D"]["last"]["3"]
    assert harness_verdict_lecture(db, _rule())["verdict"] == "INCONCLUSIVE_N"


def test_nan_and_empty_raise_instead_of_fabricating():
    db = _db()
    db["arms"]["A"]["last"]["0"] = float("nan")
    with pytest.raises(ValueError, match="nan"):
        harness_verdict_lecture(db, _rule())
    with pytest.raises(ValueError, match="vide"):
        measure_noise_floor({}, {})


def test_noise_floor_band_is_min_max_of_paired_ratios():
    out = measure_noise_floor(_col([0.93] * 12), _col([0.93 / r for r in np.linspace(0.95, 1.05, 12)]))
    assert out["band"][0] == pytest.approx(0.95, abs=1e-6) and out["band"][1] == pytest.approx(1.05, abs=1e-6)


def test_necessity_uses_the_band_of_the_WEAK_arm_not_only_A():
    """R3 : a p = 0,27 la bande du bras D est large (+-18 %) ; un ratio A/D ~1,55 DANS la bande de D est
    WITHIN_NOISE. Fix round 1 : D=0,60 (pas 0,62) -- avec la garde CRITICAL 1/IMPORTANT 1 armée, un ratio
    qui tombe dans la zone GRISE de `ablation_verdict` (1,3 < ratio < 1,5, ni collapse ni decoy) rend
    INCONCLUSIVE, jamais un NOT_NECESSARY fabriqué par un `in_band` en filet de sécurité -- 0,62 rendait
    un ratio médian 1,4986 (juste SOUS le seuil de collapse 1,5 après jitter indépendant), ce que le test
    voulait précisément AU-DESSUS pour exercer la branche X_DEMANDED-mais-dans-la-bande. 0,60 rend ~1,55,
    marge confortable au-dessus de 1,5 même sous le jitter des deux bras."""
    db = _db(D=0.60, D2=0.60)                                  # ratio A/D ~ 1,55 : hors bande de A (+-1 %)...
    db["eval"]["noop"]["D"] = _col([0.60 / r for r in np.linspace(0.6, 1.6, 12)])   # ...mais DANS la bande de D
    out = harness_verdict_lecture(db, _rule())
    assert out["noise_floor"]["D"]["band"][1] > 1.5
    assert out["necessity"]["bilinear"]["verdict"] == "NOT_NECESSARY"
    assert out["necessity"]["bilinear"]["in_noise_band"] is True and out["verdict"] == "PIECE_NOT_NECESSARY"


def test_mutating_necessity_threshold_to_strict_flips_the_boundary_case():
    """Porte 15 en miniature : med(D) == référence + min_sep exactement ; la règle dit <= -> NECESSARY.
    Pin des DEUX côtés de la frontière (fix round 1, MINOR) : +1e-6 au-dessus -> PIECE_PARTIAL."""
    db = _db(D=0.22, D2=0.22, A0=0.17)
    for s in SEEDS:
        db["arms"]["D"]["last"][str(s)] = 0.17 + 0.05
        db["arms"]["A0"]["last"][str(s)] = 0.17
    assert harness_verdict_lecture(db, _rule())["verdict"] == "DEMANDED_ACQUIRED_NECESSARY"

    db2 = _db(D=0.22, D2=0.22, A0=0.17)
    for s in SEEDS:
        db2["arms"]["D"]["last"][str(s)] = 0.17 + 0.05 + 1e-6
        db2["arms"]["A0"]["last"][str(s)] = 0.17
    assert harness_verdict_lecture(db2, _rule())["verdict"] == "PIECE_PARTIAL"


def test_duplicate_lrs_in_sweep_raises_ValueError_not_LR_ARTIFACT():
    """IMPORTANT 2 (fix round 1) : un sweep à lrs dupliqués est un défaut de RÈGLE, jamais un verdict --
    avant le fix, le `PreflightError` interne de `assert_verdict_invariant_to_optimizer` ("il faut au
    moins deux pas distincts") se faisait avaler par le `except PreflightError` de `_e19` et republier
    LR_ARTIFACT, un FAUX artefact scientifique."""
    rule = _rule()
    rule["sweep"] = [{"lr": 0.02}, {"lr": 0.02}]
    with pytest.raises(ValueError, match="distincts"):
        harness_verdict_lecture(_db(), rule)


def test_short_provenance_raises_ValueError_not_CEILING_ABOVE_BAR():
    """IMPORTANT 2 : une provenance non déclarée (< 20 caractères) est un défaut de RÈGLE -- avant le
    fix, le `except PreflightError` générique de `_acquisition` la confondait avec « la barre ne sépare
    rien » et publiait CEILING_ABOVE_BAR comme un FAIT."""
    rule = _rule()
    rule["incapable_ceiling"] = {"value": 0.5, "provenance": "trop court", "proven": False}
    with pytest.raises(ValueError, match="provenance"):
        harness_verdict_lecture(_db(), rule)


def test_incapable_ceiling_below_the_bar_is_SEPARATES():
    """IMPORTANT 4 (fix round 1) : contrôle POSITIF de la garde de barre -- un plafond de l'incapable
    SOUS la barre doit la laisser SÉPARER, jamais publier CEILING_ABOVE_BAR par défaut."""
    rule = _rule()
    rule["incapable_ceiling"] = {"value": 0.10, "provenance": "plancher jouet sous la barre, controle positif de la garde de separation"}
    out = harness_verdict_lecture(_db(), rule)
    assert out["acquisition"]["bar_status"] == "SEPARATES"
    assert out["acquisition"]["representational_ceiling_above_bar"] is False


def test_incapable_ceiling_none_is_CEILING_UNVALIDATED():
    """IMPORTANT 4 : sans plafond déclaré, la barre reste explicitement NON VALIDÉE -- jamais confondue
    avec « séparée » ni avec « au-dessus »."""
    rule = _rule()
    rule["incapable_ceiling"] = None
    out = harness_verdict_lecture(_db(), rule)
    assert out["acquisition"]["bar_status"] == "CEILING_UNVALIDATED"
    assert out["acquisition"]["representational_ceiling_above_bar"] is None


def test_measure_ablated_bayes_ceiling_certifies_the_declared_floor():
    """Décision 6 (task-5-brief §Gate 2) : la certification du Bayes-ceiling ABLATÉ sur une tâche RÉELLE
    (pas une db factice) — l'oracle sous `permute_key` doit noter ~1/K, dans la bande [declared ± 2 se],
    avec un espace d'états énumérable (CompositionTask.enumerate_states() = K*K)."""
    from tools.harness.tasks.composition import CompositionTask
    task = CompositionTask(K=6)
    ablation = next(a for a in task.demand.ablations if a.name == "permute_key")
    out = measure_ablated_bayes_ceiling(task, ablation, n=4096, seed=0)
    assert out["certified"] is True
    assert out["declared"] == pytest.approx(1 / 6)
    assert abs(out["measured"] - 1 / 6) <= 2.0 * out["se"]


def test_measure_ablated_bayes_ceiling_flags_a_wrong_declared_floor():
    """IMPORTANT 4 (fix round 1) : un `bayes_floor` DÉCLARÉ faux (0,5 au lieu de 1/6 réel) doit rendre
    `certified=False` -- l'instrument ne certifie jamais une valeur non mesurée."""
    from tools.harness.tasks.composition import CompositionTask
    task = CompositionTask(K=6)
    real = next(a for a in task.demand.ablations if a.name == "permute_key")
    wrong = dataclasses.replace(real, bayes_floor=0.5)
    out = measure_ablated_bayes_ceiling(task, wrong, n=4096, seed=0)
    assert out["declared"] == pytest.approx(0.5)
    assert out["certified"] is False


def test_measure_ablated_bayes_ceiling_uncertified_when_state_space_not_enumerable():
    """IMPORTANT 4 : un espace d'états NON énumérable (`enumerate_states() is None`) doit rendre
    `certified=False` même si la valeur déclarée est mesurée juste -- la certification exige les DEUX."""
    from tools.harness.tasks.composition import CompositionTask

    class _UnknownStateSpace(CompositionTask):
        def enumerate_states(self):
            return None

    task = _UnknownStateSpace(K=6)
    ablation = next(a for a in task.demand.ablations if a.name == "permute_key")
    out = measure_ablated_bayes_ceiling(task, ablation, n=4096, seed=0)
    assert out["certified"] is False
