# -*- coding: utf-8 -*-
"""Lot 2 « Science » (P2.84). EXEMPTION DÉCLARÉE de la garde de bail : aucun monde, aucun bail.
Aucun test n'écrit dans l'arbre : sources injectées, fichiers sous tmp_path."""
import copy
import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import index_artefacts as IX  # noqa: E402
from tools.pm import science as S  # noqa: E402

_LEASE_GUARD_EXEMPT = True
NOW = 1_800_000_000.0
PIPE = {"couverture": {"inspectees": 20, "sans_grandeur": 13, "sans_record": 2, "total": 35},
        "familles_sans_record": ["EVO-022", "EVO-028-SMOKE"], "raison": None}
GRAPHE = {"verdicts": 2, "chemin": "C:/depot/graphe.json", "raison": None}
CLES_SEMAINES = {"date", "semaines", "sans_date", "semaine_partielle", "raison"}


def _ts(jour, heure=12):
    """Horodatage UTC d'un jour `AAAA-MM-JJ`, à midi."""
    return datetime.datetime.fromisoformat(jour).replace(hour=heure, tzinfo=datetime.timezone.utc).timestamp()


def _art(famille, chemin, **k):
    a = {"famille": famille, "chemin": chemin, "titre": None, "date_declaree": None, "date_source": None,
         "date_ajout_git": None, "etat": None, "etat_source": None, "regime": None, "scelle": None, "gate": None,
         "liens": []}
    a.update(k)
    return a


def _index(arts, historique="complet", now=NOW):
    """index_v1 COHÉRENT : chaque famille réelle, ses comptes et ses manques de date recalculés depuis `arts` comme
    l'indexeur les compterait (sans date d'ajout : sans_ajout_trouve si l'instantané est complet, dates_absentes
    sinon ; sans date déclarée : nom_non_date). L'instantané des dates est pris une minute avant `now`."""
    familles = []
    for f in IX.FAMILLES:
        siens = [a for a in arts if a["famille"] == f.nom]
        manques = {}
        for champ, raison in (("date_ajout_git", "sans_ajout_trouve" if historique == "complet" else "dates_absentes"),
                              ("date_declaree", "nom_non_date")):
            n = sum(1 for a in siens if not a[champ])
            manques[champ] = {raison: n} if n else {}
        familles.append({"nom": f.nom, "motif": f.motif, "repertoire": f.nom, "exclus": [], "fichiers": len(siens),
                         "indexes": len(siens), "illisibles": [], "champs_introuvables": manques,
                         "format_declare": {}})
    dates = None if historique is None else {"generated_at": now - 60, "age_s": 60.0, "head": "abc",
                                             "historique": historique}
    return {"schema": "index_v1", "generated_at": now, "repo_root": "C:/depot", "aveugle": [], "dates": dates,
            "familles": familles, "hors_familles": None, "artefacts": arts}


def _famille(index, nom):
    return next(f for f in index["familles"] if f["nom"] == nom)


def _taxo():
    return {"chemin": "C:/depot/agi_taxonomy", "raison": None,
            "capabilities": [{"id": "perception", "title": "P", "record": "docs/EDR/a.md"}, {"id": "memory"}],
            "demands": [{"capability": "memory", "prerequisite": "perception", "strength": "hard",
                         "evidence": {"ablation_verdict": "X_DEMANDED", "ratio": 3.9, "n": 12,
                                      "record": "docs/EDR/b.md"}, "reason": "r"}],
            "refuted": [{"capability": "memory", "prerequisite": "perception", "verdict": "NEGATIVE_NOT_MEASURABLE",
                         "reason": "r2", "evidence": {"n": 12, "record": "docs/EDR/c.md"},
                         "superseded_by": "docs/EDR/b.md"}]}


def _science(arts, **k):
    now = k.get("now", NOW)
    return S.compute_science(k.get("index") or _index(arts, k.get("historique", "complet"), now), k.get("pipe", PIPE),
                             k.get("taxo") or _taxo(), k.get("graphe", GRAPHE), now)


