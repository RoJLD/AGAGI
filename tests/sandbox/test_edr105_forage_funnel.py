import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.lewis_survival_sweep import _cfg, _measure_forage, _verdict_forage


def _agg(p_reach, p_cap, income_t, drain_t):
    return {"p_reach": p_reach, "p_cap": p_cap, "income_t": income_t, "drain_t": drain_t}


def test_verdict_forage_approche():
    assert _verdict_forage(_agg(0.3, 1.0, 5.0, 1.0)) == "GOULOT=APPROCHE"


def test_verdict_forage_capture():
    assert _verdict_forage(_agg(0.9, 0.3, 5.0, 1.0)) == "GOULOT=CAPTURE"


def test_verdict_forage_revenu():
    assert _verdict_forage(_agg(0.9, 0.9, 0.5, 1.0)) == "GOULOT=REVENU"


def test_verdict_forage_suffisant():
    assert _verdict_forage(_agg(0.9, 0.9, 2.0, 1.0)) == "FORAGE SUFFISANT"


# --------------------------------------------------------------------------------------------------
# P2.49 (2026-09-10) — DEFAUT REEL, mesure avant correctif, et il est du genre RARE dans ce depot :
# un POSITIF fabrique. `_verdict_forage` sur une agregation dont les quatre grandeurs valent `nan`
# rendait "FORAGE SUFFISANT" — parce que `nan < 0.5` vaut False, donc les trois tests de la cascade
# tombent et le verdict de QUEUE sort : « l'entonnoir tient, le mur est ailleurs ».
# ⚠️ Ce qui rend ce cas plus dangereux que les negatifs fabriques que le depot traque : il ne
# RESSEMBLE pas aux autres resultats. Un « PAS DE RUNG » fabrique se noie dans un depot plein de
# negatifs ; un « FORAGE SUFFISANT » fabrique se remarquerait — s'il etait faux dans l'autre sens.
# ⚠️ Et `nan` en ENTREE est precisement ce que le depot demande de RENDRE en cas d'absence (porte 14).
# Le consommer comme une mesure annule tout le benefice de l'avoir rendu : la chaine casse au
# maillon suivant.
# --------------------------------------------------------------------------------------------------

def test_verdict_forage_REFUSE_une_agregation_NON_FINIE():
    """CONTRE-EXEMPLE GELE : l'incident rejoue tel quel."""
    import math

    import pytest
    nan = float("nan")
    with pytest.raises(ValueError, match="NON FINIES"):
        _verdict_forage(_agg(nan, nan, nan, nan))
    # une SEULE grandeur non finie suffit : la cascade s'arrete au premier etage evaluable
    with pytest.raises(ValueError, match="NON FINIES"):
        _verdict_forage(_agg(0.9, 0.9, math.inf, 1.0))


def test_verdict_forage_REFUSE_une_agregation_INCOMPLETE():
    """Une grandeur ABSENTE levait deja (KeyError), mais sans dire laquelle ni pourquoi — et un
    `KeyError` accidentel n'est pas une garde : il disparait au premier refactor qui met un defaut."""
    import pytest
    with pytest.raises(ValueError, match="ABSENTES"):
        _verdict_forage({"p_reach": 0.9, "p_cap": 0.9})


def test_verdict_forage_ACCEPTE_les_valeurs_FINIES_extremes():
    """NO-OP APPARIE de la garde : elle ne doit refuser que le NON FINI, pas les bornes legitimes.
    Sans ce cas, une garde qui refuserait 0.0 ou 1.0 passerait les deux tests precedents tout en
    rendant l'instrument inutilisable sur les regimes qui l'interessent le plus."""
    assert _verdict_forage(_agg(0.0, 1.0, 0.0, 0.0)) == "GOULOT=APPROCHE"
    assert _verdict_forage(_agg(1.0, 1.0, 0.0, 0.0)) == "FORAGE SUFFISANT"


def _mk_env(trace_forage):
    cfg = WorldConfig()
    cfg.base_metabolism = 0.25
    cfg.trace_forage = trace_forage
    env = Biosphere3D(cfg)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    env.use_ref_head = False
    env.decode_act = False
    for _ in range(4):
        env.add_agent(MambaAgent(), energy=80.0)
    env.current_era = 1
    return env


def test_config_default_trace_forage_off():
    assert WorldConfig().trace_forage is False


def test_trace_forage_off_is_inert():
    env = _mk_env(trace_forage=False)
    env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    assert pool, "des agents doivent exister"
    for ag in pool:
        assert "_forage_min_dist" not in ag
        assert "_forage_contacts" not in ag
        assert "_forage_income" not in ag


def test_trace_forage_on_records_min_dist():
    env = _mk_env(trace_forage=True)
    for _ in range(3):
        env.step()
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    traced = [ag for ag in pool if "_forage_min_dist" in ag]
    assert traced, "des agents doivent porter _forage_min_dist (proies presentes)"
    for ag in traced:
        assert np.isfinite(ag["_forage_min_dist"])
        assert ag["_forage_min_dist"] >= 0


def test_cfg_trace_forage_param():
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True)
    assert cfg.trace_forage is True
    assert cfg.trace_energy_sinks is True
    assert cfg.base_metabolism == 0.0


def test_measure_forage_smoke():
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True)
    agg = _measure_forage(cfg, [105, 106], n_apex=0, max_ticks=20)
    assert agg["n_agents"] > 0
    assert 0.0 <= agg["p_reach"] <= 1.0
    assert 0.0 <= agg["p_cap"] <= 1.0
    assert agg["income_t"] >= 0.0
    assert agg["drain_t"] >= 0.0
    assert np.isfinite(agg["mean_min_dist"])
