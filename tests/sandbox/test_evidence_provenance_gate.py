"""Porte 20 : une evidence citee par un record EXISTE et est SUIVIE par git (ou publiee par son hash) --
sinon la conclusion repose sur un fichier que personne ne peut rouvrir (E27, mesure deux fois cette
semaine sur des clones/worktrees neufs)."""
import json
import os
import re
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
