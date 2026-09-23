"""P2.56 (b), huitième fournée — les six derniers RUNNERS DE MONDE muets (`Biosphere3D(config)` construit dans la
fonction) sous CLASSE de monde factice injectée, à dose connue, 0 monde réel. Les maillons coûteux ou dépendants du
monde réel sont remplacés par des ENREGISTREURS : `_setup_grab_training` (spawn d'objets), `_setup3` (monde de Lewis à
3 référents), `new_head` / `train_population` (co-évolution par gradient : 24 têtes × 5000 pas), `seed_at`. Ce qui est
jugé : les réglages de régime POSÉS sur le monde (E8 : `crit_base`, `crit_eras`, `group_reward_eras`, `current_era`,
`craft_level`, `use_ref_head`, `decode_act`, `explore_eps`), l'appariement des seeds (base + seed transmis), la
préparation conditionnelle du monde (`training`), les agrégats (proies moyennes par ère, crafts, survivants, pool
MAP-Elites avec ses stats, information mutuelle contre permutée), ce qui est COMPTÉ ou IGNORÉ (les tués de mammouth
des seuls SURVIVANTS dans `func_benefit` ; un agent sans génome hors du pool ; un agent sans apex perçu hors des
tokens) et les valeurs d'absence publiées telles quelles (`(0.0, n)` sous 5 tokens : porte 14 légataire).

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

import tools.ablation_multi as AM  # noqa: E402
import tools.curriculum_developmental as CD  # noqa: E402
import tools.curriculum_grab as CG  # noqa: E402
import tools.func_benefit as FB  # noqa: E402
import tools.map_elites_compare as ME  # noqa: E402
import tools.wire_ref_head as WR  # noqa: E402
from src.agents.mamba_agent import MambaAgent  # noqa: E402

TOK0, TOK1, SILENT = [1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]


def _fake_world(die_at=4, big_kills=2, preys=3, crafts=1, mammoth=0, leurre_hits=0, spoken=None):
    """Fabrique une CLASSE de monde factice (instanciée par le runner) dont les instances sont journalisées."""
    made = []

    class _W:
        def __init__(self, config=None):
            self.config = config if config is not None else SimpleNamespace()
            self.agents, self.dead_agents, self.items, self.t = [], [], [], 0
            self.big_kills, self.leurre_hits = big_kills, leurre_hits
            made.append(self)

        def add_agent(self, agent, x=None, y=None, energy=80.0):
            i = len(self.agents) + len(self.dead_agents)
            self.agents.append({"id": i, "age": 0, "energy": energy, "preys_eaten": preys, "spears_crafted": crafts,
                                "mammoth_kills": mammoth, "model": agent, "x": 0, "y": 0,
                                "last_spoken": (spoken(i) if spoken else SILENT)})

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


def _hof(mod, monkeypatch, saved):
    monkeypatch.setattr(mod, "save_to_hall_of_fame", lambda cand: saved.append(cand["id"]))
    monkeypatch.setattr(mod, "calculate_life_score", lambda cand: cand["id"])


def _heads(mod, monkeypatch, trained):
    monkeypatch.setattr(mod, "new_head", lambda M, V, H, rng: ("tete", M, V, H))
    monkeypatch.setattr(mod, "train_population", lambda heads, steps, seed: trained.append((len(heads), steps, seed)))


def test_ablation_multi_run_condition_applies_the_mechanism_once_per_era_at_the_given_crit(monkeypatch):
    W = _fake_world(die_at=3, big_kills=2, preys=3)
    monkeypatch.setattr(AM, "Biosphere3D", W)
    monkeypatch.setattr(AM, "init_primordial_soup", _soup(4))
    applied = []
    out = AM.run_condition(SimpleNamespace(), None, applied.append, crit_base=0.0, n_eras=2, num_agents=4, max_ticks=10)
    assert out == (3.0, 2.0) and applied == W.made and len(applied) == 2, "le mecanisme est applique a CHAQUE ere, sur le monde de l'ere"
    w = W.made[-1]
    assert (w.crit_base, w.config.target_prey_count, w.explore_eps, w.craft_level, w.night_enabled, w.current_era) == (0.0, 12, 0.2, 0, False, 1)
    with pytest.raises(ValueError):
        AM.run_condition(SimpleNamespace(), None, applied.append, crit_base=0.6, n_eras=0)


def test_curriculum_developmental_run_era_pilots_every_weaning_on_the_GLOBAL_era(monkeypatch):
    W = _fake_world(die_at=4, big_kills=1, preys=2, crafts=1)
    monkeypatch.setattr(CD, "Biosphere3D", W)
    monkeypatch.setattr(CD, "init_primordial_soup", _soup(3))
    saved = []
    _hof(CD, monkeypatch, saved)
    out = CD.run_era(SimpleNamespace(), None, global_era=9, rarity=11, crit_eras=20, group_eras=15, crit_base=0.4, eps=0.1,
                     num_agents=3, max_ticks=10)
    assert out == (3, 1, 2.0, 4)
    w = W.made[-1]
    assert (w.config.target_prey_count, w.crit_eras, w.group_reward_eras, w.current_era) == (11, 20, 15, 9), "les trois sevrages lisent l'ere GLOBALE"
    assert (w.crit_base, w.explore_eps, w.craft_level, w.night_enabled) == (0.4, 0.1, 0, False)
    assert saved == [2, 1, 0], "les 5 meilleurs par life_score (ici 3 agents, tous promus, tries)"
    with pytest.raises(ValueError):
        CD.run_era(SimpleNamespace(), None, global_era=9, rarity=11, crit_eras=20, group_eras=15, num_agents=0)


def test_curriculum_grab_run_one_era_prepares_the_world_ONLY_in_training(monkeypatch):
    W = _fake_world(die_at=10 ** 9, crafts=2)
    monkeypatch.setattr(CG, "Biosphere3D", W)
    monkeypatch.setattr(CG, "init_primordial_soup", _soup(5))
    _hof(CG, monkeypatch, [])
    rec = []
    monkeypatch.setattr(CG, "_setup_grab_training", lambda env, eps, n_items, keep_prey: rec.append((env, eps, n_items, keep_prey)))
    out = CG.run_one_era(SimpleNamespace(), None, training=True, eps=0.25, n_items=7, keep_prey=True, craft_level=2, num_agents=5, max_ticks=6)
    assert out == (10, 6, 5), "crafts sommes, l'horizon borne la boucle (cohorte immortelle), 5 survivants"
    assert rec == [(W.made[-1], 0.25, 7, True)] and W.made[-1].craft_level == 2 and W.made[-1].current_era == 1
    assert CG.run_one_era(SimpleNamespace(), None, training=False, num_agents=5, max_ticks=6) == (10, 6, 5)
    assert len(rec) == 1, "hors entrainement, le monde n'est PAS prepare"
    with pytest.raises(ValueError):
        CG.run_one_era(SimpleNamespace(), None, training=True, max_ticks=0)


def test_func_benefit_run_seed_pairs_the_seed_and_counts_mammoths_of_SURVIVORS_only(monkeypatch):
    W = _fake_world(die_at=10 ** 9, mammoth=2, leurre_hits=4)

    class _OneDies(W):
        def step(self):
            super().step()
            if self.t == 2:                                  # l'agent 0 meurt au tick 2 : ses tues sortent du compte
                self.dead_agents.append(self.agents.pop(0))
    monkeypatch.setattr(FB, "Biosphere3D", _OneDies)
    monkeypatch.setattr(FB, "init_primordial_soup", _soup(3))
    seeds, setup, trained = [], [], []
    monkeypatch.setattr(FB, "seed_at", lambda base, seed: seeds.append((base, seed)))
    monkeypatch.setattr(FB, "_setup3", setup.append)
    _heads(FB, monkeypatch, trained)
    out = FB.run_seed(SimpleNamespace(), None, seed=5, use_head=True, decode_act=False, num_agents=3, max_ticks=8, base=100)
    assert out == {"mammoth": 4, "leurre": 4, "survivors": 2, "energy": 80.0, "n0": 3}, "2 survivants x 2 tues ; le mort ne compte pas"
    w = W.made[-1]
    assert seeds == [(100, 5)] and setup == [w] and trained == [(3, 5000, 5)], "appariement base + seed ; une tete par genome, entrainees ensemble"
    assert (w.use_ref_head, w.decode_act, w.current_era) == (True, False, 1)
    assert all(a["model"].ref_head == ("tete", 3, 4, 12) for a in w.agents + w.dead_agents), "chaque agent porte SA tete"
    with pytest.raises(ValueError):
        FB.run_seed(SimpleNamespace(), None, seed=5, use_head=True, decode_act=True, num_agents=0)


def test_map_elites_run_era_pool_returns_the_whole_pool_with_stats_and_skips_genome_less_agents(monkeypatch):
    W = _fake_world(die_at=3, preys=1, crafts=0, mammoth=1)
    monkeypatch.setattr(ME, "Biosphere3D", W)
    monkeypatch.setattr(ME, "calculate_life_score", lambda ag: ag["id"])
    genomes = [MambaAgent().genome for _ in range(4)]
    pool, info = ME.run_era_pool(SimpleNamespace(), genomes, max_ticks=10)
    assert info == {"score": 3.0, "ticks": 3.0} and [p[0] for p in pool] == [0.0, 1.0, 2.0, 3.0]
    assert all(p[2] == {"num_nodes": p[1].num_nodes, "preys_eaten": 1, "spears_crafted": 0, "mammoth_kills": 1} for p in pool)

    class _Orphan(W):
        def add_agent(self, agent, **kw):
            super().add_agent(agent, **kw)
            if len(self.agents) == 1:
                self.agents.append({"id": 99, "age": 0, "energy": 80.0})     # ni model ni genome
    monkeypatch.setattr(ME, "Biosphere3D", _Orphan)
    pool, info = ME.run_era_pool(SimpleNamespace(), genomes[:2], max_ticks=10)
    assert [p[0] for p in pool] == [0.0, 2.0] and info["score"] == 2.0, "un agent sans genome (id 99) est IGNORE du pool et de son meilleur score"
    with pytest.raises(ValueError):
        ME.run_era_pool(SimpleNamespace(), [], max_ticks=10)


def test_wire_ref_head_run_seed_reads_MI_of_speakers_near_an_apex_and_publishes_absence_as_zero(monkeypatch):
    W = _fake_world(die_at=10 ** 9, spoken=lambda i: TOK0 if i == 0 else TOK1 if i == 1 else SILENT)

    class _Apex(W):
        def _apex_idx(self, ag):
            return {0: 0, 1: 1}.get(ag["id"])                # l'agent 2 ne percoit aucun apex : hors des tokens
    monkeypatch.setattr(WR, "Biosphere3D", _Apex)
    monkeypatch.setattr(WR, "init_primordial_soup", _soup(3))
    setup, trained = [], []
    monkeypatch.setattr(WR, "_setup3", setup.append)
    _heads(WR, monkeypatch, trained)
    np.random.seed(0)                                         # la base permutee tire dans le RNG global
    gain, n = WR.run_seed(SimpleNamespace(), None, seed=2, use_head=False, num_agents=3, max_ticks=20)
    assert n == 40 and gain > 0.7, "2 parleurs parfaits x 20 ticks ; MI - base permutee proche de 1 bit"
    assert trained == [] and setup == [W.made[-1]] and W.made[-1].use_ref_head is False
    gain, n = WR.run_seed(SimpleNamespace(), None, seed=2, use_head=True, num_agents=3, max_ticks=2)
    assert (gain, n) == (0.0, 4) and trained == [(3, 5000, 2)], "sous 5 tokens : absence publiee 0.0 (porte 14 legataire) ; tetes entrainees si use_head"
    with pytest.raises(ValueError):
        WR.run_seed(SimpleNamespace(), None, seed=2, use_head=False, max_ticks=0)
