# -*- coding: utf-8 -*-
"""Index des artefacts (P2.87). EXEMPTION DÉCLARÉE de la garde de bail : aucun monde, aucun bail.
Aucun test n'écrit dans l'arbre : fichiers sous tmp_path, AGAGI_DATA_ROOT sur tmp_path dès qu'un code peut écrire."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import index_artefacts as IX  # noqa: E402

_LEASE_GUARD_EXEMPT = True
NOW = 1_800_000_000.0
FAM = {f.nom: f for f in IX.FAMILLES}


def _ecrire(p, texte, mode="w"):
    p.parent.mkdir(parents=True, exist_ok=True)
    if mode == "wb":
        p.write_bytes(texte)
    else:
        p.write_text(texte, encoding="utf-8")
    return p


def _lire(p, famille):
    return IX.lire_fichier(str(p), p.name, FAM[famille])


def test_record_a_frontmatter_complet(tmp_path):
    p = _ecrire(tmp_path / "001_x.md", "---\nid: EDR-001\ntype: EDR\ntitle: Un titre\nstatus: validated\n"
                "verdict: X_DEMANDED\ngate: G1\ndate: 2026-09-01\ntests: [SDR-G1]\ncorrected_by: EDR-002\n---\ncorps\n")
    etat, a, manques, fmt = _lire(p, "record")
    assert etat == "indexe" and manques == {}
    assert (a["titre"], a["etat"], a["etat_source"], a["gate"]) == ("Un titre", "X_DEMANDED", "verdict", "G1")
    assert (a["date_declaree"], a["date_source"]) == ("2026-09-01", "frontmatter")
    assert {"rel": "tests", "cible": "SDR-G1"} in a["liens"] and {"rel": "corrected_by", "cible": "EDR-002"} in a["liens"]
    assert fmt == {"date"}


def test_record_SANS_frontmatter_ne_FABRIQUE_ni_titre_ni_statut(tmp_path):
    """B1 de la revue : parse_record rendait title tiré du NOM et status 'open' pour 34 EDR légataires."""
    p = _ecrire(tmp_path / "011_World_Model.md", "# World Model\ncorps\n")
    etat, a, manques, _ = _lire(p, "record")
    assert etat == "indexe"
    assert a["titre"] is None and a["etat"] is None and a["etat_source"] is None
    assert manques == {"titre": "frontmatter_absent", "date_declaree": "frontmatter_absent", "etat": "frontmatter_absent",
                       "liens": "frontmatter_absent"} and a["liens"] is None


def test_ref_sans_status_n_est_pas_open(tmp_path):
    p = _ecrire(tmp_path / "Baldwin.md", "---\nid: REF-B\ntype: REF\ntitle: Baldwin\n---\n")
    _, a, manques, _ = _lire(p, "ref")
    assert a["etat"] is None and manques["etat"] == "cle_absente"


@pytest.mark.parametrize("bloc, raison", [
    ("title: [a, b\n", "frontmatter_yaml_invalide"),
    ("date: 2026-13-45\n", "frontmatter_yaml_invalide"),
    ("- a\n- b\n", "frontmatter_non_dict"),
])
def test_frontmatter_casse_est_ILLISIBLE_et_nomme(tmp_path, bloc, raison):
    p = _ecrire(tmp_path / "x.md", "---\n" + bloc + "---\n")
    assert _lire(p, "record") == ("illisible", raison, None, None)


def test_types_inattendus_normalises_a_None(tmp_path):
    p = _ecrire(tmp_path / "x.md", "---\nid: X\ntitle: [a, b]\nverdict: {x: 1}\nstatus: 3\ntests: 5\n---\n")
    etat, a, manques, _ = _lire(p, "record")
    assert etat == "indexe" and a["titre"] is None and a["etat"] is None
    assert manques["titre"] == "type_inattendu" and manques["etat"] == "type_inattendu"
    assert manques["liens"] == "type_inattendu" and a["liens"] == []


def test_fichier_vide_et_encodage(tmp_path):
    assert _lire(_ecrire(tmp_path / "v.md", ""), "spec") == ("illisible", "fichier_vide", None, None)
    assert _lire(_ecrire(tmp_path / "e.md", b"\xff\xfe\x00titre", "wb"), "spec")[1] == "encodage_invalide"


def test_crlf_et_bom(tmp_path):
    """Review Focus 4 : un éditeur Windows écrit CRLF et parfois un BOM — même lecture qu'en LF."""
    p = _ecrire(tmp_path / "2026-09-26-x.md", "﻿---\r\netat: brouillon\r\n---\r\n# Titre CRLF\r\n".encode("utf-8"),
                "wb")
    etat, a, manques, fmt = _lire(p, "spec")
    assert etat == "indexe" and a["titre"] == "Titre CRLF" and a["etat"] == "brouillon" and fmt == {"etat"}


