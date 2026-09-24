"""Porte 20 : une evidence citee par un record EXISTE et est SUIVIE par git (ou publiee par son hash) --
sinon la conclusion repose sur un fichier que personne ne peut rouvrir (E27, mesure deux fois cette
semaine sur des clones/worktrees neufs)."""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_evidence_provenance as P  # noqa: E402

T = "Résultat (`results/a.json`) puis `results/b_r{1,2}.json` et `results/perdu.json` (sha256 0123456789abcdef)."


def test_evaluer_classe_absents_non_suivis_et_publies_par_hash():
    existe = lambda rel: rel in ("results/a.json", "results/b_r1.json")
    suivi = lambda rel: rel == "results/a.json"
    v = P.evaluer(T, existe, suivi, root=os.getcwd())
    assert v["cites"] == ["results/a.json", "results/b_r1.json", "results/b_r2.json", "results/perdu.json"]
    assert v["absents"] == ["results/b_r2.json"] and v["non_suivis"] == ["results/b_r1.json"]
    assert v["par_hash"] == ["results/perdu.json"] and v["statut"] == "ABSENT"


def test_CONTRE_EXEMPLE_GELE_un_chemin_absent_est_ABSENT_et_un_present_suivi_est_OK():
    assert P.evaluer("(`results/x.json`)", lambda r: False, lambda r: False, root=".")["statut"] == "ABSENT"
    assert P.evaluer("(`results/x.json`)", lambda r: True, lambda r: False, root=".")["statut"] == "NON_SUIVI"
    assert P.evaluer("(`results/x.json`)", lambda r: True, lambda r: True, root=".")["statut"] == "OK"
    assert P.evaluer("rien de cité", lambda r: False, lambda r: False, root=".")["statut"] == "OK"


def test_publie_par_hash_exige_sha256_dans_la_fenetre_apres_la_citation():
    assert P.publie_par_hash("`results/p.json` (sha256 0123456789abcdef)", "results/p.json") is True
    loin = "`results/p.json`" + " x" * 80 + " sha256 0123456789abcdef"          # le hash est a > 120 caracteres : hors fenetre
    assert P.publie_par_hash(loin, "results/p.json") is False
    assert P.publie_par_hash("`results/p.json` (sha256 zz)", "results/p.json") is False


def test_analyze_sur_un_arbre_factice_et_records_illisibles(tmp_path):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "A.md").write_text("(`results/a.json`)", encoding="utf-8")
    (d / "B.md").write_bytes(b"\xff\xfe\x00 invalide \x80")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "a.json").write_text("{}", encoding="utf-8")
    a = P.analyze(str(tmp_path), suivi=lambda root, rel: False)
    assert a["records"]["docs/EDR/A.md"]["statut"] == "NON_SUIVI" and a["illisibles"] == ["docs/EDR/B.md"]


def test_le_depot_REEL_n_a_aucune_paire_HORS_baseline():
    a = P.analyze(P._ROOT)
    assert sum(len(v["cites"]) for v in a["records"].values()) >= 60, "le périmètre est vide, le test ne prouverait rien"
    base = P._load_baseline()
    hors = {}
    for f, v in a["records"].items():
        gele = base.get(f, {})
        nouveau = {c: v["causes"][c] for c in (v["absents"] + v["non_suivis"])
                   if c not in gele or P._RANG.get(v["causes"][c], 2) > P._RANG.get(gele[c], 0)}
        if nouveau:
            hors[f] = nouveau
    assert hors == {}, hors


def test_main_ratchet_1_puis_gel_puis_0(tmp_path, monkeypatch):
    """Padding a 60 fichiers : sous le seuil minor (i), --update-baseline refuserait d'ecrire (garde de
    compte, leçon de la tâche 1) -- meme motif que test_main_rend_1... de check_regime_claims.py."""
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "N.md").write_text("(`results/absent.json`)", encoding="utf-8")
    for i in range(60):
        (d / f"PADDING-{i:02d}.md").write_text("rien ici, juste pour depasser le seuil de 50 records.",
                                                 encoding="utf-8")
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    monkeypatch.setattr(P, "_tracked", lambda root, rel: False)
    assert P.main(["--root", str(tmp_path)]) == 1
    assert P.main(["--root", str(tmp_path), "--update-baseline"]) == 0
    assert P.main(["--root", str(tmp_path)]) == 0


