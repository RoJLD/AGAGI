"""P2.56 (b), sixième fournée — cinq SIMULATEURS muets qui construisent leur monde EUX-MÊMES (`Biosphere3D(config)`,
`FamineWorld`, `AgriculturalWorld`, `WORLDS[clé]`) reçoivent une CLASSE de monde factice injectée dans leur module, à dose
connue, 0 monde réel : cohorte ajoutée par `add_agent`, `step()` qui compte les ticks et tue la cohorte à un tick connu
(les âges publiés sont alors CONNUS), compteurs (`big_kills`, `preys_eaten`, `spears_crafted`, items, saison) fixés.
Ce qui est jugé : la boucle d'ères et de ticks, les réglages de régime posés sur le monde (E8 : ce que le runner dit
appliquer est appliqué), l'injection du substrat, les agrégats (médiane de médianes, moyenne de proies, crafts) et les
gardes d'anomalie (cohorte introuvable → lève, jamais une survie nulle).

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

import tools.comm_lever as CL  # noqa: E402
import tools.curriculum_world as CW  # noqa: E402
import tools.substrate_world_ab as SW  # noqa: E402
import tools.famine_harshness_probe as FH  # noqa: E402
import tools.agricultural_demand_probe as AG  # noqa: E402
from src.agents.mamba_agent import MambaAgent  # noqa: E402


def _fake_world(die_at=4, big_kills=2, preys=3, crafts=1, extra=None):
    """Fabrique une CLASSE de monde factice (instanciée par le runner) dont les instances sont journalisées."""
    made = []

    class _W:
        def __init__(self, config=None):
            self.config = config if config is not None else SimpleNamespace()
            self.agents, self.dead_agents, self.items, self.t = [], [], [], 0
            self.big_kills, self.season = big_kills, "ete"
            for k, v in (extra or {}).items():
                setattr(self, k, v)
            made.append(self)

        def add_agent(self, agent, energy=80.0):
            self.agents.append({"id": len(self.agents), "age": 0, "energy": energy, "preys_eaten": preys,
                                "spears_crafted": crafts, "reserve": 0.0, "_agent": agent})

        def step(self):
            self.t += 1
            for a in self.agents:
                a["age"] += 1
            if self.t >= die_at:
                self.dead_agents, self.agents = self.dead_agents + self.agents, []
    _W.made = made
    return _W


def _soup(n):
    g = MambaAgent().genome
    return lambda num_agents=n, shared_db=None, config=None, **kw: ([g] * num_agents, None)


def test_comm_lever_run_era_applies_the_lever_and_aggregates_crafts_kills_and_preys(monkeypatch):
    W = _fake_world(die_at=3, big_kills=5, preys=2, crafts=1)
    monkeypatch.setattr(CL, "Biosphere3D", W)
    monkeypatch.setattr(CL, "init_primordial_soup", _soup(6))
    saved = []
    monkeypatch.setattr(CL, "save_to_hall_of_fame", lambda cand: saved.append(cand["id"]))
    monkeypatch.setattr(CL, "calculate_life_score", lambda cand: cand["id"])
    crafts, kills, mp = CL.run_era(SimpleNamespace(), None, hear_radius=7, target_prey=9, num_agents=6, max_ticks=10)
    w = W.made[-1]
    assert (crafts, kills, mp) == (6, 5, 2.0) and w.t == 3 and len(w.dead_agents) == 6
    assert w.hear_radius == 7 and w.config.target_prey_count == 9 and w.night_enabled is False and w.config.active_exp_variable == "LANGUAGE"
    assert saved == [5, 4, 3, 2, 1], "les 5 meilleurs par life_score"
    with pytest.raises(ValueError):
        CL.run_era(SimpleNamespace(), None, hear_radius=7, num_agents=0)


def test_curriculum_world_run_world_era_returns_mean_preys_and_the_tick_count(monkeypatch):
    W = _fake_world(die_at=5, preys=4)
    monkeypatch.setattr(CW, "Biosphere3D", W)
    monkeypatch.setattr(CW, "init_primordial_soup", _soup(3))
    monkeypatch.setattr(CW, "save_to_hall_of_fame", lambda cand: None)
    monkeypatch.setattr(CW, "calculate_life_score", lambda cand: cand["id"])
    mean_prey, t = CW.run_world_era(SimpleNamespace(), None, target_prey=11, num_agents=3, max_ticks=20)
    assert (mean_prey, t) == (4.0, 5) and W.made[-1].config.target_prey_count == 11
    mean_prey, t = CW.run_world_era(SimpleNamespace(), None, target_prey=11, num_agents=3, max_ticks=2)
    assert t == 2, "l'horizon borne la boucle avant la mort de la cohorte"


def test_measure_survival_injects_the_substrate_and_returns_one_median_per_eval_era(monkeypatch):
    import tools.s2_demand as S2
    W = _fake_world(die_at=7)
    monkeypatch.setitem(S2.WORLDS, "factice", W)
    med = SW.measure_survival("factice", seed=3, backend_cls="SUBSTRAT", genome=None, k_eval=3, num_agents=4, max_ticks=50)
    assert med == [7.0, 7.0, 7.0] and len(W.made) == 3, "une mediane PAR ere d'eval (l'appelant agrege)"
    assert all(w.batch_model_cls == "SUBSTRAT" and w.benchmark_mode is True and w.night_enabled is False and w.current_era == 10_000 for w in W.made)
    monkeypatch.setitem(S2.WORLDS, "vide", _fake_world(die_at=10 ** 9))

    class _Sans(W):
        def add_agent(self, agent, energy=80.0):
            pass                                            # la cohorte n'est jamais ajoutée : anomalie de harnais
    monkeypatch.setitem(S2.WORLDS, "sans", _Sans)
    with pytest.raises(ValueError, match="INTROUVABLE"):
        SW.measure_survival("sans", seed=3, backend_cls="SUBSTRAT", k_eval=1, num_agents=2, max_ticks=5)


def test_famine_measure_regime_sets_the_harsh_regime_and_injects_the_reserve(monkeypatch):
    W = _fake_world(die_at=6)
    monkeypatch.setattr(FH, "FamineWorld", W)
    genome = MambaAgent().genome
    med = FH.measure_regime(genome, cache=True, cyc_ab=8, cyc_fam=12, inject_reserve=5.0, seed=1, n_eras=2, n_agents=3, max_ticks=30)
    assert med == 6.0 and len(W.made) == 2
    w = W.made[-1]
    assert w.cache_enabled is True and (w.cycle_abundance, w.cycle_famine) == (8, 12) and w.benchmark_mode is True
    assert all(a["reserve"] == 5.0 for a in w.dead_agents), "la réserve injectée est posée sur CHAQUE agent (plafonnée à RESERVE_CAP)"
    assert w.config.base_metabolism == FH.SWEET_METAB and w.config.forage_payoff == FH.SWEET_PAYOFF, "régime sweet spot (E8)"
    with pytest.raises(ValueError):
        FH.measure_regime(genome, cache=True, cyc_ab=8, cyc_fam=12, n_eras=0)


def test_run_agricultural_captures_season_items_and_cohort_per_tick(monkeypatch):
    W = _fake_world(die_at=3)
    monkeypatch.setattr(AG, "AgriculturalWorld", W)
    monkeypatch.setattr(AG, "_ITEM_KEYS", ("Seed", "Wheat"), raising=False)

    class _WithItems(W):
        def step(self):
            super().step()
            self.items = [{"type": "Seed"}] * self.t + [{"type": "Autre"}]
            self.season = "hiver" if self.t >= 2 else "ete"
    monkeypatch.setattr(AG, "AgriculturalWorld", _WithItems)
    traj = AG.run_agricultural(None, seed=4, num_agents=5, max_ticks=10)
    assert [r["t"] for r in traj] == [1, 2, 3] and [r["n_agents"] for r in traj] == [5, 5, 0]
    assert [r["season"] for r in traj] == ["ete", "hiver", "hiver"] and [r["Seed"] for r in traj] == [1, 2, 3]
    assert all("Autre" not in r for r in traj), "seuls les items déclarés sont comptés"
    with pytest.raises(ValueError):
        AG.run_agricultural(None, seed=4, num_agents=0)