def test_spec_titre_date_du_nom_et_etat_non_declare(tmp_path):
    p = _ecrire(tmp_path / "2026-09-26-design.md", "```\n# pas un titre\n```\n# Le vrai titre\n")
    etat, a, manques, fmt = _lire(p, "spec")
    assert (a["titre"], a["date_declaree"], a["date_source"]) == ("Le vrai titre", "2026-09-26", "nom")
    assert manques == {"etat": "frontmatter_absent", "liens": "frontmatter_absent"} and fmt == set()


@pytest.mark.parametrize("nom, raison", [("sans-date.md", "nom_non_date"), ("2026-13-45-x.md", "nom_date_invalide")])
def test_plan_nom_sans_date_valide_jamais_de_repli(tmp_path, nom, raison):
    p = _ecrire(tmp_path / nom, "# Titre\n")
    _, a, manques, _ = _lire(p, "plan")
    assert a["date_declaree"] is None and a["date_source"] is None and manques["date_declaree"] == raison


def test_spec_sans_titre_md(tmp_path):
    _, a, manques, _ = _lire(_ecrire(tmp_path / "2026-09-26-x.md", "pas de titre\n"), "spec")
    assert a["titre"] is None and manques["titre"] == "titre_md_absent"


def test_date_frontmatter_invalide_ne_retombe_pas_sur_le_nom(tmp_path):
    _, a, manques, _ = _lire(_ecrire(tmp_path / "2026-09-26-x.md", "---\ndate: bientot\n---\n# T\n"), "spec")
    assert a["date_declaree"] is None and manques["date_declaree"] == "date_invalide"


def test_json_resultat_et_preinscription(tmp_path):
    r = _ecrire(tmp_path / "r.json", json.dumps({"name": "run", "verdict": {"x": 1}, "etat": "ok", "_regime": {},
                                                 "date": "2026-09-02"}))
    etat, a, manques, fmt = _lire(r, "resultat")
    assert (a["titre"], a["etat"], a["etat_source"], a["regime"], a["scelle"]) == ("run", "ok", "etat", True, None)
    assert (a["date_declaree"], a["date_source"]) == ("2026-09-02", "cle") and fmt == {"date", "etat"}
    s = _ecrire(tmp_path / "S2-X.json", json.dumps({"name": "S2-X", "rule": {}, "seal": "abc"}))
    _, b, manques, _ = _lire(s, "preinscription")
    assert b["scelle"] is True and b["etat"] is None and manques["etat"] == "cle_absente"


def test_json_verdict_dict_n_est_pas_un_etat(tmp_path):
    _, a, manques, _ = _lire(_ecrire(tmp_path / "r.json", json.dumps({"verdict": {"x": 1}})), "resultat")
    assert a["etat"] is None and manques["etat"] == "type_inattendu" and manques["titre"] == "cle_absente"


def test_json_racine_liste_et_json_invalide(tmp_path):
    etat, a, manques, _ = _lire(_ecrire(tmp_path / "l.json", "[1, 2]"), "resultat")
    assert etat == "indexe" and set(manques.values()) == {"racine_non_objet"} and a["regime"] is None
    assert _lire(_ecrire(tmp_path / "b.json", "{pas du json"), "resultat") == ("illisible", "json_invalide", None, None)