def test_NO_OP_EXACT_toutes_sources_absentes():
    index = {"schema": "index_v1", "generated_at": NOW, "repo_root": None, "aveugle": ["index: RuntimeError: x"],
             "dates": None, "familles": None, "hors_familles": None, "artefacts": None}
    out = S.compute_science(index, {"couverture": None, "familles_sans_record": None, "raison": "RacineSansSource: x"},
                            {"chemin": "C:/x", "raison": "capabilities.json introuvable", "capabilities": None,
                             "demands": None, "refuted": None},
                            {"verdicts": None, "chemin": "C:/x/g.json", "raison": "introuvable"}, NOW)
    assert (out["pipeline"], out["taxonomie"], out["trouvailles"]) == (None, None, None)
    prefixes = {a.split(" : ")[0] for a in out["aveugle"]}
    assert prefixes == {"pipeline", "taxonomie", "trouvailles"}, out["aveugle"]
    assert not any(a.startswith(("science:", "index:")) for a in out["aveugle"])     # relayé SOUS « trouvailles : »


def test_pipeline_recopiee_a_l_identique_et_preinscriptions_de_l_index():
    arts = [_art("preinscription", "docs/preregistrations/A.json", titre="A", scelle=True, date_ajout_git="2026-09-02"),
            _art("preinscription", "docs/preregistrations/B.json")]
    p = _science(arts)["pipeline"]
    assert p["couverture"] == PIPE["couverture"] and p["familles_sans_record"] == ["EVO-022", "EVO-028-SMOKE"]
    assert p["preinscriptions"] == [
        {"chemin": "docs/preregistrations/A.json", "titre": "A", "scelle": True, "date_ajout_git": "2026-09-02"},
        {"chemin": "docs/preregistrations/B.json", "titre": None, "scelle": None, "date_ajout_git": None}]


def test_pipeline_module_SANS_racine_leve_et_devient_null(tmp_path, monkeypatch):
    """Contre-exemple B2 gelé : sans ses répertoires, le module rendait (0, 0, 0, 0) ; depuis P2.135 il lève."""
    from tools import check_preregistration_applied as cpa
    monkeypatch.setattr(cpa, "_PREREG", str(tmp_path / "absent_prereg"))
    monkeypatch.setattr(cpa, "_EDR", str(tmp_path / "absent_edr"))
    lu = S.lire_pipeline()
    assert lu["couverture"] is None and lu["raison"].startswith("RacineSansSource")
    out = _science([], pipe=lu)
    assert out["pipeline"] is None
    assert any(a.startswith("pipeline : ") and "RacineSansSource" in a for a in out["aveugle"])


def test_pipeline_famille_preinscription_non_lue_liste_null_jamais_vide():
    index = _index([])
    _famille(index, "preinscription")["fichiers"] = None
    out = _science([], index=index)
    assert out["pipeline"]["preinscriptions"] is None
    assert any(a.startswith("pipeline : ") and "pré-inscriptions" in a for a in out["aveugle"])


def test_pipeline_PARITE_compte_contre_liste_DITE():
    """Revue de la tâche 1 (M4) : `couverture()` et `familles_sans_record()` sont deux passes de `_inspection()` sur un
    arbre PARTAGÉ ; le compte et la liste peuvent diverger. Les deux sont servis tels quels, l'écart est DIT."""
    pipe = copy.deepcopy(PIPE)
    pipe["familles_sans_record"] = ["EVO-022"]
    out = _science([], pipe=pipe)
    assert out["pipeline"]["couverture"]["sans_record"] == 2 and out["pipeline"]["familles_sans_record"] == ["EVO-022"]
    assert any(a.startswith("pipeline : ") and "2 famille(s) sans record" in a and "en nomme 1" in a
               for a in out["aveugle"]), out["aveugle"]
    assert not any(a.startswith("pipeline : ") for a in _science([])["aveugle"])          # 2 contre 2 : aucune ligne


def test_taxonomie_REELLE_etablies_et_refutees_depassees():
    from tools.pm.pilotage import racine_depot
    out = S.compute_science(_index([]), PIPE, S.lire_taxonomie(racine_depot()), GRAPHE, NOW)
    t = out["taxonomie"]
    etablies = [a for a in t["aretes"] if a["nature"] == "etablie"]
    refutees = [a for a in t["aretes"] if a["nature"] == "refutee"]
    assert (len(t["capacites"]), len(etablies), len(refutees)) == (4, 3, 2)
    assert all(a["depassee_par"] for a in refutees) and all(a["verdict"] for a in t["aretes"])
    # I5 : le contrôle qui fonde chaque arête établie est servi avec elle (check_agi_taxonomy l'exige « pass »)
    assert all(a["preuves"]["specificity_control"] == "pass" and a["preuves"]["ceiling_provenance"] for a in etablies)
    assert not any(a.startswith("taxonomie : ") for a in out["aveugle"]), out["aveugle"]


