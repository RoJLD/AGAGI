# -*- coding: utf-8 -*-
"""P2.60 (2026-09-15) -- calibration du banc EDR-177 (`compare_factorial`, `tools/torch_throw_gate_inworld_ab.py`)
et des couches PURES du driver EDR-178 (`tools/factorial_regime_sweep.py`), tous deux portes dans HEAD par
FUSION 3-voies du tag `keep/edr-177-178-factorial-regime-sweep` (merge-tree sans conflit).

Les deux sont des ORCHESTRATEURS : `compare_factorial` ne simule pas lui-meme, il appelle `run_arm` 2 x K
fois par cellule (ON puis SHUFFLE, apparies par seed) et AGREGE 16 cellules 2^4 ; `run_sweep` appelle
`compare_factorial` par regime et pivote les effets. C'est cette couche -- appariement, mappage des
facteurs, agregation, verdict -- qui transforme des mesures en affirmation, et c'est elle qu'on calibre
ici, par INJECTION A DOSE CONNUE (technique de `test_orchestrator_injection.py`) : on impose un `run_arm`
(resp. un `compare_fn`) factice dont les gaps suivent un modele additif connu, et on exige que
l'orchestrateur RETROUVE la dose exactement. AUCUN monde n'est construit ; aucune simulation ; cout nul.

Trois formes (CLAUDE.md) : no-op EXACT (dose 0 + bruit par seed -> diffs exactement 0.0, l'appariement
annule le bruit), PREDICTION (dose imposee -> effets = dose, interaction = gamma/2 en forme close), et
les branches NEGATIVES du verdict (sans elles, classe E1 : un test qui ne peut pas echouer). Plus la
garde d'arguments EN TETE (E14 retro-appliquee au banc, meme forme que les autres `compare_*`) et la
definition UNIQUE de `_factorial_effects` (le driver importe celle du banc, corrigee porte 14).

Ce que ce fichier ne calibre PAS : `run_arm` (le maillon qui simule) -- tests/sandbox/test_torch_throw_gate_factorial.py
et test_torch_throw_gate_world.py le couvrent, sous la garde de bail de tests/conftest.py.
"""
import inspect
import itertools
import math
import time

import pytest

from tools import factorial_regime_sweep as FRS
from tools import torch_throw_gate_inworld_ab as AB
from tools.factorial_regime_sweep import (
    REGIMES, run_sweep, _factorial_effects, _regime_main_effects_table, _cell0, _cell0_verdict,
)

_FACTORS = ("no_consume", "weightless", "dense", "conditional_credit")
_ZERO = {f: 0.0 for f in _FACTORS}


def _cells_from_dose(dose, seeds, prey_sparse=15, prey_dense=300, gamma=0.0, verdict="NEUTRE", sign_p=1.0):
    """16 cellules 2^4 dont les diffs suivent un modele ADDITIF connu (+ interaction no_consume x dense
    de taille `gamma`). Meme forme de sortie que `compare_factorial` (EDR-177)."""
    cells = []
    for nc, wl, dn, cc in itertools.product([False, True], repeat=4):
        diff = (dose["no_consume"] * nc + dose["weightless"] * wl + dose["dense"] * dn
                + dose["conditional_credit"] * cc + gamma * (nc and dn))
        cells.append({"no_consume": nc, "weightless": wl, "dense": dn, "conditional_credit": cc,
                      "prey_count": prey_dense if dn else prey_sparse,
                      "verdict": {"verdict": verdict, "sign_p": sign_p},
                      "median_diff": diff, "median_gap_on": diff, "median_kills": 0.0,
                      "median_throw": 0.0, "diffs": [diff for _ in seeds], "rows": []})
    return cells


def _fake_compare(dose_of_regime, calls=None, gamma=0.0):
    """`compare_factorial` factice : la dose depend du REGIME recu (via `energy`), les appels sont
    journalises. C'est l'injection a dose connue de l'orchestrateur `run_sweep`."""
    def compare(**kw):
        if calls is not None:
            calls.append(dict(kw))
        dose = dose_of_regime(kw)
        return _cells_from_dose(dose, kw["seeds"], kw["prey_sparse"], kw["prey_dense"], gamma=gamma)
    return compare


