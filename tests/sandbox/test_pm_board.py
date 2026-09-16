"""Tableau PM : `compute` est PUR — chaque alerte a son cas positif et son no-op, chaque source absente rend
un AVEUGLEMENT visible et jamais un « 0 alerte »."""
import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import board as B  # noqa: E402

NOW = 1_800_000_000.0
ROOT = "c:/x/agagi"


def _reg(name, sid, cwd=ROOT, started=NOW - 600):
    return {"pid": 1, "session_id": sid, "name": name, "cwd": cwd, "kind": "interactive",
            "started_at": started, "updated_at": NOW}


def _bul(sid, files=(), claims=(), heartbeat=NOW - 60, branch="feat/x"):
    return {"session_id": sid, "files_touched": list(files), "claims": list(claims),
            "heartbeat_at": heartbeat, "branch": branch}


def _snap(**kw):
    base = {"now": NOW, "repo_root": ROOT, "psutil": True,
            "registry": [_reg("agagi-11", "s1"), _reg("agagi-52", "s2"), _reg("elysium-d4", "e1", cwd="c:/x/elysium")],
            "bulletins": [_bul("s1"), _bul("s2")],
            "worktrees": [{"path": ROOT, "branch": "main", "head": "abc", "merged": True, "head_time": NOW}],
            "commits": [{"sha": "abc1234567", "sujet": "ok", "insertions": 3, "deletions": 2, "amputations": []}],
            "leases": {"live": [], "dead": []}, "processes": [], "cpu_5min_pct": 12.0,
            "backlog_paths": {"P4.9": ["tools/evo_runs/s2_credit_ablation.py"], "P2.78": []}}
    base.update(kw)
    return base


def _ids(board, id_):
    return [a for a in board["alertes"] if a["id"] == id_]


def test_NOOP_exact_un_etat_sain_ne_leve_AUCUNE_alerte_ni_aveuglement():
    b = B.compute(_snap())
    assert b["alertes"] == [] and b["aveugle"] == []
    assert [s["name"] for s in b["sessions"]] == ["agagi-11", "agagi-52"]     # elysium hors dépôt


def test_A1_deux_sessions_sur_le_meme_fichier_et_pas_une_seule():
    b = B.compute(_snap(bulletins=[_bul("s1", files=["src/paths.py"]), _bul("s2", files=["src/paths.py", "x.py"])]))
    a = _ids(b, "A1")
    assert len(a) == 1 and a[0]["preuve"] == {"fichier": "src/paths.py", "sessions": ["agagi-11", "agagi-52"]}
    assert a[0]["cle"] == "A1:src/paths.py" and a[0]["gravite"] == "alerte"
    assert _ids(B.compute(_snap(bulletins=[_bul("s1", files=["x.py"]), _bul("s2", files=["y.py"])])), "A1") == []


def test_A2_bail_orphelin_ALERTE_et_ttl_expire_detenteur_vivant_INFO():
    morts = [{"resource": "kuzu", "pid": 9, "owner": "o", "created": 0, "expires_at": 1, "ttl_s": 1, "vivant": False,
              "detenteur_vivant": False},
             {"resource": "pm", "pid": 8, "owner": "p", "created": 0, "expires_at": 1, "ttl_s": 1, "vivant": False,
              "detenteur_vivant": True}]
    b = B.compute(_snap(leases={"live": [], "dead": morts}))
    a = {x["cle"]: x["gravite"] for x in _ids(b, "A2")}
    assert a == {"A2:kuzu": "alerte", "A2:pm": "info"}


def test_A2_sans_psutil_l_identite_des_detenteurs_est_AVEUGLE_pas_fausse():
    b = B.compute(_snap(psutil=False, leases={"live": [], "dead": [{"resource": "kuzu", "pid": 9, "owner": "o",
                  "created": 0, "expires_at": 1, "ttl_s": 1, "vivant": False, "detenteur_vivant": False}]}))
    assert _ids(b, "A2") == [] and any("psutil" in x for x in b["aveugle"])


def test_A3_worktree_sans_session_fusionne_ou_inactif_et_pas_celui_d_une_session():
    wts = [{"path": ROOT, "branch": "main", "head": "a", "merged": True, "head_time": NOW},
           {"path": ROOT + "/.claude/worktrees/wf-1", "branch": "wf-1", "head": "b", "merged": True, "head_time": NOW},
           {"path": ROOT + "/.worktrees/vieux", "branch": "chantier/vieux", "head": "c", "merged": False,
            "head_time": NOW - 8 * 86400},
           {"path": ROOT + "/.worktrees/actif", "branch": "chantier/actif", "head": "d", "merged": False,
            "head_time": NOW - 8 * 86400}]
    reg = [_reg("agagi-11", "s1"), _reg("agagi-52", "s2", cwd=ROOT + "/.worktrees/actif")]
    b = B.compute(_snap(worktrees=wts, registry=reg))
    assert sorted(a["cle"] for a in _ids(b, "A3")) == ["A3:" + ROOT + "/.claude/worktrees/wf-1", "A3:" + ROOT + "/.worktrees/vieux"]


