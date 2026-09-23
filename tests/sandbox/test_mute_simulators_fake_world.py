"""P2.56 (b), quatrième fournée — quatre SIMULATEURS muets reçoivent un MONDE FACTICE à dose connue, 0 monde réel :
`_world` (le maillon qui construit Biosphere3D + soupe primordiale) est remplacé par une fabrique d'environnements
minimaux (agents = dicts, `step()` qui compte les ticks et vide la cohorte à un tick connu), et les lecteurs de contexte
(`_apex_ctx`, `_adjacent_ref`) rendent des contextes CONNUS. Ce qui est jugé : la boucle d'ères, la collecte par tick et
par agent, les agrégats (information mutuelle contre sa permutation, part de silence, paires token/référent, tués par
ère) et les valeurs d'absence PUBLIÉES telles qu'elles sont (0,0 / 1,0 : des défauts légataires de porte 14, documentés
ici, jamais corrigés en silence).

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

import tools.lewis_world as LW  # noqa: E402
import tools.speaker_incentive as SI  # noqa: E402
import tools.lexicon as LX  # noqa: E402
import tools.nas_memory as NM  # noqa: E402


class _Env:
    """Monde factice : `n` agents porteurs de `last_spoken`, vidés au tick `die_at` ; `big_kills` fixe."""

    def __init__(self, spoken, die_at=3, big_kills=0):
        self.agents = [dict(a) for a in spoken]
        self.dead_agents = []
        self.t = 0
        self.die_at = die_at
        self.big_kills = big_kills

    def step(self):
        self.t += 1
        if self.t >= self.die_at:
            self.dead_agents, self.agents = self.agents, []


TOK0, TOK1, SILENT = [1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]


def test_lewis_measure_mi_reads_a_perfect_code_near_apex_and_ignores_agents_far_from_it(monkeypatch):
    # 2 parleurs parfaits (Mammouth -> tok 0, Leurre -> tok 1), 1 agent loin de tout apex (ctx 0 : ignoré)
    agents = [{"id": "m", "last_spoken": TOK0}, {"id": "l", "last_spoken": TOK1}, {"id": "x", "last_spoken": TOK1}]
    monkeypatch.setattr(LW, "_world", lambda config, db: _Env(agents, die_at=3))
    monkeypatch.setattr(LW, "_apex_ctx", lambda env, ag: {"m": 1, "l": -1, "x": 0}[ag["id"]])
    mi, base, n = LW.measure_mi(None, None, eras=2, max_ticks=10)
    assert n == 2 * 2 * 2, "2 ères x 2 ticks vivants x 2 agents près d'un apex ; l'agent loin n'est pas compté"
    assert mi > 0.5 and mi > base, "un code parfait porte de l'information, sa permutation non"
    monkeypatch.setattr(LW, "_apex_ctx", lambda env, ag: 0)
    assert LW.measure_mi(None, None, eras=1, max_ticks=10) == (0.0, 0.0, 0), "absence publiée telle quelle (défaut légataire porte 14)"
    with pytest.raises(ValueError):
        LW.measure_mi(None, None, eras=0)


def test_speaker_incentive_measure_reads_silence_and_information_from_known_speakers(monkeypatch):
    agents = [{"id": "m", "last_spoken": TOK0}, {"id": "l", "last_spoken": TOK1}, {"id": "s", "last_spoken": SILENT}]
    seen = []
    monkeypatch.setattr(SI, "_world", lambda config, db, prime: seen.append(prime) or _Env(agents, die_at=2))
    monkeypatch.setattr(SI, "_apex_ctx", lambda env, ag: {"m": 1, "l": -1, "s": 1}[ag["id"]])
    mi, base, silent = SI.measure(None, None, eras=3, max_ticks=10)
    assert seen == [0.0] * 3, "la mesure lit les politiques évoluées : prime OFF à chaque ère"
    assert silent == pytest.approx(1 / 3) and mi > base
    monkeypatch.setattr(SI, "_apex_ctx", lambda env, ag: 0)
    assert SI.measure(None, None, eras=1, max_ticks=10) == (0.0, 0.0, 1.0)      # absence publiée telle quelle
    with pytest.raises(ValueError):
        SI.measure(None, None, eras=1, max_ticks=0)


def test_lexicon_measure_collects_token_referent_pairs_only_next_to_a_referent(monkeypatch):
    agents = [{"id": "a", "last_spoken": TOK0}, {"id": "b", "last_spoken": SILENT}, {"id": "c", "last_spoken": TOK1}]
    monkeypatch.setattr(LX, "_world", lambda config, db: _Env(agents, die_at=2))
    monkeypatch.setattr(LX, "_adjacent_ref", lambda env, ag: {"a": "Mammouth", "b": "Mammouth", "c": None}[ag["id"]])
    pairs = LX.measure(None, None, eras=2, max_ticks=10)
    assert pairs == [(0, "Mammouth"), (4, "Mammouth")] * 2, "token 4 = silence ; c (aucun référent adjacent) n'est pas collecté"
    with pytest.raises(ValueError):
        LX.measure(None, None, eras=0)


def test_nas_memory_run_seed_promotes_five_per_era_and_averages_big_kills(monkeypatch):
    agents = [{"id": str(i), "last_spoken": SILENT} for i in range(7)]
    saved, restored = [], []
    monkeypatch.setattr(NM, "_world", lambda config, db, transient, add_node: _Env(agents, die_at=2, big_kills=2))
    monkeypatch.setattr(NM, "_restore", lambda: restored.append(True))
    monkeypatch.setattr(NM, "save_to_hall_of_fame", lambda cand: saved.append(cand["id"]))
    monkeypatch.setattr(NM, "hof_stats", lambda: (12.5, 20))
    monkeypatch.setattr(NM, "calculate_life_score", lambda cand: int(cand["id"]))
    mean_nodes, max_nodes, mammo = NM.run_seed(None, None, transient=True, seed=3, eras=2, max_ticks=10)
    assert (mean_nodes, max_nodes, mammo) == (12.5, 20, 2.0)
    assert restored == [True] and len(saved) == 10 and saved[:5] == ["6", "5", "4", "3", "2"], "les 5 meilleurs par ère, triés par life_score"
    with pytest.raises(ValueError):
        NM.run_seed(None, None, transient=True, seed=3, eras=0)