def _fake_run_arm(dose_of_cell, noise=None, calls=None):
    """`run_arm` factice pour `compare_factorial` : gap_ON = dose(cellule) + bruit(seed), gap_SHUFFLE =
    bruit(seed). Le bruit est APPARIE par seed (meme tirage dans les deux bras, comme le CRN du vrai
    banc) : la difference ON - SHUFFLE doit retrouver la dose EXACTEMENT. Aucun monde."""
    def run_arm(**kw):
        if calls is not None:
            calls.append(dict(kw))
        eps = noise(kw["seed"]) if noise is not None else 0.0
        gap = eps + (0.0 if kw["shuffle"] else dose_of_cell(kw))
        return {"shuffle": bool(kw["shuffle"]), "seed": int(kw["seed"]), "binding_gap_inworld": gap,
                "kills_with_tool": 7, "spear_n": 10, "nospear_n": 10, "n_alive_end": 4, "throw_rate": 0.5}
    return run_arm


def _never_called(**kw):
    raise AssertionError("le maillon aval a ete APPELE : la garde d'arguments n'est pas EN TETE")


def _dose_of_cell(kw):
    """Modele additif a dose connue sur les FLAGS que compare_factorial passe a run_arm."""
    return 0.40 * bool(kw["no_consume"]) + 0.16 * (kw["prey_count"] >= 300)


# ===================================================================================================
# compare_factorial (banc EDR-177) -- garde EN TETE, defaut de seeds, 16 cellules, mappage, no-op, dose
# ===================================================================================================

@pytest.mark.parametrize("bad", [
    dict(seeds=()),
    dict(ticks=0),
    dict(n_agents=0),
    dict(ticks=10, warmup=10),
])
def test_compare_factorial_refuses_degenerate_arguments_before_any_world(monkeypatch, bad):
    """Garde d'arguments EN TETE (E14 retro-appliquee, meme forme que compare_debias/density/warmstart/
    rp_sweep). Un argument degenere est une erreur d'APPEL, pas un fait sur le monde : sans garde,
    `seeds=()` rendait 16 cellules a `median([])` / verdict NEUTRE de fond. Le refus precede tout appel a
    `run_arm` (`_never_called` leve sinon) et il est instantane (< 0.5 s : la garde est AVANT le monde)."""
    monkeypatch.setattr(AB, "run_arm", _never_called)
    kw = dict(seeds=(0, 1, 2, 3, 4), ticks=12, warmup=3, n_agents=4)
    kw.update(bad)
    t0 = time.time()
    with pytest.raises(ValueError, match="degenere"):
        AB.compare_factorial(**kw)
    assert time.time() - t0 < 0.5, "compare_factorial refuse trop lentement : la garde est posee trop bas"


def test_compare_factorial_default_seeds_are_five_like_every_other_compare():
    """P2.49 (2026-09-09) : `compute_ab_verdict` exige `sign_p < 0.1`, donc n >= 5 pour qu'un positif soit
    seulement POSSIBLE. Le defaut du tag etait (0,1,2,3) -- un bras qui ne peut pas reussir (E2). Aligne
    sur les autres `compare_*` du banc."""
    default = inspect.signature(AB.compare_factorial).parameters["seeds"].default
    assert tuple(default) == (0, 1, 2, 3, 4)
    assert tuple(default) == tuple(inspect.signature(AB.compare_rp_sweep).parameters["seeds"].default)