def test_taxonomie_prediction_une_refutee_retiree_est_NOMMEE_absente():
    from tools.pm.pilotage import racine_depot
    source = S.lire_taxonomie(racine_depot())
    retiree = copy.deepcopy(source)
    perdue = retiree["refuted"].pop(0)
    t = S.compute_science(_index([]), PIPE, retiree, GRAPHE, NOW)["taxonomie"]
    refutees = [a for a in t["aretes"] if a["nature"] == "refutee"]
    assert len(refutees) == 1 and perdue["evidence"]["record"] not in {a["record"] for a in refutees}


def test_taxonomie_entrees_illisibles_comptees_et_nommees():
    taxo = _taxo()
    taxo["demands"].append({"capability": "memory"})                           # sans prérequis
    taxo["demands"][0]["evidence"]["ratio"] = float("nan")                     # json.load accepte NaN
    taxo["refuted"].append({"capability": "language", "prerequisite": "vision", "verdict": "X"})
    out = _science([], taxo=taxo)
    t = out["taxonomie"]
    assert len(t["aretes"]) == 3 and t["aretes"][0]["ratio"] is None
    assert any("1 entrée(s) de demands.json" in a and "indice 1" in a for a in out["aveugle"]), out["aveugle"]
    assert any("capacité non déclarée" in a and "language" in a and "vision" in a for a in out["aveugle"])
    # M2 : le NaN n'est plus avalé sans ligne
    assert any("mal typée" in a and "demands.json[0].evidence.ratio" in a for a in out["aveugle"]), out["aveugle"]


def test_taxonomie_PREUVES_recopiees_et_assainies():
    """Revue de la tâche 1, I5 — décision d'intégrateur (Master 2, 2026-10-14) : `specificity_control` porte le contenu
    empirique de l'arête (`check_agi_taxonomy`) ; une arête « établie » ne se sert pas sans lui. Les sept champs sont
    recopiés dans `preuves` : une chaîne ou un nombre FINI passe ; une autre valeur devient null AVEC sa ligne ; un
    champ ABSENT reste null sans ligne (la source ne déclare rien, c'est une recopie fidèle)."""
    taxo = _taxo()
    taxo["demands"][0]["evidence"].update(specificity_control="pass", functional_aliasing="n/a", coord_intact=0.65,
                                          emergence_bar=float("inf"), incapable_ceiling=[0.2],
                                          ceiling_provenance="plafond d'un agent non entraîné")
    out = _science([], taxo=taxo)
    etablie, refutee = out["taxonomie"]["aretes"]
    assert etablie["preuves"] == {"specificity_control": "pass", "functional_aliasing": "n/a", "ablation_target": None,
                                  "coord_intact": 0.65, "emergence_bar": None, "incapable_ceiling": None,
                                  "ceiling_provenance": "plafond d'un agent non entraîné"}
    ligne = next(a for a in out["aveugle"] if "mal typée" in a)
    assert ligne.startswith("taxonomie : 2 valeur(s)"), ligne
    assert "demands.json[0].evidence.emergence_bar" in ligne and "demands.json[0].evidence.incapable_ceiling" in ligne
    assert "ablation_target" not in ligne                                         # absent : rien à dire
    assert set(refutee["preuves"]) == set(S.PREUVES) and set(refutee["preuves"].values()) == {None}


def test_taxonomie_ENTIER_GEANT_et_chaines_mal_typees_null_et_NOMMES():
    """Revue de la tâche 1, M3 : `math.isfinite(10**400)` lève OverflowError — compute_science levait, le service
    basculait en `science:` et les TROIS blocs passaient à null pour un seul champ. M2 : un `superseded_by` mal typé
    faisait lire la réfutée comme toujours valable, sans un mot."""
    taxo = _taxo()
    taxo["demands"][0]["evidence"]["ratio"] = 10 ** 400
    taxo["demands"][0]["strength"] = 3
    taxo["refuted"][0]["superseded_by"] = ["docs/EDR/b.md"]
    out = _science([], taxo=taxo)
    etablie, refutee = out["taxonomie"]["aretes"]
    assert (etablie["ratio"], etablie["force"], refutee["depassee_par"]) == (None, None, None)
    ligne = next(a for a in out["aveugle"] if "mal typée" in a)
    for nom in ("demands.json[0].evidence.ratio", "demands.json[0].strength", "refuted.json[0].superseded_by"):
        assert nom in ligne, ligne
    assert out["pipeline"] is not None and out["trouvailles"] is not None