# ---------------------------------------------------------------------------------------------------
# Lecons preventives de la tache 1 (imposees par le controleur pour la tache 2).


def test_p1_causes_distinctes_absent_non_suivi_glob_vide(tmp_path):
    """Un chemin « fautif » nomme sa cause parmi TROIS formes distinctes : fichier inexistant sur le
    disque, existant mais NON SUIVI, et un motif a glob qui ne developpe vers RIEN -- ne pas les fondre
    sous une etiquette unique (sinon un motif a glob mort disparait silencieusement : ni absent ni
    non_suivi, juste ABSENT du compte, exactement la faute « donnee absente -> verdict de fond »
    documentee dans CLAUDE.md)."""
    texte = "(`results/absent.json`) (`results/present_non_suivi.json`) (`results/x_*.json`)"
    existe = lambda rel: rel == "results/present_non_suivi.json"
    suivi = lambda rel: False
    v = P.evaluer(texte, existe, suivi, root=str(tmp_path))
    assert v["causes"]["results/absent.json"] == "absent"
    assert v["causes"]["results/present_non_suivi.json"] == "non_suivi"
    assert v["causes"]["results/x_*.json"] == "glob_vide"
    assert "results/x_*.json" in v["cites"], "un motif a glob mort ne doit pas disparaitre de cites"
    assert v["statut"] == "ABSENT"


def test_p1_glob_qui_developpe_reellement_nest_pas_glob_vide(tmp_path):
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "y_1.json").write_text("{}", encoding="utf-8")
    v = P.evaluer("(`results/y_*.json`)", lambda r: True, lambda r: True, root=str(tmp_path))
    assert v["cites"] == ["results/y_1.json"] and v["statut"] == "OK"


def test_p2_baseline_par_paire_et_cause__non_suivi_vers_absent_est_une_regression(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "R.md").write_text("(`results/r.json`)", encoding="utf-8")
    for i in range(60):
        (d / f"PAD-{i:02d}.md").write_text("rien.", encoding="utf-8")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "r.json").write_text("{}", encoding="utf-8")   # existe, non suivi
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {"docs/EDR/R.md": {"results/r.json": "non_suivi"}}}),
                 encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    monkeypatch.setattr(P, "_tracked", lambda root, rel: False)
    assert P.main(["--root", str(tmp_path)]) == 0          # identique au gel (meme paire, meme cause) -> ne bloque pas
    (tmp_path / "results" / "r.json").unlink()              # le fichier disparait du disque -> ABSENT
    assert P.main(["--root", str(tmp_path)]) == 1           # PIRE que NON_SUIVI gele, meme paire -> REGRESSION -> bloque