def test_A4_commit_a_grosse_suppression_OU_amputation_et_pas_un_commit_ordinaire():
    gros = {"sha": "dead000000", "sujet": "menage", "insertions": 0, "deletions": 2372, "amputations": []}
    ampute = {"sha": "beef000000", "sujet": "x", "insertions": 1, "deletions": 120,
              "amputations": [{"chemin": "docs/roadmap/PRIORITES_ET_DETTES.md", "avant": 2352, "apres": 0}]}
    b = B.compute(_snap(commits=[gros, ampute, {"sha": "ok", "sujet": "ok", "insertions": 1, "deletions": 499, "amputations": []}]))
    assert sorted(a["cle"] for a in _ids(b, "A4")) == ["A4:beef000000", "A4:dead000000"]


def test_A5_deux_simulations_en_vol_ou_cpu_sature_et_ni_l_un_ni_l_autre_sinon():
    procs = [{"pid": 1, "age_min": 5, "rss_mb": 10, "cmd": "python tools/evo_runs/x_run.py", "simulation": True},
             {"pid": 2, "age_min": 5, "rss_mb": 10, "cmd": "python tools/s2_probe.py", "simulation": True},
             {"pid": 3, "age_min": 5, "rss_mb": 10, "cmd": "python -m pytest", "simulation": False}]
    b = B.compute(_snap(processes=procs))
    assert [a["cle"] for a in _ids(b, "A5")] == ["A5:sims"] and b["charge_connue"]["sims_en_vol"] == 2
    b2 = B.compute(_snap(cpu_5min_pct=91.0))
    assert [a["cle"] for a in _ids(b2, "A5")] == ["A5:cpu"]
    assert _ids(B.compute(_snap(processes=procs[:1], cpu_5min_pct=79.9)), "A5") == []


def test_A6_meme_P_item_revendique_par_deux_sessions():
    b = B.compute(_snap(bulletins=[_bul("s1", claims=["P4.9"]), _bul("s2", claims=["P4.9", "P2.78"])]))
    a = _ids(b, "A6")
    assert len(a) == 1 and a[0]["preuve"] == {"p_item": "P4.9", "sessions": ["agagi-11", "agagi-52"]}


def test_A7_session_active_plus_d_une_heure_sans_claim_ni_inference_est_une_INFO():
    reg = [_reg("agagi-11", "s1", started=NOW - 2 * 3600), _reg("agagi-52", "s2", started=NOW - 2 * 3600)]
    bul = [_bul("s1"), _bul("s2", files=["tools/evo_runs/s2_credit_ablation.py"])]
    b = B.compute(_snap(registry=reg, bulletins=bul))
    a = _ids(b, "A7")
    assert [x["cle"] for x in a] == ["A7:agagi-11"] and a[0]["gravite"] == "info"
    s2 = [s for s in b["sessions"] if s["name"] == "agagi-52"][0]
    assert s2["claims_inferes"] == ["P4.9"]                     # inféré des fichiers touchés, marqué comme tel


def test_A8_heartbeat_vieux_de_plus_de_deux_heures_est_une_INFO():
    b = B.compute(_snap(bulletins=[_bul("s1", heartbeat=NOW - 3 * 3600), _bul("s2")]))
    assert [x["cle"] for x in _ids(b, "A8")] == ["A8:agagi-11"]


def test_chaque_source_ABSENTE_est_nommee_AVEUGLE_et_ses_alertes_sont_supprimees():
    b = B.compute(_snap(registry=None, bulletins=None, worktrees=None, commits=None, leases=None, processes=None,
                        cpu_5min_pct=None, backlog_paths=None))
    assert b["alertes"] == [] and b["sessions"] == []
    assert len(b["aveugle"]) == 7
    assert b["charge_connue"] == {"sims_en_vol": None, "cpu_5min_pct": None, "bails_vivants": None}
    md = B.render_md(b)
    assert md.splitlines()[2].startswith("AVEUGLE SUR")          # en tête, avant toute autre ligne


def test_render_et_summary_portent_les_alertes_et_la_charge():
    b = B.compute(_snap(bulletins=[_bul("s1", files=["a.py"]), _bul("s2", files=["a.py"])]))
    md = B.render_md(b)
    assert "A1" in md and "agagi-11" in md and "charge connue" in md.lower()
    s = B.summary(b)
    assert len(s.splitlines()) <= 25 and "A1" in s


def test_main_ecrit_BOARD_json_et_md_sous_pm_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    code = B.main(["--repo-root", os.getcwd(), "--registry-dir", str(tmp_path / "aucun"),
                   "--sessions-dir", str(tmp_path / "aucun")])
    assert code == 0
    j = json.loads((tmp_path / "pm" / "BOARD.json").read_text(encoding="utf-8"))
    assert "registre natif" in " ".join(j["aveugle"])
    assert (tmp_path / "pm" / "BOARD.md").read_text(encoding="utf-8").startswith("# Tableau PM")
