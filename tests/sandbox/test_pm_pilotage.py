# -*- coding: utf-8 -*-
"""Pilotage : `compute_pilotage` est PURE et `parse_roadmap` réutilise le cliquet du backlog.
EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde ni ne prend de bail."""
import json
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import pilotage as P  # noqa: E402

_LEASE_GUARD_EXEMPT = True

NOW = 1_800_000_000.0


def test_la_racine_est_ancree_sur_le_module_et_en_POSIX():
    """`find_repo_root` essaie `Path.cwd()` EN PREMIER (tools/parity_check.py:44-47) : lancé depuis un autre
    dépôt il rend l'autre dépôt, et le pilotage accuserait alors les bons fichiers d'être absents — un
    négatif FABRIQUÉ. La racine s'ancre donc sur le MODULE, et se publie en POSIX (un antislash dans un
    href est encodé %5C et VS Code ne le résout pas)."""
    r = P.racine_depot()
    assert "\\" not in r, f"la racine doit être en POSIX : {r!r}"
    assert os.path.isdir(os.path.join(r, "tools", "pm")), r
    assert os.path.isfile(os.path.join(r, "docs", "roadmap", "PRIORITES_ET_DETTES.md")), r


_BACKLOG_SYNTH = """# Backlog synthétique

**P2.10 — ⚠️ OUVERTE (2026-09-01) — une entrée ouverte qui cite `tools/cost_guard.py`.**
Corps de l'entrée.
<!-- closes_when:grep_present=tools/cost_guard.py::process_time -->

**P2.11 — rang 3 — ✅ CLOSE le 2026-09-02 — une entrée close.**
Corps.

**P2.12 — 🗑️ PÉRIMÉE (2026-09-03) — une entrée périmée.**
Corps.

**P2.0 / P2.1 — rang 14 ter — OUVERTE (2026-09-04) — une tête COMPOSITE.**
Corps de la composite.

**P4.9 — OUVERTE (2026-09-05) —
rang 4 quinquies — le rang est sur la DEUXIÈME ligne, et porte un suffixe long.**
Corps.
"""