def test_compare_factorial_builds_16_distinct_cells_maps_prey_count_and_passes_factors_to_run_arm(monkeypatch):
    """La carte 2^4 est COMPLETE et DISTINCTE (16 cellules, cellule-0 presente), la densite est mappee sur
    `prey_count` (dense -> prey_dense, sinon prey_sparse), et chaque cellule transmet SES trois flags a
    `run_arm`, 2 fois par seed (ON puis SHUFFLE), en regime non-biaise (penalty=0.0) avec `night` transmis."""
    calls = []
    monkeypatch.setattr(AB, "run_arm", _fake_run_arm(lambda kw: 0.0, calls=calls))
    seeds = (0, 1)
    cells = AB.compare_factorial(seeds=seeds, prey_sparse=15, prey_dense=300, ticks=12, warmup=3,
                                 n_agents=4, night=True)
    assert len(cells) == 16
    keys = {(c["no_consume"], c["weightless"], c["dense"], c["conditional_credit"]) for c in cells}
    assert len(keys) == 16 and (True, True, True, True) in keys
    for c in cells:
        assert c["prey_count"] == (300 if c["dense"] else 15)
        assert len(c["diffs"]) == len(seeds) and len(c["rows"]) == len(seeds)
    assert len(calls) == 16 * 2 * len(seeds)
    for i, c in enumerate(cells):
        mine = calls[i * 2 * len(seeds):(i + 1) * 2 * len(seeds)]
        for j, s in enumerate(seeds):
            on, sh = mine[2 * j], mine[2 * j + 1]
            assert (on["shuffle"], sh["shuffle"]) == (False, True) and on["seed"] == sh["seed"] == s
            for k in (on, sh):
                assert k["no_consume"] == c["no_consume"] and k["weightless"] == c["weightless"]
                assert k["conditional_credit"] == c["conditional_credit"]
                assert k["prey_count"] == c["prey_count"]
                assert k["penalty"] == 0.0 and k["night"] is True
                assert k["ticks"] == 12 and k["warmup"] == 3 and k["n_agents"] == 4


def test_compare_factorial_noop_exact_pairing_cancels_seed_noise(monkeypatch):
    """No-op EXACT : dose 0 dans toutes les cellules, mais un bruit par seed de 161x l'amplitude de la
    bande. L'appariement ON/SHUFFLE par seed doit l'annuler EXACTEMENT : diff == 0.0 partout, verdict
    NEUTRE, et les effets du plan 2^4 exactement 0.0 (pas approx)."""
    monkeypatch.setattr(AB, "run_arm", _fake_run_arm(lambda kw: 0.0, noise=lambda s: 3.22 * (s + 1)))
    cells = AB.compare_factorial(seeds=(0, 1, 2, 3, 4), ticks=12, warmup=3, n_agents=4)
    for c in cells:
        assert c["diffs"] == [0.0] * 5 and c["median_diff"] == 0.0
        assert c["verdict"]["verdict"] == "NEUTRE"
    eff = AB._factorial_effects(cells)
    assert all(e == 0.0 for e in eff["main"].values())
    assert all(e == 0.0 for e in eff["interactions"].values())


def test_compare_factorial_recovers_imposed_dose_and_the_clean_cell_can_be_positive(monkeypatch):
    """PREDICTION : dose additive (no_consume +0.40, dense +0.16) sous un bruit par seed de grande
    amplitude. Chaque cellule rend SA dose exactement, les effets principaux la retrouvent en forme close,
    les autres facteurs et toutes les interactions sont a 0 ; et la cellule tout-propre rend
    GRADIENT_GAGNE a K=5 -- le banc PEUT produire l'issue positive (E1)."""
    monkeypatch.setattr(AB, "run_arm", _fake_run_arm(_dose_of_cell, noise=lambda s: 1.7 * s - 4.0))
    cells = AB.compare_factorial(seeds=(0, 1, 2, 3, 4), ticks=12, warmup=3, n_agents=4)
    for c in cells:
        want = 0.40 * c["no_consume"] + 0.16 * c["dense"]
        assert c["median_diff"] == pytest.approx(want, abs=1e-12)
        assert all(d == pytest.approx(want, abs=1e-12) for d in c["diffs"])
    eff = AB._factorial_effects(cells)
    assert eff["main"]["no_consume"] == pytest.approx(0.40, abs=1e-12)
    assert eff["main"]["dense"] == pytest.approx(0.16, abs=1e-12)
    assert eff["main"]["weightless"] == pytest.approx(0.0, abs=1e-12)
    assert eff["main"]["conditional_credit"] == pytest.approx(0.0, abs=1e-12)
    assert all(v == pytest.approx(0.0, abs=1e-12) for v in eff["interactions"].values())
    c0 = _cell0(cells)
    assert c0["verdict"]["verdict"] == "GRADIENT_GAGNE"
    plain = next(c for c in cells if not any(c[f] for f in _FACTORS))
    assert plain["verdict"]["verdict"] == "NEUTRE"


# ===================================================================================================
# _factorial_effects -- UNE definition (le driver importe celle du banc), pool vide -> nan (porte 14)
# ===================================================================================================

