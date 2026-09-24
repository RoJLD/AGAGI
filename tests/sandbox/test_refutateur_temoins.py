"""Temoins GELES du Refutateur : le roster, l'extraction ANONYME, et le BAREME A DEUX ETAGES.

Ce fichier gele, en contre-exemples, tout ce que la re-revue du 2026-09-23 a mesure -- et qui
condamnait le bareme precedent :

  1. une seule phrase vague, identique pour les quatre temoins, ecrite SANS ouvrir un fichier,
     passait 4/4 : le PLANCHER DE FAUSSES RETROUVAILLES valait le SIGNAL MAXIMAL (lecon
     `run_ablation_map` du depot -- un instrument de contraste dans cet etat ne voit rien) ;
  2. recopier UNE ligne du temoin extrait passait deux des trois defauts ;
  3. LE SIGNE ETAIT INVERSE : la critique JUSTE du defaut E26, avec sa sonde et son fichier:ligne,
     rendait « revue NULLE » faute du mot « corps ».

Le motif `attendu` n'est donc plus le bareme (il survit en SIGNAL RAPPORTE). A sa place : un plancher
MECANIQUE (verdict confirme + preuve de FORME + anti-recopie), puis un JUGE calibre sur cinq textes
reels a reponse connue. Chaque etage est teste sur SES DEUX ISSUES, controle intact d'abord.
"""
import json
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import refutateur_temoins as T  # noqa: E402

_REF = os.path.join(T._ROOT, "docs", "REF", "REF-REVUE-ADVERSARIALE.md")
_WORKFLOW = os.path.join(T._ROOT, ".claude", "workflows", "refutateur.js")


def _lire(chemin):
    with open(chemin, encoding="utf-8") as fh:
        return fh.read()


def _crit(verdict="confirmé", constat="", sonde="", preuve="", prompt="P1", classe="aucune"):
    return {"prompt": prompt, "constat": constat, "sonde": sonde, "preuve": preuve,
            "classe": classe, "verdict": verdict}


def _cas(nom):
    """Vue COMPLÈTE : les tests ont droit aux réponses, le juge non."""
    return [c for c in T.cas_du_juge(avec_reponses=True) if c["nom"] == nom][0]


@pytest.fixture(scope="module")
def extraits(tmp_path_factory):
    """Les quatre temoins extraits une fois : {nom: texte}."""
    d = tmp_path_factory.mktemp("temoins")
    return {nom: _lire(chemin) for nom, chemin in T.extraire_tous(str(d)).items()}, str(d)


# --------------------------------------------------------------------------------------------- #
# Le roster gele
# --------------------------------------------------------------------------------------------- #


def test_trois_temoins_a_defaut_et_un_noop_tous_presents_dans_git():
    tem = T.charger()
    ok, raison = T.roster_conforme()
    assert ok, raison
    for t in tem:
        assert re.fullmatch(r"[0-9a-f]{40}", t["sha"]), t
        p = subprocess.run(["git", "cat-file", "-e", f"{t['sha']}:{t['chemin']}"],
                           cwd=T._ROOT, capture_output=True)
        assert p.returncode == 0, f"{t['nom']} : {t['sha']}:{t['chemin']} absent de git"
        re.compile(t["attendu"] or ".")
        re.compile(t["signature"])
        re.compile(t["antisignature"] or ".")


def test_roster_conforme_REFUSE_un_roster_affaibli():
    tem = T.charger()
    assert T.roster_conforme(tem)[0] is True, "controle INTACT avant toute mutation"
    assert T.roster_conforme([t for t in tem if t["genre"] == "noop"])[0] is False
    doublon = [dict(tem[0]), dict(tem[1]), dict(tem[2]), dict(tem[3], nom=tem[0]["nom"])]
    assert T.roster_conforme(doublon)[0] is False
    sans_seuil = [{k: v for k, v in t.items() if k != "seuil_critiques"} if t["genre"] == "noop" else t
                  for t in tem]
    ok, raison = T.roster_conforme(sans_seuil)
    assert ok is False and "seuil_critiques" in raison


def test_un_attendu_DEGENERE_est_refuse_meme_s_il_n_est_plus_le_bareme():
    """`attendu` n'est qu'un signal RAPPORTE depuis la re-revue -- mais un signal faux reste faux."""
    assert T.attendu_est_degenere(".") is True
    assert T.attendu_est_degenere(".*") is True
    assert T.attendu_est_degenere("") is True
    assert T.attendu_est_degenere("[") is True  # regex invalide : indecidable -> refusee
    assert T.attendu_est_degenere("forage_payoff") is False
    mute = [dict(t, attendu=".") if t["genre"] == "defaut" else t for t in T.charger()]
    ok, raison = T.roster_conforme(mute)
    assert ok is False and "DÉGÉNÉRÉ" in raison