def test_p2_baseline_absent_vers_non_suivi_nest_PAS_une_regression(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "R.md").write_text("(`results/r.json`)", encoding="utf-8")
    for i in range(60):
        (d / f"PAD-{i:02d}.md").write_text("rien.", encoding="utf-8")
    (tmp_path / "results").mkdir()
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {"docs/EDR/R.md": {"results/r.json": "absent"}}}),
                 encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    # Le fichier APPARAIT sur le disque mais reste non suivi -> ameliore (absent -> non_suivi) -> pas de blocage.
    (tmp_path / "results" / "r.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(P, "_tracked", lambda root, rel: False)
    assert P.main(["--root", str(tmp_path)]) == 0


def test_p3_illisible_bloque_et_nest_jamais_gelable(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "B.md").write_bytes(b"\xff\xfe\x00 invalide \x80")
    for i in range(60):
        (d / f"PAD-{i:02d}.md").write_text("rien.", encoding="utf-8")
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    monkeypatch.setattr(P, "_tracked", lambda root, rel: True)
    assert P.main(["--root", str(tmp_path)]) == 1
    # --update-baseline ne peut pas geler un illisible : il reste bloquant meme apres gel.
    assert P.main(["--root", str(tmp_path), "--update-baseline"]) == 0
    assert P.main(["--root", str(tmp_path)]) == 1


def test_p4_main_rend_1_sur_un_NOUVEAU_ABSENT_et_sur_un_NOUVEAU_NON_SUIVI_separement(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "ABS.md").write_text("(`results/nouveau_absent.json`)", encoding="utf-8")
    for i in range(60):
        (d / f"PAD-{i:02d}.md").write_text("rien.", encoding="utf-8")
    (tmp_path / "results").mkdir()
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    monkeypatch.setattr(P, "_tracked", lambda root, rel: False)
    assert P.main(["--root", str(tmp_path)]) == 1        # NOUVEAU ABSENT

    (d / "ABS.md").unlink()
    (d / "NS.md").write_text("(`results/nouveau_non_suivi.json`)", encoding="utf-8")
    (tmp_path / "results" / "nouveau_non_suivi.json").write_text("{}", encoding="utf-8")
    assert P.main(["--root", str(tmp_path)]) == 1        # NOUVEAU NON_SUIVI (existe, non suivi)


def test_p5_le_hook_declenche_sur_son_propre_module_et_ne_scope_only_que_si_pur_EDR():
    hook = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "hooks", "pre-commit")
    with open(hook, encoding="utf-8") as fh:
        src = fh.read()
    i = src.index("# 20.")
    j = src.index("\nfi\n", i) + len("\nfi\n")
    bloc = src[i:j]
    assert "tools/check_evidence_provenance\\.py" in bloc
    assert "tools/evidence_provenance_baseline\\.json" in bloc
    assert "results/.*\\.json" in bloc
    assert re.search(r"non_edr\w*\s*=", bloc) or "non_edr" in bloc
    # Point 7 de la revue architecte : la porte 20 tire TOUT son perimetre de cited_results/_developper,
    # importes de check_regime_claims.py -- un changement de ce module (ex. un correctif de _developper)
    # devait re-declencher la porte 20 (E4 occ. 5), or il n'etait pas dans la regex declenchante.
    assert "tools/check_regime_claims\\.py" in bloc


# =======================================================================================================
# Revue architecte, 7 Important (tous tranches reels par le controleur) -- corrections ci-dessous.
# =======================================================================================================


def _depot_jetable(tmp_path):
    """Un VRAI depot git jetable, SANS AUCUN monkeypatch de _tracked/_dans_head -- point 1 de la revue :
    _tracked n'avait aucun temoin qui exerce le VRAI oracle git (les 5 tests non_suivi du premier tir
    injectaient tous suivi=lambda: False, donc _tracked pouvait devenir `return True` sans qu'un seul
    test ne rougisse). Trois etats distincts :
      * results/committe.json  -- ajoute ET committe (suivi + dans HEAD) ;
      * results/stage_seul.json -- ajoute (suivi, INDEX) mais PAS committe (absent de HEAD) -- le cas
        que _dans_head distingue de _tracked (point 4) ;
      * results/nu.json        -- present sur le disque, JAMAIS `git add` (non suivi)."""
    repo = tmp_path

    def git(*args):
        # env=P._env_isole() : sans ca, un GIT_INDEX_FILE herite de l'EXTERIEUR (git commit -- <pathspec>
        # en fixe un pour ses hooks -- cf. P._env_isole) ferait lire/ecrire ce depot JETABLE dans
        # l'index d'un AUTRE depot. Reproduit puis corrige (voir rapport de correction).
        #
        # ⚠️ -C <repo> ET l'identite EN LIGNE (-c), jamais `git config` : un test qui ECRIT une config
        # est a UNE regression d'isolation pres de polluer le depot REEL, et c'est arrive. Mesure d'une
        # session parallele, ancree sur toutes les branches : 33 commits sur 1725 portent l'identite
        # `Test <test@example.com>`, et la PREMIERE est 7d6c04c9 -- « fix(porte 20) : temoin REEL de la
        # seconde issue (depot git jetable) », mtime de .git/config au 2026-09-23 22:51, la soiree ou
        # cette porte travaillait. Une ronde intermediaire avait casse l'isolation avant que la suivante
        # ne la repare. Avec -c il n'y a RIEN A ECRIRE : la famille de pannes disparait au lieu d'etre
        # gardee. C'est la forme qu'emploient deja test_backlog_freshness.py:84 et
        # test_harness_provenance.py:50.
        r = subprocess.run(
            ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
            cwd=str(repo), capture_output=True, text=True, env=P._env_isole())
        assert r.returncode == 0, f"git {args} a echoue : {r.stderr}"
        return r

    git("init", "-b", "main")
    (repo / "results").mkdir()
    (repo / "results" / "committe.json").write_text("{}", encoding="utf-8")
    git("add", "results/committe.json")
    git("commit", "-m", "init")
    (repo / "results" / "stage_seul.json").write_text("{}", encoding="utf-8")
    git("add", "results/stage_seul.json")
    (repo / "results" / "nu.json").write_text("{}", encoding="utf-8")          # jamais ajoute
    return repo