def test_factorial_effects_is_one_definition_shared_by_driver_and_bench():
    """Le driver EDR-178 n'a pas de COPIE de `_factorial_effects` : il importe celle du banc EDR-177.
    Deux definitions divergeraient en silence (la copie portee rendait nan, l'original 0.0)."""
    assert FRS._factorial_effects is AB._factorial_effects


def test_bench_factorial_effects_empty_pool_says_nan_not_zero():
    """Porte 14, sur le BANC : un niveau JAMAIS mesure n'a pas un effet de 0.0, il n'a PAS d'effet mesure.
    L'original du tag rendait `0.0` sur un pool vide -- « aucun effet » la ou il n'y avait aucune mesure."""
    eff0 = AB._factorial_effects([])
    assert all(math.isnan(v) for v in eff0["main"].values())
    assert all(math.isnan(v) for v in eff0["interactions"].values())


# ---------------------------------------------------------------------------------------------------
# run_sweep -- guard-before-world
# ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    dict(regimes={}),
    dict(seeds=()),
    dict(ticks=0),
    dict(n_agents=0),
    dict(ticks=10, warmup=10),
])
def test_run_sweep_refuses_degenerate_arguments_before_any_measure(bad):
    """Un argument degenere est une erreur d'APPEL, pas un fait sur le monde (garde E14 retro-appliquee,
    meme forme que les `compare_*` de HEAD). Le refus precede tout appel : `_never_called` leve sinon."""
    kw = dict(regimes={"neutralise": REGIMES["neutralise"]}, seeds=(0, 1, 2, 3, 4), ticks=12, warmup=3,
              n_agents=4, compare_fn=_never_called)
    kw.update(bad)
    with pytest.raises(ValueError):
        run_sweep(**kw)


# ---------------------------------------------------------------------------------------------------
# run_sweep -- passthrough : les knobs de CHAQUE regime atteignent le banc, une fois, dans l'ordre
# ---------------------------------------------------------------------------------------------------

def test_run_sweep_passes_each_regime_knobs_through_exactly_once():
    calls = []
    fake = _fake_compare(lambda kw: _ZERO, calls=calls)
    regimes = {"neutralise": REGIMES["neutralise"], "rare": REGIMES["rare"]}
    out = run_sweep(regimes, seeds=(0, 1, 2, 3, 4), ticks=12, warmup=3, n_agents=4, compare_fn=fake)
    assert list(out) == ["neutralise", "rare"]                      # une entree par regime, dans l'ordre
    assert len(calls) == 2
    for (name, rk), kw in zip(regimes.items(), calls):
        for k, v in rk.items():
            assert kw[k] == v, (name, k)                            # chaque knob de regime, intact
        assert kw["seeds"] == (0, 1, 2, 3, 4) and kw["ticks"] == 12 and kw["warmup"] == 3 and kw["n_agents"] == 4
    for res in out.values():
        assert len(res["cells"]) == 16 and set(res["effects"]["main"]) == set(_FACTORS)


# ---------------------------------------------------------------------------------------------------
# run_sweep -- no-op EXACT et PREDICTION (dose retrouvee), regimes isoles les uns des autres
# ---------------------------------------------------------------------------------------------------

def test_run_sweep_noop_exact_dose_zero_gives_effects_exactly_zero():
    fake = _fake_compare(lambda kw: _ZERO)
    out = run_sweep({"neutralise": REGIMES["neutralise"]}, seeds=(0, 1, 2, 3, 4), ticks=12, warmup=3,
                    n_agents=4, compare_fn=fake)
    eff = out["neutralise"]["effects"]
    assert all(e == 0.0 for e in eff["main"].values())            # EXACT, pas approx
    assert all(e == 0.0 for e in eff["interactions"].values())