def test_le_nom_d_un_temoin_est_une_FORME_DERIVEE_et_non_un_libelle_libre():
    """La garde. `<identifiant du record>-<sha7>`, RECOMPUTE depuis `chemin` et `sha`.

    Une liste noire de mots ne repond jamais a « ce nom divulgue-t-il le GENRE ? » : elle repond
    « contient-il l'un de ces mots ». Mesure du 2026-09-23 : elle a attrape `LOCK-002-sain` et LAISSE
    PASSER `RETAIN-COMPOSE-pre-retractation`, vu seulement A L'OEIL.
    ⚠️ CE QU'ELLE NE VOIT PAS : la FORME DU NOM, jamais le CONTENU du fichier extrait.
    """
    for t in T.charger():
        assert t["nom"] == T.nom_attendu(t), f"nom hors forme : {t['nom']!r}"
        assert re.fullmatch(r"[A-Za-z0-9.\-]+-[0-9a-f]{7}", t["nom"]), t["nom"]


def test_un_nom_renomme_A_LA_MAIN_est_REFUSE_et_rend_le_CLI_2(tmp_path):
    tem = T.charger()
    assert T.roster_conforme(tem)[0] is True
    for libelle in ("LOCK-002-sain", "RETAIN-COMPOSE-pre-retractation", "temoin-4", ""):
        mute = [dict(t, nom=libelle) if t["genre"] == "noop" else t for t in tem]
        ok, raison = T.roster_conforme(mute)
        assert ok is False, f"un nom libre {libelle!r} passe la forme"
        assert "FORME" in raison or "collision" in raison
    f = tmp_path / "x.json"
    f.write_text("[]", encoding="utf-8")
    vrai = T.charger
    T.charger = lambda: [dict(t, nom="LOCK-002-sain") if t["genre"] == "noop" else t for t in vrai()]
    try:
        assert T.main(["--verifier", "EDR-GRAB-COST-1828371", str(f)]) == 2
    finally:
        T.charger = vrai


def test_plancher_secondaire_aucun_nom_ne_contient_un_mot_de_genre():
    """PLANCHER, pas la garde : un mot de genre peut se glisser dans un NOM DE FICHIER de record."""
    for t in T.charger():
        for mot in ("sain", "noop", "ok", "propre", "clean", "bug", "faux", "bon"):
            assert mot not in t["nom"].lower(), f"le nom {t['nom']} declare son genre"


# --------------------------------------------------------------------------------------------- #
# Extraction ANONYME
# --------------------------------------------------------------------------------------------- #


def test_les_fichiers_d_extraction_sont_NEUTRES_et_decorreles_de_l_ordre_du_roster():
    tem = T.charger()
    for t in tem:
        assert re.fullmatch(r"temoin-\d+\.md", t["fichier"]), f"{t['nom']} : nom de fichier parlant"
        assert t["nom"] not in t["fichier"]
        for mot in ("sain", "noop", "defaut", "GRAB", "BLIND", "RETAIN", "LOCK"):
            assert mot.lower() not in t["fichier"].lower()
    assert [t["fichier"] for t in tem] != [f"temoin-{i}.md" for i in range(1, len(tem) + 1)], (
        "les fichiers suivent l'ordre du roster : « le dernier est le no-op » redeviendrait devinable")


@pytest.mark.parametrize("nom", [t["nom"] for t in T.charger()])
def test_la_version_gelee_porte_ENCORE_son_defaut_connu(nom, extraits):
    """Signature PRESENTE et antisignature ABSENTE : le regard « a l'oeil », execute."""
    textes, _ = extraits
    t, txt = T.par_nom(nom), textes[nom]
    assert re.search(t["signature"], txt), (
        f"{nom} : signature {t['signature']!r} ABSENTE de {t['sha'][:9]} — mauvais SHA")
    if t["antisignature"]:
        assert not re.search(t["antisignature"], txt), (
            f"{nom} : antisignature PRESENTE — la version gelee est deja corrigee")


def test_extraire_tous_rend_la_correspondance_a_l_appelant_et_n_ecrit_RIEN_qui_la_trahisse(tmp_path):
    correspondance = T.extraire_tous(str(tmp_path))
    assert set(correspondance) == {t["nom"] for t in T.charger()}
    assert sorted(os.listdir(tmp_path)) == sorted(t["fichier"] for t in T.charger())
    for fichier in os.listdir(tmp_path):
        contenu = _lire(os.path.join(tmp_path, fichier))
        for t in T.charger():
            assert t["nom"] not in contenu, f"{fichier} nomme le temoin {t['nom']}"
            assert t["defaut"] not in contenu


def test_extraire_leve_sur_un_temoin_dont_le_SHA_ne_porte_pas_le_chemin(tmp_path):
    faux = dict(T.par_nom("EDR-GRAB-COST-1828371"), nom="FAUX", chemin="docs/EDR/_inexistant_.md")
    with pytest.raises(RuntimeError):
        T.extraire(faux, str(tmp_path))


