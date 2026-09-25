"""P2.56 (b) — six orchestrateurs MUETS (aucun test n'importait-et-appelait leur symbole) reçoivent une INJECTION
À DOSE CONNUE : `run_arm` est remplacé par un bras factice qui rend des mesures dont on connaît la réponse, et
c'est la COUCHE qui transforme des mesures en verdict (appariement par seed, différence ON−SHUFFLE, `compute_ab_verdict`
avec bande ET test de signe, comptes publiés) qui est confrontée. Aucun monde construit (les gardes en tête restent
couvertes par leurs cas existants).

Réponses connues : à n = 5 seeds en séparation PARFAITE, `sign_p` = 2 × 0,5⁵ = 0,0625 < 0,1 → un ON à +0,30 contre un
SHUFFLE à +0,05 rend `GRADIENT_GAGNE` ; ON == SHUFFLE rend `NEUTRE` (no-op EXACT) ; à n = 3 la même dose rend `NEUTRE`
avec `underpowered` (la garde de puissance dit pourquoi). Chaque orchestrateur est jugé sur SA structure de sortie.

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import os
import sys

import numpy as np
import pytest

pytest.importorskip("torch")  # la CI installe requirements.txt SANS torch : sans cette garde le module ERRE
# à la collecte — et jusqu'au 2026-09-26 UNE erreur de collecte interrompait TOUTE la suite (8 modules,
# 0 test exécuté pendant ~10 jours, run 36154477100).

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

import tools.torch_throw_gate_inworld_ab as G  # noqa: E402
import tools.torch_binary_gate_probe as B  # noqa: E402

SEEDS5 = (0, 1, 2, 3, 4)
ON, SH = 0.30, 0.05          # dose : gap ON, gap SHUFFLE -> diff 0,25 > bande 0,02


def _arm(gap, kills=3, throw=0.4, alive=20):
    return {"binding_gap_inworld": gap, "kills_with_tool": kills, "throw_rate": throw,
            "spear_n": 11, "nospear_n": 9, "n_alive_end": alive}


def _fake_run_arm(seen, rule):
    """`rule(kwargs) -> gap ON` ; le SHUFFLE rend toujours SH. Chaque appel est journalisé (seed, drapeaux)."""
    def run_arm(shuffle=False, seed=0, **kw):
        seen.append((seed, shuffle, {k: kw.get(k) for k in ("penalty", "shaping", "warm_w", "prey_count")}))
        return _arm(SH if shuffle else rule(kw), kills=(0 if shuffle else 3))
    return run_arm


def test_compare_reads_a_known_dose_as_GRADIENT_GAGNE_and_a_noop_as_NEUTRE(monkeypatch):
    seen = []
    monkeypatch.setattr(G, "run_arm", _fake_run_arm(seen, lambda kw: ON))
    out = G.compare(seeds=SEEDS5, ticks=10, n_agents=4)
    assert out["verdict"]["verdict"] == "GRADIENT_GAGNE" and out["verdict"]["n"] == 5
    assert [r["diff"] for r in out["rows"]] == pytest.approx([ON - SH] * 5)
    assert [r["seed"] for r in out["rows"]] == list(SEEDS5) and all(r["kills_on"] == 3 for r in out["rows"])
    assert [s[1] for s in seen] == [False, True] * 5, "ON puis SHUFFLE, apparié par seed"
    # no-op EXACT : le shuffle vaut l'ON -> aucune différence -> NEUTRE, jamais un positif fabriqué
    monkeypatch.setattr(G, "run_arm", _fake_run_arm([], lambda kw: SH))
    assert G.compare(seeds=SEEDS5, ticks=10, n_agents=4)["verdict"]["verdict"] == "NEUTRE"


def test_compare_at_three_seeds_cannot_be_positive_and_SAYS_it(monkeypatch):
    monkeypatch.setattr(G, "run_arm", _fake_run_arm([], lambda kw: ON))
    v = G.compare(seeds=(0, 1, 2), ticks=10, n_agents=4)["verdict"]
    assert v["verdict"] == "NEUTRE" and v["underpowered"] is True and v["median_diff"] == pytest.approx(ON - SH)


def test_compare_debias_separates_the_biased_and_unbiased_arms_by_penalty(monkeypatch):
    # dose : le bras NON biaisé (penalty 0.0) lie, le bras biaisé (penalty −0.5) ne lie pas
    seen = []
    monkeypatch.setattr(G, "run_arm", _fake_run_arm(seen, lambda kw: ON if kw.get("penalty") == 0.0 else SH))
    out = G.compare_debias(seeds=SEEDS5, ticks=10, n_agents=4)
    assert out["biased"]["verdict"]["verdict"] == "NEUTRE"
    assert out["unbiased"]["verdict"]["verdict"] == "GRADIENT_GAGNE"
    assert len(out["info"]) == 5 and out["info"][0]["kills_u"] == 3 and out["info"][0]["u_on"] == ON
    assert sorted({s[2]["penalty"] for s in seen}) == [-0.5, 0.0] and len(seen) == 20


def test_compare_density_separates_sparse_and_dense_credit_by_shaping(monkeypatch):
    seen = []
    monkeypatch.setattr(G, "run_arm", _fake_run_arm(seen, lambda kw: ON if kw.get("shaping") else SH))
    out = G.compare_density(seeds=SEEDS5, ticks=10, n_agents=4)
    assert out["sparse"]["verdict"]["verdict"] == "NEUTRE" and out["dense"]["verdict"]["verdict"] == "GRADIENT_GAGNE"
    assert out["info"][0]["dense_on"] == ON and out["info"][0]["sparse_on"] == SH and len(seen) == 20


def test_compare_warmstart_reads_retention_only_in_the_WARM_arm_and_warm_vs_cold(monkeypatch):
    seen = []
    monkeypatch.setattr(G, "_collect_warm_direction", lambda **kw: (np.ones(3, dtype=np.float32), None))
    monkeypatch.setattr(G, "run_arm", _fake_run_arm(seen, lambda kw: ON if kw.get("warm_w") is not None else SH))
    out = G.compare_warmstart(seeds=SEEDS5, ticks=10, n_agents=4)
    assert out["cold"]["verdict"]["verdict"] == "NEUTRE"
    assert out["warm"]["verdict"]["verdict"] == "GRADIENT_GAGNE"
    assert out["warm_vs_cold"]["verdict"]["verdict"] == "GRADIENT_GAGNE"
    assert all(i["warm_ok"] for i in out["info"]) and out["info"][0]["warm_on"] == ON and out["info"][0]["cold_on"] == SH
    # direction WARM introuvable (None) : le bras warm devient un bras froid, et `warm_ok` le DIT
    monkeypatch.setattr(G, "_collect_warm_direction", lambda **kw: (None, None))
    out = G.compare_warmstart(seeds=SEEDS5, ticks=10, n_agents=4)
    assert out["warm"]["verdict"]["verdict"] == "NEUTRE" and not any(i["warm_ok"] for i in out["info"])


def test_compare_rp_sweep_finds_the_prey_level_where_binding_crosses_the_floor(monkeypatch):
    seen = []
    monkeypatch.setattr(G, "run_arm", _fake_run_arm(seen, lambda kw: ON if kw.get("prey_count", 0) >= 60 else SH))
    out = G.compare_rp_sweep(seeds=SEEDS5, prey_levels=(15, 60, 150), ticks=10, n_agents=4)
    assert [o["prey_count"] for o in out] == [15, 60, 150]
    assert [o["verdict"]["verdict"] for o in out] == ["NEUTRE", "GRADIENT_GAGNE", "GRADIENT_GAGNE"]
    assert out[0]["median_diff"] == pytest.approx(0.0) and out[1]["median_diff"] == pytest.approx(ON - SH)
    assert out[1]["median_kills"] == 3 and out[1]["median_gap_on"] == ON and len(seen) == 30


def _fake_binary_arm(gap_on, gap_off, gap_sh, comp=0.5):
    def run_arm(gate_on, episodes=800, n_agents=64, seed=0, lr=0.05, antisat=6.0, shuffle_label=False):
        gap = gap_sh if shuffle_label else (gap_on if gate_on else gap_off)
        return {"binding_gap": gap, "comp_rate": comp, "throw_rate": 0.3}
    return run_arm


def test_binary_gate_compare_reads_a_true_binding_and_a_MEMORIZED_label_differently(monkeypatch):
    # vrai binding : ON 0,40 > OFF 0,10 ET ON > SHUFFLE 0,10 -> les deux verdicts positifs
    monkeypatch.setattr(B, "run_arm", _fake_binary_arm(0.40, 0.10, 0.10))
    out = B.compare(seeds=SEEDS5, episodes=5, n_agents=4)
    assert out["verdict"]["verdict"] == "GRADIENT_GAGNE" and out["verdict_vs_shuffle"]["verdict"] == "GRADIENT_GAGNE"
    assert out["n_gap_indefini"] == 0 and [r["diff_vs_shuffle"] for r in out["rows"]] == pytest.approx([0.30] * 5)
    # confond C1/I1 : le readout mémorise N'IMPORTE QUEL label fixe -> ON == SHUFFLE : diff positif mais
    # diff_vs_shuffle nul -> le VRAI test de binding rend NEUTRE
    monkeypatch.setattr(B, "run_arm", _fake_binary_arm(0.40, 0.10, 0.40))
    out = B.compare(seeds=SEEDS5, episodes=5, n_agents=4)
    assert out["verdict"]["verdict"] == "GRADIENT_GAGNE" and out["verdict_vs_shuffle"]["verdict"] == "NEUTRE"


def test_binary_gate_compare_COUNTS_undefined_gaps_instead_of_inventing_a_value(monkeypatch):
    # un gap INDÉFINI (None : aucun craft dans le dernier quart) vaut 0,0 par convention ET est COMPTÉ
    monkeypatch.setattr(B, "run_arm", _fake_binary_arm(None, 0.10, 0.10))
    out = B.compare(seeds=SEEDS5, episodes=5, n_agents=4)
    assert out["n_gap_indefini"] == 5 and all(r["on"] == 0.0 and r["gaps_indefinis"] == 1 for r in out["rows"])
    assert out["verdict"]["verdict"] in ("NEUTRE", "HEBBIEN_GAGNE")          # jamais un positif fabriqué