def test_pyyaml_absent_ne_rend_illisibles_que_les_fichiers_A_frontmatter(tmp_path, monkeypatch):
    import builtins
    vrai_import = builtins.__import__

    def _sans_yaml(name, *a, **k):
        if name == "yaml":
            raise ImportError("No module named 'yaml'", name="yaml")
        return vrai_import(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", _sans_yaml)
    avec = _ecrire(tmp_path / "2026-09-26-a.md", "---\netat: x\n---\n# A\n")
    sans = _ecrire(tmp_path / "2026-09-26-b.md", "# B\n")
    assert _lire(avec, "spec") == ("illisible", "pyyaml_absent", None, None)
    assert _lire(sans, "spec")[0] == "indexe"


def test_raisons_produites_toutes_dans_le_vocabulaire_ferme():
    assert IX.RAISONS_ILLISIBLE.isdisjoint(IX.RAISONS_CHAMP)
    for r in ("frontmatter_absent", "cle_absente", "type_inattendu", "racine_non_objet", "titre_md_absent",
              "nom_non_date", "nom_date_invalide", "date_invalide"):
        assert r in IX.RAISONS_CHAMP


def _depot(tmp_path):
    """Un dépôt jetable (fichiers seulement, pas de git) portant une famille de chaque forme."""
    r = tmp_path / "depot"
    _ecrire(r / "docs" / "EDR" / "001_a.md", "---\nid: EDR-001\ntitle: A\nverdict: V\n---\n")
    _ecrire(r / "docs" / "EDR" / "002_b.md", "# B sans frontmatter\n")
    _ecrire(r / "docs" / "EDR" / "README.md", "# lisez-moi\n")
    _ecrire(r / "docs" / "EDR" / "003_c.md", "---\ntitle: [x\n---\n")
    _ecrire(r / "docs" / "superpowers" / "specs" / "2026-09-01-s.md", "# S\n")
    _ecrire(r / "docs" / "superpowers" / "plans" / "sans-date.md", "# P\n")
    _ecrire(r / "results" / "r.json", json.dumps({"name": "r"}))
    _ecrire(r / "results" / "records_graph.json", "{}")
    return r


def _sans_dates(r):
    return {"doc": None, "chemin": str(r / "data" / "pm" / "DATES_GIT.json"), "raison": "introuvable"}


def _dates(dates, suivis, historique="complet"):
    return {"doc": {"schema": IX.SCHEMA_DATES, "generated_at": NOW - 600, "head": "abc", "historique": historique,
                    "raison": None, "dates": dates, "suivis": suivis}, "chemin": "x", "raison": None}


@pytest.fixture
def resultats_dans_le_depot(monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", "sentinelle")
    monkeypatch.delenv("AGAGI_RESULTS_ROOT", raising=False)


def _famille(out, nom):
    return next(f for f in out["familles"] if f["nom"] == nom)


def test_NO_OP_EXACT_racine_vide(tmp_path, resultats_dans_le_depot):
    out = IX.indexer(str(tmp_path), _sans_dates(tmp_path), NOW)
    assert out["schema"] == "index_v1" and out["artefacts"] == [] and out["hors_familles"] is None
    for f in out["familles"]:
        assert f["fichiers"] is None and f["indexes"] is None and f["illisibles"] is None, f
        assert f["exclus"] is None, f                  # revue du pas 1 (I5) : `[]` se lisait « rien d'exclu, mesuré »
    lignes = [a for a in out["aveugle"] if a.startswith("famille ")]
    assert len(lignes) == len(IX.FAMILLES) and all("absent" in a for a in lignes)
    assert any(a.startswith("dates : ") for a in out["aveugle"])
    assert not any(a.startswith("index:") for a in out["aveugle"])     # réservé au mode dégradé du service


def test_injection_a_dose_connue(tmp_path, resultats_dans_le_depot):
    r = _depot(tmp_path)
    out = IX.indexer(str(r), _sans_dates(r), NOW)
    rec = _famille(out, "record")
    assert (rec["fichiers"], rec["indexes"], rec["exclus"]) == (4, 2, ["README.md"])
    assert rec["illisibles"] == [{"chemin": "docs/EDR/003_c.md", "raison": "frontmatter_yaml_invalide"}]
    assert rec["champs_introuvables"]["titre"] == {"frontmatter_absent": 1}
    assert rec["champs_introuvables"]["date_ajout_git"] == {"dates_absentes": 2}
    res = _famille(out, "resultat")
    assert (res["fichiers"], res["indexes"], res["exclus"]) == (2, 1, ["records_graph.json"])
    plan = _famille(out, "plan")
    assert plan["champs_introuvables"]["date_declaree"] == {"nom_non_date": 1}
    assert _famille(out, "adr")["fichiers"] is None                     # répertoire absent : inconnu, jamais 0
    assert out["dates"] is None
    b = next(a for a in out["artefacts"] if a["chemin"] == "docs/EDR/002_b.md")
    assert b["titre"] is None and b["etat"] is None                    # contre-exemple B1 gelé


def test_prediction_un_fichier_de_plus(tmp_path, resultats_dans_le_depot):
    r = _depot(tmp_path)
    avant = IX.indexer(str(r), _sans_dates(r), NOW)
    _ecrire(r / "docs" / "superpowers" / "specs" / "2026-09-02-t.md", "# T\n")
    apres = IX.indexer(str(r), _sans_dates(r), NOW)
    for fa, fb in zip(avant["familles"], apres["familles"]):
        attendu = 1 if fa["nom"] == "spec" else 0
        if fa["fichiers"] is not None:
            assert (fb["fichiers"] - fa["fichiers"], fb["indexes"] - fa["indexes"]) == (attendu, attendu), fa["nom"]


def test_parite_rompue_aveugle_la_FAMILLE_seule(tmp_path, resultats_dans_le_depot, monkeypatch):
    r = _depot(tmp_path)
    vrai = IX.lire_fichier

    def _perd_un(chemin, rel, fam):
        return ("perdu", None, None, None) if rel.endswith("001_a.md") else vrai(chemin, rel, fam)
    monkeypatch.setattr(IX, "lire_fichier", _perd_un)
    out = IX.indexer(str(r), _sans_dates(r), NOW)
    assert _famille(out, "record")["fichiers"] is None and _famille(out, "record")["exclus"] is None
    assert any(a.startswith("famille record : parité rompue") for a in out["aveugle"])
    assert _famille(out, "spec")["indexes"] == 1                          # les autres familles restent servies
    assert not any(a["famille"] == "record" for a in out["artefacts"])


def test_fichier_disparu_entre_glob_et_lecture(tmp_path, resultats_dans_le_depot, monkeypatch):
    """Review Focus 1 : arbre partagé — une autre session supprime le fichier entre le glob et la lecture."""
    r = _depot(tmp_path)
    vrai_open = open

    def _open(chemin, *a, **k):
        if str(chemin).endswith("2026-09-01-s.md"):
            raise FileNotFoundError(chemin)
        return vrai_open(chemin, *a, **k)
    monkeypatch.setattr("builtins.open", _open)
    out = IX.indexer(str(r), _sans_dates(r), NOW)
    spec = _famille(out, "spec")
    assert spec["illisibles"] == [{"chemin": "docs/superpowers/specs/2026-09-01-s.md", "raison": "lecture_impossible"}]
    assert spec["fichiers"] == 1 and spec["indexes"] == 0


def test_dates_lues_age_sur_generated_at(tmp_path, resultats_dans_le_depot):
    r = _depot(tmp_path)
    out = IX.indexer(str(r), _dates({"docs/EDR/001_a.md": "2026-09-01"},
                                    ["docs/EDR/001_a.md", "docs/EDR/002_b.md", "docs/roadmap/X.md"]), NOW)
    a = next(x for x in out["artefacts"] if x["chemin"] == "docs/EDR/001_a.md")
    b = next(x for x in out["artefacts"] if x["chemin"] == "docs/EDR/002_b.md")
    assert a["date_ajout_git"] == "2026-09-01" and b["date_ajout_git"] is None
    assert _famille(out, "record")["champs_introuvables"]["date_ajout_git"] == {"sans_ajout_trouve": 1}
    assert out["dates"] == {"generated_at": NOW - 600, "age_s": 600.0, "head": "abc", "historique": "complet"}
    assert out["hors_familles"] == {"n": 1, "repertoires": {"docs/roadmap": 1}}


def test_hors_familles_groupe_par_REPERTOIRE_jamais_par_fichier(tmp_path, resultats_dans_le_depot):
    """Mesuré sur le dépôt réel : un fichier directement sous docs/ devenait sa propre clé (« docs/README.md: 1 »)."""
    r = _depot(tmp_path)
    out = IX.indexer(str(r), _dates({}, ["docs/README.md", "docs/BACKLOG.md", "docs/roadmap/a/b.md",
                                         "docs/roadmap/c.md", "results/s6/x.json"]), NOW)
    assert out["hors_familles"] == {"n": 5, "repertoires": {"docs": 2, "docs/roadmap": 2, "results/s6": 1}}


def test_chemin_absent_de_l_instantane(tmp_path, resultats_dans_le_depot):
    """Review Focus 2 : instantané écrit sur une autre branche — un chemin neuf n'a PAS de date, jamais une autre."""
    r = _depot(tmp_path)
    out = IX.indexer(str(r), _dates({}, []), NOW)
    assert all(x["date_ajout_git"] is None for x in out["artefacts"])
    assert _famille(out, "spec")["champs_introuvables"]["date_ajout_git"] == {"absent_des_dates": 1}


def test_chemin_DATE_mais_NON_SUIVI_n_a_pas_de_date(tmp_path, resultats_dans_le_depot):
    """Revue du pas 1 (I2) : l'historique porte un ajout, mais le chemin n'est pas dans l'instantané (retiré par
    `git rm`, recréé sur disque sans être ajouté) — aucune date, jamais celle d'un fichier qui n'existe plus."""
    r = _depot(tmp_path)
    out = IX.indexer(str(r), _dates({"docs/EDR/001_a.md": "2026-09-01"}, ["docs/EDR/002_b.md"]), NOW)
    a = next(x for x in out["artefacts"] if x["chemin"] == "docs/EDR/001_a.md")
    assert a["date_ajout_git"] is None
    assert _famille(out, "record")["champs_introuvables"]["date_ajout_git"] == {"absent_des_dates": 1,
                                                                               "sans_ajout_trouve": 1}


def test_json_trop_PROFOND_est_illisible_et_n_aveugle_pas_l_index(tmp_path, resultats_dans_le_depot):
    """Revue du pas 1 (I4) : sur une imbrication profonde, json.loads lève RecursionError, pas ValueError — un seul
    fichier faisait lever l'index ENTIER (principe §1.8 : un illisible est compté, il n'aveugle pas le reste)."""
    r = _depot(tmp_path)
    _ecrire(r / "results" / "profond.json", "[" * 100_000 + "]" * 100_000)
    out = IX.indexer(str(r), _sans_dates(r), NOW)
    assert {"chemin": "results/profond.json", "raison": "json_invalide"} in _famille(out, "resultat")["illisibles"]
    assert _famille(out, "record")["indexes"] == 2


@pytest.mark.parametrize("historique, raison", [("tronque", "historique_tronque"), ("indisponible", "git_indisponible")])
def test_historique_non_complet(tmp_path, resultats_dans_le_depot, historique, raison):
    r = _depot(tmp_path)
    out = IX.indexer(str(r), _dates(None, None, historique), NOW)
    assert _famille(out, "record")["champs_introuvables"]["date_ajout_git"] == {raison: 2}
    assert out["hors_familles"] is None and any(a.startswith("dates : ") for a in out["aveugle"])


def test_read_dates_absent_illisible_et_de_forme_inattendue(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    r = str(tmp_path)
    assert IX.read_dates(r)["raison"] == "introuvable"
    (tmp_path / "pm").mkdir()
    (tmp_path / "pm" / "DATES_GIT.json").write_text("{casse", encoding="utf-8")
    assert IX.read_dates(r)["raison"].startswith("illisible")
    (tmp_path / "pm" / "DATES_GIT.json").write_text(json.dumps({"schema": "autre"}), encoding="utf-8")
    assert IX.read_dates(r)["raison"].startswith("de forme inattendue")
    (tmp_path / "pm" / "DATES_GIT.json").write_text(json.dumps(
        {"schema": IX.SCHEMA_DATES, "generated_at": NOW, "head": "h", "historique": "complet", "raison": None,
         "dates": {"a.md": "2026-09-01"}, "suivis": ["a.md"]}), encoding="utf-8")
    lu = IX.read_dates(r)
    assert lu["raison"] is None and lu["doc"]["dates"] == {"a.md": "2026-09-01"}
    assert "AGAGI_DATA_ROOT" in os.environ                               # posé par le test, pas écrit par le lecteur


def test_age_des_dates_jamais_le_mtime(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    (tmp_path / "pm").mkdir()
    p = tmp_path / "pm" / "DATES_GIT.json"
    p.write_text(json.dumps({"schema": IX.SCHEMA_DATES, "generated_at": NOW - 3600, "head": "h",
                             "historique": "complet", "raison": None, "dates": {}, "suivis": []}), encoding="utf-8")
    os.utime(p, (NOW, NOW))                                              # mtime FRAIS, contenu d'il y a une heure
    out = IX.indexer(str(tmp_path), IX.read_dates(str(tmp_path)), NOW)
    assert out["dates"]["age_s"] == 3600.0


def test_read_dates_HOSTILE_refuse_localement_jamais_leve(tmp_path, monkeypatch):
    """Revue du pas 2 (I3, M8) : un entier géant faisait lever OverflowError, une imbrication profonde RecursionError
    — la route entière tombait en mode dégradé ; une date suivie d'un saut de ligne (le motif finissait par un
    dollar, qui l'accepte), une date impossible et un head non chaîne passaient la forme."""
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    (tmp_path / "pm").mkdir()
    p = tmp_path / "pm" / "DATES_GIT.json"
    base = {"schema": IX.SCHEMA_DATES, "generated_at": NOW, "head": "h", "historique": "complet", "raison": None,
            "dates": {"a.md": "2026-09-01"}, "suivis": ["a.md"]}
    cas = [('{"schema": "dates_git_v1", "generated_at": 1' + "0" * 400 + "}", "de forme inattendue"),
           ("[" * 200_000 + "]" * 200_000, "illisible"),
           (json.dumps({**base, "dates": {"a.md": "2026-01-01\n"}}), "de forme inattendue"),
           (json.dumps({**base, "dates": {"a.md": "2026-99-99"}}), "de forme inattendue"),
           (json.dumps({**base, "head": 12345}), "de forme inattendue")]
    for texte, debut in cas:
        p.write_text(texte, encoding="utf-8")
        lu = IX.read_dates(str(tmp_path))
        assert lu["doc"] is None and lu["raison"].startswith(debut), (texte[:60], lu["raison"])
    p.write_text(json.dumps(base), encoding="utf-8")
    assert IX.read_dates(str(tmp_path))["raison"] is None                  # contrôle : la forme saine passe


def test_instantane_dans_le_FUTUR_est_dit(tmp_path, resultats_dans_le_depot):
    """Revue du pas 2 (M8) : un écrivain à l'horloge en avance rendait un âge négatif, servi sans un mot."""
    r = _depot(tmp_path)
    lecture = _dates({}, [])
    lecture["doc"]["generated_at"] = NOW + 3600
    out = IX.indexer(str(r), lecture, NOW)
    assert out["dates"]["age_s"] == -3600.0
    assert any(a.startswith("dates : instantané daté dans le FUTUR") for a in out["aveugle"]), out["aveugle"]


def test_racine_avec_crochets_jamais_zero_fabrique(tmp_path, resultats_dans_le_depot):
    """Revue du pas 2 (M9) : glob lisait « [1] » d'un chemin comme une classe de caractères — 0 fichier, sans ligne."""
    r = _depot(tmp_path / "tmp_crochet[1]")
    rec = _famille(IX.indexer(str(r), _sans_dates(r), NOW), "record")
    assert (rec["fichiers"], rec["indexes"]) == (4, 2)


def test_liens_NON_LUS_valent_null_et_sont_comptes(tmp_path):
    """Revue du pas 2 (I5) : `liens: []` était servi pour les 34 records SANS frontmatter et pour tout json ou md —
    une liste vide présentée comme une mesure. [] = frontmatter lu, aucune arête déclarée ; null = rien n'a été lu
    ou la forme ne déclare pas de clé `liens` (spec §3.3), compté avec sa raison."""
    _, a, m, _ = _lire(_ecrire(tmp_path / "011_x.md", "# X\n"), "record")
    assert a["liens"] is None and m["liens"] == "frontmatter_absent"
    _, a, m, _ = _lire(_ecrire(tmp_path / "012_y.md", "---\nid: EDR-012\n---\n"), "record")
    assert a["liens"] == [] and "liens" not in m                          # lu, aucune arête : mesuré
    _, a, m, _ = _lire(_ecrire(tmp_path / "2026-09-26-s.md", "---\nliens: [EDR-A, EDR-B]\n---\n# S\n"), "spec")
    assert a["liens"] == [{"rel": "liens", "cible": "EDR-A"}, {"rel": "liens", "cible": "EDR-B"}]
    assert "liens" not in m
    _, a, m, _ = _lire(_ecrire(tmp_path / "2026-09-26-t.md", "---\netat: x\n---\n# T\n"), "spec")
    assert a["liens"] is None and m["liens"] == "cle_absente"
    _, a, m, _ = _lire(_ecrire(tmp_path / "2026-09-26-u.md", "# U\n"), "spec")
    assert a["liens"] is None and m["liens"] == "frontmatter_absent"
    _, a, m, _ = _lire(_ecrire(tmp_path / "r.json", json.dumps({"name": "r"})), "resultat")
    assert a["liens"] is None and m["liens"] == "cle_absente"
    _, a, m, _ = _lire(_ecrire(tmp_path / "q.json", json.dumps({"liens": ["EDR-C", 3]})), "resultat")
    assert a["liens"] == [{"rel": "liens", "cible": "EDR-C"}] and m["liens"] == "type_inattendu"


def test_parite_sur_le_depot_REEL():
    """Chaque fichier globbé des familles réelles finit dans exactement un compartiment, et aucune n'est null."""
    from tools.pm.pilotage import racine_depot
    r = racine_depot()
    out = IX.indexer(r, {"doc": None, "chemin": "-", "raison": "introuvable"}, NOW)
    for f in out["familles"]:
        assert f["fichiers"] is not None, (f["nom"], out["aveugle"])
        assert f["indexes"] + len(f["illisibles"]) + len(f["exclus"]) == f["fichiers"], f["nom"]
    raisons = {r for f in out["familles"] for c in f["champs_introuvables"].values() for r in c}
    raisons |= {i["raison"] for f in out["familles"] for i in f["illisibles"]}
    assert raisons <= IX.RAISONS_CHAMP | IX.RAISONS_ILLISIBLE | IX.RAISONS_DATE_GIT, raisons


import pathlib  # noqa: E402
import subprocess  # noqa: E402

from tools._git_env import env_isole  # noqa: E402


def _git(repo, *args, date=None):
    env = env_isole()
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                          cwd=repo, env=env, capture_output=True, encoding="utf-8", check=True).stdout


@pytest.fixture
def depot_git(tmp_path, monkeypatch):
    """Dépôt jetable RÉEL : deux commits à dates connues. AGAGI_DATA_ROOT sur tmp_path : l'écrivain n'écrit jamais
    dans le data/ réel. Environnement git isolé (règle à deux faces)."""
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path / "data").replace("\\", "/"))
    for v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(v, raising=False)
    r = tmp_path / "depot"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _ecrire(r / "docs" / "EDR" / "001_a.md", "---\nid: EDR-001\n---\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "a", date="2026-09-01T23:30:00+00:00")
    _ecrire(r / "docs" / "superpowers" / "specs" / "2026-09-02-s.md", "# S\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "s", date="2026-09-08T00:30:00+02:00")      # 2026-09-07 22:30 UTC
    return r


def test_calculer_dates_complet_en_UTC(depot_git):
    doc = IX.calculer_dates_git(str(depot_git), NOW)
    assert doc["historique"] == "complet" and doc["raison"] is None and len(doc["head"]) == 40
    assert doc["dates"] == {"docs/EDR/001_a.md": "2026-09-01",
                            "docs/superpowers/specs/2026-09-02-s.md": "2026-09-07"}       # jour UTC, pas local
    assert set(doc["suivis"]) == set(doc["dates"])


def test_chemin_ajoute_supprime_recree_prend_la_date_la_plus_ANCIENNE(depot_git):
    _git(depot_git, "rm", "-q", "docs/EDR/001_a.md")
    _git(depot_git, "commit", "-q", "-m", "rm", date="2026-09-10T12:00:00+00:00")
    _ecrire(depot_git / "docs" / "EDR" / "001_a.md", "---\nid: EDR-001\n---\nv2\n")
    _git(depot_git, "add", "-A")
    _git(depot_git, "commit", "-q", "-m", "re", date="2026-09-12T12:00:00+00:00")
    assert IX.calculer_dates_git(str(depot_git), NOW)["dates"]["docs/EDR/001_a.md"] == "2026-09-01"


def test_renommage_est_une_entree_du_chemin(depot_git):
    _git(depot_git, "mv", "docs/EDR/001_a.md", "docs/EDR/001_b.md")
    _git(depot_git, "commit", "-q", "-m", "mv", date="2026-09-15T12:00:00+00:00")
    assert IX.calculer_dates_git(str(depot_git), NOW)["dates"]["docs/EDR/001_b.md"] == "2026-09-15"


def test_config_heritee_sans_effet(depot_git):
    """Review Focus 5 : diff.renames, core.quotepath et log.showRoot posés dans la config du dépôt ne changent rien.
    `log.showRoot=false` (revue du pas 1, I1) retirait au commit RACINE sa liste de fichiers : ses ajouts perdaient
    leur date."""
    avant = IX.calculer_dates_git(str(depot_git), NOW)["dates"]
    assert "docs/EDR/001_a.md" in avant                                   # contrôle : ajouté par le commit racine
    _git(depot_git, "config", "diff.renames", "copies")
    _git(depot_git, "config", "core.quotepath", "true")
    _git(depot_git, "config", "log.showRoot", "false")
    assert IX.calculer_dates_git(str(depot_git), NOW)["dates"] == avant


def test_nom_non_ascii_est_date(depot_git):
    """Review Focus 3 : sans core.quotepath=false, git citerait le nom entre guillemets, octets échappés."""
    _ecrire(depot_git / "docs" / "EDR" / "002_été.md", "# x\n")
    _git(depot_git, "add", "-A")
    _git(depot_git, "commit", "-q", "-m", "e", date="2026-09-20T12:00:00+00:00")
    assert IX.calculer_dates_git(str(depot_git), NOW)["dates"].get("docs/EDR/002_été.md") == "2026-09-20"


def test_clone_superficiel_est_TRONQUE_jamais_date_du_jour(depot_git, tmp_path):
    """B3 de la revue : un clone --depth 1 datait tout du jour du clone."""
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--depth", "1", pathlib.Path(depot_git).as_uri(), str(clone))   # file:///C:/…
    doc = IX.calculer_dates_git(str(clone), NOW)
    assert doc["historique"] == "tronque" and doc["dates"] is None and doc["suivis"] is None
    assert "superficiel" in doc["raison"]


def test_vieux_git_qui_renvoie_le_drapeau_n_est_JAMAIS_lu_comme_complet(depot_git, monkeypatch):
    """Revue du pas 1 (I3) : rev-parse renvoie TEL QUEL un drapeau qu'il ne connaît pas, avec le code 0 (mesuré sur
    le git courant avec un drapeau inexistant) ; un git antérieur à 2.15 ferait de même avec
    --is-shallow-repository, et un clone superficiel passait pour complet. Seuls true et false sont des réponses."""
    vrai = IX._git

    def _vieux(racine, env, *args):
        if "--is-shallow-repository" in args:
            return "--is-shallow-repository\n", None
        return vrai(racine, env, *args)
    monkeypatch.setattr(IX, "_git", _vieux)
    doc = IX.calculer_dates_git(str(depot_git), NOW)
    assert doc["historique"] == "indisponible" and doc["dates"] is None and doc["suivis"] is None
    assert "--is-shallow-repository" in doc["raison"]


def test_fuite_de_GIT_DIR_REFUSEE_jamais_datee_par_un_autre_depot(depot_git, tmp_path, monkeypatch):
    """Revue du pas 1 (B1). Racine = dépôt courant : l'environnement est HÉRITÉ (`_env_pour` rend None). Un GIT_DIR
    hérité d'un AUTRE dépôt passait la garde du toplevel (`--show-toplevel` rend alors le cwd) et l'instantané
    sortait « complet », avec les dates et le head de l'autre dépôt (spec §3.1 et §5 : ce cas est refusé)."""
    autre = tmp_path / "autre"
    autre.mkdir()
    _git(autre, "init", "-q", "-b", "main")
    _ecrire(autre / "docs" / "EDR" / "009_z.md", "# z\n")
    _git(autre, "add", "-A")
    _git(autre, "commit", "-q", "-m", "z", date="2026-01-01T12:00:00+00:00")
    from tools import check_evidence_provenance as P
    monkeypatch.setattr(P, "_env_pour", lambda root: None)
    monkeypatch.setenv("GIT_DIR", str(autre / ".git"))
    doc = IX.calculer_dates_git(str(depot_git), NOW)
    assert doc["historique"] == "indisponible" and doc["dates"] is None and doc["suivis"] is None
    assert doc["head"] is None                                           # jamais le head de l'autre dépôt
    assert "GIT_DIR" in doc["raison"] and "autre" in doc["raison"]


def test_GIT_DIR_herite_du_MEME_depot_reste_complet(depot_git, monkeypatch):
    """Contre-exemple du refus ci-dessus : pendant un hook, git exporte GIT_DIR vers le dépôt MÊME (souvent en
    relatif). Refuser dès qu'une variable GIT_* est héritée aveuglerait un tick lancé depuis un hook."""
    from tools import check_evidence_provenance as P
    monkeypatch.setattr(P, "_env_pour", lambda root: None)
    monkeypatch.setenv("GIT_DIR", ".git")
    doc = IX.calculer_dates_git(str(depot_git), NOW)
    assert doc["historique"] == "complet" and doc["raison"] is None


def test_suivis_viennent_de_HEAD_jamais_de_l_index(depot_git):
    """Revue du pas 1 : l'instantané publie `head` ; ses suivis sont ceux de HEAD. L'index ambiant de l'arbre
    PARTAGÉ porte le travail stagé d'autres sessions — il ne décrit aucun commit."""
    _ecrire(depot_git / "docs" / "EDR" / "010_stage.md", "# s\n")
    _git(depot_git, "add", "docs/EDR/010_stage.md")
    doc = IX.calculer_dates_git(str(depot_git), NOW)
    assert doc["historique"] == "complet"
    assert "docs/EDR/010_stage.md" not in doc["suivis"] and "docs/EDR/001_a.md" in doc["suivis"]


def test_chemin_retire_puis_recree_hors_git_n_a_pas_de_date(depot_git, resultats_dans_le_depot):
    """Revue du pas 1 (I2), le scénario de la sonde bout à bout : ajouté, `git rm`, recréé sur disque sans `git add`."""
    _git(depot_git, "rm", "-q", "docs/EDR/001_a.md")
    _git(depot_git, "commit", "-q", "-m", "rm", date="2026-09-10T12:00:00+00:00")
    _ecrire(depot_git / "docs" / "EDR" / "001_a.md", "---\nid: EDR-001\n---\n")
    doc = IX.calculer_dates_git(str(depot_git), NOW)
    assert "docs/EDR/001_a.md" in doc["dates"] and "docs/EDR/001_a.md" not in doc["suivis"]   # l'histoire garde l'ajout
    out = IX.indexer(str(depot_git), {"doc": doc, "chemin": "-", "raison": None}, NOW)
    a = next(x for x in out["artefacts"] if x["chemin"] == "docs/EDR/001_a.md")
    assert a["date_ajout_git"] is None
    assert _famille(out, "record")["champs_introuvables"]["date_ajout_git"] == {"absent_des_dates": 1}


def test_hors_depot_et_racine_qui_n_est_pas_le_toplevel(tmp_path, depot_git):
    assert IX.calculer_dates_git(str(tmp_path / "nulle_part"), NOW)["historique"] == "indisponible"
    doc = IX.calculer_dates_git(str(depot_git / "docs"), NOW)             # un sous-répertoire n'est pas la racine
    assert doc["historique"] == "indisponible" and "toplevel" in doc["raison"]


def test_ecrire_puis_lire_boucle_complete(depot_git):
    doc, chemin = IX.ecrire_dates_git(str(depot_git), NOW)
    assert os.path.isfile(chemin) and chemin.endswith("pm/DATES_GIT.json")
    lu = IX.read_dates(str(depot_git))
    assert lu["raison"] is None and lu["doc"] == doc
    out = IX.indexer(str(depot_git), lu, NOW)
    a = next(x for x in out["artefacts"] if x["chemin"] == "docs/EDR/001_a.md")
    assert a["date_ajout_git"] == "2026-09-01"


def test_main_json_n_ecrit_rien_et_ecrire_dates_ecrit_UN_fichier(depot_git, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    avant = sorted(os.listdir(tmp_path))
    assert IX.main(["--json", "--repo-root", str(depot_git)]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == "index_v1"
    assert sorted(os.listdir(tmp_path)) == avant
    assert IX.main(["--ecrire-dates", "--repo-root", str(depot_git)]) == 0
    assert os.listdir(tmp_path / "data" / "pm") == ["DATES_GIT.json"]


def test_ecrire_dates_sur_clone_superficiel_n_annonce_pas_0_date(depot_git, tmp_path, capsys):
    """Revue du pas 1 : la CLI imprimait « 0 date(s) » quand AUCUNE date n'est publiée (dates null) — un zéro
    fabriqué dans un message, la forme (a) du biais du dépôt."""
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--depth", "1", pathlib.Path(depot_git).as_uri(), str(clone))
    capsys.readouterr()
    assert IX.main(["--ecrire-dates", "--repo-root", str(clone)]) == 1
    sortie = capsys.readouterr().out
    assert "0 date" not in sortie and "aucune date publiée" in sortie and "tronque" in sortie