# --------------------------------------------------------------------------------------------- #
# ETAGE 1 — le plancher MECANIQUE, sur les cinq textes REELS de la re-revue
# --------------------------------------------------------------------------------------------- #


def test_les_cinq_cas_geles_rendent_a_l_etage_1_ce_qu_ils_declarent(extraits):
    """LES DEUX ISSUES, sur des textes reels : trois attaques rejetees, deux critiques justes recues."""
    textes, _ = extraits
    vus = set()
    for cas in T.cas_du_juge(avec_reponses=True):
        for t in T.charger():
            if "*" not in cas["temoins"] and t["nom"] not in cas["temoins"]:
                continue
            if t["genre"] != "defaut":
                continue
            r = T.recevabilite(t, cas["critiques"], textes[t["nom"]])
            attendu_recevable = cas["etage1"] == "recevable"
            assert bool(r["recevables"]) is attendu_recevable, (
                f"{cas['nom']} sur {t['nom']} : etage1 attendu {cas['etage1']}, "
                f"recevables={len(r['recevables'])}, rejets={[x['raison'] for x in r['rejets']]}")
            vus.add(cas["nom"])
    assert len(vus) == len(T.cas_du_juge()), "un cas gele n'a ete confronte a aucun temoin"


def test_l_attaque_universelle_est_tuee_par_la_SEULE_absence_de_preuve_de_forme(extraits):
    """CONTRE-EXEMPLE GELE n.1 : elle passait 4/4. Aucun agent n'a besoin de la lire."""
    textes, _ = extraits
    attaque = _cas("attaque-universelle")["critiques"]
    ok, raison = T.preuve_de_forme(attaque[0])
    assert ok is False and "preuve de forme" in raison
    for t in T.charger():
        if t["genre"] != "defaut":
            continue
        r = T.recevabilite(t, attaque, textes[t["nom"]])
        assert r["recevables"] == []
        assert all("preuve de forme" in x["raison"] for x in r["rejets"])


def test_recopier_une_ligne_du_temoin_ne_retrouve_plus_rien(extraits):
    """CONTRE-EXEMPLE GELE n.2 : le token attendu est DANS le texte qu'on relit."""
    textes, _ = extraits
    for nom_cas, nom_temoin in (("recopie-une-ligne-du-temoin-GRAB", "EDR-GRAB-COST-1828371"),
                                ("recopie-une-ligne-du-temoin-RETAIN", "EDR-RETAIN-COMPOSE-4204f8f")):
        critiques = _cas(nom_cas)["critiques"]
        assert T.preuve_de_forme(critiques[0])[0] is True, "la recopie porte une preuve de BONNE forme"
        r = T.recevabilite(T.par_nom(nom_temoin), critiques, textes[nom_temoin])
        assert r["recevables"] == []
        assert any("RECOPIE" in x["raison"] for x in r["rejets"]), r["rejets"]


def test_le_seuil_de_recopie_SEPARE_les_recopies_des_critiques_justes(extraits):
    """Le seuil est MESURE, et cette mesure est REJOUEE : si un des cinq textes bouge, ceci rougit.

    Mesure du 2026-09-23 : recopies 32 et 24 mots communs · critiques justes 4 et 2 · attaque
    universelle 2 a 4. Tout N dans [5, 24] separe ; 8 est pris avec ses deux marges.
    """
    textes, _ = extraits
    fenetres = {"recopie": [], "juste": []}
    for cas in T.cas_du_juge(avec_reponses=True):
        famille = "recopie" if cas["nom"].startswith("recopie-") else (
            "juste" if cas["etage1"] == "recevable" else None)
        if famille is None:
            continue
        for nom_temoin in cas["temoins"]:
            for c in cas["critiques"]:
                fenetres[famille].append(
                    T.plus_longue_fenetre_commune(c["constat"], textes[nom_temoin]))
    n = T.mots_recopie()
    plafond_juste, plancher_recopie = max(fenetres["juste"]), min(fenetres["recopie"])
    assert plafond_juste < n <= plancher_recopie, (
        f"le seuil {n} ne separe plus : critiques justes jusqu'a {plafond_juste} mots, "
        f"recopies a partir de {plancher_recopie}")
    assert plancher_recopie - plafond_juste >= 8, (
        f"separation trop etroite ({plafond_juste} vs {plancher_recopie}) : le seuil devient un "
        "reglage, plus une mesure")