def test_run_sweep_recovers_imposed_dose_per_regime_and_keeps_regimes_apart():
    """Dose imposee = f(energy) : neutralise (250) et letal (150) recoivent des doses DIFFERENTES ; le
    driver doit rendre a chaque regime SES effets (appariement regime -> cellules) et les retrouver
    exactement -- forme close du plan 2^4 equilibre : effet principal = dose."""
    def dose_of(kw):
        s = kw["energy"] / 250.0
        return {"no_consume": 0.40 * s, "weightless": 0.02 * s, "dense": 0.16 * s, "conditional_credit": 0.0}
    fake = _fake_compare(dose_of)
    regimes = {"neutralise": REGIMES["neutralise"], "letal": REGIMES["letal"]}
    out = run_sweep(regimes, seeds=(0, 1, 2, 3, 4), ticks=12, warmup=3, n_agents=4, compare_fn=fake)
    tbl = _regime_main_effects_table({n: r["effects"] for n, r in out.items()})
    assert tbl["no_consume"]["neutralise"] == pytest.approx(0.40, abs=1e-12)
    assert tbl["no_consume"]["letal"] == pytest.approx(0.40 * 150.0 / 250.0, abs=1e-12)
    assert tbl["dense"]["neutralise"] == pytest.approx(0.16, abs=1e-12)
    assert tbl["dense"]["letal"] == pytest.approx(0.16 * 0.6, abs=1e-12)
    assert tbl["conditional_credit"]["neutralise"] == 0.0 and tbl["conditional_credit"]["letal"] == 0.0
    assert tbl["no_consume"]["neutralise"] != tbl["no_consume"]["letal"]   # les regimes ne se melangent pas


# ---------------------------------------------------------------------------------------------------
# run_sweep -- chemin par DEFAUT : c'est bien le banc EDR-177 qui est appele (sinon l'injection serait
# un controle qui ne peut pas echouer, classe E1)
# ---------------------------------------------------------------------------------------------------

def test_run_sweep_default_path_calls_the_bench_compare_factorial(monkeypatch):
    calls = []
    monkeypatch.setattr(FRS, "compare_factorial", _fake_compare(lambda kw: _ZERO, calls=calls))
    out = run_sweep({"rare": REGIMES["rare"]}, seeds=(0, 1, 2, 3, 4), ticks=12, warmup=3, n_agents=4)
    assert len(calls) == 1 and calls[0]["prey_dense"] == REGIMES["rare"]["prey_dense"]
    assert set(out) == {"rare"}


# ---------------------------------------------------------------------------------------------------
# _factorial_effects -- isolation, interaction en forme close, pool vide -> nan (porte 14)
# ---------------------------------------------------------------------------------------------------

def test_factorial_effects_isolates_a_single_main_effect():
    dose = dict(_ZERO, conditional_credit=1.0)
    eff = _factorial_effects(_cells_from_dose(dose, seeds=(0, 1)))
    assert eff["main"]["conditional_credit"] == pytest.approx(1.0, abs=1e-12)
    for f in ("no_consume", "weightless", "dense"):
        assert eff["main"][f] == 0.0
    assert all(v == pytest.approx(0.0, abs=1e-12) for v in eff["interactions"].values())


def test_factorial_effects_interaction_is_half_gamma_in_closed_form():
    """diff = gamma ssi (no_consume ET dense) : l'interaction 2-way vaut gamma/2 et chacun des deux effets
    principaux herite gamma/2 (le plan est equilibre) ; les autres paires restent a 0."""
    eff = _factorial_effects(_cells_from_dose(_ZERO, seeds=(0,), gamma=1.0))
    assert eff["interactions"]["no_consume×dense"] == pytest.approx(0.5, abs=1e-12)
    assert eff["main"]["no_consume"] == pytest.approx(0.5, abs=1e-12)
    assert eff["main"]["dense"] == pytest.approx(0.5, abs=1e-12)
    assert eff["main"]["weightless"] == 0.0 and eff["main"]["conditional_credit"] == 0.0
    assert eff["interactions"]["weightless×conditional_credit"] == pytest.approx(0.0, abs=1e-12)


def test_factorial_effects_empty_pool_says_nan_not_zero():
    """Porte 14 : un niveau JAMAIS mesure n'a pas un effet de 0.0, il n'a PAS d'effet mesure. Ici toutes
    les cellules sont no_consume=True -> le pool 'confond' est vide -> nan, et aucune exception."""
    dose = dict(_ZERO, no_consume=0.3)
    cells = [c for c in _cells_from_dose(dose, seeds=(0,)) if c["no_consume"]]
    eff = _factorial_effects(cells)
    assert math.isnan(eff["main"]["no_consume"])
    assert eff["main"]["dense"] == 0.0                              # les autres facteurs restent mesurables
    assert math.isnan(eff["interactions"]["no_consume×dense"])
    eff0 = _factorial_effects([])
    assert all(math.isnan(v) for v in eff0["main"].values())
    assert all(math.isnan(v) for v in eff0["interactions"].values())