def test_taxonomie_absente_null_et_ligne(tmp_path, monkeypatch):
    monkeypatch.delenv("AGAGI_DATA_ROOT", raising=False)
    lu = S.lire_taxonomie(str(tmp_path))
    assert lu["raison"] == "capabilities.json introuvable" and lu["capabilities"] is None
    out = _science([], taxo=lu)
    assert out["taxonomie"] is None and any(a.startswith("taxonomie : ") for a in out["aveugle"])


@pytest.mark.parametrize("contenu, debut", [("[", "capabilities.json illisible (JSON invalide"),
                                            ('{"a": 1}', "capabilities.json n'est pas une liste")])
def test_lire_taxonomie_ILLISIBLE_ou_non_liste_NOMMEE(tmp_path, monkeypatch, contenu, debut):
    """Revue de la tâche 1 (M9) : les branches « illisible » et « pas une liste » n'avaient aucun témoin."""
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path / "d"))
    (tmp_path / "d" / "agi_taxonomy").mkdir(parents=True)
    (tmp_path / "d" / "agi_taxonomy" / "capabilities.json").write_text(contenu, encoding="utf-8")
    lu = S.lire_taxonomie(str(tmp_path))
    assert lu["raison"].startswith(debut) and (lu["capabilities"], lu["demands"], lu["refuted"]) == (None, None, None)


def test_trouvailles_verdicts_de_l_index_et_ecart_au_graphe():
    arts = [_art("record", "docs/EDR/1.md", titre="A", etat="X_DEMANDED", etat_source="verdict", gate="G1",
                 date_ajout_git="2026-09-01"),
            _art("record", "docs/EDR/2.md", etat="NEG", etat_source="verdict"),
            _art("record", "docs/EDR/3.md", etat="open", etat_source="status"),
            _art("resultat", "x/r.json", etat="V", etat_source="verdict")]       # M9 : un résultat n'est pas un record
    tr = _science(arts)["trouvailles"]
    assert [v["chemin"] for v in tr["verdicts"]] == ["docs/EDR/1.md", "docs/EDR/2.md"]
    assert tr["verdicts"][0] == {"chemin": "docs/EDR/1.md", "titre": "A", "verdict": "X_DEMANDED", "gate": "G1",
                                 "date_ajout_git": "2026-09-01"}
    assert tr["verdicts_partiels"] is False
    out = _science(arts, graphe={"verdicts": 5, "chemin": "C:/depot/graphe.json", "raison": None})
    assert any("compte 5 verdicts" in a and "en lit 2" in a for a in out["aveugle"])
    assert not any("compte" in a for a in _science(arts)["aveugle"])       # 2 contre 2 : aucune ligne d'écart


def test_ecart_au_graphe_LIBELLE_PAR_LES_FAITS_jamais_une_cause():
    """Revue de la tâche 1 (I6) : le graphe couvre SDR/ADR/EDR/REF, l'index docs/EDR seulement ; « graphe à
    regénérer » affirmait une cause sur deux populations différentes."""
    arts = [_art("record", "docs/EDR/1.md", etat="V", etat_source="verdict")]
    out = _science(arts, graphe={"verdicts": 3, "chemin": "C:/depot/graphe.json", "raison": None})
    ligne = next(a for a in out["aveugle"] if "compte 3 verdicts" in a)
    assert "SDR/ADR/EDR/REF" in ligne and "docs/EDR" in ligne and "non attribué" in ligne, ligne