def test_la_parite_porte_sur_les_BLOCS_pas_sur_les_entrees():
    """DÉFAUT BLOQUANT trouvé en revue (spec §2.2) : `compter_entrees` compte des LIGNES de tête, donc une
    tête composite `P2.0 / P2.1` vaut UN. Asserter la parité sur les ENTRÉES la ferait lever au premier
    composite, `compute_pilotage` tomberait dans le `except` du service et TOUT le pilotage deviendrait
    aveugle à cause d'une seule tête."""
    from tools.check_backlog_freshness import compter_entrees
    out = P.parse_roadmap(_BACKLOG_SYNTH, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    assert out["comptes"]["blocs"] == compter_entrees(_BACKLOG_SYNTH) == 5
    assert out["comptes"]["numeros"] == 6, "la composite donne DEUX entrées après l'assertion"
    assert len(out["entrees"]) == 6


def test_tete_composite_une_entree_par_numero_memes_bornes():
    out = P.parse_roadmap(_BACKLOG_SYNTH, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    comp = [e for e in out["entrees"] if e["num"] in ("P2.0", "P2.1")]
    assert [e["num"] for e in comp] == ["P2.0", "P2.1"]
    assert comp[0]["nums"] == comp[1]["nums"] == ["P2.0", "P2.1"]
    assert comp[0]["bloc"] == comp[1]["bloc"]
    assert comp[0]["lignes"] == comp[1]["lignes"]


def test_statuts_rang_et_date():
    out = P.parse_roadmap(_BACKLOG_SYNTH, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    par = {e["num"]: e for e in out["entrees"]}
    assert par["P2.10"]["statut"] == "ouverte" and par["P2.10"]["date"] == "2026-09-01"
    assert par["P2.11"]["statut"] == "close" and par["P2.11"]["rang"] == "3"
    assert par["P2.12"]["statut"] == "perimee"
    assert par["P2.0"]["rang"] == "14 ter"
    assert par["P4.9"]["rang"] == "4 quinquies", "rang sur la 2e ligne, suffixe NON tronqué"
    assert par["P2.10"]["priorite"] == "P2" and par["P4.9"]["priorite"] == "P4"


def test_ordre_des_rangs_par_base_puis_suffixe():
    """Un tri de CHAÎNES mettrait `14 quater` avant `14 ter` et `10` avant `2` : la vue centrale de
    l'avancement serait illisible. Et un rang n'est pas unique — 5 rangs sont portés par deux entrées sur
    le backlog réel —, donc la direction est une liste par rang."""
    txt = _BACKLOG_SYNTH + """
**P2.20 — rang 14 quater — OUVERTE (2026-09-06) — après ter.**
Corps.

**P2.21 — rang 2 — OUVERTE (2026-09-07) — avant dix.**
Corps.

**P2.22 — rang 10 — OUVERTE (2026-09-08) — après deux.**
Corps.
"""
    out = P.parse_roadmap(txt, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    rangs = [r["rang"] for r in out["direction"]["rangs"]]
    assert rangs == ["2", "3", "4 quinquies", "10", "14 ter", "14 quater"], rangs
    assert all(isinstance(r["p_items"], list) for r in out["direction"]["rangs"])


def test_clause_REELLE_sur_le_depot_trois_reponses_connues():
    """Contrôle positif de la couche d'évaluation, sans évaluateur factice : `_evalue_clause` juge contre
    le dépôt du module et exige un fichier SUIVI par git. Deux réponses connues : un motif présent dans
    un fichier suivi → true ; un chemin qui n'existe pas → false. La branche « existe mais non suivi par git »
    est couverte par le test suivant avec un dépôt git jetable."""
    txt = ("**P9.1 — OUVERTE (2026-09-01) — vraie.**\nCorps.\n"
           "<!-- closes_when:grep_present=tools/cost_guard.py::process_time -->\n\n"
           "**P9.2 — OUVERTE (2026-09-02) — fausse.**\nCorps.\n"
           "<!-- closes_when:path_present=zzz/nexiste/pas.py -->\n\n"
           "**P9.3 — OUVERTE (2026-09-03) — inexistant.**\nCorps.\n"
           "<!-- closes_when:path_present=" + os.path.abspath(os.sep).replace(os.sep, "/") + "tmp_hors_depot.py -->\n")
    out = P.parse_roadmap(txt, P.racine_depot(), NOW)              # évaluateur RÉEL
    par = {e["num"]: e for e in out["entrees"]}
    assert par["P9.1"]["clause"]["satisfaite"] is True
    assert par["P9.2"]["clause"]["satisfaite"] is False
    assert par["P9.3"]["clause"]["satisfaite"] is False


def test_clause_sur_un_fichier_qui_EXISTE_mais_n_est_PAS_SUIVI_par_git(tmp_path, monkeypatch):
    """Troisième réponse connue, celle que le cas d'origine n'exerçait pas : `_evalue_clause` rend `None`
    PLUS une raison quand le fichier existe mais n'est pas suivi par git — la clause est alors invérifiable
    sur un clone. Il faut un dépôt git JETABLE pour l'atteindre : `_evalue_clause` juge contre le `_ROOT`
    de son module, et un test n'écrit jamais dans l'arbre partagé (P2.81)."""
    import subprocess
    import tools.check_backlog_freshness as cb

    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    (tmp_path / "temoin.py").write_text("x = 1", encoding="utf-8")
    monkeypatch.setattr(cb, "_ROOT", str(tmp_path))

    txt = ("**P9.6 — OUVERTE (2026-09-01) — cite un fichier present mais non suivi.**\nCorps.\n"
           "<!-- closes_when:path_present=temoin.py -->\n")
    out = P.parse_roadmap(txt, str(tmp_path), NOW)          # évaluateur RÉEL
    clause = out["entrees"][0]["clause"]
    assert clause["satisfaite"] is None, clause
    assert "PAS SUIVI par git" in (clause["raison"] or ""), clause


def test_les_chemins_non_captes_par_le_motif_sont_COMPTES_jamais_avales():
    """Le motif du cliquet n'admet que py|md|json|yml|yaml et refuse un chemin commençant par un point :
    mesuré le 2026-09-24, 163 des 364 fragments backtickés du backlog réel sont invisibles. Présenter la
    liste comme complète serait un motif qui TRONQUE en silence."""
    txt = ("**P9.4 — OUVERTE (2026-09-01) — cite `tools/cost_guard.py`, `.github/workflows/ci.yml` "
           "et `tools/hooks/pre-commit`.**\nCorps.\n")
    out = P.parse_roadmap(txt, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    e = out["entrees"][0]
    assert [c["rel"] for c in e["chemins"]] == ["tools/cost_guard.py"]
    assert e["chemins_non_captes"] == 2, "les deux autres sont comptés, jamais présentés comme absents"


def test_bloc_illisible_est_COMPTE_jamais_perdu(monkeypatch):
    """Une exception sur UN bloc ne fait pas disparaître l'entrée : elle devient `illisible` et la parité
    tient. Sans ce cas, une entrée mal formée réduirait silencieusement le compte publié."""
    txt = "**P9.5 — OUVERTE (2026-09-01) — normale.**\nCorps.\n"
    def _boum(*a, **k):
        raise RuntimeError("bloc casse")
    monkeypatch.setattr(P, "_entrees_du_bloc", _boum)
    out = P.parse_roadmap(txt, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    assert out["comptes"]["illisibles"] == 1
    assert out["entrees"][0]["statut"] == "illisible"
    assert out["comptes"]["blocs"] == 1


def test_un_lecteur_absent_rend_None_jamais_un_defaut(tmp_path):
    """Porte 14 appliquée aux lecteurs : un fichier absent ne rend ni {} ni [] ni 0 — il rend None, et
    c'est `compute_pilotage` qui en fait une ligne `aveugle`."""
    assert P.read_records_graph(str(tmp_path)) is None
    assert P.read_roles_counts(str(tmp_path)) is None
    assert P.read_board(str(tmp_path)) is None
    assert P.read_backlog(str(tmp_path)) is None


def _git_jetable(*args, cwd):
    """`git` pour un dépôt JETABLE : aucune variable `GIT_*` héritée (un crochet pose `GIT_INDEX_FILE` /
    `GIT_DIR`, le dépôt jetable en hériterait et écrirait dans l'index du vrai dépôt) et une identité
    passée par `-c`, LOCALE à la commande — jamais écrite dans une configuration.

    G1 : `commit.gpgsign=false` aussi, par `-c` — la config GLOBALE de cette machine porte
    `commit.gpgsign = true`, et le commit jetable était signé de la clé personnelle de robla (en-tête
    `gpgsig` mesuré ; un gpg-agent à cache froid pouvait bloquer le test). Aucun tag n'est créé ici, donc
    `tag.gpgsign` n'a rien à neutraliser."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["git", "-c", "user.name=pilotage-test", "-c", "user.email=pilotage@test.invalid",
                           "-c", "commit.gpgsign=false", *args], cwd=str(cwd), check=True, capture_output=True,
                          encoding="utf-8", env=env)


def test__git_jetable_ne_SIGNE_jamais_meme_si_la_config_GLOBALE_l_exige(tmp_path, monkeypatch):
    """G1 : `_git_jetable` se déclarait hermétique mais héritait de `commit.gpgsign = true`, posé dans la
    config GLOBALE de la machine de robla — mesuré, le commit jetable portait un en-tête `gpgsig`, signé de
    sa clé PERSONNELLE ; gpg-agent à cache froid, pinentry pouvait bloquer le test (faux rouge ou garde-temps).

    Le dispositif rend le défaut visible PARTOUT, CI comprise : un HOME factice dont la config globale
    EXIGE une signature par un programme INEXISTANT. Non neutralisée, la signature fait échouer le commit ;
    neutralisée, le commit passe et ne porte aucun `gpgsig`. Contrôle : git lit bien cette config."""
    home = tmp_path / "home"
    home.mkdir()
    gpg_absent = (home / "gpg-absent.exe").as_posix()
    (home / ".gitconfig").write_text("[commit]\n\tgpgsign = true\n[gpg]\n\tprogram = " + gpg_absent + "\n",
                                     encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home))
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    lu = subprocess.run(["git", "config", "--global", "--get", "commit.gpgsign"], cwd=str(tmp_path),
                        capture_output=True, encoding="utf-8", env=env)
    assert lu.stdout.strip() == "true", ("contrôle : la config globale factice doit être celle que git lit",
                                         lu.stdout, lu.stderr)
    depot = tmp_path / "depot"
    depot.mkdir()
    _git_jetable("init", "-q", "-b", "main", cwd=depot)
    (depot / "a.md").write_text("x", encoding="utf-8")
    _git_jetable("add", "a.md", cwd=depot)
    _git_jetable("commit", "-q", "-m", "init", cwd=depot)
    entetes = _git_jetable("cat-file", "commit", "HEAD", cwd=depot).stdout.split("\n\n")[0]
    assert "gpgsig" not in entetes, f"le commit jetable est SIGNÉ : {entetes}"


def _depot_commun_et_worktree(tmp_path, monkeypatch):
    """Un dépôt jetable (un commit) + un worktree lié ; `BOARD.json` et `ROLES_COUNTS.json` écrits dans
    l'arbre PRINCIPAL jetable, jamais dans le worktree. Environnement nettoyé : `AGAGI_DATA_ROOT` et les
    variables `GIT_*` qui détourneraient `git rev-parse` sont retirées par la sentinelle setenv PUIS
    delenv (le seul enchaînement qui enregistre une restauration monkeypatch pour une clé jusque-là
    ABSENTE — cf. `test_pm_snapshot.py`)."""
    for v in ("AGAGI_DATA_ROOT", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        monkeypatch.setenv(v, "sentinelle-a-effacer")
        monkeypatch.delenv(v, raising=False)
    depot = tmp_path / "depot"
    depot.mkdir()
    _git_jetable("init", "-q", "-b", "main", cwd=depot)
    (depot / "a.md").write_text("x", encoding="utf-8")
    _git_jetable("add", "a.md", cwd=depot)
    _git_jetable("commit", "-q", "-m", "init", cwd=depot)
    wt = tmp_path / "wt"
    _git_jetable("worktree", "add", "-q", "-b", "chantier/ancre-pilotage", str(wt), cwd=depot)

    pm_dir = depot / "data" / "pm"
    pm_dir.mkdir(parents=True)
    (pm_dir / "BOARD.json").write_text(json.dumps({"generated_at": NOW, "sessions": []}), encoding="utf-8")
    (pm_dir / "ROLES_COUNTS.json").write_text(json.dumps({"ratio_science_methodo": 1.0}), encoding="utf-8")
    assert not (wt / "data").exists(), "le worktree jetable ne doit porter AUCUN data/ : sinon rien n'est testé"
    return depot, wt


def test_read_board_SEUL_trouve_le_BOARD_du_depot_COMMUN_depuis_un_worktree(tmp_path, monkeypatch):
    """CRITIQUE 1, lecteur par lecteur. Depuis un worktree, `paths.pm_dir(...)` rend un chemin RELATIF
    que `_ancre` joignait à la racine du WORKTREE — où `BOARD.json` n'existe PAS, même quand il existe
    dans le dépôt COMMUN.

    F1 : l'ancien test enchaînait `read_board` PUIS `read_roles_counts` ; la re-revue a mesuré que l'ancrage
    du second était MASQUÉ par l'ordre (le premier posait `AGAGI_DATA_ROOT` pour tout le processus). Chaque
    lecteur est donc appelé SEUL, dans un environnement nettoyé, sur son propre dépôt jetable."""
    _depot, wt = _depot_commun_et_worktree(tmp_path, monkeypatch)
    board = P.read_board(str(wt))
    assert board is not None and board["sessions"] == [], (
        f"read_board(worktree) devait trouver le BOARD.json du dépôt COMMUN : {board}")
    assert "AGAGI_DATA_ROOT" not in os.environ, "l'ancrage doit être une résolution PURE (F1)"


def test_read_roles_counts_SEUL_trouve_ROLES_COUNTS_du_depot_COMMUN_depuis_un_worktree(tmp_path, monkeypatch):
    """Pendant du précédent pour `read_roles_counts`, appelé SEUL — aucun autre lecteur ne tourne avant
    lui dans ce test, donc aucun ancrage d'un autre lecteur ne peut le couvrir."""
    _depot, wt = _depot_commun_et_worktree(tmp_path, monkeypatch)
    roles = P.read_roles_counts(str(wt))
    assert roles is not None and roles["ratio_science_methodo"] == 1.0, (
        f"read_roles_counts(worktree) devait trouver le ROLES_COUNTS.json du dépôt COMMUN : {roles}")
    assert "AGAGI_DATA_ROOT" not in os.environ, "l'ancrage doit être une résolution PURE (F1)"


def test_backlog_VIDE_est_ILLISIBLE_jamais_un_backlog_de_zero_entree():
    """CRITIQUE 2 : `read_backlog` rend `""` sur un fichier vide (pas `None`), et `compter_entrees("")`
    rend 0 -- l'assertion de parité passait et `compute_pilotage` publiait `blocs: 0, numeros: 0` SANS
    une ligne d'aveuglement. Contre-exemple réel : le backlog est déjà tombé de 2352 lignes à 0
    (2026-09-09, `check_backlog_freshness.compter_entrees`). Un fichier vide est une source ILLISIBLE."""
    out = P.compute_pilotage(None, "", None, None, None, NOW, repo_root=P.racine_depot())
    assert out["roadmap"] is None, out["roadmap"]
    assert any("VIDE" in a for a in out["aveugle"]), out["aveugle"]
    texte = json.dumps(out, ensure_ascii=False)
    assert '"blocs": 0' not in texte and '"numeros": 0' not in texte


def test_backlog_SANS_AUCUNE_TETE_reconnue_est_ILLISIBLE():
    """Variante non-vide de CRITIQUE 2 : du texte présent, mais aucune tête `**Pn.m` -- même verdict,
    un backlog de forme méconnaissable n'est pas un backlog à 0 entrée."""
    out = P.compute_pilotage(None, "# Juste un titre\n\nDu texte sans aucune tête d'entrée.\n", None, None,
                             None, NOW, repo_root=P.racine_depot())
    assert out["roadmap"] is None, out["roadmap"]
    assert any("AUCUNE" in a for a in out["aveugle"]), out["aveugle"]


def test_tete_indentee_rompt_la_PARITE_et_devient_une_ligne_aveugle_jamais_une_exception():
    """Minor (revue finale) : `_ENTREE` exige `^\\*\\*` ancré en tout DÉBUT de ligne, `compter_entrees`
    matche sur `ln.strip()` -- une tête INDENTÉE est comptée par le second, invisible pour le premier :
    `parse_roadmap` lève une erreur de parité qui, non rattrapée, remontait jusqu'au `except` du service et
    aveuglait TOUT (flotte, portes, charge compris), pas seulement le backlog.

    F11 : l'erreur est une `ValueError` EXPLICITE, plus une `AssertionError` — sous `python -O` un `assert`
    disparaît (cf. le test suivant). L'assertion cherche le NOUVEAU type, à force égale."""
    txt = "  **P9.9 — OUVERTE (2026-09-01) — tête indentée de deux espaces.**\nCorps.\n"
    out = P.compute_pilotage(None, txt, None, None, [], NOW, repo_root=P.racine_depot(),
                             board={"sessions": []})
    assert out["roadmap"] is None, out["roadmap"]
    assert any("backlog" in a and "ValueError" in a for a in out["aveugle"]), out["aveugle"]
    assert out["portes"] == [], "le reste du pilotage ne doit PAS être aveuglé par le backlog"
    assert out["flotte"] is not None, "le reste du pilotage ne doit PAS être aveuglé par le backlog"


_DEUX_TETES_PLUS_UNE_INDENTEE = ("**P9.1 — OUVERTE (2026-09-01) — une.**\nCorps.\n\n"
                                 "**P9.2 — OUVERTE (2026-09-02) — deux.**\nCorps.\n\n"
                                 "  **P9.3 — OUVERTE (2026-09-03) — indentée, perdue par _ENTREE.**\nCorps.\n")


def test_parite_rompue_LEVE_ValueError_meme_sous_python_O(tmp_path):
    """F11 : la parité reposait sur un `assert`. Sous `python -O` il disparaît : un backlog à 2 têtes
    valides plus 1 tête indentée sortait avec `blocs = 2` SANS ligne d'aveuglement — l'entrée indentée
    perdue en silence (forme (c) du registre : une troncature qui ne lève jamais). Le contre-exemple tourne
    dans un interpréteur `-O` RÉEL (drapeau vérifié), pas dans celui de pytest."""
    src = tmp_path / "backlog.md"
    src.write_text(_DEUX_TETES_PLUS_UNE_INDENTEE, encoding="utf-8")
    code = ("import sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from tools.pm import pilotage as P\n"
            "txt = open(sys.argv[2], encoding='utf-8').read()\n"
            "print('optimize', sys.flags.optimize)\n"
            "try:\n"
            "    out = P.parse_roadmap(txt, sys.argv[1], 0.0, evaluer_clause=lambda p, a: (True, None))\n"
            "    print('PAS DE LEVEE blocs', out['comptes']['blocs'])\n"
            "except Exception as exc:\n"
            "    print('LEVEE', type(exc).__name__)\n")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-O", "-c", code, P.racine_depot(), str(src)], capture_output=True,
                       encoding="utf-8", env=env, timeout=120)
    lignes = r.stdout.strip().splitlines()
    assert lignes[:1] == ["optimize 1"], (r.stdout, r.stderr)
    assert lignes[1:] == ["LEVEE ValueError"], (r.stdout, r.stderr)
    with pytest.raises(ValueError, match="parité rompue"):
        P.parse_roadmap(_DEUX_TETES_PLUS_UNE_INDENTEE, P.racine_depot(), NOW,
                        evaluer_clause=lambda p, a: (True, None))


def test_portes_agi_perdues_SANS_backlog_est_DIT_quand_records_graph_est_present():
    """Minor (revue finale) : `portes_agi` vit DANS `roadmap`. Si le backlog manque (ou est illisible)
    alors que `records_graph.json` est présent, les portes G0-G4 sont jetées avec `roadmap` sans qu'aucun
    mot ne le dise -- une des TROIS lectures de l'avancement (spec §2.3) disparaît en silence."""
    rg = {"roadmap": {"G0": {"status": "validated"}}}
    out = P.compute_pilotage(None, None, rg, None, None, NOW, repo_root=P.racine_depot())
    assert out["roadmap"] is None
    assert any("portes_agi" in a for a in out["aveugle"]), out["aveugle"]


def test_records_graph_SANS_cle_roadmap_le_DIT_jamais_un_None_muet():
    """F9 : backlog valide et `records_graph` présent mais SANS clé `roadmap` -> `portes_agi` valait `None`
    avec un `aveugle` VIDE. Une absence n'est jamais une mesure : elle se NOMME."""
    out = P.compute_pilotage(None, _BACKLOG_SYNTH, {"graph": {}}, None, None, NOW, repo_root=P.racine_depot())
    assert out["roadmap"] is not None and out["roadmap"]["comptes"]["blocs"] == 5
    assert out["roadmap"]["portes_agi"] is None
    assert any(a.startswith("portes_agi") and "roadmap" in a for a in out["aveugle"]), out["aveugle"]


@pytest.mark.parametrize("rg", [{"roadmap": []}, {"roadmap": "G0"}, {"roadmap": None}, [1], "x"])
def test_records_graph_de_FORME_inattendue_n_aveugle_que_portes_agi(rg):
    """F3, couche 2 : `records_graph.json` est une source ÉTRANGÈRE (writer : `check_record_links`). Un
    `roadmap` non-dict passait tel quel dans `Roadmap.portes_agi` et la validation de la route levait HORS
    du filet du service (500) ; un graphe non-dict faisait lever `.get` et aveuglait TOUT le pilotage. Seul
    `portes_agi` tombe, avec une ligne nommée ; la roadmap du backlog reste servie."""
    out = P.compute_pilotage(None, _BACKLOG_SYNTH, rg, None, [], NOW, repo_root=P.racine_depot(),
                             board={"generated_at": NOW, "sessions": []})
    assert out["roadmap"] is not None and out["roadmap"]["comptes"]["blocs"] == 5
    assert out["roadmap"]["portes_agi"] is None
    assert any(("portes_agi" in a or "graphe de records" in a) and "inattendue" in a
               for a in out["aveugle"]), out["aveugle"]
    assert out["flotte"] is not None and out["portes"] == []


def test_fichiers_INDISPONIBLES_ne_publient_pas_le_zero_FABRIQUE_de_ROLES_COUNTS():
    """F10 : `roles_counts.compute_counts` rend `fichiers = {science: 0, methodo: 0, autre: 0}` quand git est
    muet, et le DIT dans le drapeau voisin `fichiers_disponibles = False`. Le pilotage recopiait `fichiers`
    sans lire le drapeau : un zéro fabriqué publié. Les deux entrées sont produites par le VRAI
    `compute_counts` (jamais un drapeau réinventé) : `None` pour git muet, une liste pour le contrôle."""
    from tools.pm.roles_counts import compute_counts
    muet = compute_counts([], None, NOW)
    assert muet["fichiers_disponibles"] is False and muet["fichiers"] == {"science": 0, "methodo": 0, "autre": 0}
    out = P.compute_pilotage(None, None, None, muet, None, NOW, repo_root=P.racine_depot())
    assert out["charge"] is not None and out["charge"]["fichiers"] is None, out["charge"]
    assert any("fichiers_disponibles" in a for a in out["aveugle"]), out["aveugle"]

    temoin = compute_counts([], ["docs/EDR/x.md", "tools/check_y.py"], NOW)
    assert temoin["fichiers_disponibles"] is True
    ok = P.compute_pilotage(None, None, None, temoin, None, NOW, repo_root=P.racine_depot())
    assert ok["charge"]["fichiers"] == {"science": 1, "methodo": 1, "autre": 0}
    assert not any("fichiers_disponibles" in a for a in ok["aveugle"]), ok["aveugle"]


@pytest.mark.parametrize("rc", [[1], "x", 3])
def test_ROLES_COUNTS_de_FORME_inattendue_n_aveugle_que_ses_champs(rc):
    """Même classe que I4 : un `ROLES_COUNTS.json` non-dict faisait lever `.get` dans `compute_pilotage` et
    aveuglait TOUT le pilotage via le filet du service. Il est ILLISIBLE, jamais « introuvable » ; la charge
    connue du board, elle, reste servie."""
    board = {"generated_at": NOW, "sessions": [],
             "charge_connue": {"sims_en_vol": 0, "cpu_pct": 5.0, "bails_vivants": []}}
    out = P.compute_pilotage(None, _BACKLOG_SYNTH, None, rc, None, NOW, repo_root=P.racine_depot(), board=board)
    assert out["roadmap"] is not None and out["flotte"] is not None
    assert out["charge"] is not None and out["charge"]["cpu_pct"] == 5.0
    assert out["charge"]["ratio_science_methodo"] is None and out["charge"]["fichiers"] is None
    assert any("ROLES_COUNTS" in a and "inattendue" in a for a in out["aveugle"]), out["aveugle"]
    assert not any("ROLES_COUNTS" in a and "introuvable" in a for a in out["aveugle"]), out["aveugle"]


def test_racine_ETRANGERE_nomme_la_racine_jamais_un_fichier_absent(tmp_path):
    """IMPORTANT 3 (spec §3.1 et §6, ligne « racine étrangère ») : depuis un dépôt jetable qui ne porte NI
    le backlog NI le hook, le pilotage accusait chaque fichier d'être absent, un par un, sans jamais
    nommer la racine en cause. Mesuré depuis un `tempfile.mkdtemp()`. Contre-exemple gelé : un cwd
    étranger portant `.git`."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True, capture_output=True,
                   encoding="utf-8")
    out = P.compute_pilotage(None, None, None, None, None, NOW, repo_root=str(tmp_path))
    assert len(out["aveugle"]) == 1, out["aveugle"]
    assert str(tmp_path).replace("\\", "/") in out["aveugle"][0].replace("\\", "/")
    assert "introuvable" not in out["aveugle"][0] and "illisible" not in out["aveugle"][0], out["aveugle"]
    assert out["flotte"] is None and out["roadmap"] is None
    assert out["portes"] is None and out["charge"] is None


def test_racine_qui_porte_le_HOOK_SEUL_est_AGAGI_avec_un_backlog_ABSENT(tmp_path):
    """F5 (ruling du contrôleur) : la garde de santé ne se déclenche que si la racine ne porte NI le backlog
    NI le hook. Une racine qui porte l'un des deux est AGAGI avec un fichier manquant — l'accident E22 que
    ce dépôt a déjà subi — et c'est la ligne PAR SOURCE qui doit le NOMMER. Avant : `not (A and B)` disait
    « racine suspecte » et mettait flotte/portes/charge à `None`, sources saines comprises."""
    (tmp_path / "tools" / "hooks").mkdir(parents=True)
    shutil.copyfile(os.path.join(P.racine_depot(), "tools", "hooks", "pre-commit"),
                    str(tmp_path / "tools" / "hooks" / "pre-commit"))
    racine = str(tmp_path)
    out = P.compute_pilotage(None, P.read_backlog(racine), None, None, P.read_portes(racine), NOW,
                             repo_root=racine, board={"generated_at": NOW, "sessions": []})
    assert not any("suspecte" in a for a in out["aveugle"]), out["aveugle"]
    assert any("PRIORITES_ET_DETTES.md" in a and "introuvable" in a for a in out["aveugle"]), out["aveugle"]
    assert out["portes"] is not None and len(out["portes"]) > 0, "portes calculé depuis le hook copié"
    assert out["flotte"] is not None and out["roadmap"] is None


def test_racine_qui_porte_le_BACKLOG_SEUL_est_AGAGI_avec_un_hook_ABSENT(tmp_path):
    """Symétrique du précédent : le backlog seul -> la roadmap est calculée, la ligne nomme le hook absent,
    aucune « racine suspecte »."""
    (tmp_path / "docs" / "roadmap").mkdir(parents=True)
    (tmp_path / "docs" / "roadmap" / "PRIORITES_ET_DETTES.md").write_text(_BACKLOG_SYNTH, encoding="utf-8")
    racine = str(tmp_path)
    out = P.compute_pilotage(None, P.read_backlog(racine), None, None, P.read_portes(racine), NOW,
                             repo_root=racine, board={"generated_at": NOW, "sessions": []})
    assert not any("suspecte" in a for a in out["aveugle"]), out["aveugle"]
    assert any("pre-commit" in a for a in out["aveugle"]), out["aveugle"]
    assert out["portes"] is None
    assert out["roadmap"] is not None and out["roadmap"]["comptes"]["blocs"] == 5
    assert out["flotte"] is not None


def test_board_NON_DICT_est_ILLISIBLE_ne_nuit_pas_au_reste_du_pilotage():
    """IMPORTANT 4 : sonde du reviewer, `board = [1, 2, 3]` faisait lever `AttributeError` sur
    `flotte.get(...)`, attrapée par le `except` du SERVICE -- qui mettait roadmap/portes/charge à `null`
    alors qu'une seule source (le board) est en cause. `compute_pilotage` doit rester debout tout seul."""
    out = P.compute_pilotage(None, _BACKLOG_SYNTH, None, None, None, NOW, repo_root=P.racine_depot(),
                             board=[1, 2, 3])
    assert out["flotte"] is None
    assert any("flotte" in a and "list" in a for a in out["aveugle"]), out["aveugle"]
    assert out["roadmap"] is not None and out["roadmap"]["comptes"]["blocs"] == 5


def test_board_generated_at_NON_NUMERIQUE_est_ILLISIBLE_ne_nuit_pas_au_reste_du_pilotage():
    """IMPORTANT 4 : sonde du reviewer, `board = {"generated_at": "2026-09-24 12:00:00"}` faisait lever
    `ValueError` sur `float(gen)` -- exactement la forme dont la docstring de `read_board` prévient déjà
    (`json.dump(..., default=str)` stringifie en silence). Même verdict : illisible, pas contagieux."""
    board = {"generated_at": "2026-09-24 12:00:00", "sessions": []}
    out = P.compute_pilotage(None, _BACKLOG_SYNTH, None, None, None, NOW, repo_root=P.racine_depot(),
                             board=board)
    assert out["flotte"] is None
    assert any("flotte" in a for a in out["aveugle"]), out["aveugle"]
    assert out["roadmap"] is not None and out["roadmap"]["comptes"]["blocs"] == 5


@pytest.mark.parametrize("board,mot", [
    ({"generated_at": NOW, "sessions": [], "charge_connue": [1]}, "charge_connue"),     # AttributeError : tout aveuglé
    ({"generated_at": NOW, "sessions": [], "charge_connue": []}, "charge_connue"),      # charge tout à None SANS ligne
    ({"generated_at": NOW, "sessions": [], "charge_connue": "x"}, "charge_connue"),
    ({"generated_at": NOW, "sessions": [], "aveugle": 5}, "aveugle"),                   # TypeError
    ({"generated_at": NOW, "sessions": [], "aveugle": "abc"}, "aveugle"),               # « flotte: a », « b »…
    ({"generated_at": NOW, "sessions": [], "aveugle": ["ok", 3]}, "aveugle"),
    ({"generated_at": True, "sessions": []}, "generated_at"),                           # âge absurde : now - 1.0
    ({"generated_at": float("nan"), "sessions": []}, "generated_at"),                   # âge nan
    ({"generated_at": float("inf"), "sessions": []}, "generated_at"),
])
def test_board_de_FORME_inattendue_aveugle_la_flotte_SEULE_et_le_NOMME(board, mot):
    """F8 : `_board_valide` ne regardait que le type racine et `generated_at`. Chaque cas est une sonde
    MESURÉE par la re-revue (commentaire en regard) : une exception qui aveuglait tout, une charge à `None`
    sans ligne, trois lignes fabriquées depuis une chaîne, un âge absurde ou `nan` publié. Verdict commun :
    la flotte est ILLISIBLE et le dit en nommant le champ ; la roadmap reste servie."""
    out = P.compute_pilotage(None, _BACKLOG_SYNTH, None, None, None, NOW, repo_root=P.racine_depot(),
                             board=board)
    assert out["flotte"] is None
    assert any(a.startswith("flotte :") and "BOARD.json" in a and mot in a for a in out["aveugle"]), out["aveugle"]
    assert not any(a.startswith("flotte: ") for a in out["aveugle"]), "aucune ligne recopiée d'un aveugle malformé"
    assert out["charge"] is None, "ni flotte lisible ni ROLES_COUNTS : aucune charge, jamais des None muets"
    assert out["roadmap"] is not None and out["roadmap"]["comptes"]["blocs"] == 5


def test_board_SANS_generated_at_est_servi_avec_une_ligne_AGE_INCONNU():
    """F8 : un board sans `generated_at` rendait `flotte_age_s = None` SANS ligne. Il reste servi (le reste
    de son contenu est lisible), mais l'âge inconnu se DIT."""
    board = {"sessions": [], "aveugle": [], "charge_connue": {"sims_en_vol": 0, "cpu_pct": 5.0, "bails_vivants": []}}
    out = P.compute_pilotage(None, None, None, None, None, NOW, repo_root=P.racine_depot(), board=board)
    assert out["flotte"] == board
    assert out["charge"]["flotte_age_s"] is None
    assert any("âge inconnu" in a and "generated_at" in a for a in out["aveugle"]), out["aveugle"]
    avec = dict(board, generated_at=NOW - 60.0)
    ok = P.compute_pilotage(None, None, None, None, None, NOW, repo_root=P.racine_depot(), board=avec)
    assert ok["charge"]["flotte_age_s"] == 60.0
    assert not any("âge inconnu" in a for a in ok["aveugle"]), ok["aveugle"]


def test_board_SANS_charge_connue_le_DIT():
    """Même classe que F8/F9 : un board lisible mais sans `charge_connue` rendait `sims_en_vol`, `cpu_pct` et
    `bails_vivants` à `None` sans un mot — trois inconnues présentées comme des valeurs."""
    board = {"generated_at": NOW, "sessions": [], "aveugle": []}
    out = P.compute_pilotage(None, None, None, None, None, NOW, repo_root=P.racine_depot(), board=board)
    assert out["flotte"] == board
    assert out["charge"]["sims_en_vol"] is None and out["charge"]["cpu_pct"] is None
    assert any("charge_connue" in a for a in out["aveugle"]), out["aveugle"]


@pytest.mark.parametrize("cc,absents", [
    ({}, ["sims_en_vol", "cpu_pct", "bails_vivants"]),
    ({"cpu_pct": 5.0}, ["sims_en_vol", "bails_vivants"]),
    ({"sims_en_vol": 0, "cpu_pct": 5.0, "bails_vivants": []}, []),              # contrôle : rien d'absent
])
def test_charge_connue_sans_un_champ_attendu_NOMME_chaque_absent(cc, absents):
    """G7 (classe F8) : `charge_connue = {}` passait la garde du board (c'est un dict) et les trois champs de
    `charge` tombaient à `None` SANS ligne — trois inconnues présentées comme des valeurs. Chaque champ
    attendu ABSENT est nommé, sur une seule ligne ; un champ présent n'y figure pas."""
    board = {"generated_at": NOW, "sessions": [], "aveugle": [], "charge_connue": cc}
    out = P.compute_pilotage(None, None, None, None, None, NOW, repo_root=P.racine_depot(), board=board)
    assert out["flotte"] == board and out["charge"] is not None
    lignes = [a for a in out["aveugle"] if a.startswith("charge") and "charge_connue" in a]
    if not absents:
        assert not lignes, lignes
        return
    assert len(lignes) == 1, out["aveugle"]
    for champ in ("sims_en_vol", "cpu_pct", "bails_vivants"):
        assert (champ in lignes[0]) == (champ in absents), (champ, lignes[0])
        if champ in absents:
            assert out["charge"][champ] is None


@pytest.mark.parametrize("roles,attendu", [
    ({"fichiers": {"science": 3, "methodo": 1, "autre": 0}}, "inconnue"),                       # drapeau absent
    ({"fichiers": {"science": 3, "methodo": 1, "autre": 0}, "fichiers_disponibles": None}, "inconnue"),
    ({"fichiers": {"science": 3, "methodo": 1, "autre": 0}, "fichiers_disponibles": "true"}, "inconnue"),
    ({"fichiers": {"science": 3, "methodo": 1, "autre": 0}, "fichiers_disponibles": 1}, "inconnue"),
    ({"fichiers": {"science": 0, "methodo": 0, "autre": 0}, "fichiers_disponibles": False}, "indisponibles"),
    ({"fichiers": {"science": 3, "methodo": 1, "autre": 0}, "fichiers_disponibles": True}, None),  # contrôle
])
def test_fichiers_publies_SEULEMENT_si_fichiers_disponibles_est_True(roles, attendu):
    """G7 (classe F10) : seul `fichiers_disponibles = false` retenait `fichiers` ; un drapeau ABSENT ou d'un
    type inattendu laissait publier des zéros sans un mot. La justification « ancien format » est RÉFUTÉE :
    `git log -S fichiers_disponibles` montre le drapeau né avec `roles_counts.py` (ff99e849) — aucun
    ROLES_COUNTS.json légitime n'en est dépourvu. `fichiers` n'est publié que si le drapeau est `True` ;
    sinon `None` et une ligne qui distingue « disponibilité inconnue » de « indisponibles »."""
    out = P.compute_pilotage(None, None, None, roles, None, NOW, repo_root=P.racine_depot())
    lignes = [a for a in out["aveugle"] if "fichiers_disponibles" in a]
    if attendu is None:
        assert out["charge"]["fichiers"] == roles["fichiers"]
        assert not lignes, lignes
        return
    assert out["charge"]["fichiers"] is None, out["charge"]
    assert len(lignes) == 1, out["aveugle"]
    autre = "indisponibles" if attendu == "inconnue" else "inconnue"
    assert attendu in lignes[0].lower() and autre not in lignes[0].lower(), lignes[0]


def test_board_generated_at_ENTIER_GEANT_est_ILLISIBLE_jamais_une_OverflowError():
    """G8 : un entier JSON de plus de 309 chiffres fait lever `OverflowError` à `float(generated_at)`, que la
    garde n'attrapait pas (`TypeError`, `ValueError` seulement) : l'exception sortait de `compute_pilotage`
    et aveuglait TOUT le pilotage. Il est lu par `json.loads`, comme `read_board` le lirait."""
    board = json.loads('{"generated_at": 1' + "0" * 400 + ', "sessions": []}')
    out = P.compute_pilotage(None, _BACKLOG_SYNTH, None, None, None, NOW, repo_root=P.racine_depot(),
                             board=board)
    assert out["flotte"] is None
    assert any(a.startswith("flotte :") and "BOARD.json" in a and "generated_at" in a
               for a in out["aveugle"]), out["aveugle"]
    assert out["roadmap"] is not None and out["roadmap"]["comptes"]["blocs"] == 5


def test_BOARD_et_ROLES_introuvables_NOMMENT_le_chemin_et_les_DEUX_causes_sans_en_choisir_une(tmp_path,
                                                                                           monkeypatch):
    """G9 : « ni instantané ni BOARD.json — le tick PM n'a pas encore tourné » affirmait une CAUSE tirée
    d'une absence. Mesuré : git absent du PATH, un backend lancé depuis un worktree disait exactement cela
    pendant que le tick tournait — la vraie cause était la racine de données non résolue. La ligne NOMME le
    chemin cherché et donne les deux causes sans en choisir une.

    Oracle indépendant du lecteur : `AGAGI_DATA_ROOT` pointée vers un répertoire VIDE, le chemin cherché est
    construit ici depuis ce répertoire (`src/paths.py` : `<data_root>/pm/<fichier>`)."""
    vide = tmp_path / "donnees"
    vide.mkdir()
    monkeypatch.setenv("AGAGI_DATA_ROOT", vide.as_posix())
    out = P.compute_pilotage(None, None, None, None, None, NOW, repo_root=P.racine_depot())
    for fichier, prefixe in (("BOARD.json", "flotte"), ("ROLES_COUNTS.json", "compteurs du PM")):
        attendu = vide.as_posix() + "/pm/" + fichier
        lignes = [a for a in out["aveugle"] if a.startswith(prefixe) and fichier in a]
        assert len(lignes) == 1, (fichier, out["aveugle"])
        assert attendu in lignes[0], (attendu, lignes[0])
        assert "introuvable" in lignes[0] and "tick PM" in lignes[0] and "racine de données" in lignes[0], lignes[0]
    assert not any("pas encore tourné" in a for a in out["aveugle"]), out["aveugle"]


def test_les_lecteurs_ANCRENT_le_chemin_relatif_de_paths(tmp_path, monkeypatch):
    """`src/paths.py` rend du RELATIF sans variable d'environnement (mesuré : `results/records_graph.json`,
    `os.path.isabs` False) : un lecteur qui ne l'ancre pas dépend du répertoire courant du processus, et
    celui d'uvicorn n'est pas garanti.

    Étendu (minor, revue finale) : `read_board` et `read_roles_counts` — les deux lecteurs faux de C1 —
    n'étaient testés que contre un `tmp_path` VIDE, où toute implémentation (correcte ou non) rend `None`.
    Ici `tmp_path` porte ses propres `data/pm/{BOARD,ROLES_COUNTS}.json` et n'est PAS un dépôt git (cwd
    hors dépôt, donc `ancrer_data_root` ne trouve rien à ancrer et se tait) : le test isole ainsi le
    comportement de repli sur `repo_root` de celui, distinct, de l'ancrage sur le dépôt COMMUN (couvert
    par son propre test)."""
    for v in ("AGAGI_DATA_ROOT", "AGAGI_RESULTS_ROOT", "AGAGI_DB_ROOT"):
        monkeypatch.delenv(v, raising=False)
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "records_graph.json").write_text('{"roadmap": {"G0": {"status": "validated"}}}',
                                                             encoding="utf-8")
    (tmp_path / "data" / "pm").mkdir(parents=True)
    (tmp_path / "data" / "pm" / "BOARD.json").write_text('{"sessions": []}', encoding="utf-8")
    (tmp_path / "data" / "pm" / "ROLES_COUNTS.json").write_text('{"ratio_science_methodo": 3.0}',
                                                                encoding="utf-8")
    monkeypatch.chdir(tmp_path.parent)                     # cwd DIFFÉRENT de la racine passée, HORS DÉPÔT git
    g = P.read_records_graph(str(tmp_path))
    assert g is not None and g["roadmap"]["G0"]["status"] == "validated"
    b = P.read_board(str(tmp_path))
    assert b is not None and b["sessions"] == [], b
    r = P.read_roles_counts(str(tmp_path))
    assert r is not None and r["ratio_science_methodo"] == 3.0, r


def test_inventaire_des_portes_recompute_depuis_le_HOOK_pas_depuis_PORTES():
    """`check_gate_mutation.PORTES` est la table des portes MUTÉES, pas l'inventaire des gardes : mesuré le
    2026-09-24, le hook lance 19 scripts `check_*` et PORTES en a 16 — `check_staged_authorship` (porte 7)
    et `check_gate_mutation` (porte 15) en sont absents. Et la numérotation du hook n'est ni contiguë
    (ni 19 ni 20) ni dans l'ordre du fichier (le bloc 21 précède le 18).

    I7 : la spec (§6, « inventaire des portes ») exige la PARITÉ EXACTE avec le hook recomputé, pas un
    plancher `>= 16` — un plancher laisserait une porte ajoutée À L'INTÉRIEUR d'un bloc existant du hook
    disparaître de l'inventaire sans qu'aucun test ne rougisse."""
    from tools.check_synthesis_counts import _portes_hook
    portes = P.read_portes(P.racine_depot())
    assert portes is not None and len(portes) == _portes_hook(), (len(portes), _portes_hook())
    nums = [p["num"] for p in portes]
    assert nums == sorted(nums, key=int), "ordre par int(num), pas un tri de chaînes"
    assert all(isinstance(p["num"], str) for p in portes)
    modules = {p["module"] for p in portes}
    assert any("staged_authorship" in m for m in modules), "porte 7 : absente de PORTES, présente au hook"
    assert any("gate_mutation" in m for m in modules), "porte 15 : le cliquet des cliquets"
    sans_mutation = [p for p in portes if p["mutations"] is None]
    assert sans_mutation, "une porte du hook hors PORTES porte mutations=None, jamais 0"
    with_base = [p for p in portes if p["baseline"]]
    assert with_base and all("existe" in p["baseline"] for p in with_base)


def test_une_tete_de_bloc_DECOREE_du_hook_n_efface_pas_sa_porte(tmp_path):
    """Mesuré le 2026-09-26 (run CI 36230848727, suite-complete : 68 -> 69 rouges) : la porte 24 est entrée au
    hook sous la tête « # --- 24. Seuil a MARGE ... ». Le motif de tête exigeait « # 24. », donc le bloc 24
    n'existait pas pour `read_portes`, son `check_grid_threshold` tombait dans le bloc 23 (déjà pourvu) et
    DISPARAISSAIT de l'inventaire : 23 portes servies pour 24 branchées. Le test de parité ci-dessus l'a vu ;
    celui-ci fige la forme, sur un hook FACTICE, sans dépendre de l'état du vrai hook."""
    (tmp_path / "tools" / "hooks").mkdir(parents=True)
    (tmp_path / "tools" / "hooks" / "pre-commit").write_text(
        "#!/bin/sh\n"
        "# 1. PREMIERE\n"
        "python tools/check_record_links.py\n"
        "# --- 2. DECOREE (tete avec tirets)\n"
        "python tools/check_instrument_calibration.py\n"
        "# 2026-09-26 : une date en commentaire n'est PAS une tete de bloc\n", encoding="utf-8")
    portes = P.read_portes(str(tmp_path))
    assert [(p["num"], p["module"]) for p in portes] == [
        ("1", "tools.check_record_links"), ("2", "tools.check_instrument_calibration")], portes


def test_une_porte_du_hook_sans_baseline_declaree_porte_baseline_None():
    portes = P.read_portes(P.racine_depot())
    assert any(p["baseline"] is None for p in portes), (
        "le mappage module -> baseline est EXPLICITE (record_link_baseline.json, sans s) : "
        "une porte non déclarée ne doit pas inventer un chemin")


def test_NO_OP_EXACT_tout_absent_rend_cinq_aveuglements_et_aucun_zero():
    """Spécificité de l'instrument : sans aucune source, il ne dit pas « 0 alerte, 0 entrée » — il dit
    qu'il est AVEUGLE, cinq fois, et laisse les quatre blocs à None.

    `repo_root` DOIT être une racine SAINE (`racine_depot()`) : `c:/x` n'existe pas sur le disque et
    déclencherait désormais la garde de santé (I3), qui court-circuite tout en UNE seule ligne nommant
    la racine — un cas différent, couvert par son propre test (racine étrangère)."""
    out = P.compute_pilotage(None, None, None, None, None, NOW, repo_root=P.racine_depot())
    assert out["schema"] == "pilotage_v1" and out["generated_at"] == NOW
    assert out["flotte"] is None and out["roadmap"] is None
    assert out["portes"] is None and out["charge"] is None
    assert len(out["aveugle"]) == 5, out["aveugle"]
    texte = json.dumps(out, ensure_ascii=False)
    assert ": 0" not in texte and "[]" not in texte, f"un zéro ou une liste vide fabriqués : {texte}"


def test_flotte_est_la_sortie_du_board_SANS_transformation():
    """Non-duplication : les clés de la flotte sont le CONTRAT du board, figé par ses 119 tests. Le
    pilotage n'en renomme, n'en retire et n'en ajoute aucune."""
    from tools.pm import board as B
    snap = {"now": NOW, "repo_root": "c:/x/agagi", "psutil": True, "registry": [], "bulletins": [],
            "worktrees": [], "commits": [], "leases": {"live": [], "dead": []}, "processes": [],
            "cpu_pct": 10.0, "backlog_paths": {},
            "hook_errors": {}}  # DICT {événement: n}, jamais une liste : board._alertes fait .items()
    attendu = B.compute(snap, now=NOW)
    # `repo_root` du COMPUTE (garde de santé I3) est distinct de `snap["repo_root"]` (interne au board,
    # jamais mesuré sur disque) : le premier doit être SAIN, le second reste un identifiant quelconque.
    out = P.compute_pilotage(snap, None, None, None, None, NOW, repo_root=P.racine_depot())
    assert out["flotte"] == attendu


def test_charge_porte_la_FENETRE_glissante_jamais_la_constante_depuis():
    """`ROLES_COUNTS.json` publie `depuis` (constante DEBUT, début du rôle PM) ET `fenetre` (glissante,
    30 j). Servir `depuis` comme fenêtre attribuerait le ratio à une période qui n'est pas la sienne."""
    rc = {"depuis": "2026-09-16", "fenetre": {"depuis": "2026-08-24", "jours": 30},
          "ratio_science_methodo": 1.12, "fichiers": {"science": 239, "methodo": 213, "autre": 604}}
    out = P.compute_pilotage(None, None, None, rc, None, NOW, repo_root=P.racine_depot())
    assert out["charge"]["fenetre"] == {"depuis": "2026-08-24", "jours": 30}
    assert out["charge"]["ratio_science_methodo"] == 1.12
    assert "depuis" not in out["charge"], "la constante DEBUT n'est pas une fenêtre"


def test_age_de_la_flotte_vient_de_generated_at_jamais_du_mtime(tmp_path):
    """Un `git checkout`, une copie ou une écriture interrompue donne un mtime FRAIS sur un contenu
    périmé : la vue annoncerait une fraîcheur supposée. Seul contre-exemple qui distingue les deux
    règles : un fichier dont le mtime et le `generated_at` diffèrent de plusieurs minutes."""
    board = {"generated_at": NOW - 1800.0, "repo_root": "c:/x", "aveugle": [], "sessions": [],
             "sessions_mortes": [], "alertes": [],
             "charge_connue": {"sims_en_vol": 0, "cpu_pct": 5.0, "bails_vivants": []},
             "worktrees": [], "bails": None}
    out = P.compute_pilotage(None, None, None, None, None, NOW, repo_root=P.racine_depot(), board=board)
    assert out["charge"]["flotte_age_s"] == 1800.0
    sans = dict(board)
    sans.pop("generated_at")
    out2 = P.compute_pilotage(None, None, None, None, None, NOW, repo_root=P.racine_depot(), board=sans)
    assert out2["charge"]["flotte_age_s"] is None, "clé absente -> None, jamais un mtime de repli"


def test_prediction_une_entree_close_de_plus_ne_bouge_que_son_compte():
    """Linéarité en la dose : ajouter UNE entrée close augmente `closes` de 1 et ne touche rien d'autre."""
    base = P.compute_pilotage(None, _BACKLOG_SYNTH, None, None, None, NOW, repo_root=P.racine_depot())
    plus = P.compute_pilotage(None, _BACKLOG_SYNTH + "\n**P2.99 — ✅ CLOSE le 2026-09-09 — une de plus.**\nCorps.\n",
                              None, None, None, NOW, repo_root=P.racine_depot())
    a, b = base["roadmap"]["comptes"], plus["roadmap"]["comptes"]
    assert b["par_priorite"]["P2"]["closes"] == a["par_priorite"]["P2"]["closes"] + 1
    assert b["par_priorite"]["P2"]["ouvertes"] == a["par_priorite"]["P2"]["ouvertes"]
    assert b["blocs"] == a["blocs"] + 1 and b["numeros"] == a["numeros"] + 1


def test_parite_sur_le_backlog_REEL():
    """Sur le vrai fichier : autant de blocs que le cliquet compte de têtes, et aucun bloc illisible."""
    from tools.check_backlog_freshness import compter_entrees
    txt = P.read_backlog(P.racine_depot())
    assert txt is not None
    out = P.compute_pilotage(None, txt, None, None, None, NOW, repo_root=P.racine_depot())
    c = out["roadmap"]["comptes"]
    assert c["blocs"] == compter_entrees(txt)
    illis = [e["num"] for e in out["roadmap"]["entrees"] if e["statut"] == "illisible"]
    assert not illis, f"entrées illisibles sur le backlog réel : {illis}"


def test_main_json_n_ecrit_AUCUN_fichier(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    avant = sorted(os.listdir(tmp_path))
    P.main(["--json", "--repo-root", P.racine_depot()])
    assert sorted(os.listdir(tmp_path)) == avant, "main a écrit un fichier"
    assert json.loads(capsys.readouterr().out)["schema"] == "pilotage_v1"
