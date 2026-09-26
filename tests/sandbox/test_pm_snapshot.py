"""Lecteurs du tableau PM : chaque source absente rend None (jamais une valeur), chaque source presente est lue."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import snapshot as S  # noqa: E402
from tools._git_env import env_isole  # noqa: E402  (P2.107 b : un dépôt JETABLE isole GIT_*, règle à deux faces)


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, encoding="utf-8", check=True,
                          env=env_isole()).stdout


def test_P2_107_b_le_git_du_depot_jetable_ISOLE_un_GIT_DIR_qui_fuit(tmp_path, monkeypatch):
    """P2.107 (b) : cette aide vise un dépôt JETABLE ; elle ISOLE la famille GIT_* (règle à deux faces). La fixture de
    conftest purge l'environnement AVANT le test ; un `GIT_DIR` posé PENDANT le test, lui, détournait l'`init` vers le
    dépôt pointé — et le `user.email` qui suit écrasait son identité (P2.86). ROUGE sans `env=env_isole()`."""
    sentinelle = tmp_path / "sentinelle"
    sentinelle.mkdir()
    _git(sentinelle, "init", "-q", "-b", "main")
    monkeypatch.setenv("GIT_DIR", (sentinelle / ".git").as_posix())
    cible = tmp_path / "cible"
    cible.mkdir()
    _git(cible, "init", "-q", "-b", "main")
    assert (cible / ".git").is_dir(), "l'init a ete DETOURNE vers la sentinelle"


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


def test_registry_JSON_non_dict_est_rapporte_illisible_pas_une_exception(tmp_path):
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "valide.json").write_text(json.dumps({"pid": 1, "sessionId": "s", "name": "n"}), encoding="utf-8")
    (d / "liste.json").write_text(json.dumps([1, 2]), encoding="utf-8")
    (d / "nul.json").write_text(json.dumps(None), encoding="utf-8")
    reg = S.read_registry(str(d))
    assert len(reg) == 3
    illisibles = {r["illisible"] for r in reg if "illisible" in r}
    assert illisibles == {"liste.json", "nul.json"}
    ok = [r for r in reg if "illisible" not in r][0]
    assert ok["name"] == "n" and ok["pid"] == 1


def test_bulletins_ABSENTS_rend_None_et_presents_sont_lus(tmp_path):
    assert S.read_bulletins(str(tmp_path / "rien")) is None
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "s1.json").write_text(json.dumps({"session_id": "s1", "claims": ["P4.9"]}), encoding="utf-8")
    assert S.read_bulletins(str(d)) == [{"session_id": "s1", "claims": ["P4.9"]}]


def test_worktrees_liste_l_arbre_principal_avec_sa_branche(repo):
    w = S.read_worktrees(str(repo))
    assert len(w) == 1 and w[0]["branch"] == "main" and w[0]["path"] == S.norm(str(repo))
    assert w[0]["head_time"] is not None and w[0]["locked"] is False
    # CONTRE-EXEMPLE GELE : `main` est fusionnee DANS `main`, donc `git branch --merged main` la
    # liste toujours. La compter comme fusionnee faisait d'un worktree pose sur la branche de base
    # une A3 PERMANENTE -- une alerte qu'aucune action ne peut eteindre.
    assert w[0]["merged"] is False


def test_worktrees_lit_les_worktrees_LIES_leur_branche_et_l_etat_VERROUILLE(repo, tmp_path):
    wt = tmp_path / "wt-libre"
    wv = tmp_path / "wt-verrouille"
    _git(repo, "worktree", "add", "-q", "-b", "chantier/libre", str(wt))
    _git(repo, "worktree", "add", "-q", "-b", "chantier/verrou", str(wv))
    _git(repo, "worktree", "lock", str(wv), "--reason", "garde volontairement")
    par_branche = {w["branch"]: w for w in S.read_worktrees(str(repo))}
    assert par_branche["chantier/libre"]["locked"] is False
    assert par_branche["chantier/verrou"]["locked"] is True
    assert par_branche["chantier/libre"]["merged"] is True          # creee depuis main, donc fusionnee


def test_read_cpu_pct_CONTROLE_POSITIF_rend_la_mesure_instantanee_et_None_sans_psutil(monkeypatch):
    """CONTRE-EXEMPLE GELE (C1) : `getloadavg()` est EMULE par psutil sur Windows depuis un thread
    qui doit avoir tourne ~5 min -- un processus court lisait **0.0** pendant que
    `cpu_percent(interval=1)` rendait 84.9. Un zero FABRIQUE sur la mesure de charge. Le controle
    positif impose une valeur connue a travers la seule fonction desormais appelee."""
    class FauxPsutil:
        def __init__(self):
            self.vu = []

        def cpu_percent(self, interval=None):
            self.vu.append(interval)
            return 42.0

        def getloadavg(self):                      # si l'implementation y revenait, le test le verrait
            raise AssertionError("read_cpu_pct ne doit PLUS lire getloadavg")

    faux = FauxPsutil()
    monkeypatch.setattr(S, "_psutil", lambda: faux)
    assert S.read_cpu_pct() == 42.0 and faux.vu == [1.0]
    monkeypatch.setattr(S, "_psutil", lambda: None)
    assert S.read_cpu_pct() is None


def test_read_cpu_pct_rend_None_et_jamais_0_quand_psutil_leve(monkeypatch):
    class Casse:
        def cpu_percent(self, interval=None):
            raise RuntimeError("compteur indisponible")
    monkeypatch.setattr(S, "_psutil", lambda: Casse())
    assert S.read_cpu_pct() is None


def test_read_registry_mesure_la_VIE_de_chaque_pid_et_None_sans_psutil(tmp_path, monkeypatch):
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "vivant.json").write_text(json.dumps({"pid": os.getpid(), "sessionId": "s1", "name": "vivant"}),
                                   encoding="utf-8")
    (d / "mort.json").write_text(json.dumps({"pid": 999_999, "sessionId": "s2", "name": "mort"}), encoding="utf-8")
    par_nom = {r["name"]: r for r in S.read_registry(str(d)) if "illisible" not in r}
    assert par_nom["vivant"]["alive"] is True and par_nom["mort"]["alive"] is False
    monkeypatch.setattr(S, "_psutil", lambda: None)
    assert all(r["alive"] is None for r in S.read_registry(str(d)))       # « je ne sais pas », pas « mort »


def test_read_registry_avec_vie_False_ne_consulte_PAS_psutil_et_rend_alive_None_pas_False(tmp_path, monkeypatch):
    """Défaut 2 (2026-09-24) : le hook `tool` relit le registre à CHAQUE outil pour ré-résoudre le nom, et l'import
    de psutil y coûtait ~70 ms sous charge contre ~2 ms la lecture. Sans mesure, `alive` vaut None (« non mesuré »),
    jamais False — et le reste de l'entrée est lu à l'identique."""
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "1.json").write_text(json.dumps({"pid": os.getpid(), "sessionId": "s1", "name": "n"}), encoding="utf-8")
    appels, vrai = [], S._psutil
    monkeypatch.setattr(S, "_psutil", lambda: appels.append(1) or vrai())
    sans = S.read_registry(str(d), avec_vie=False)
    assert appels == [] and [(r["name"], r["alive"]) for r in sans] == [("n", None)]
    avec = S.read_registry(str(d))                                          # contrôle positif : par défaut, psutil EST consulté
    assert appels == [1] and avec[0]["alive"] is True


def test_racine_commune_rend_l_arbre_PRINCIPAL_depuis_un_worktree_et_None_hors_depot(repo, tmp_path):
    wt = tmp_path / "wt"
    _git(repo, "worktree", "add", "-q", "-b", "chantier/x", str(wt))
    attendu = os.path.realpath(str(repo)).replace("\\", "/")
    assert S.racine_commune(str(wt)) == attendu
    assert S.racine_commune(str(repo)) == attendu
    assert S.racine_commune(str(tmp_path / "pas_un_depot_du_tout")) is None


def test_ancrer_data_root_pointe_les_donnees_sur_le_depot_COMMUN_et_respecte_la_variable(repo, tmp_path, monkeypatch):
    """C2.1 : sans ancrage, un hook lance dans un worktree ecrit ses bulletins dans
    `<worktree>/data/sessions` -- chaque worktree tient SON tableau et le PM de l'arbre principal est
    aveugle sur ces sessions SANS le dire."""
    from src import paths
    wt = tmp_path / "wt"
    _git(repo, "worktree", "add", "-q", "-b", "chantier/ancre", str(wt))
    monkeypatch.chdir(wt)
    # E5 (etat global) : la variable est d'ordinaire ABSENTE, donc delenv(raising=False) sur une cle
    # jamais posee n'enregistre rien -- monkeypatch ne peut restaurer une absence qu'il n'a pas vue.
    # Poser une sentinelle AVANT force l'enregistrement : le teardown efface ensuite la cle entiere.
    monkeypatch.setenv("AGAGI_DATA_ROOT", "sentinelle-a-effacer")
    monkeypatch.delenv("AGAGI_DATA_ROOT", raising=False)
    pose = S.ancrer_data_root()
    principal = os.path.realpath(str(repo)).replace("\\", "/")
    assert pose == principal + "/data"
    assert paths.sessions_dir().startswith(principal + "/data/sessions")

    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path / "ailleurs").replace("\\", "/"))
    assert S.ancrer_data_root() == str(tmp_path / "ailleurs").replace("\\", "/")
    assert os.environ["AGAGI_DATA_ROOT"] == str(tmp_path / "ailleurs").replace("\\", "/")


def test_read_hook_errors_compte_PAR_EVENEMENT_dans_la_fenetre(tmp_path):
    p = tmp_path / "hook_errors.log"
    p.write_text(
        "2026-09-16T10:00:00 stop ValueError: hook sans session_id\n"
        "Traceback (most recent call last):\n  File \"x.py\", line 1\nValueError: boum\n"
        "2026-09-16T11:00:00 stop ValueError: hook sans session_id\n"
        "2026-09-16T11:30:00 start OSError: disque plein\n"
        "2026-09-10T09:00:00 tool KeyError: trop vieux\n", encoding="utf-8")
    import time as T
    now = T.mktime(T.strptime("2026-09-16T12:00:00", "%Y-%m-%dT%H:%M:%S"))
    assert S.read_hook_errors(str(tmp_path), now=now) == {"stop": 2, "start": 1}    # le vieux est hors fenetre
    assert S.read_hook_errors(str(tmp_path), now=now, fenetre_s=30 * 86400) == {"stop": 2, "start": 1, "tool": 1}


def test_read_hook_errors_ABSENT_rend_un_dict_VIDE_et_illisible_rend_None(tmp_path, monkeypatch):
    assert S.read_hook_errors(str(tmp_path / "rien")) == {}       # jamais echoue = MESURE, pas lacune
    p = tmp_path / "hook_errors.log"
    p.write_text("2026-09-16T10:00:00 stop ValueError: x\n", encoding="utf-8")

    def refuse(*a, **k):
        raise OSError("verrouille")
    monkeypatch.setattr("builtins.open", refuse)
    assert S.read_hook_errors(str(tmp_path)) is None


def test_backlog_paths_NON_VIDE_sans_aucune_entete_rend_None_et_pas_un_dict_vide(tmp_path):
    """CONTRE-EXEMPLE GELE (I5) : `{}` et `None` ne disent pas la meme chose. Un backlog dont le
    FORMAT a change (aucune entete `**P...`) rendait `{}`, que `compute` lisait comme « aucune entree
    ne cite de chemin » -- une affirmation de fond fabriquee a partir d'une lecture ratee."""
    d = tmp_path / "docs" / "roadmap"
    d.mkdir(parents=True)
    (d / "PRIORITES_ET_DETTES.md").write_text(
        "# Backlog\n\nDu texte sans la moindre entete de P-item, citant `tools/a.py`.\n", encoding="utf-8")
    assert S.read_backlog_paths(str(tmp_path)) is None
    (d / "PRIORITES_ET_DETTES.md").write_text("", encoding="utf-8")
    assert S.read_backlog_paths(str(tmp_path)) == {}              # fichier VIDE : rien a lire, pas une panne


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