def test_preuve_de_forme_accepte_les_TROIS_formes_et_refuse_le_reste():
    assert T.preuve_de_forme(_crit(preuve="src/agents/mamba_agent.py:47-50"))[0] is True
    assert T.preuve_de_forme(_crit(sonde="grep -n foo bar.py", preuve="3 occurrences"))[0] is True
    assert T.preuve_de_forme(_crit(preuve="0 repas / 20 776 agent-ticks"))[0] is True
    assert T.preuve_de_forme(_crit(preuve="aucune"))[0] is False
    assert T.preuve_de_forme(_crit(preuve=""))[0] is False
    assert T.preuve_de_forme(_crit(sonde="lecture du record", preuve="le record ne le publie pas"))[0] is False
    # Une commande SANS sortie chiffree ne suffit pas : « j'ai lance un grep » n'est pas une preuve.
    assert T.preuve_de_forme(_crit(sonde="grep -n foo bar.py", preuve="rien trouve"))[0] is False


def test_une_critique_NON_CONFIRMEE_n_est_jamais_recevable(extraits):
    textes, _ = extraits
    t = T.par_nom("S2-BLIND-CHAMPION-42e9357")
    juste = _cas("E26-juste-sans-le-mot-corps")["critiques"][0]
    assert T.recevabilite(t, [juste], textes[t["nom"]])["recevables"], "controle INTACT"
    for verdict in ("non confirmé", "hors périmètre", ""):
        r = T.recevabilite(t, [dict(juste, verdict=verdict)], textes[t["nom"]])
        assert r["recevables"] == [] and "verdict non confirmé" in r["rejets"][0]["raison"]


# --------------------------------------------------------------------------------------------- #
# Le SIGNE : les deux critiques justes que l'ancien bareme REFUSAIT
# --------------------------------------------------------------------------------------------- #


@pytest.mark.parametrize("nom_cas,nom_temoin", [
    ("E26-juste-sans-le-mot-corps", "S2-BLIND-CHAMPION-42e9357"),
    ("GRAB-fait-c-sans-le-token", "EDR-GRAB-COST-1828371"),
])
def test_une_critique_JUSTE_passe_desormais_meme_sans_le_token(nom_cas, nom_temoin, extraits):
    """CONTRE-EXEMPLE GELE n.3 : LE SIGNE ETAIT INVERSE.

    Ces deux textes sont la critique EXACTE du defaut connu, avec sonde, classe et preuve de forme.
    L'ancien bareme les rendait NULLES faute du token. Ils sont desormais RECEVABLES, et le signal
    `attendu` -- qui reste RAPPORTE -- se trompe sur le premier : c'est la preuve, gelee, qu'il ne
    decide plus.
    """
    textes, _ = extraits
    t, critiques = T.par_nom(nom_temoin), _cas(nom_cas)["critiques"]
    r = T.recevabilite(t, critiques, textes[nom_temoin])
    assert len(r["recevables"]) == 1, r["rejets"]
    v = T.verdict_temoin(t, critiques, textes[nom_temoin], jugement="OUI")
    assert v["statut"] == "RETROUVE" and v["code"] == 0
    assert T.verdict_temoin(t, critiques, textes[nom_temoin], jugement="NON")["statut"] == "NULLE"


def test_le_signal_attendu_est_RAPPORTE_et_se_TROMPE_sans_changer_le_verdict(extraits):
    """La critique juste d'E26 ne contient pas le mot « corps » : le signal est FAUX, le verdict BON."""
    textes, _ = extraits
    t = T.par_nom("S2-BLIND-CHAMPION-42e9357")
    critiques = _cas("E26-juste-sans-le-mot-corps")["critiques"]
    v = T.verdict_temoin(t, critiques, textes[t["nom"]], jugement="OUI")
    assert v["signal_attendu"] is False, "le signal devrait etre faux ici : c'est tout le propos"
    assert v["statut"] == "RETROUVE"
    # Et inversement : la recopie porte le signal a True tout en etant rejetee a l'etage 1.
    g = T.par_nom("EDR-GRAB-COST-1828371")
    recopie = _cas("recopie-une-ligne-du-temoin-GRAB")["critiques"]
    assert T.signal_attendu(g, recopie) is True
    assert T.verdict_temoin(g, recopie, textes[g["nom"]])["statut"] == "NULLE"


# --------------------------------------------------------------------------------------------- #
# Verdict par temoin, et le no-op
# --------------------------------------------------------------------------------------------- #


def test_un_temoin_a_defaut_sans_JUGEMENT_est_INDECIDABLE_jamais_retrouve(extraits):
    """L'etage 1 ne dit jamais qu'un defaut a ete trouve : il dit qu'une critique est RECEVABLE."""
    textes, _ = extraits
    t = T.par_nom("EDR-GRAB-COST-1828371")
    critiques = _cas("GRAB-fait-c-sans-le-token")["critiques"]
    v = T.verdict_temoin(t, critiques, textes[t["nom"]])
    assert v["statut"] == "INDECIDABLE" and v["code"] == 2
    assert T.verdict_temoin(t, critiques, textes[t["nom"]], "INDECIDABLE")["code"] == 2