def test_p6_tracked_a_un_temoin_REEL_sur_un_depot_git_jetable(tmp_path):
    """Le coeur du point 1 : _tracked exerce l'INDEX reel de git, pas une constante injectee."""
    repo = _depot_jetable(tmp_path)
    assert P._tracked(str(repo), "results/committe.json") is True
    assert P._tracked(str(repo), "results/stage_seul.json") is True     # ajoute (index) -> suivi
    assert P._tracked(str(repo), "results/nu.json") is False             # jamais ajoute -> non suivi


def test_p6_dans_head_distingue_stage_de_committe(tmp_path):
    """Point 4 : suivi (INDEX) != dans_head (HEAD) -- un fichier juste `git add`-e est suivi mais pas
    encore dans HEAD ; un clone qui ne recupere que les commits ne le verrait pas."""
    repo = _depot_jetable(tmp_path)
    assert P._dans_head(str(repo), "results/committe.json") is True
    assert P._dans_head(str(repo), "results/stage_seul.json") is False
    assert P._dans_head(str(repo), "results/nu.json") is False


def test_p6_analyze_et_main_SANS_monkeypatch_classent_nu_json_non_suivi(tmp_path, monkeypatch):
    """Le point du controleur, a la lettre : SANS monkeypatch de suivi/_tracked, analyze()/main() sur un
    VRAI depot classent bien le chemin non ajoute en non_suivi et font bloquer main()."""
    repo = _depot_jetable(tmp_path)
    d = repo / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "R.md").write_text("(`results/committe.json`) (`results/nu.json`)", encoding="utf-8")
    for i in range(60):
        (d / f"PAD-{i:02d}.md").write_text("rien.", encoding="utf-8")
    subprocess.run(["git", "add", "docs"], cwd=str(repo), capture_output=True, text=True, check=True, env=P._env_isole())
    b = repo / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    a = P.analyze(str(repo))                       # AUCUN suivi= injecte -> _tracked REEL
    v = a["records"]["docs/EDR/R.md"]
    assert v["causes"]["results/nu.json"] == "non_suivi"
    assert "results/committe.json" not in v["causes"]
    assert P.main(["--root", str(repo)]) == 1


def test_p6_report_publie_le_compte_CONTRE_HEAD(tmp_path, capsys, monkeypatch):
    """Point 4 : --report publie une ligne separee, avec sa definition, distincte du compte 'non suivi'
    (INDEX) -- results/stage_seul.json est suivi (index) mais absent de HEAD -> compte 1."""
    repo = _depot_jetable(tmp_path)
    d = repo / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "R.md").write_text("(`results/committe.json`) (`results/stage_seul.json`)", encoding="utf-8")
    for i in range(60):
        (d / f"PAD-{i:02d}.md").write_text("rien.", encoding="utf-8")
    subprocess.run(["git", "add", "docs"], cwd=str(repo), capture_output=True, text=True, check=True, env=P._env_isole())
    b = repo / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    code = P.main(["--root", str(repo), "--report"])
    out = capsys.readouterr().out
    assert code == 0
    assert "contre HEAD : 1 chemin" in out


