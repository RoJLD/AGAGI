"""Les hooks du PM : quatre evenements, une commande portable sans backtick ni variable de shell."""
import json
import os
import re

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SETTINGS = os.path.join(_ROOT, ".claude", "settings.json")
_INTERDIT = re.compile(r"[`$\\]")


def _hooks():
    with open(_SETTINGS, encoding="utf-8") as fh:
        return json.load(fh)["hooks"]


def test_les_quatre_evenements_du_bulletin_sont_branches():
    h = _hooks()
    assert {"SessionStart", "PostToolUse", "Stop", "SessionEnd"} <= set(h)
    attendu = {"SessionStart": "start", "PostToolUse": "tool", "Stop": "stop", "SessionEnd": "end"}
    for ev, verbe in attendu.items():
        cmds = [x["command"] for grp in h[ev] for x in grp["hooks"] if x["type"] == "command"]
        assert f"python -m tools.pm.bulletin {verbe}" in cmds, (ev, cmds)


def test_PostToolUse_ne_vise_que_les_outils_qui_ecrivent():
    grp = [g for g in _hooks()["PostToolUse"] if any("tools.pm.bulletin" in x["command"] for x in g["hooks"])][0]
    assert grp["matcher"] == "Edit|Write|MultiEdit|NotebookEdit"


def test_aucune_commande_de_hook_ne_contient_backtick_dollar_ou_backslash():
    for ev, grps in _hooks().items():
        for g in grps:
            for x in g["hooks"]:
                assert not _INTERDIT.search(x["command"]), (ev, x["command"])
                assert x.get("timeout", 10) <= 15, "un hook du bulletin doit rester sous la seconde ; 15 s est le plafond"
