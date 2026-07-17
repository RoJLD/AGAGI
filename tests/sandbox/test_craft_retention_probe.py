"""Tests des fonctions pures de tools/craft_retention_probe (sans le sim)."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.craft_retention_probe import _metrics, _craft_elites, _verdict_retention


class _FakeArchive:
    def __init__(self, elites):
        self._elites = elites

    def elites(self):
        return self._elites


def test_metrics_frac_craft_and_recraft():
    stats = [{"spears_crafted": 0}, {"spears_crafted": 1},
             {"spears_crafted": 2}, {"spears_crafted": 3}]
    m = _metrics(stats)
    assert m["frac_craft"] == 0.75      # 3/4 ont crafté >=1
    assert m["frac_recraft"] == 0.5     # 2/4 ont re-crafté >=2
    assert m["total_spears"] == 6
    assert m["n"] == 4


def test_metrics_empty():
    m = _metrics([])
    assert m["frac_craft"] == 0.0 and m["frac_recraft"] == 0.0 and m["total_spears"] == 0


def test_craft_elites_filters_crafters_only():
    g_forage, g_craft, g_apex = object(), object(), object()
    arch = _FakeArchive([
        (10.0, g_forage, {"spears_crafted": 0, "preys_eaten": 3}),
        (20.0, g_craft, {"spears_crafted": 2}),
        (30.0, g_apex, {"spears_crafted": 1, "mammoth_kills": 1}),
    ])
    elites = _craft_elites(arch)
    assert g_craft in elites and g_apex in elites   # les deux ont crafté
    assert g_forage not in elites
    assert len(elites) == 2


def test_verdict_retention_lever_when_lifts_and_off_floor():
    base = {"frac_craft": 0.10}
    best = {"frac_craft": 0.25}   # +0.15 et >=0.10
    assert _verdict_retention(base, "incitation_flat", best).startswith("RETENTION_LEVER")


def test_verdict_policy_locked_when_no_lever_moves():
    base = {"frac_craft": 0.10}
    best = {"frac_craft": 0.11}   # +0.01 < 0.03
    assert _verdict_retention(base, "memoire_recette", best) == "POLICY_LOCKED"
