# tests/sandbox/test_s2_stats.py
import numpy as np
from src.seed_ai.s2_stats import cliffs_delta, median_ratio


def test_cliffs_delta_full_dominance():
    # tous les a > tous les b -> delta = +1
    assert cliffs_delta([5, 6, 7], [1, 2, 3]) == 1.0


def test_cliffs_delta_full_dominance_negative():
    assert cliffs_delta([1, 2, 3], [5, 6, 7]) == -1.0


def test_cliffs_delta_no_difference():
    assert cliffs_delta([1, 2, 3], [1, 2, 3]) == 0.0


def test_median_ratio_basic():
    assert median_ratio([20, 40, 60], [10, 20, 30]) == 2.0


def test_median_ratio_zero_denominator_returns_inf():
    assert median_ratio([5, 5, 5], [0, 0, 0]) == float("inf")


from src.seed_ai.s2_stats import wilcoxon_signed_rank


def test_wilcoxon_all_positive_is_significant():
    # 15 différences toutes positives -> p très petit
    d = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    w, p = wilcoxon_signed_rank(d)
    assert p < 0.01


def test_wilcoxon_symmetric_not_significant():
    d = [1.0, -1.0, 2.0, -2.0, 3.0, -3.0, 4.0, -4.0]
    w, p = wilcoxon_signed_rank(d)
    assert p > 0.5


def test_wilcoxon_drops_zeros_and_handles_empty():
    assert wilcoxon_signed_rank([0.0, 0.0])[1] == 1.0


from src.seed_ai.s2_stats import bootstrap_ci, median_ratio as _mr


def test_bootstrap_ci_brackets_point_estimate():
    # NB : espacement NON uniforme (et non proportionnel à b) -> le bootstrap apparié a une vraie
    # variance. med(a)=32, med(b)=15.5 -> ratio vrai ~2. (Des données a==2*b donneraient lo==hi.)
    a = [18, 21, 23, 26, 28, 31, 33, 35, 38, 41, 43, 46]
    b = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
    lo, hi = bootstrap_ci(_mr, a, b, n_boot=500, alpha=0.05, seed=1)
    assert lo <= 2.0 <= hi          # ratio vrai ~2
    assert lo < hi


def test_bootstrap_ci_is_deterministic_with_seed():
    a, b = [3, 4, 5, 6], [1, 2, 3, 4]
    assert bootstrap_ci(_mr, a, b, n_boot=200, seed=7) == bootstrap_ci(_mr, a, b, n_boot=200, seed=7)


from src.seed_ai.s2_stats import holm, iut_pvalue


def test_holm_known_values():
    # Holm step-down : p triés [.01,.02,.04] * [3,2,1] = [.03,.04,.04] (monotone)
    adj = holm([0.04, 0.01, 0.02])
    assert abs(adj[1] - 0.03) < 1e-9     # le .01 -> .03
    assert adj[0] >= adj[2]              # monotonie après tri


def test_holm_caps_at_one():
    assert all(p <= 1.0 for p in holm([0.9, 0.8, 0.7]))


def test_iut_pvalue_is_max():
    # Intersection-Union : on ne rejette que si TOUTES rejettent -> p = max
    assert iut_pvalue([0.01, 0.2, 0.03]) == 0.2


import numpy as np
from src.seed_ai.s2_stats import s2_verdict


def _rng_arr(seed, lo, hi, n=14):
    return list(np.random.default_rng(seed).uniform(lo, hi, n))


def _cond(surv, life):
    """Condition de test : chaque valeur = un agent (poolé) ET une ère (par seed) -> les deux
    granularités coïncident, ce qui exerce Cliff (poolé) ET le Wilcoxon apparié PAR SEED (par ère)."""
    return {"survival": surv, "life_score": life, "era_survival": surv, "era_life": life}


