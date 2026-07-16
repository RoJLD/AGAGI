from tools.lewis_survival_sweep import (_cfg, _measure_forage, _verdict_deconfound,
                                        main_forage_deconfound)


def test_measure_forage_accepts_disable_repro_default_false():
    # signature : disable_repro existe et vaut False par defaut (non-regression).
    import inspect
    sig = inspect.signature(_measure_forage)
    assert "disable_repro" in sig.parameters
    assert sig.parameters["disable_repro"].default is False


def test_disable_repro_freezes_cohort_and_lifts_p_reach():
    # A proies figees, couper la reproduction -> pool BEAUCOUP plus petit (cohorte fixe) ET p_reach
    # plus haut (pas de dilution par nouveau-nes tardifs). Verification directe du mecanisme.
    seeds = [1140 + i for i in range(4)]
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True, prey_speed_scale=0.0)
    with_repro = _measure_forage(cfg, seeds, n_apex=0, max_ticks=150, disable_repro=False)
    no_repro = _measure_forage(cfg, seeds, n_apex=0, max_ticks=150, disable_repro=True)
    assert no_repro["n_agents"] < with_repro["n_agents"], "no-repro doit figer la cohorte (pool plus petit)"
    assert no_repro["p_reach"] > with_repro["p_reach"], "couper la repro doit lever p_reach (de-confond)"


def test_non_regression_disable_repro_false_deterministic():
    seeds = [777 + i for i in range(3)]
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True, prey_speed_scale=0.0)
    a = _measure_forage(cfg, seeds, n_apex=0, max_ticks=150, disable_repro=False)
    b = _measure_forage(cfg, seeds, n_apex=0, max_ticks=150, disable_repro=False)
    assert a["p_reach"] == b["p_reach"]
    assert a["n_agents"] == b["n_agents"]


def _agg(p_reach):
    return {"p_reach": p_reach, "p_cap": 1.0, "mean_min_dist": 0.5, "n_agents": 100, "reached_raw": [1, 0]}


def test_verdict_deconfound_branches():
    confirme = [(False, 1.0, _agg(0.18)), (False, 0.0, _agg(0.21)),
                (True, 1.0, _agg(0.30)), (True, 0.0, _agg(0.43))]   # ratio figees 0.43/0.21 = 2.05
    assert _verdict_deconfound(confirme) == "CONFOND CONFIRME"
    negl = [(False, 0.0, _agg(0.40)), (True, 0.0, _agg(0.42))]      # ratio 1.05
    assert _verdict_deconfound(negl) == "CONFOND NEGLIGEABLE"
    assert _verdict_deconfound([(False, 1.0, _agg(0.2)), (True, 1.0, _agg(0.4))]) == "INDETERMINE"


def test_main_forage_deconfound_smoke():
    r = main_forage_deconfound(speeds=(0.0,), n_eval=2, R=1, seed=99140, _return=True)
    assert r["verdict"] in ("CONFOND CONFIRME", "CONFOND NEGLIGEABLE", "INDETERMINE")
    assert len(r["table"]) == 2   # 2 cellules : {repro on/off} x {1 vitesse}