def test_le_noop_compte_les_critiques_RECEVABLES_et_son_seuil_vit_dans_le_roster(extraits):
    textes, _ = extraits
    noop = T.par_nom("LOCK-002-286f244")
    txt = textes[noop["nom"]]
    assert noop["seuil_critiques"] == 1
    assert T.verdict_temoin(noop, [], txt)["statut"] == "RETROUVE"
    bonne = _crit(constat="le budget projete n'est pas re-mesure a charge connue",
                  preuve="tools/cost_guard.py:12")
    assert T.verdict_temoin(noop, [bonne], txt)["statut"] == "RETROUVE"
    assert T.verdict_temoin(noop, [bonne, dict(bonne, preuve="tools/preregister.py:30")],
                            txt)["statut"] == "NULLE"
    # L'attaque universelle ne fait plus CRIER le no-op : elle n'est meme pas recevable.
    attaque = _cas("attaque-universelle")["critiques"]
    assert T.verdict_temoin(noop, attaque * 5, txt)["n_recevables"] == 0


# --------------------------------------------------------------------------------------------- #
# ETAGE 2 — la calibration du JUGE
# --------------------------------------------------------------------------------------------- #


def test_les_cinq_cas_du_juge_declarent_leurs_deux_issues():
    cas = T.cas_du_juge(avec_reponses=True)
    assert len(cas) == 5
    assert sorted(c["juge"] for c in cas) == ["NON", "NON", "NON", "OUI", "OUI"]
    for c in cas:
        assert c["etage1"] in ("recevable", "rejete")
        assert c["pourquoi"].strip() and c["critiques"]
    assert len(T.cas_du_juge("S2-BLIND-CHAMPION-42e9357")) == 2  # le cas E26 + l'attaque universelle


def test_les_cas_servis_au_JUGE_sont_REDIGES_et_la_vue_complete_est_le_controle_positif(capsys):
    """CONTRE-EXEMPLE GELE : une consigne de « ne pas regarder » n'est pas une garde.

    Le juge était sommé de lire le JSON de calibration « sans regarder le champ juge » — or ce fichier
    donne la réponse TROIS fois (`juge`, `pourquoi` en clair, `etage1`). `juge_est_calibre` ne pouvait
    jamais rougir. Troisième occurrence de la même loi en une soirée : dès qu'un instrument
    s'auto-administre, sa clé de réponse voyage avec lui.

    ⚠️ Les DEUX volets sont indispensables : un test qui ne trouve RIEN dans la vue rédigée ne
    distingue pas « rédigé » de « cassé ». Le second volet est le contrôle POSITIF du motif.
    """
    redige = T.cas_du_juge()
    complet = T.cas_du_juge(avec_reponses=True)
    assert len(redige) == len(complet) == 5
    for c in redige:
        assert set(c) == {"ref", "temoins", "critiques"}, f"champ de trop dans la vue rédigée : {set(c)}"
    motifs = (r"juge=", r"étage1=", r"\bOUI\b", r"\bNON\b", r"\brejete\b", r"\brecevable\b",
              # ⚠️ Le NOM du cas annonçait lui aussi la réponse (`attaque-…`, `recopie-…`, `…-juste-…`) :
              # rédiger les trois autres champs en le laissant n'aurait rien fermé. Le juge reçoit une
              # REF opaque, stable, dérivée du nom.
              r"attaque", r"recopie", r"juste", r"universelle")
    # Volet 1 : la sortie servie au juge ne porte aucune réponse.
    T.main(["--cas-du-juge"])
    servi = capsys.readouterr().out
    for motif in motifs:
        assert not re.search(motif, servi, re.I), f"la vue RÉDIGÉE publie {motif!r}"
    for c in complet:
        assert c["nom"] not in servi, f"le NOM du cas {c['nom']} annonce sa réponse"
        assert c["pourquoi"] not in servi, "l'explication est servie au juge"
        assert c["ref"] in servi, "la REF opaque doit être servie : c'est la clé de reponse du juge"
    # `*` est un indice (« ce cas vise TOUS les témoins ») : il est résolu en liste concrète.
    assert "'*'" not in servi and '"*"' not in servi
    # Volet 2 — CONTRÔLE POSITIF : les mêmes motifs SONT présents dans la vue complète.
    T.main(["--cas-du-juge-avec-reponses"])
    reserve = capsys.readouterr().out
    for motif in motifs:
        assert re.search(motif, reserve, re.I), (
            f"{motif!r} absent de la vue COMPLÈTE : le motif du volet 1 ne prouve rien")
    for c in complet:
        assert c["nom"] in reserve and c["pourquoi"] in reserve