def test_p7_tete_publie_motifs_chemins_distincts_et_paires_separement(tmp_path, capsys, monkeypatch):
    """Point 2 : un motif a accolade se developpe en PLUSIEURS chemins -- 1 motif, 2 chemins, 2 paires
    pour un SEUL record ; les trois comptes de tete doivent etre DISTINGUABLES."""
    racine = str(tmp_path)

    def _analyze_factice(root=P._ROOT, suivi=None):
        v = P.evaluer("(`results/w_{1,2}.json`)", lambda c: True, lambda c: True, root=racine)
        return {"records": {"docs/EDR/W.md": v}, "illisibles": []}
    monkeypatch.setattr(P, "analyze", _analyze_factice)
    P.main([])
    out = capsys.readouterr().out
    assert "motifs cites : 1" in out
    assert "chemins distincts : 2" in out
    assert "paires record" in out and "chemin : 2" in out


def test_p7_tete_distingue_absent_de_glob_vide(tmp_path, capsys, monkeypatch):
    """Point 3 : `absents` fondait `absent` et `glob_vide` sous UNE etiquette -- la tete doit les
    denombrer separement. root=tmp_path (vide) : le joker ne peut developper vers rien que par hasard."""
    racine = str(tmp_path)

    def _analyze_factice(root=P._ROOT, suivi=None):
        v = P.evaluer("(`results/absent.json`) (`results/vide_*.json`)", lambda c: False, lambda c: False,
                       root=racine)
        return {"records": {"docs/EDR/W.md": v}, "illisibles": []}
    monkeypatch.setattr(P, "analyze", _analyze_factice)
    P.main([])
    out = capsys.readouterr().out
    assert "absents : 1" in out
    assert "glob vides : 1" in out


def test_p8_baseline_gele_les_chemins_publies_par_hash_et_leur_disparition_bloque(tmp_path, monkeypatch):
    """Point 6 : un chemin publie par hash est GELE (auditable) ; s'il perd sa declaration sans que le
    fichier devienne suivi, c'est une REGRESSION (par_hash -> non_suivi, rang 0 -> 1)."""
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "H.md").write_text("(`results/h.json`) (sha256 0123456789abcdef)", encoding="utf-8")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "h.json").write_text("{}", encoding="utf-8")
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    monkeypatch.setattr(P, "_tracked", lambda root, rel: False)
    # 1) le hash declare -> par_hash -> ne bloque PAS (statut OK), meme si le fichier est non suivi.
    assert P.main(["--root", str(tmp_path)]) == 0
    # 2) --update-baseline GELE la paire sous la cause par_hash (auditable, pas seulement acceptee).
    for i in range(60):
        (d / f"PAD-{i:02d}.md").write_text("rien.", encoding="utf-8")
    assert P.main(["--root", str(tmp_path), "--update-baseline"]) == 0
    base = json.loads(b.read_text(encoding="utf-8"))
    assert base["legataires"]["docs/EDR/H.md"]["results/h.json"] == "par_hash"
    # 3) le sha256 disparait du texte ; le fichier RESTE non suivi -> non_suivi, PIRE que par_hash gele
    #    (rang 1 > 0) -> REGRESSION -> bloque.
    (d / "H.md").write_text("(`results/h.json`)", encoding="utf-8")
    assert P.main(["--root", str(tmp_path)]) == 1


def test_p8_report_liste_les_chemins_publies_par_hash_comme_declaratifs(tmp_path, capsys, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "H.md").write_text("(`results/h.json`) (sha256 0123456789abcdef)", encoding="utf-8")
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    code = P.main(["--root", str(tmp_path), "--report"])
    out = capsys.readouterr().out
    assert code == 0
    assert "DECLARATIFS" in out and "results/h.json" in out