def test_trouvailles_records_ILLISIBLES_liste_PARTIELLE_dite():
    """Revue de la tâche 1 (I1-a) : un record illisible sortait de la liste des verdicts sans une ligne."""
    index = _index([_art("record", "docs/EDR/1.md", etat="V", etat_source="verdict")])
    _famille(index, "record").update(fichiers=2, illisibles=[{"chemin": "docs/EDR/2.md",
                                                              "raison": "frontmatter_yaml_invalide"}])
    out = _science([], index=index)
    assert len(out["trouvailles"]["verdicts"]) == 1 and out["trouvailles"]["verdicts_partiels"] is True
    assert any(a.startswith("trouvailles : ") and "1 record(s) illisible(s)" in a and "frontmatter_yaml_invalide" in a
               and "PARTIELLE" in a for a in out["aveugle"]), out["aveugle"]


def test_trouvailles_TOUS_illisibles_verdicts_null_jamais_une_liste_vide():
    """Revue de la tâche 1 (I1-a, sonde S6) : PyYAML absent, `verdicts == []` était servi et la seule ligne émise
    accusait le graphe."""
    index = _index([])
    _famille(index, "record").update(fichiers=3, indexes=0, illisibles=[
        {"chemin": f"docs/EDR/{i}.md", "raison": "pyyaml_absent"} for i in range(3)])
    out = _science([], index=index)
    assert out["trouvailles"]["verdicts"] is None and out["trouvailles"]["verdicts_partiels"] is None
    assert any(a.startswith("trouvailles : ") and "aucun des 3 record(s)" in a and "pyyaml_absent" in a
               for a in out["aveugle"]), out["aveugle"]
    assert not any("compte 2 verdicts" in a for a in out["aveugle"])         # l'écart n'accuse plus le graphe


def test_trouvailles_ETAT_MAL_TYPE_relaye():
    """Revue de la tâche 1 (I1-b) : l'index compte désormais un verdict mal typé (`type_inattendu`) au lieu de le
    masquer par `status` ; science le RELAIE — un verdict peut manquer à la liste."""
    index = _index([_art("record", "docs/EDR/1.md", etat="V", etat_source="verdict"), _art("record", "docs/EDR/2.md")])
    _famille(index, "record")["champs_introuvables"]["etat"] = {"type_inattendu": 1}
    out = _science([], index=index)
    assert out["trouvailles"]["verdicts_partiels"] is True
    assert any(a.startswith("trouvailles : ") and "1 record(s) à état mal typé" in a for a in out["aveugle"])


def test_graphe_absent_ecart_non_mesure_verdicts_servis():
    arts = [_art("record", "docs/EDR/1.md", etat="V", etat_source="verdict")]
    out = _science(arts, graphe={"verdicts": None, "chemin": "C:/depot/graphe.json", "raison": "introuvable"})
    assert out["trouvailles"]["compte_graphe"] is None and len(out["trouvailles"]["verdicts"]) == 1
    assert any(a.startswith("trouvailles : ") and "non mesuré" in a for a in out["aveugle"])


@pytest.mark.parametrize("contenu, verdicts, raison", [
    (None, None, "introuvable"),
    ("{", None, "illisible"),
    ("[]", None, "illisible"),
    ('{"graph": {"nodes": {}}}', None, "illisible"),
    ('{"graph": {"nodes": "VV"}}', None, "illisible"),
    ('{"graph": {"nodes": [{"verdict": "A"}, {"verdict": " "}, {"verdict": 3}, {"id": "B"}, "C", {"verdict": "D"}]}}',
     2, None),
])
def test_lire_graphe_COMPTE_CONNU_et_formes_refusees(tmp_path, monkeypatch, contenu, verdicts, raison):
    """Revue de la tâche 1 (I6) : `lire_graphe` n'était exercé par AUCUN témoin (un mutant `len(noeuds)` survivait),
    et un `nodes` dict ou chaîne rendait `verdicts: 0` avec `raison: None` — servi comme une mesure."""
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "r"))
    if contenu is not None:
        (tmp_path / "r").mkdir()
        (tmp_path / "r" / "records_graph.json").write_text(contenu, encoding="utf-8")
    g = S.lire_graphe(str(tmp_path))
    assert g["verdicts"] == verdicts
    if raison is None:
        assert g["raison"] is None
    else:
        assert g["raison"].startswith(raison), g["raison"]


def test_index_degrade_trouvailles_null_taxonomie_servie():
    index = _index([])
    index.update(familles=None, artefacts=None, aveugle=["index: RuntimeError: boum"])
    out = _science([], index=index)
    assert out["trouvailles"] is None and out["taxonomie"] is not None
    assert out["pipeline"]["preinscriptions"] is None