def test_backlog_paths_en_tete_composite_attribue_a_CHAQUE_P_item(tmp_path):
    d = tmp_path / "docs" / "roadmap"
    d.mkdir(parents=True)
    (d / "PRIORITES_ET_DETTES.md").write_text(
        "**P1.x / P2.45 — titre.**\nQuoi : `tools/a.py`.\n", encoding="utf-8")
    bp = S.read_backlog_paths(str(tmp_path))
    assert bp["P1.x"] == ["tools/a.py"]
    assert bp["P2.45"] == ["tools/a.py"]


def test_processes_et_cpu_sans_psutil_rendent_None_et_snapshot_le_declare(tmp_path, repo, monkeypatch):
    monkeypatch.setattr(S, "_psutil", lambda: None)
    assert S.read_processes() is None
    assert S.read_cpu_pct() is None
    snap = S.snapshot(str(repo), registry_dir=str(tmp_path / "r"), sessions_dir=str(tmp_path / "s"),
                      leases_dir=tmp_path / "l", pm_dir=str(tmp_path / "pm"), now=1000.0)
    assert snap["psutil"] is False


def test_snapshot_porte_toutes_les_cles_et_ne_leve_pas_sans_sources(tmp_path, repo):
    snap = S.snapshot(str(repo), registry_dir=str(tmp_path / "r"), sessions_dir=str(tmp_path / "s"),
                      leases_dir=tmp_path / "l", pm_dir=str(tmp_path / "pm"), now=1000.0)
    assert snap["now"] == 1000.0 and snap["repo_root"] == S.norm(str(repo))
    assert snap["registry"] is None and snap["bulletins"] is None
    assert snap["backlog_paths"] is None                      # pas de backlog dans ce depot factice
    assert snap["leases"] == {"live": [], "dead": []}
    assert snap["hook_errors"] == {}                          # journal absent : aucun echec MESURE
    assert set(snap) >= {"psutil", "worktrees", "commits", "processes", "cpu_pct", "hook_errors"}


def test_zz_aucune_fuite_de_AGAGI_DATA_ROOT_apres_l_ancrage():
    """Place en DERNIER dans le fichier (l'ordre pytest suit l'ordre de definition) : verifie que
    `test_ancrer_data_root_pointe_les_donnees_sur_le_depot_COMMUN_et_respecte_la_variable` n'a rien
    laisse fuiter dans os.environ pour les tests suivants, dans CE fichier et au-dela."""
    assert not os.environ.get("AGAGI_DATA_ROOT", "").endswith("/depot/data")
