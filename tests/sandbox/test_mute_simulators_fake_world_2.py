"""P2.56 (b), cinquième fournée — cinq SIMULATEURS muets sous MONDE FACTICE à dose connue (0 monde réel), même dispositif
que test_mute_simulators_fake_world.py : `_world` rend un environnement minimal, les lecteurs de contexte rendent des
contextes connus, la persistance HoF est capturée. Ce qui est jugé : l'état global `persistence.SPECIATE` /
`SPECIATE_MODE` posé PUIS RESTAURÉ (même sur exception : E5 état global), la promotion des 5 meilleurs par ère, les
agrégats (tués par ère, proies moyennes sur la seconde moitié, information mutuelle réelle contre permutée) et les valeurs
d'absence publiées telles quelles.

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

import tools.speciation as SP  # noqa: E402
import tools.nas_rich as NR  # noqa: E402
import tools.reconfirm_047 as RC  # noqa: E402
import tools.lang_speciation as LS  # noqa: E402
import tools.arm_language as AL  # noqa: E402

TOK0, TOK1, SILENT = [1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]


class _Env:
    def __init__(self, agents, die_at=2, big_kills=0):
        self.agents = [dict(a) for a in agents]
        self.dead_agents = []
        self.t, self.die_at, self.big_kills = 0, die_at, big_kills

    def step(self):
        self.t += 1
        if self.t >= self.die_at:
            self.dead_agents, self.agents = self.agents, []


def _hof(mod, monkeypatch, saved):
    monkeypatch.setattr(mod, "_restore", lambda: None)
    monkeypatch.setattr(mod, "save_to_hall_of_fame", lambda cand: saved.append(cand["id"]))
    monkeypatch.setattr(mod, "hof_stats", lambda: (11.0, 19), raising=False)      # absent des modules qui ne le lisent pas
    monkeypatch.setattr(mod, "calculate_life_score", lambda cand: int(cand["id"]) if str(cand["id"]).isdigit() else 0)


def test_speciation_run_seed_sets_and_RESTORES_the_global_speciate_flag_even_on_error(monkeypatch):
    agents = [{"id": str(i), "last_spoken": SILENT} for i in range(6)]
    saved, seen = [], []
    _hof(SP, monkeypatch, saved)
    monkeypatch.setattr(SP, "_world", lambda config, db, transient, add_node: seen.append(SP.persistence.SPECIATE) or _Env(agents, big_kills=3))
    monkeypatch.setattr(SP.persistence, "SPECIATE", False)
    assert SP.run_seed(None, None, speciate=True, seed=1, eras=2, max_ticks=5) == (3.0, 11.0, 19)
    assert seen == [True, True] and SP.persistence.SPECIATE is False and len(saved) == 10
    monkeypatch.setattr(SP, "_world", lambda *a: (_ for _ in ()).throw(RuntimeError("monde")))
    with pytest.raises(RuntimeError):
        SP.run_seed(None, None, speciate=True, seed=1, eras=1, max_ticks=5)
    assert SP.persistence.SPECIATE is False, "l'état global est restauré même sur exception (E5)"
    with pytest.raises(ValueError):
        SP.run_seed(None, None, speciate=True, seed=1, eras=0)


def test_nas_rich_run_seed_averages_preys_over_the_SECOND_half_of_eras(monkeypatch):
    saved, era = [], {"i": 0}
    _hof(NR, monkeypatch, saved)

    def _world(config, db, transient):
        era["i"] += 1
        return _Env([{"id": str(i), "preys_eaten": era["i"]} for i in range(6)])
    monkeypatch.setattr(NR, "_world", _world)
    monkeypatch.setattr(NR.persistence, "SPECIATE", False)
    mean_nodes, max_nodes, preys = NR.run_seed(None, None, transient=True, seed=2, eras=4, max_ticks=5)
    assert (mean_nodes, max_nodes) == (11.0, 19) and preys == pytest.approx(3.5), "ères 3 et 4 seulement (seconde moitié)"
    assert NR.persistence.SPECIATE is False and len(saved) == 20
    with pytest.raises(ValueError):
        NR.run_seed(None, None, transient=True, seed=2, eras=1, max_ticks=0)


def test_reconfirm_047_trains_then_measures_MI_on_four_extra_eras_and_publishes_absence_as_zero(monkeypatch):
    saved, worlds = [], []
    _hof(RC, monkeypatch, saved)
    agents = [{"id": "m", "last_spoken": TOK0}, {"id": "l", "last_spoken": TOK1}]

    def _world(config, db, demand):
        worlds.append(demand)
        return _Env(agents, die_at=2)
    monkeypatch.setattr(RC, "_world", _world)
    monkeypatch.setattr(RC, "_apex_ctx", lambda env, ag: {"m": 1, "l": -1}[ag["id"]])
    mi_real, mi_perm = RC.run_seed(None, None, seed=5, eras=3, max_ticks=5)
    assert len(worlds) == 3 + 4 and all(d == RC.DEMAND for d in worlds) and len(saved) == 3 * 2
    assert mi_real > 0.5 and mi_real > mi_perm
    monkeypatch.setattr(RC, "_apex_ctx", lambda env, ag: 0)
    assert RC.run_seed(None, None, seed=5, eras=1, max_ticks=5) == (0.0, 0.0)     # absence publiée telle quelle (porte 14, légataire)


def test_lang_speciation_run_seed_uses_token_mode_then_restores_size_mode(monkeypatch):
    saved, seen = [], []
    _hof(LS, monkeypatch, saved)
    monkeypatch.setattr(LS, "_world", lambda config, db: seen.append((LS.persistence.SPECIATE, LS.persistence.SPECIATE_MODE)) or _Env([{"id": "1"}, {"id": "2"}]))
    monkeypatch.setattr(LS, "_gain", lambda config, db: 0.42)
    monkeypatch.setattr(LS.persistence, "SPECIATE", False)
    monkeypatch.setattr(LS.persistence, "SPECIATE_MODE", "size")
    assert LS.run_seed(None, None, speciate=True, seed=7, eras=2, max_ticks=5) == 0.42
    assert seen == [(True, "token")] * 2 and (LS.persistence.SPECIATE, LS.persistence.SPECIATE_MODE) == (False, "size")
    with pytest.raises(ValueError):
        LS.run_seed(None, None, speciate=True, seed=7, eras=0)


def test_arm_language_measure_mi_counts_every_agent_with_its_mammoth_context(monkeypatch):
    agents = [{"id": "near", "last_spoken": TOK0}, {"id": "far", "last_spoken": TOK1}]
    seen = []
    monkeypatch.setattr(AL, "_world", lambda config, db, pressure: seen.append(pressure) or _Env(agents, die_at=3))
    monkeypatch.setattr(AL, "_near_mammoth", lambda env, ag: ag["id"] == "near")
    mi, base = AL.measure_mi(None, None, eras=2, max_ticks=10)
    assert seen == [0.0, 0.0], "mesure pure : pression OFF"
    assert mi > 0.5 and mi > base
    with pytest.raises(ValueError):
        AL.measure_mi(None, None, eras=0)