def test_par_semaine_DENSE_semaine_intermediaire_a_zero():
    arts = [_art("record", "docs/EDR/1.md", date_ajout_git="2026-09-01"),
            _art("record", "docs/EDR/2.md", date_ajout_git="2026-09-15"),
            _art("record", "docs/EDR/3.md")]
    ps = _science(arts, now=_ts("2026-09-16"))["trouvailles"]["par_semaine"]
    assert ps["record"] == {"date": "date_ajout_git", "semaines": {"2026-W36": 1, "2026-W37": 0, "2026-W38": 1},
                            "sans_date": {"sans_ajout_trouve": 1}, "semaine_partielle": "2026-W38", "raison": None}
    assert ps["adr"] == {"date": "date_ajout_git", "semaines": {}, "sans_date": {}, "semaine_partielle": None,
                         "raison": None}                                       # répertoire lu, vide : mesuré


def test_par_semaine_DENSE_JUSQU_A_L_INSTANTANE_zeros_mesures_semaine_partielle_dite():
    """Revue de la tâche 1 (I3) : l'intervalle s'arrêtait à la dernière date — les semaines vides jusqu'à l'instantané
    manquaient au lieu d'être des zéros mesurés, et la semaine de l'instantané se lisait pleine."""
    now = _ts("2026-09-23")
    out = _science([_art("record", "docs/EDR/1.md", date_ajout_git="2026-09-01")], now=now)
    ps = out["trouvailles"]["par_semaine"]["record"]
    assert ps["semaines"] == {"2026-W36": 1, "2026-W37": 0, "2026-W38": 0, "2026-W39": 0}
    assert ps["semaine_partielle"] == "2026-W39"
    assert out["trouvailles"]["dates"] == {"generated_at": now - 60, "age_s": 60.0, "head": "abc",
                                           "historique": "complet"}
    assert _science([], historique=None)["trouvailles"]["dates"] is None


def test_par_semaine_borne_par_l_INSTANTANE_pour_git_par_now_pour_le_nom():
    now = _ts("2026-09-23")
    index = _index([_art("record", "docs/EDR/1.md", date_ajout_git="2026-09-01"),
                    _art("spec", "docs/superpowers/specs/2026-09-01-s.md", date_declaree="2026-09-01")], now=now)
    index["dates"].update(generated_at=_ts("2026-09-08"), age_s=now - _ts("2026-09-08"))
    ps = _science([], index=index, now=now)["trouvailles"]["par_semaine"]
    assert list(ps["record"]["semaines"]) == ["2026-W36", "2026-W37"]
    assert ps["record"]["semaine_partielle"] == "2026-W37"
    assert list(ps["spec"]["semaines"])[-1] == "2026-W39" and ps["spec"]["semaine_partielle"] == "2026-W39"


def test_instantane_HORS_CALENDRIER_borne_par_now_jamais_une_exception():
    """`_forme_dates` accepte tout `generated_at` FINI : 1e300 passe l'index (ligne FUTUR) et ne doit pas faire lever
    la conversion en jour."""
    now = _ts("2026-09-16")
    index = _index([_art("record", "docs/EDR/1.md", date_ajout_git="2026-09-15")], now=now)
    index["dates"].update(generated_at=1e300, age_s=now - 1e300)
    ps = _science([], index=index, now=now)["trouvailles"]["par_semaine"]["record"]
    assert ps["semaines"] == {"2026-W38": 1} and ps["semaine_partielle"] == "2026-W38"


def test_date_FUTURE_jamais_en_semaines_futures_ni_en_exception():
    """Revue de la tâche 1 (I4) : une date déclarée future fabriquait des centaines de semaines de « zéros mesurés »,
    et 9999-12-31 faisait lever OverflowError — refus GLOBAL des trois blocs pour un seul fichier."""
    arts = [_art("spec", "docs/superpowers/specs/2026-09-15-a.md", date_declaree="2026-09-15"),
            _art("spec", "docs/superpowers/specs/2062-09-01-b.md", date_declaree="2062-09-01"),
            _art("spec", "docs/superpowers/specs/9999-12-31-c.md", date_declaree="9999-12-31")]
    out = _science(arts, now=_ts("2026-09-16"))
    ps = out["trouvailles"]["par_semaine"]["spec"]
    assert ps["semaines"] == {"2026-W38": 1} and ps["sans_date"] == {"date_future": 2} and ps["raison"] is None
    assert any(a.startswith("trouvailles : famille spec") and "2 artefact(s)" in a and "date_future" in a
               for a in out["aveugle"]), out["aveugle"]