def test_la_REF_opaque_est_STABLE_et_ne_dit_rien_du_cas():
    """Le juge repond par une ref ; le verificateur la remappe. Elle doit etre stable entre appels."""
    a = {c["ref"] for c in T.cas_du_juge()}
    b = {c["ref"] for c in T.cas_du_juge()}
    assert a == b and len(a) == 5, "les refs bougent d'un appel a l'autre : le remappage casse"
    for c in T.cas_du_juge(avec_reponses=True):
        assert c["ref"] == T.ref_du_cas(c["nom"])
        assert re.fullmatch(r"[0-9a-f]{8}", c["ref"])
        for mot in ("attaque", "recopie", "juste", "e26", "grab", "retain"):
            assert mot not in c["ref"].lower()
    # `juge_est_calibre` accepte la REF (ce que rend le juge) comme le nom (tests, CLI).
    par_ref = {c["ref"]: c["juge"] for c in T.cas_du_juge(avec_reponses=True)}
    assert T.juge_est_calibre(par_ref)[0] is True
    faux = dict(par_ref)
    faux[next(iter(faux))] = "INDECIDABLE"
    assert T.juge_est_calibre(faux)[0] is False


def test_la_redaction_MELANGE_l_ordre_des_cas():
    """L'ordre portait de l'information : les attaques d'abord, les critiques justes ensuite."""
    reference = [c["ref"] for c in T.cas_du_juge(avec_reponses=True)]
    ordres = {tuple(c["ref"] for c in T.cas_du_juge()) for _ in range(40)}
    assert len(ordres) > 1, "la vue rédigée sert toujours le même ordre : il redevient un indice"
    assert all(sorted(o) == sorted(reference) for o in ordres), "le mélange perd ou duplique un cas"


def test_juge_est_calibre_rend_ses_DEUX_issues():
    parfait = {c["nom"]: c["juge"] for c in T.cas_du_juge(avec_reponses=True)}
    ok, details = T.juge_est_calibre(parfait)
    assert ok is True and all(d["juste"] for d in details)
    # Un juge qui dit OUI a tout : il retrouverait tout, y compris les attaques.
    ok, details = T.juge_est_calibre({c["nom"]: "OUI" for c in T.cas_du_juge(avec_reponses=True)})
    assert ok is False and sum(1 for d in details if not d["juste"]) == 3
    # Un juge muet.
    assert T.juge_est_calibre({})[0] is False
    # Un juge qui rate LE cas du signe inverse.
    presque = dict(parfait, **{"E26-juste-sans-le-mot-corps": "NON"})
    assert T.juge_est_calibre(presque)[0] is False


# --------------------------------------------------------------------------------------------- #
# Lecture des critiques : les deux formes d'entree
# --------------------------------------------------------------------------------------------- #


def test_charger_critiques_accepte_la_LISTE_et_l_objet_rendu_par_les_agents():
    liste = [_crit(constat="x", preuve="a.py:1")]
    assert T.charger_critiques(json.dumps(liste)) == liste
    assert T.charger_critiques(json.dumps({"critiques": liste})) == liste


def test_charger_critiques_leve_sur_un_texte_illisible_ou_une_critique_sans_verdict():
    for illisible in ("P2 : forage_payoff non publie", "{\"autre\": []}", "[1, 2]", "[[]]"):
        with pytest.raises(T.FormatInvalide):
            T.charger_critiques(illisible)
    with pytest.raises(T.FormatInvalide):
        T.charger_critiques(json.dumps([{"verdict": "confirme"}, {"constat": "x"}]))


# --------------------------------------------------------------------------------------------- #
# ETAGE 3 — le plancher, et le fait qu'il VOYAGE avec le score
# --------------------------------------------------------------------------------------------- #


def test_le_plancher_de_fausses_retrouvailles_est_NUL_apres_correctif(extraits):
    _, dossier = extraits
    p = T.plancher(dossier)
    assert p["majorant_fausses_retrouvailles"] == 0, p["cas"]
    assert p["defauts_vises_par_les_attaques"] == 5, "les trois attaques doivent viser 5 paires"
    justes = [l for l in p["cas"] if l["juge_attendu"] == "OUI"]
    assert justes and all(l["defauts_retrouvables"] == l["defauts_vises"] for l in justes), (
        "les critiques JUSTES doivent, elles, etre retrouvables : sinon on a un plancher nul "
        "parce que l'instrument ne voit plus RIEN")


def test_aucun_SCORE_de_phase_temoins_ne_peut_etre_obtenu_SANS_son_plancher(extraits):
    """Deux appels independants auraient fini publies separement. Ils n'en font qu'un."""
    _, dossier = extraits
    r = T.verdict_phase_temoins(dossier, {}, {})
    assert "plancher" in r and "score" in r
    assert r["plancher"]["majorant_fausses_retrouvailles"] == 0
    assert set(r) >= {"score", "statut", "detail", "plancher"}
    # Une phase vide : le no-op passe (se taire sur un record sain est la BONNE reponse), les trois
    # defauts sont NULLE faute de critique recevable.
    assert r["score"] == "1/4" and r["statut"] == "NULLE"