# ---------------------------------------------------------------------------------------------------
# _regime_main_effects_table / _cell0 / _cell0_verdict
# ---------------------------------------------------------------------------------------------------

def test_regime_main_effects_table_pivots_by_factor():
    regime_effects = {
        "A": {"main": {"no_consume": 0.4, "weightless": 0.0, "dense": 0.1, "conditional_credit": 0.0}},
        "B": {"main": {"no_consume": 0.5, "weightless": 0.3, "dense": 0.2, "conditional_credit": 0.0}},
    }
    tbl = _regime_main_effects_table(regime_effects)
    assert tbl["no_consume"] == {"A": 0.4, "B": 0.5}
    assert tbl["weightless"] == {"A": 0.0, "B": 0.3}
    assert set(tbl) == set(_FACTORS)


def test_cell0_finds_the_all_clean_cell_and_refuses_its_absence():
    cells = _cells_from_dose(_ZERO, seeds=(0,))
    c0 = _cell0(cells)
    assert (c0["no_consume"], c0["weightless"], c0["dense"], c0["conditional_credit"]) == (True,) * 4
    with pytest.raises(ValueError):
        _cell0([c for c in cells if not c["conditional_credit"]])


def _c0(verdict, sign_p=0.0005, median_diff=0.3):
    return {"no_consume": True, "weightless": True, "dense": True, "conditional_credit": True,
            "verdict": {"verdict": verdict, "sign_p": sign_p}, "median_diff": median_diff,
            "median_kills": 300.0, "diffs": [median_diff]}


def test_cell0_verdict_positive_is_BINDE_only_at_or_above_twelve_seeds():
    """Garde-fou power-evaporation (EDR-177 §Confirmation) : GRADIENT_GAGNE a n=8 est NON-CONCLUANT,
    a n=12 il est BINDE. La frontiere est STRICTE a 12."""
    v12 = _cell0_verdict(_c0("GRADIENT_GAGNE"), n_seeds=12)
    assert v12["conclusion"] == "BINDE" and v12["powered"] is True
    v8 = _cell0_verdict(_c0("GRADIENT_GAGNE"), n_seeds=8)
    assert v8["powered"] is False and "NON-CONCLUANT" in v8["conclusion"] and "n=8" in v8["conclusion"]
    v11 = _cell0_verdict(_c0("GRADIENT_GAGNE"), n_seeds=11)
    assert v11["powered"] is False


def test_cell0_verdict_negative_branches_and_underpowered_null_is_not_a_measured_null():
    n = _cell0_verdict(_c0("NEUTRE", sign_p=0.125, median_diff=0.005), n_seeds=12)
    assert n["conclusion"] == "PLAT" and n["verdict"] == "NEUTRE" and n["powered"] is True
    h = _cell0_verdict(_c0("HEBBIEN_GAGNE", median_diff=-0.3), n_seeds=12)
    assert h["conclusion"] == "SHUFFLE_BINDE_PLUS"
    n4 = _cell0_verdict(_c0("NEUTRE", sign_p=0.5, median_diff=0.0), n_seeds=4)
    assert n4["powered"] is False and "NON-CONCLUANT" in n4["conclusion"]   # un nul sous puissance n'est pas un nul


def test_cell0_verdict_refuses_unknown_label_and_degenerate_n():
    with pytest.raises(ValueError):
        _cell0_verdict(_c0("BINDE"), n_seeds=12)                    # etiquette hors vocabulaire
    with pytest.raises(ValueError):
        _cell0_verdict(_c0("NEUTRE"), n_seeds=0)
    with pytest.raises(ValueError):
        _cell0_verdict({"no_consume": True}, n_seeds=12)             # verdict absent


def test_regimes_are_the_three_calibrated_ones_of_edr178():
    assert set(REGIMES) == {"neutralise", "letal", "rare"}
    for rk in REGIMES.values():
        assert set(rk) == {"night", "energy", "base_metabolism", "forage_payoff", "prey_sparse", "prey_dense"}
    assert REGIMES["letal"]["energy"] < REGIMES["neutralise"]["energy"]
    assert REGIMES["rare"]["prey_dense"] < REGIMES["neutralise"]["prey_dense"]
    assert FRS._FACTORS == _FACTORS