@pytest.mark.parametrize("historique, raison", [(None, "dates_absentes"), ("tronque", "historique_tronque"),
                                                ("indisponible", "git_indisponible")])
def test_par_semaine_git_indisponible_CAUSE_DITE_et_sans_date_de_l_index(historique, raison):
    """Revue de la tâche 1 (I2) : `semaines: null` se libellait « git indisponible » quelle que soit la cause."""
    arts = [_art("record", "docs/EDR/1.md"), _art("spec", "docs/superpowers/specs/2026-09-01-s.md",
                                                  date_declaree="2026-09-01")]
    ps = _science(arts, historique=historique, now=_ts("2026-09-02"))["trouvailles"]["par_semaine"]
    assert ps["record"] == {"date": "date_ajout_git", "semaines": None, "sans_date": {"dates_absentes": 1},
                            "semaine_partielle": None, "raison": raison}
    assert ps["spec"]["semaines"] == {"2026-W36": 1}                          # datée par son nom : mesurable


def test_semaine_iso_aux_bornes_d_annee():
    assert S.semaine_iso("2025-12-29") == "2026-W01"
    assert S.semaine_iso("2026-12-31") == "2026-W53" and S.semaine_iso("2027-01-01") == "2026-W53"
    assert list(S.semaines_denses(["2026-12-28", "2027-01-11"])) == ["2026-W53", "2027-W01", "2027-W02"]
    assert S.semaines_denses(["2026-12-28"], "2027-01-11") == {"2026-W53": 1, "2027-W01": 0, "2027-W02": 0}


def test_famille_non_lue_par_semaine_CAUSE_DITE():
    """Revue de la tâche 1 (I2) : `null` avait trois causes non dites ; l'objet est toujours servi, sa raison nommée."""
    index = _index([_art("record", "docs/EDR/1.md", date_ajout_git="2026-09-01")])
    _famille(index, "adr").update(fichiers=None, indexes=None, champs_introuvables=None)
    assert _science([], index=index)["trouvailles"]["par_semaine"]["adr"] == {
        "date": "date_ajout_git", "semaines": None, "sans_date": None, "semaine_partielle": None,
        "raison": "famille_non_lue"}


def test_famille_inconnue_nommee_jamais_comptee():
    index = _index([])
    index["familles"].append({"nom": "nouvelle", "motif": "*.md", "repertoire": "x", "exclus": [], "fichiers": 0,
                              "indexes": 0, "illisibles": [], "champs_introuvables": {}, "format_declare": {}})
    out = _science([], index=index)
    assert out["trouvailles"]["par_semaine"]["nouvelle"] == {"date": None, "semaines": None, "sans_date": None,
                                                             "semaine_partielle": None, "raison": "sans_date_nommee"}
    assert any("famille nouvelle sans date nommée" in a for a in out["aveugle"])


def test_parite_rompue_famille_null_et_ligne():
    index = _index([_art("record", "docs/EDR/1.md")])
    _famille(index, "record")["champs_introuvables"]["date_ajout_git"] = {}
    out = _science([], index=index)
    assert out["trouvailles"]["par_semaine"]["record"]["raison"] == "parite_rompue"
    assert out["trouvailles"]["par_semaine"]["record"]["semaines"] is None
    assert any(a.startswith("trouvailles : famille record") and "servie à null" in a for a in out["aveugle"])


def test_parite_contre_INDEXES_artefacts_tronques_jamais_un_sous_compte():
    """Revue de la tâche 1 (M1, sonde S8) : la parité se jugeait contre `len(siens)`, jamais contre `indexes` — des
    artefacts tronqués passaient pour un compte complet."""
    arts = [_art("record", f"docs/EDR/{i}.md", date_ajout_git=f"2026-09-0{i}") for i in (1, 2, 3)]
    index = _index(arts, now=_ts("2026-09-04"))
    index["artefacts"] = arts[:1]
    out = _science([], index=index, now=_ts("2026-09-04"))
    assert out["trouvailles"]["par_semaine"]["record"]["raison"] == "parite_rompue"
    assert any(a.startswith("trouvailles : famille record") and "servie à null" in a for a in out["aveugle"])