def test_une_phase_temoins_PASSEE_porte_quand_meme_son_plancher(extraits):
    textes, dossier = extraits
    critiques = {
        "S2-BLIND-CHAMPION-42e9357": _cas("E26-juste-sans-le-mot-corps")["critiques"],
        "EDR-GRAB-COST-1828371": _cas("GRAB-fait-c-sans-le-token")["critiques"],
    }
    jugements = {n: "OUI" for n in critiques}
    r = T.verdict_phase_temoins(dossier, critiques, jugements)
    assert r["score"] == "3/4", [d["statut"] for d in r["detail"]]  # 2 defauts + le no-op
    assert r["plancher"]["majorant_fausses_retrouvailles"] == 0


# --------------------------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------------------------- #


def test_main_rend_0_puis_1_puis_2_et_imprime_le_plancher_a_cote(tmp_path, capsys):
    assert T.main(["--extraire", str(tmp_path)]) == 0
    extrait = str(tmp_path / T.par_nom("EDR-GRAB-COST-1828371")["fichier"])
    bon = tmp_path / "ok.json"
    bon.write_text(
        json.dumps({"critiques": _cas("GRAB-fait-c-sans-le-token")["critiques"]}, ensure_ascii=False),
        encoding="utf-8")
    vide = tmp_path / "vide.json"
    vide.write_text("   ", encoding="utf-8")
    illisible = tmp_path / "illisible.txt"
    illisible.write_text("rien a signaler", encoding="utf-8")
    assert T.main(["--verifier", "EDR-GRAB-COST-1828371", str(bon), "--extrait", extrait,
                   "--jugement", "OUI"]) == 0
    sortie = capsys.readouterr().out
    assert "PLANCHER DE FAUSSES RETROUVAILLES" in sortie, "un score sans son plancher est interdit"
    assert T.main(["--verifier", "EDR-GRAB-COST-1828371", str(vide), "--extrait", extrait]) == 1
    assert T.main(["--verifier", "EDR-GRAB-COST-1828371", str(illisible), "--extrait", extrait]) == 2
    assert T.main(["--verifier", "EDR-GRAB-COST-1828371", str(bon), "--jugement", "OUI"]) == 2
    assert "--extrait manquant" in capsys.readouterr().out
    assert T.main(["--verifier", "INCONNU", str(bon), "--extrait", extrait]) == 2
    assert T.main(["--plancher", str(tmp_path)]) == 0
    assert T.main(["--cas-du-juge"]) == 0


# --------------------------------------------------------------------------------------------- #
# Le REF : forme, roles, et AUCUNE cle de reponse
# --------------------------------------------------------------------------------------------- #


def test_le_REF_est_un_record_et_fige_dix_prompts():
    txt = _lire(_REF)
    assert txt.startswith("---\n")
    entete = txt.split("---", 2)[1]
    for champ in ("id: REF-REVUE-ADVERSARIALE", "type: REF", "status: active"):
        assert champ in entete
    for i in range(1, 11):
        assert re.search(rf"\|\s*P{i}\s*\|", txt), f"prompt P{i} absent du tableau du REF"
    assert not re.search(r"\|\s*P11\s*\|", txt)


def _lignes_prompts():
    return [l for l in _lire(_REF).splitlines() if re.match(r"\|\s*P\d+\s*\|", l)]


def test_le_REF_dit_pour_CHAQUE_prompt_s_il_DELEGUE_a_une_porte_ou_s_il_JUGE():
    lignes = _lignes_prompts()
    assert len(lignes) == 10
    for l in lignes:
        assert ("DÉLÈGUE" in l) or ("JUGE" in l), f"role non declare : {l[:60]}"
    delegue = [l for l in lignes if "DÉLÈGUE" in l]
    assert delegue and len(delegue) < len(lignes)
    for l in delegue:
        portes = re.findall(r"tools/check_\w+\.py", l)
        assert portes, f"DÉLÈGUE sans porte nommee : {l[:80]}"
        for porte in portes:
            assert os.path.exists(os.path.join(T._ROOT, porte)), f"{porte} n'existe pas"


def test_le_recapitulatif_du_REF_se_derive_du_TABLEAU_et_non_de_la_memoire():
    txt = _lire(_REF)
    du_tableau = {"DÉLÈGUE": [], "JUGE": []}
    for l in _lignes_prompts():
        pid = re.match(r"\|\s*(P\d+)\s*\|", l).group(1)
        du_tableau["DÉLÈGUE" if "DÉLÈGUE" in l else "JUGE"].append(pid)
    for role, ids in du_tableau.items():
        ligne = re.search(rf"\*\*{role}NT\*\*\s*:\s*([^—\n]+)", txt)
        assert ligne, f"recapitulatif {role}NT absent du REF"
        assert re.findall(r"P\d+", ligne.group(1)) == ids


