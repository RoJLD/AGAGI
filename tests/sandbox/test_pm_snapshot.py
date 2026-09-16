"""Lecteurs du tableau PM : chaque source absente rend None (jamais une valeur), chaque source presente est lue."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import snapshot as S  # noqa: E402


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, encoding="utf-8", check=True).stdout


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "depot"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "a.md").write_text("\n".join(f"ligne {i}" for i in range(300)), encoding="utf-8")
    _git(r, "add", "a.md")
    _git(r, "commit", "-q", "-m", "init")
    return r


def test_registry_ABSENT_rend_None_pas_une_liste_vide(tmp_path):
    assert S.read_registry(str(tmp_path / "nulle_part")) is None


def test_registry_lit_les_champs_natifs_et_convertit_les_millisecondes(tmp_path):
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "18276.json").write_text(json.dumps({"pid": 18276, "sessionId": "6f3a", "cwd": "c:\\x\\AGAGI",
                                              "startedAt": 1789515082665, "updatedAt": 1789515090000,
                                              "kind": "interactive", "name": "agagi-11"}), encoding="utf-8")
    (d / "casse.json").write_text("{pas du json", encoding="utf-8")
    reg = S.read_registry(str(d))
    assert len(reg) == 2
    ok = [r for r in reg if "illisible" not in r][0]
    assert ok["name"] == "agagi-11" and ok["session_id"] == "6f3a" and ok["pid"] == 18276
    assert ok["started_at"] == pytest.approx(1789515082.665)
    assert [r for r in reg if "illisible" in r][0]["illisible"] == "casse.json"


def test_bulletins_ABSENTS_rend_None_et_presents_sont_lus(tmp_path):
    assert S.read_bulletins(str(tmp_path / "rien")) is None
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "s1.json").write_text(json.dumps({"session_id": "s1", "claims": ["P4.9"]}), encoding="utf-8")
    assert S.read_bulletins(str(d)) == [{"session_id": "s1", "claims": ["P4.9"]}]


def test_worktrees_liste_l_arbre_principal_avec_sa_branche(repo):
    w = S.read_worktrees(str(repo))
    assert len(w) == 1 and w[0]["branch"] == "main" and w[0]["path"] == S.norm(str(repo))
    assert w[0]["head_time"] is not None and w[0]["merged"] is True


def test_worktrees_hors_depot_rend_None(tmp_path):
    assert S.read_worktrees(str(tmp_path)) is None


def test_commits_recents_mesurent_les_suppressions_et_l_AMPUTATION(repo):
    (repo / "a.md").write_text("ligne 0\n", encoding="utf-8")            # 300 -> 1 ligne non vide
    _git(repo, "commit", "-q", "-am", "ampute")
    c = S.read_recent_commits(str(repo), since="1 day ago", amputation_seuil=100)
    assert c[0]["sujet"] == "ampute" and c[0]["deletions"] >= 299
    assert c[0]["amputations"] == [{"chemin": "a.md", "avant": 300, "apres": 1}]
    assert c[1]["sujet"] == "init" and c[1]["amputations"] == []


def test_leases_lit_le_repertoire_injecte_et_dit_si_le_detenteur_vit(tmp_path):
    from tools.jobs import lease as L
    L.acquire("kuzu", owner="vivant", ttl_s=3600.0, leases_dir=tmp_path, pid=os.getpid())
    L.acquire("pm", owner="fantome", leases_dir=tmp_path, pid=999_999)
    lz = S.read_leases(leases_dir=tmp_path)
    assert [x["resource"] for x in lz["live"]] == ["kuzu"]
    mort = lz["dead"][0]
    assert mort["resource"] == "pm" and mort["vivant"] is False and mort["detenteur_vivant"] is False


def test_backlog_paths_associe_chaque_P_item_aux_chemins_qu_il_cite(tmp_path):
    d = tmp_path / "docs" / "roadmap"
    d.mkdir(parents=True)
    (d / "PRIORITES_ET_DETTES.md").write_text(
        "**P4.9 — OUVERTE — ablation du credit.**\nQuoi : `tools/evo_runs/s2_credit_ablation.py` et `results/x.json`.\n\n"
        "**P2.78 — OUVERTE — autre.**\nRien de cite ici.\n", encoding="utf-8")
    bp = S.read_backlog_paths(str(tmp_path))
    assert bp["P4.9"] == ["results/x.json", "tools/evo_runs/s2_credit_ablation.py"]
    assert bp["P2.78"] == []
    assert S.read_backlog_paths(str(tmp_path / "ailleurs")) is None


def test_snapshot_porte_toutes_les_cles_et_ne_leve_pas_sans_sources(tmp_path, repo):
    snap = S.snapshot(str(repo), registry_dir=str(tmp_path / "r"), sessions_dir=str(tmp_path / "s"),
                      leases_dir=tmp_path / "l", now=1000.0)
    assert snap["now"] == 1000.0 and snap["repo_root"] == S.norm(str(repo))
    assert snap["registry"] is None and snap["bulletins"] is None
    assert snap["backlog_paths"] is None                      # pas de backlog dans ce depot factice
    assert snap["leases"] == {"live": [], "dead": []}
    assert set(snap) >= {"psutil", "worktrees", "commits", "processes", "cpu_5min_pct"}
