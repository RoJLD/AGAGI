"""Les hooks du PM : quatre evenements, une commande portable sans backtick ni variable de shell.

⚠️ Jusqu'a la vague finale, AUCUN test n'EXECUTAIT la commande configuree : on verifiait que la
CHAINE etait dans settings.json, jamais qu'elle tourne. Une commande bien orthographiee qui plante a
l'import (module deplace, dependance absente, cwd inattendu) serait passee -- et comme un hook sort
0 quoi qu'il arrive, l'echec ne se serait vu NULLE PART."""
import json
import os
import re
import subprocess
import sys

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


def test_CHAQUE_commande_configuree_S_EXECUTE_REELLEMENT_et_sort_0(tmp_path):
    """CONTROLE POSITIF de la configuration elle-meme : on lance les quatre commandes telles que
    settings.json les ecrit, depuis la racine du depot (le cwd que Claude Code donne a un hook), avec
    une racine de donnees jetable. Un hook sortant 0 ne prouverait rien a lui seul -- on exige AUSSI
    qu'aucun `hook_errors.log` ne soit ecrit : c'est la seule trace qu'un hook laisse quand il
    echoue."""
    env = dict(os.environ, AGAGI_DATA_ROOT=str(tmp_path).replace("\\", "/"), PYTHONIOENCODING="utf-8")
    payload = json.dumps({"session_id": "test-hook-cmd", "cwd": _ROOT, "hook_event_name": "SessionStart"})
    lancees = []
    for ev, grps in _hooks().items():
        for g in grps:
            for x in g["hooks"]:
                mots = x["command"].split()
                assert mots[0] == "python", x["command"]
                r = subprocess.run([sys.executable] + mots[1:], cwd=_ROOT, input=payload, env=env,
                                   capture_output=True, text=True, timeout=120)
                assert r.returncode == 0, (ev, x["command"], r.stdout[-2000:], r.stderr[-2000:])
                lancees.append(x["command"])
    assert len(lancees) == 4, lancees                    # le test ne doit pas passer sur ZERO commande
    log = tmp_path / "pm" / "hook_errors.log"
    assert not log.exists(), log.read_text(encoding="utf-8", errors="replace")[-2000:]
    assert (tmp_path / "sessions" / "test-hook-cmd.json").exists()    # le bulletin a bien ete ecrit


def test_aucune_commande_de_hook_ne_contient_backtick_dollar_ou_backslash():
    for ev, grps in _hooks().items():
        for g in grps:
            for x in g["hooks"]:
                assert not _INTERDIT.search(x["command"]), (ev, x["command"])
                assert x.get("timeout", 10) <= 15, "un hook du bulletin doit rester sous la seconde ; 15 s est le plafond"