def test_cles_de_sortie_enumerees_aucune_tendance():
    out = _science([_art("record", "docs/EDR/1.md", date_ajout_git="2026-09-01", etat="V", etat_source="verdict")])
    assert set(out) == {"schema", "generated_at", "repo_root", "aveugle", "pipeline", "taxonomie", "trouvailles"}
    assert set(out["trouvailles"]) == {"verdicts", "verdicts_partiels", "compte_graphe", "par_semaine", "dates"}
    for e in out["trouvailles"]["par_semaine"].values():
        assert set(e) == CLES_SEMAINES and (e["raison"] is None or e["raison"] in S.RAISONS_SEMAINES)
    assert S.RAISONS_SEMAINES == {"famille_non_lue", "parite_rompue", "sans_date_nommee", "dates_absentes",
                                  "historique_tronque", "git_indisponible"}
    assert S.PREUVES == ("specificity_control", "functional_aliasing", "ablation_target", "coord_intact",
                         "emergence_bar", "incapable_ceiling", "ceiling_provenance")
    for a in out["taxonomie"]["aretes"]:
        assert set(a) == {"capacite", "prerequis", "nature", "force", "verdict", "ratio", "n", "record", "raison",
                          "depassee_par", "preuves"}


def test_aveugle_de_l_INDEX_RELAYE_sous_trouvailles():
    """Revue de la tâche 2 (mineurs 4 et 5) : la vue Science n'affiche que /science ; un âge négatif de l'instantané,
    une famille non lue, le mode dégradé de l'index y étaient servis sans leur ligne, restée dans /api/pm/index.
    Chaque ligne de l'index est relayée telle quelle, sous le préfixe du bloc qu'elle qualifie — jamais `index:` en
    tête (réservé au service de l'index), jamais une ligne inventée."""
    index = _index([])
    index["aveugle"] = ["dates : instantané daté dans le FUTUR de 3600 s (horloge de l'écrivain en avance ?)",
                        "famille adr : répertoire docs/ADR absent -- fichiers INCONNUS, jamais 0"]
    out = _science([], index=index)
    assert [a for a in out["aveugle"] if a.startswith("trouvailles : (index) ")] == [
        "trouvailles : (index) " + a for a in index["aveugle"]]
    assert not any(a.startswith(("science:", "index:")) for a in out["aveugle"])
    assert not any("(index)" in a for a in _science([])["aveugle"])           # rien à relayer : rien d'inventé


def test_compute_science_ne_MUTE_jamais_l_index_PARTAGE():
    """Revue de la tâche 2 (mineur 7) : `get_index` rend son cache PAR RÉFÉRENCE. Sans la copie de `sans_date`, une
    date future écrirait `date_future` DANS `champs_introuvables` de l'index — servie par /api/pm/index, puis comptée
    deux fois au calcul suivant."""
    index = _index([_art("spec", "docs/superpowers/specs/2999-01-01-a.md", date_declaree="2999-01-01"),
                    _art("record", "docs/EDR/1.md", etat="V", etat_source="verdict", date_ajout_git="2026-09-01")])
    avant = copy.deepcopy(index)
    _science([], index=index, now=_ts("2026-09-16"))
    _science([], index=index, now=_ts("2026-09-16"))
    assert index == avant


def test_DATE_PAR_FAMILLE_couvre_exactement_les_familles_de_l_index():
    assert set(S.DATE_PAR_FAMILLE) == {f.nom for f in IX.FAMILLES}


def test_REEL_bout_a_bout():
    from tools.pm.pilotage import racine_depot
    r = racine_depot()
    index = IX.indexer(r, IX.read_dates(r), NOW)
    out = S.compute_science(index, S.lire_pipeline(), S.lire_taxonomie(r), S.lire_graphe(r), NOW)
    assert out["pipeline"]["couverture"]["total"] > 0
    assert len(out["trouvailles"]["verdicts"]) > 100
    assert out["trouvailles"]["compte_graphe"] > 100                             # I6 : le lecteur réel est exercé
    assert not any(a.startswith(("science:", "index:")) for a in out["aveugle"]), out["aveugle"]