def test_verdict_exige_when_champion_dominates():
    champ = _cond(_rng_arr(1, 200, 260), _rng_arr(5, 2000, 3000))
    baselines = {"random": _cond(_rng_arr(2, 10, 30), _rng_arr(6, 0, 50)),
                 "newborn": _cond(_rng_arr(3, 20, 40), _rng_arr(7, 0, 80)),
                 "reflex": _cond(_rng_arr(4, 40, 70), _rng_arr(8, 50, 200))}
    v = s2_verdict(champ, baselines)
    assert v["verdict"] == "EXIGE"
    assert v["coherence_ok"] is True


def test_verdict_void_when_champion_fails_coherence():
    # champion ne bat PAS les baselines sur sa propre fitness (life_score) -> VOID
    champ = _cond(_rng_arr(1, 200, 260), _rng_arr(9, 0, 10))      # life_score champion FAIBLE
    baselines = {"reflex": _cond(_rng_arr(4, 40, 70), _rng_arr(10, 100, 300))}
    v = s2_verdict(champ, baselines)
    assert v["verdict"] == "VOID"


def test_verdict_nexige_pas_when_champion_equiv_reflex():
    # seed 21 : champion GENUINEMENT equivalent au reflex (|Cliff|=0.01 < EQUIV_MARGIN=0.147) ET
    # difference par seed non significative (p >= alpha) -> equivalence (pas AMBIGU). Le seed 1
    # donnait |Cliff|=0.163 (bruit d'echantillonnage) = AMBIGU, pas une vraie equivalence.
    champ = _cond(_rng_arr(21, 40, 70), _rng_arr(5, 500, 800))
    baselines = {"random": _cond(_rng_arr(2, 10, 30), _rng_arr(6, 0, 50)),
                 "reflex": _cond(_rng_arr(4, 40, 70), _rng_arr(8, 50, 200))}
    v = s2_verdict(champ, baselines)
    assert v["verdict"] == "N'EXIGE PAS"


def test_verdict_from_survival_cmps_exige():
    # Re-render (addendum 2026-06-30) : champion domine tous les baselines en survie -> EXIGE.
    from src.seed_ai.s2_stats import verdict_from_survival_cmps
    cmps = {"random_action": {"p": 0.0025, "cliff": 0.92, "ratio_lo": 3.4, "ratio_hi": 4.2},
            "random_genome": {"p": 0.0025, "cliff": 0.93, "ratio_lo": 3.4, "ratio_hi": 4.2},
            "reflex":        {"p": 0.0025, "cliff": 0.95, "ratio_lo": 3.4, "ratio_hi": 4.5}}
    v = verdict_from_survival_cmps(cmps)
    assert v["verdict"] == "EXIGE"
    assert v["coherence_basis"] == "survival"
    assert v["strongest_baseline"] == "random_action"   # cliff minimal = le plus dur à battre
    assert v["p_monde"] == 0.0025


def test_verdict_from_survival_cmps_void_when_incoherent():
    # p_monde >= alpha (un baseline non battu) -> incohérent -> VOID (pas de verdict survie forcé).
    from src.seed_ai.s2_stats import verdict_from_survival_cmps
    cmps = {"reflex": {"p": 0.40, "cliff": 0.10}, "random_action": {"p": 0.01, "cliff": 0.5}}
    assert verdict_from_survival_cmps(cmps)["verdict"] == "VOID"


def test_verdict_from_survival_cmps_void_when_champion_dominated():
    # champion DOMINÉ (cliff négatif) -> incohérent (cohérence exige tous cliff>0) -> VOID.
    from src.seed_ai.s2_stats import verdict_from_survival_cmps
    cmps = {"reflex": {"p": 0.001, "cliff": -0.8}, "random_action": {"p": 0.001, "cliff": -0.7}}
    assert verdict_from_survival_cmps(cmps)["verdict"] == "VOID"


def test_verdict_from_survival_cmps_ambigu_subthreshold():
    # cohérent (tous cliff>0, p<alpha) mais effet sous le seuil (cliff<0.33) -> AMBIGU.
    from src.seed_ai.s2_stats import verdict_from_survival_cmps
    cmps = {"reflex": {"p": 0.01, "cliff": 0.20}, "random_action": {"p": 0.01, "cliff": 0.25}}
    assert verdict_from_survival_cmps(cmps)["verdict"] == "AMBIGU"
