"""Bulletin de session : les hooks l'écrivent, jamais la session ; un hook sort toujours 0."""
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import bulletin as BU  # noqa: E402

NOW = 1_800_000_000.0


def _payload(event, **kw):
    p = {"session_id": "s1", "cwd": "c:/x/agagi", "hook_event_name": event}
    p.update(kw)
    return p


def test_start_cree_le_bulletin_avec_les_champs_du_schema():
    b = BU.appliquer("start", _payload("SessionStart"), {}, now=NOW, branche_fn=lambda cwd: ("feat/x", "c:/x/agagi"))
    assert b["session_id"] == "s1" and b["started_at"] == NOW and b["branch"] == "feat/x"
    assert b["claims"] == [] and b["files_touched"] == [] and b["ended_at"] is None


def test_tool_ajoute_le_fichier_edite_sans_doublon_et_plafonne_a_200():
    b = BU.appliquer("start", _payload("SessionStart"), {}, now=NOW, branche_fn=lambda c: (None, None))
    for i in range(205):
        b = BU.appliquer("tool", _payload("PostToolUse", tool_name="Edit", tool_input={"file_path": f"c:/x/agagi/f{i}.py"}),
                         b, now=NOW + i, branche_fn=lambda c: (None, None))
    b = BU.appliquer("tool", _payload("PostToolUse", tool_name="Write", tool_input={"file_path": "c:/x/agagi/f204.py"}),
                     b, now=NOW + 300, branche_fn=lambda c: (None, None))
    assert len(b["files_touched"]) == 200 and b["files_touched"][-1] == "f204.py"     # relatif au cwd, FIFO
    assert b["files_touched"][0] == "f5.py" and b["last_tool_at"] == NOW + 300


def test_tool_sans_file_path_ne_change_rien():
    b0 = BU.appliquer("start", _payload("SessionStart"), {}, now=NOW, branche_fn=lambda c: (None, None))
    b1 = BU.appliquer("tool", _payload("PostToolUse", tool_name="Bash", tool_input={"command": "ls"}), dict(b0), now=NOW + 1,
                      branche_fn=lambda c: (None, None))
    assert b1["files_touched"] == [] and b1["last_tool_at"] == NOW + 1


def test_tool_sur_bulletin_vide_fixe_le_cwd_des_le_premier_evenement():
    b = BU.appliquer("tool", _payload("PostToolUse", tool_name="Edit", tool_input={"file_path": "c:/x/agagi/f0.py"}),
                     {}, now=NOW, branche_fn=lambda c: (None, None))
    assert b["cwd"] == "c:/x/agagi" and b["files_touched"] == ["f0.py"]


def test_tool_sans_cwd_connu_garde_le_chemin_absolu():
    b = BU.appliquer("tool", _payload("PostToolUse", cwd=None, tool_name="Edit", tool_input={"file_path": "c:/x/agagi/f0.py"}),
                     {}, now=NOW, branche_fn=lambda c: (None, None))
    assert b["cwd"] is None
    assert b["files_touched"] == [BU.norm("c:/x/agagi/f0.py")]


def test_stop_met_le_heartbeat_et_la_branche_et_end_la_fin():
    b = BU.appliquer("start", _payload("SessionStart"), {}, now=NOW, branche_fn=lambda c: ("a", "w"))
    b = BU.appliquer("stop", _payload("Stop"), b, now=NOW + 60, branche_fn=lambda c: ("feat/y", "c:/x/agagi/.worktrees/w"))
    assert b["heartbeat_at"] == NOW + 60 and b["branch"] == "feat/y" and b["worktree"] == "c:/x/agagi/.worktrees/w"
    b = BU.appliquer("end", _payload("SessionEnd"), b, now=NOW + 120, branche_fn=lambda c: (None, None))
    assert b["ended_at"] == NOW + 120


def test_ecrire_puis_charger_est_identite_et_charger_un_absent_rend_un_dict_vide(tmp_path):
    b = BU.appliquer("start", _payload("SessionStart"), {}, now=NOW, branche_fn=lambda c: (None, None))
    BU.ecrire(b, str(tmp_path))
    assert BU.charger("s1", str(tmp_path)) == b
    assert BU.charger("inconnu", str(tmp_path)) == {}
    assert sorted(os.listdir(tmp_path)) == ["s1.json"]                        # pas de .tmp résiduel


def test_nom_depuis_registre_joint_par_sessionId_et_None_sinon(tmp_path):
    (tmp_path / "1.json").write_text(json.dumps({"pid": 1, "sessionId": "s1", "name": "agagi-11"}), encoding="utf-8")
    assert BU.nom_depuis_registre("s1", str(tmp_path)) == "agagi-11"
    assert BU.nom_depuis_registre("s9", str(tmp_path)) is None
    assert BU.nom_depuis_registre("s1", str(tmp_path / "absent")) is None


def test_main_start_ecrit_le_bulletin_imprime_le_resume_et_sort_0(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "reg"))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("SessionStart"))))
    assert BU.main(["start"]) == 0
    b = json.loads((tmp_path / "sessions" / "s1.json").read_text(encoding="utf-8"))
    assert b["session_id"] == "s1" and b["name"] is None
    assert "[PM] tableau absent" in capsys.readouterr().out


def test_main_start_avec_BOARD_en_cache_imprime_le_resume_du_tableau(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "reg"))
    (tmp_path / "pm").mkdir()
    (tmp_path / "pm" / "BOARD.json").write_text(json.dumps({"generated_at": NOW, "aveugle": ["bails (tools/jobs)"], "sessions": [],
                                                           "alertes": [], "charge_connue": {"sims_en_vol": 0, "cpu_5min_pct": 1.0, "bails_vivants": []}}),
                                                encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("SessionStart"))))
    assert BU.main(["start"]) == 0
    out = capsys.readouterr().out
    assert "[PM] AVEUGLE SUR bails" in out and "0 sessions AGAGI" in out


def test_main_avec_stdin_illisible_sort_0_et_journalise(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr("sys.stdin", io.StringIO("{pas du json"))
    assert BU.main(["stop"]) == 0
    log = (tmp_path / "pm" / "hook_errors.log").read_text(encoding="utf-8")
    assert "stop" in log and "JSONDecodeError" in log


def test_main_claim_ajoute_le_P_item_sans_doublon(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "reg"))
    assert BU.main(["claim", "P4.9", "--session", "s1"]) == 0
    assert BU.main(["claim", "P4.9", "--session", "s1"]) == 0
    assert BU.main(["claim", "P2.78", "--session", "s1"]) == 0
    assert json.loads((tmp_path / "sessions" / "s1.json").read_text(encoding="utf-8"))["claims"] == ["P4.9", "P2.78"]


def test_main_claim_sans_session_resolue_sort_0_et_l_ecrit(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "reg"))         # registre absent -> aucune session
    assert BU.main(["claim", "P4.9"]) == 0
    assert "session introuvable" in capsys.readouterr().out


def test_main_avec_argv_malforme_sort_0_et_journalise_argv(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    assert BU.main(["bogus"]) == 0
    log = (tmp_path / "pm" / "hook_errors.log").read_text(encoding="utf-8")
    assert "argv" in log
