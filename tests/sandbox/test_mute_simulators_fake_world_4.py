"""P2.56 (b), septième fournée — cinq `run_era` du même patron (Biosphere3D construit dans la fonction, soupe primordiale,
boucle de ticks, promotion des 5 meilleurs, agrégats sur le pool vivants + morts) sous CLASSE de monde factice injectée,
à dose connue, 0 monde réel. Ce qui est jugé : les réglages de régime posés sur le monde (E8 : `scramble_signal`,
`hear_radius`, `craft_level`, `crit_base`, `crit_eras`, `current_era` global, `target_prey_count`, `explore_eps`,
`active_exp_variable`), la borne d'horizon, les agrégats (crafts, tués, proies moyennes, parleurs, taille du pool) et,
pour `evolve_competence`, le classement des génomes retournés avec leur score.

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

import tools.confirm_scramble as CS  # noqa: E402
import tools.curriculum_2d as C2  # noqa: E402
import tools.persistence_test as PT  # noqa: E402
import tools.probe_impasse as PI  # noqa: E402
import tools.evolve_competence as EC  # noqa: E402
from src.agents.mamba_agent import MambaAgent  # noqa: E402

TOK, SILENT = [1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]


def _fake_world(die_at=4, big_kills=2, preys=3, crafts=1, spoken=None):
    made = []

    class _W:
        def __init__(self, config=None):
            self.config = config if config is not None else SimpleNamespace()
            self.agents, self.dead_agents, self.t, self.big_kills = [], [], 0, big_kills
            made.append(self)

        def add_agent(self, agent, energy=80.0):
            i = len(self.agents)
            self.agents.append({"id": i, "age": 0, "energy": energy, "preys_eaten": preys, "spears_crafted": crafts,
                                "model": agent, "last_spoken": (spoken(i) if spoken else SILENT)})

        def step(self):
            self.t += 1
            if self.t >= die_at:
                self.dead_agents, self.agents = self.dead_agents + self.agents, []
    _W.made = made
    return _W


def _soup(n):
    g = MambaAgent().genome
    return lambda num_agents=n, shared_db=None, config=None, **kw: ([g] * num_agents, None)


def _hof(mod, monkeypatch, saved):
    monkeypatch.setattr(mod, "save_to_hall_of_fame", lambda cand: saved.append(cand["id"]))
    monkeypatch.setattr(mod, "calculate_life_score", lambda cand: cand["id"])


def test_confirm_scramble_run_era_applies_scramble_and_hear_radius_to_the_world(monkeypatch):
    W = _fake_world(die_at=3, big_kills=4, preys=2)
    monkeypatch.setattr(CS, "Biosphere3D", W)
    monkeypatch.setattr(CS, "init_primordial_soup", _soup(5))
    saved = []
    _hof(CS, monkeypatch, saved)
    kills, mp = CS.run_era(SimpleNamespace(), None, hear_radius=6, scramble=True, num_agents=5, max_ticks=10)
    w = W.made[-1]
    assert (kills, mp) == (4, 2.0) and w.scramble_signal is True and w.hear_radius == 6 and w.config.target_prey_count == 12
    assert w.config.active_exp_variable == "LANGUAGE" and len(saved) == 5
    with pytest.raises(ValueError):
        CS.run_era(SimpleNamespace(), None, hear_radius=6, scramble=True, max_ticks=0)


def test_curriculum_2d_run_2d_era_sets_both_axes_and_returns_crafts_kills_preys_ticks(monkeypatch):
    W = _fake_world(die_at=4, big_kills=1, preys=5, crafts=2)
    monkeypatch.setattr(C2, "Biosphere3D", W)
    monkeypatch.setattr(C2, "init_primordial_soup", _soup(4))
    _hof(C2, monkeypatch, [])
    out = C2.run_2d_era(SimpleNamespace(), None, target_prey=7, craft_level=2, eps=0.3, crit_base=0.5, num_agents=4, max_ticks=10)
    w = W.made[-1]
    assert out == (8, 1, 5.0, 4)
    assert (w.config.target_prey_count, w.craft_level, w.explore_eps, w.crit_base, w.night_enabled) == (7, 2, 0.3, 0.5, False)


def test_persistence_test_run_era_paces_the_crit_on_the_GLOBAL_era(monkeypatch):
    W = _fake_world(die_at=2, preys=1, crafts=0)
    monkeypatch.setattr(PT, "Biosphere3D", W)
    monkeypatch.setattr(PT, "init_primordial_soup", _soup(3))
    _hof(PT, monkeypatch, [])
    out = PT.run_era(SimpleNamespace(), None, global_era=17, target_prey=5, crit_base=0.7, crit_eras=9, num_agents=3, max_ticks=10)
    w = W.made[-1]
    assert out == (0, 2, 1.0, 2) and w.current_era == 17 and (w.crit_base, w.crit_eras, w.config.target_prey_count) == (0.7, 9, 5)


def test_probe_impasse_run_era_counts_speakers_and_pool_size(monkeypatch):
    W = _fake_world(die_at=3, big_kills=0, preys=2, crafts=1, spoken=lambda i: TOK if i % 2 == 0 else SILENT)
    monkeypatch.setattr(PI, "Biosphere3D", W)
    monkeypatch.setattr(PI, "init_primordial_soup", _soup(6))
    _hof(PI, monkeypatch, [])
    crafts, kills, mp, speakers, n_pool = PI.run_era(SimpleNamespace(), None, target_prey=10, num_agents=6, max_ticks=10)
    assert (crafts, kills, mp, speakers, n_pool) == (6, 0, 2.0, 3, 6)
    assert W.made[-1].config.active_exp_variable == "LANGUAGE"


def test_evolve_competence_run_era_returns_the_ranked_genomes_with_their_scores(monkeypatch):
    W = _fake_world(die_at=5, big_kills=3, preys=2)
    monkeypatch.setattr(EC, "Biosphere3D", W)
    monkeypatch.setattr(EC, "calculate_life_score", lambda cand: float(cand["id"]))
    genomes = [MambaAgent().genome for _ in range(7)]
    scored, info = EC.run_era(SimpleNamespace(), genomes, max_ticks=20)
    assert info == {"ticks": 5, "eaten": 14, "mam": 3, "score": 6.0}
    import numpy as np
    assert [s for s, g in scored] == [6.0, 5.0, 4.0, 3.0, 2.0]
    assert all(np.array_equal(g.W, genomes[int(s)].W) for s, g in scored), "le genome rendu est celui de l'agent classe (from_genome copie)"
    with pytest.raises(ValueError):
        EC.run_era(SimpleNamespace(), [], max_ticks=20)
