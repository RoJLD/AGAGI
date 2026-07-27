"""Test de la logique PURE du probe is-machine-idle (décision, sans IO/process)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.is_machine_idle import verdict


def test_safe_when_idle_and_wal_old():
    assert verdict([], 500, idle_s=120)["safe"] is True


def test_safe_when_no_wal():
    assert verdict([], None, idle_s=120)["safe"] is True


def test_busy_when_wal_recent():
    v = verdict([], 30, idle_s=120)
    assert v["safe"] is False and any("wal" in r for r in v["reasons"])


def test_busy_when_biosphere_process_running():
    v = verdict(["python ... main_biosphere.py"], 500, idle_s=120)
    assert v["safe"] is False and any("pilote" in r for r in v["reasons"])
