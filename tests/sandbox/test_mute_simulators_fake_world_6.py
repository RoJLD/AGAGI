"""P2.56 (b), neuvième fournée — les SIX dernières muettes du dépôt, 0 monde réel : les trois sondes d'`evo_memory_inworld`
sous classe `MemoryDemandBiosphere` factice (rencontre contrôlée, navigation in-contexte, logit d'attaque avec un
`MambaBatchModel.forward` remplacé qui rend des logits CONNUS), `run_retention_map` en ORCHESTRATEUR injecté (ses quatre
maillons remplacés, son chemin de sortie en dur capturé par un `chdir` temporaire) et les deux fonctions PURES
(`run_bptt_act`, `run_refgame`) appelées à petite taille sur des réponses connues. Ce qui est jugé : le SIGNE de chaque
verdict sur une dose connue, ce qui compte comme « engagé » (la mort en attaquant), le régime posé (E8), la restauration
de l'état global (forward, logger : E5), les étiquettes de seuil (±0,02), et les absences publiées telles quelles
(`nan`, `None` sans fichier).

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import json
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

import tools.evo_memory_inworld as EM  # noqa: E402
import tools.retention_map as RM  # noqa: E402
import tools.arm_act_grad as AG  # noqa: E402
import tools.refgame as RG  # noqa: E402
from src.agents.mamba_agent import MambaAgent, MambaBatchModel  # noqa: E402


def _mem_world(positions=((0, 0),), on_step=None):
    """CLASSE de monde factice pour les sondes mémoire : agents posés à des positions CONNUES, `step()` délégué."""
    made = []

    class _W:
        def __init__(self, cfg):
            self.config, self.size, self.t = cfg, 10, 0
            self.agents, self.dead_agents, self.preys = [], [], []
            self.big_kills, self.leurre_hits = 0, 0
            made.append(self)

        def add_agent(self, agent, x=None, y=None, energy=80.0):
            i = len(self.agents)
            px, py = positions[i % len(positions)]
            self.agents.append({"id": i, "x": x if x is not None else px, "y": y if y is not None else py,
                                "energy": energy, "model": agent})

        def step(self):
            self.t += 1
            if on_step:
                on_step(self)
    _W.made = made
    return _W


def _cfg():
    return SimpleNamespace(preys={"Mammouth": SimpleNamespace(moves_per_tick=0.5, damage=10.0),
                                  "Leurre": SimpleNamespace(moves_per_tick=0.5, damage=50.0)})


def _approach_mammoth_only(w):
    p = w.preys[0]
    for ag in w.agents:
        if p["type"] == "Mammouth" and ag["x"] < p["x"]:
            ag["x"] += 1                                     # s'approche du Mammouth ; reste devant le Leurre


def test_probe_memory_discrimination_reads_approach_of_mammoth_and_death_as_engagement(monkeypatch):
    W = _mem_world(on_step=_approach_mammoth_only)
    monkeypatch.setattr(EM, "MemoryDemandBiosphere", W)
    monkeypatch.setattr(EM, "_cfg", _cfg)
    genome = MambaAgent().genome
    out = EM.probe_memory_discrimination(genome, "memory", seed=1, n_trials=4)
    assert out == {"disc": 1.0, "engage_mammouth": 1.0, "engage_leurre": 0.0}
    w = W.made[-1]
    assert (w.hide_on_approach, w.ablate_memory, w.benchmark_mode, w.night_enabled) == (True, False, True, False)
    assert w.config.preys["Mammouth"].moves_per_tick == 0.0 and w.config.preys["Leurre"].moves_per_tick == 0.0, "meme mobilite (E8)"
    assert EM.probe_memory_discrimination(genome, "ablate", seed=1, n_trials=2)["disc"] == 1.0 and W.made[-1].ablate_memory is True
    assert W.made[-1].hide_on_approach is True

    def _dies_on_leurre(w):
        if w.preys[0]["type"] == "Leurre":
            w.agents = []                                    # mort en attaquant (riposte) : compte comme ENGAGE
        else:
            _approach_mammoth_only(w)
    monkeypatch.setattr(EM, "MemoryDemandBiosphere", _mem_world(on_step=_dies_on_leurre))
    out = EM.probe_memory_discrimination(genome, "visible", seed=1, n_trials=3)
    assert out == {"disc": 0.0, "engage_mammouth": 1.0, "engage_leurre": 1.0}
    with pytest.raises(ValueError):
        EM.probe_memory_discrimination(genome, "memory", seed=1, n_trials=0)


def _lewis(env, n_each=5):
    env.preys = [{"x": 5, "y": 5, "type": "Mammouth"}, {"x": 5, "y": 0, "type": "Leurre"}]
    env.lewis_n_each = n_each


def _nav_step(w):
    for ag in w.agents:
        if ag["id"] == 0:
            ag["x"] += 1                                     # (3,5) -> (4,5) : s'approche du Mammouth
        else:
            ag["y"] += 1                                     # (5,2) -> (5,3) : s'eloigne du Leurre


def test_probe_navigation_incontext_reads_intent_against_the_apex_position_at_tick_start(monkeypatch):
    W = _mem_world(positions=((3, 5), (5, 2)), on_step=_nav_step)
    monkeypatch.setattr(EM, "MemoryDemandBiosphere", W)
    monkeypatch.setattr(EM, "_cfg", _cfg)
    monkeypatch.setattr(EM, "_setup_lewis", _lewis)
    genome = MambaAgent().genome
    out = EM.probe_navigation_incontext(genome, "memory", seed=3, num_agents=2, ticks=1, zone=3, apex_speed=0.25)
    assert out == {"disc": 1.0, "approach_mam": 1.0, "approach_leu": 0.0, "n_mam": 1, "n_leu": 1, "moved_frac": 1.0}
    w = W.made[-1]
    assert (w.current_era, w.benchmark_mode, w.night_enabled, w.lewis_n_each) == (10_000, True, False, EM.N_APEX)
    assert all(w.config.preys[t].moves_per_tick == 0.25 for t in ("Mammouth", "Leurre")), "les DEUX types a la meme vitesse (E8)"

    def _leurre_kills(w):
        w.agents = [ag for ag in w.agents if ag["id"] == 0]  # l'agent 1 meurt en attaquant : ENGAGE
        _nav_step(w)
    monkeypatch.setattr(EM, "MemoryDemandBiosphere", _mem_world(positions=((3, 5), (5, 2)), on_step=_leurre_kills))
    out = EM.probe_navigation_incontext(genome, "visible", seed=3, num_agents=2, ticks=1)
    assert (out["disc"], out["approach_leu"], out["n_leu"]) == (0.0, 1.0, 1)
    with pytest.raises(ValueError):
        EM.probe_navigation_incontext(genome, "memory", seed=3, num_agents=0)


def test_probe_attack_logit_reads_the_logit_toward_each_apex_from_captured_forward_and_restores_it(monkeypatch):
    LOGITS = np.array([[0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0],      # agent 0 : direction 3 (droite) vers le Mammouth
                       [0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])     # agent 1 : direction 0 (haut) vers le Leurre
    stub = lambda self, *a, **k: (LOGITS, None)  # noqa: E731
    monkeypatch.setattr(MambaBatchModel, "forward", stub)
    W = _mem_world(positions=((3, 5), (5, 2)), on_step=lambda w: MambaBatchModel.forward(None))
    monkeypatch.setattr(EM, "MemoryDemandBiosphere", W)
    monkeypatch.setattr(EM, "_cfg", _cfg)
    monkeypatch.setattr(EM, "_setup_lewis", _lewis)
    genome = MambaAgent().genome
    out = EM.probe_attack_logit(genome, "memory", seed=4, num_agents=2, ticks=3, zone=2)
    assert out == {"disc": 1.5, "logit_mam": 2.0, "logit_leu": 0.5, "n_mam": 3, "n_leu": 3, "logit_std": 0.75}
    assert MambaBatchModel.forward is stub, "le forward d'origine est RESTAURE apres la sonde (E5)"
    monkeypatch.setattr(EM, "MemoryDemandBiosphere", _mem_world(positions=((3, 5), (5, 2))))   # step sans forward
    out = EM.probe_attack_logit(genome, "memory", seed=4, num_agents=2, ticks=2)
    assert np.isnan(out["disc"]) and (out["n_mam"], out["n_leu"], out["logit_std"]) == (0, 0, 0.0), "absence publiee : nan, std 0.0"
    with pytest.raises(ValueError):
        EM.probe_attack_logit(genome, "memory", seed=4, ticks=0)


def _summary():
    return {"forgetting": {"a": {"mastery": 1.0, "final": 0.8, "forgetting": 0.2, "retention_ratio": 0.8},
                           "b": {"mastery": 0.9, "final": 0.9, "forgetting": 0.0, "retention_ratio": 1.0},
                           "c": {"mastery": 0.5, "final": 0.6, "forgetting": -0.1, "retention_ratio": 1.2}},
            "mean_forgetting": 0.0333}


def test_run_retention_map_orchestrates_curriculum_then_retention_and_writes_the_map_under_cwd(monkeypatch, tmp_path, capsys):
    calls = {}
    monkeypatch.chdir(tmp_path)                              # le chemin de sortie est EN DUR : capture sous un cwd temporaire
    monkeypatch.setattr(RM, "async_logger", SimpleNamespace(start=lambda: calls.setdefault("start", 0) or calls.__setitem__("start", calls.get("start", 0) + 1),
                                                            stop=lambda: calls.__setitem__("stop", calls.get("stop", 0) + 1)))
    monkeypatch.setattr(RM, "_acquire_shared_db", lambda: "db")
    monkeypatch.setattr(RM, "run_curriculum", lambda ladder, **kw: calls.__setitem__("curr", (ladder, kw)) or
                        [{"world": "a", "champion_promoted": "cA"}, {"world": "b", "champion_promoted": "cB"}])
    monkeypatch.setattr(RM, "make_run_era_fn", lambda db, cfg, **kw: calls.__setitem__("era", (db, type(cfg).__name__, kw)) or "fn")
    monkeypatch.setattr(RM, "summarize_retention", lambda fn, ladder, champs, keep: calls.__setitem__("ret", (fn, ladder, champs, keep)) or _summary())
    monkeypatch.setattr(RM, "_print_matrix", lambda summary: None)
    out = RM.run_retention_map(["a", "b", "z"], keep_memory=True, num_agents=7, max_ticks=9)
    assert out == _summary() and json.load(open(tmp_path / "results" / "retention_map.json", encoding="utf-8")) == _summary()
    assert calls["ret"] == ("fn", ["a", "b"], ["cA", "cB"], True), "echelle REELLE (celle du transcript) et champions promus transmis"
    ladder, kw = calls["curr"]
    assert ladder == ["a", "b", "z"] and (kw["keep_memory"], kw["num_agents"], kw["max_ticks"], kw["manage_logger"]) == (True, 7, 9, False)
    assert type(kw["grad_cfg"]).__name__ == "GraduationConfig" and calls["era"] == ("db", "WorldConfig", {"num_agents": 7, "max_ticks": 9})
    txt = capsys.readouterr().out
    assert "[oubli]" in txt and "[rétention]" in txt and "[transfert rétrograde]" in txt, "etiquettes de seuil a +-0.02"
    assert calls["stop"] == 1
    monkeypatch.setattr(RM, "_acquire_shared_db", lambda: None)
    (tmp_path / "results" / "retention_map.json").unlink()
    assert RM.run_retention_map(["a"], num_agents=7, max_ticks=9) is None and not (tmp_path / "results" / "retention_map.json").exists()
    assert calls["stop"] == 2, "le logger est arrete meme sans db (finally)"
    monkeypatch.setattr(RM, "_acquire_shared_db", lambda: "db")
    monkeypatch.setattr(RM, "run_curriculum", lambda ladder, **kw: [])
    assert RM.run_retention_map(["a"], num_agents=7, max_ticks=9) is None, "transcript vide -> None, jamais une carte"
    with pytest.raises(ValueError):
        RM.run_retention_map(["a"], num_agents=0)


def test_run_bptt_act_known_answers_on_a_null_and_a_direct_wire(monkeypatch):
    N, K = 19, 1
    bits = np.array([[1.0], [-1.0], [1.0]])
    dW0, acc0 = AG.run_bptt_act(np.zeros((N, N)), K, 1, bits, lambda e: e)
    assert acc0 == 0.0 and dW0.shape == (N, N), "W nul : la prediction vaut 0, son signe n'est ni +1 ni -1"
    assert dW0[0, N - AG.O_DIM] == pytest.approx(-0.25), "descendre le gradient CREE le fil entree -> sortie"
    W = np.zeros((N, N))
    W[0, N - AG.O_DIM] = 10.0
    dW1, acc1 = AG.run_bptt_act(W, K, 1, bits, lambda e: e)
    assert acc1 == 1.0 and AG.run_bptt_act(W, K, 1, bits, np.tanh)[1] == 1.0 and AG.run_bptt_act(W, K, 0, bits, lambda e: e)[1] == 1.0
    assert dW1[0, N - AG.O_DIM] == pytest.approx(0.0625), "fil trop fort : le gradient le REDUIT (prediction 5 pour une cible 1)"
    with pytest.raises(ValueError):
        AG.run_bptt_act(W, K, 1, np.zeros((0, K)), np.tanh)


def test_run_refgame_is_deterministic_collapses_at_one_epoch_and_never_decodes_beyond_injectivity():
    a, b = RG.run_refgame(M=3, V=3, H=8, epochs=200, seed=1), RG.run_refgame(M=3, V=3, H=8, epochs=200, seed=1)
    assert a == b, "deterministe par seed"
    assert RG.run_refgame(M=3, V=3, H=8, epochs=1, seed=1) == pytest.approx((1 / 3, 1 / 3)), "1 epoch : code EFFONDRE"
    for s in range(4):
        acc, inj = RG.run_refgame(M=3, V=3, H=8, epochs=200, seed=s)
        assert 0.0 <= acc <= inj <= 1.0, "un code non injectif ne se decode pas au-dela de son injectivite"
    with pytest.raises(ValueError):
        RG.run_refgame(M=1, V=3, H=8, epochs=10)