def test_le_REF_ne_publie_NI_identite_NI_nombre_NI_genre_NI_seuil_des_temoins():
    """Le nom ne dit plus le genre ; l'ORDINAL le disait encore. Mesure du 2026-09-23."""
    txt = _lire(_REF)
    roster = _lire(T._JSON)
    for t in T.charger():
        assert t["nom"] not in txt, (
            f"le REF NOMME le temoin {t['nom']} : un agent qui lit l'en-tete du fichier anonyme "
            "peut joindre les deux, et l'enumeration donne l'ordinal du no-op")
        assert t["defaut"] not in txt
        if t["attendu"]:
            assert t["attendu"] not in txt, f"regex `attendu` de {t['nom']} PUBLIEE dans le REF"
            # controle POSITIF du motif : il EST trouvable la ou il vit.
            assert json.dumps(t["attendu"], ensure_ascii=False)[1:-1] in roster
    assert "forage_payoff" not in txt and "forage_payoff" in roster
    # Ni le NOMBRE de temoins, ni la composition en genres, ni le seuil du no-op.
    for fuite in (r"\bquatre (versions|t[ée]moins)", r"trois t[ée]moins", r"un quatri[èe]me",
                  r"au plus UNE critique", r"\btrois d[ée]fauts\b"):
        assert not re.search(fuite, txt, re.I), f"le REF publie la composition des temoins : {fuite}"


def test_le_REF_ne_recopie_aucun_chiffre_de_porte_en_dur():
    txt = _lire(_REF)
    for motif in (r"\b300 records\b", r"\b74 (records|citent)\b", r"\b18 chemins\b",
                  r"\b232 records\b", r"\b8 nus\b", r"\b29 scell", r"\b104/105\b"):
        assert not re.search(motif, txt), f"chiffre de porte recopie dans le REF : {motif}"


# --------------------------------------------------------------------------------------------- #
# Le workflow : il ne juge plus rien, et il declare ce qu'il ecrit
# --------------------------------------------------------------------------------------------- #


def test_le_workflow_a_son_meta_et_ne_cite_que_des_prompts_du_REF():
    js = _lire(_WORKFLOW)
    assert "export const meta = {" in js
    bloc = js.split("export const meta = {", 1)[1].split("\n}", 1)[0]
    for champ in ("name:", "description:", "phases:"):
        assert champ in bloc
    assert "'refutateur'" in bloc or '"refutateur"' in bloc
    ref_txt = _lire(_REF)
    for pid in re.findall(r"'(P\d+)'", js):
        assert re.search(rf"\|\s*{pid}\s*\|", ref_txt), f"{pid} cite par le workflow, absent du REF"
    assert "docs/REF/REF-REVUE-ADVERSARIALE.md" in js and "docs/reviews/" in js


def test_le_workflow_ne_contient_AUCUN_bareme_et_fait_lancer_le_CLI_python():
    js = _lire(_WORKFLOW)
    for interdit in ("function retrouve", "new RegExp", "genre === 'noop'", 'genre === "noop"'):
        assert interdit not in js, f"le workflow rejuge : {interdit}"
    assert "tools/refutateur_temoins.py --verifier" in js
    assert "tools/refutateur_temoins.json" in js
    assert "--plancher" in js, "le workflow doit publier le plancher a cote du score"
    for phase in ("'Verification'", "'Juge'"):
        assert phase in js, f"phase {phase} absente"


def test_le_workflow_fait_DECLARER_les_chemins_pour_que_le_controleur_relance_le_CLI():
    """Un agent qui rend `code: 0` sans rien lancer passait : rien ne recontrolait."""
    js = _lire(_WORKFLOW)
    assert "fichier_critiques" in js
    bloc = js.split("const VERIFICATION", 1)[1].split("\n}", 1)[0] if "const VERIFICATION" in js else js
    assert "fichier_critiques" in bloc and "required" in bloc


def test_le_workflow_n_accepte_de_l_appelant_que_des_CHEMINS():
    js = _lire(_WORKFLOW)
    assert "args.fichiers" in js
    for fuite in ("args.temoins", "t.attendu", "temoin.attendu"):
        assert fuite not in js, f"le workflow accepte {fuite} de l'appelant"


def test_le_workflow_ne_construit_aucun_monde_et_ne_prend_aucun_bail():
    js = _lire(_WORKFLOW)
    for interdit in ("hold(", "jobs.run", "FamineWorld", "kuzu"):
        assert interdit not in js, f"le workflow touche a {interdit} : une revue ne simule pas"


def test_le_protocole_d_invocation_est_ecrit_dans_docs_reviews_README():
    txt = _lire(os.path.join(T._ROOT, "docs", "reviews", "README.md"))
    assert "Lancer une revue" in txt
    assert "tools/refutateur_temoins.py --extraire" in txt
    assert ".claude/workflows/refutateur.js" in txt
    assert "NUL" in txt
    assert "fichiers:" in txt and "temoins:" not in txt
    assert "--plancher" in txt, "le protocole doit imposer la publication du plancher"