def test_p9_chemin_issu_dune_expansion_ne_peut_jamais_etre_par_hash(tmp_path):
    """Minor (i) : meme si un sha256 suit l'ACCOLADE elle-meme, aucun chemin DEVELOPPE n'est marque
    par_hash -- le texte brut ne contient que le motif non developpe. `evaluer` le signale via
    `expansions` plutot que de laisser un False silencieux se confondre avec « pas de hash »."""
    texte = "(`results/b_r{1,2}.json`) (sha256 0123456789abcdef)"
    v = P.evaluer(texte, lambda r: False, lambda r: False, root=str(tmp_path))
    assert v["cites"] == ["results/b_r1.json", "results/b_r2.json"]
    assert set(v["expansions"]) == {"results/b_r1.json", "results/b_r2.json"}
    assert v["par_hash"] == []
    assert v["causes"]["results/b_r1.json"] == "absent" and v["causes"]["results/b_r2.json"] == "absent"


def test_p9_HASH_insensible_a_la_casse():
    """Minor (ii)."""
    assert P.publie_par_hash("`results/p.json` (SHA256 0123456789ABCDEF)", "results/p.json") is True


def test_p10_garde_de_compte_a_3_records_ne_modifie_PAS_la_baseline_disque(tmp_path, monkeypatch):
    """Point 5 : la garde de compte (< 50 records) refuse d'ECRIRE -- le contenu sur disque doit rester
    STRICTEMENT identique, pas seulement 'le code retourne 1'."""
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    for i in range(3):
        (d / f"R{i}.md").write_text("rien ici.", encoding="utf-8")
    b = tmp_path / "base.json"
    contenu_avant = json.dumps({"legataires": {"docs/EDR/OLD.md": {"results/x.json": "absent"}}})
    b.write_text(contenu_avant, encoding="utf-8")
    monkeypatch.setattr(P, "_BASELINE", str(b))
    assert P.main(["--root", str(tmp_path), "--update-baseline"]) == 1
    assert b.read_text(encoding="utf-8") == contenu_avant


# ---------------------------------------------------------------------------------------------------
# Re-revue architecte, meme jour : le correctif de la revue precedente (_env_isole inconditionnel dans
# _tracked) a introduit une REGRESSION -- isoler GIT_* meme quand root == _ROOT fait retomber sur
# .git/index AMBIANT (le travail stage d'une AUTRE session) au lieu de l'index TEMPORAIRE du commit en
# cours que git fixe via GIT_INDEX_FILE pour ses hooks. Corrige par _env_pour (herite sur le depot
# COURANT, isole sur un depot TIERS). Decision rendue OBSERVABLE plutot que de mocker subprocess.


def test_p11_env_pour_herite_sur_le_depot_courant_et_isole_sur_un_depot_tiers(tmp_path):
    """(b) root == _ROOT (le depot du commit en cours) -> None : herite l'environnement ambiant, donc
    GIT_INDEX_FILE quand git le fixe pour un commit partiel -- c'est l'index QU'IL FAUT juger (lecon de
    la porte 4 : « la porte juge ce qui SERA committe »), pas l'index ambiant qui peut porter le travail
    stage d'une AUTRE session sur l'arbre PARTAGE (experience du re-reviewer : session B stage
    results/y.json sans committer, session A commite docs/EDR/X.md qui le cite -- avec l'index ambiant,
    y.json ressortirait SUIVI a tort).
    (a) root != _ROOT (un depot TIERS, ex. le jetable de test) -> isole (_env_isole(), aucune variable
    GIT_* heritee) -- le defaut ORIGINAL de cette correction, deja couvert indirectement par les tests
    test_p6_* (restes verts), verifie ici DIRECTEMENT sur la fonction de decision elle-meme."""
    assert P._env_pour(P._ROOT) is None
    env_tiers = P._env_pour(str(tmp_path))
    assert env_tiers is not None
    assert all(not k.startswith("GIT_") for k in env_tiers)
