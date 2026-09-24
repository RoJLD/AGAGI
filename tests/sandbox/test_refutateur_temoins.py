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


def test_le_noop_MESURE_au_lieu_de_faire_BARRAGE(extraits):
    """CONTRE-EXEMPLE GELE : au 1er Step 4 complet, le no-op a rendu SIX critiques recevables.

    L'ancien barème rendait alors toute la revue NULLE — donc une revue qui venait de retrouver
    TROIS défauts réels, à l'aveugle et avec leur mécanisme, était jetée parce que le plancher était
    haut. C'est **supprimer la mesure au lieu de la publier**, l'inverse exact de la doctrine du
    dépôt : un plancher de bruit se publie À CÔTÉ du ratio, il ne l'annule pas. Et la mesure était
    JUSTE — une des six a été confrontée aux données : le bras ablaté fait mieux que l'intact sur
    10 seeds sur 12 (médiane 0,030), `leak_seeds` rendant 0 parce qu'il ne compte que `ci - ca > tol`,
    une fuite DIRECTIONNELLE dans le sens qu'il ne regarde pas.

    Le no-op rend donc un NOMBRE, et son dépassement de seuil est une INFORMATION, jamais un code 1.
    """
    textes, _ = extraits
    noop = T.par_nom("LOCK-002-286f244")
    txt = textes[noop["nom"]]
    assert noop["seuil_critiques"] == 1
    for n in (0, 1, 2, 6):
        crits = [_crit(constat=f"constat distinct numero {i}", preuve=f"tools/x{i}.py:{i + 1}")
                 for i in range(n)]
        v = T.verdict_temoin(noop, crits, txt)
        assert v["statut"] == "MESURE" and v["code"] == 0, (n, v["statut"])
        assert v["n_recevables"] == n
        assert v["depasse_le_seuil"] is (n > noop["seuil_critiques"])
    # L'attaque universelle ne fait pas monter le plancher : elle n'est meme pas recevable.
    attaque = _cas("attaque-universelle")["critiques"]
    assert T.verdict_temoin(noop, attaque * 5, txt)["n_recevables"] == 0


def test_chaque_temoin_declare_sa_date_de_gel_et_elle_se_RECOMPUTE_depuis_git():
    """La moitié CALCULABLE de la péremption : la date déclarée doit être celle du commit.

    Un témoin gelé mesure ce qu'on savait AU GEL. `gele_le` rend cette date lisible à côté du SHA —
    et, comme `nom_attendu`, elle se **recompute** au lieu d'être crue sur parole.
    """
    for t in T.charger():
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", t["gele_le"]), t["nom"]
        p = subprocess.run(["git", "show", "-s", "--format=%cs", t["sha"]],
                           cwd=T._ROOT, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        assert p.stdout.strip() == t["gele_le"], (
            f"{t['nom']} : gele_le={t['gele_le']} mais le commit date du {p.stdout.strip()}")
    # CONTROLE POSITIF du motif : une date fausse serait bien detectee.
    faux = dict(T.charger()[0], gele_le="2000-01-01")
    p = subprocess.run(["git", "show", "-s", "--format=%cs", faux["sha"]],
                       cwd=T._ROOT, capture_output=True, text=True)
    assert p.stdout.strip() != faux["gele_le"]


def test_la_peremption_du_roster_est_RAPPORTEE_jamais_bloquante(capsys):
    """⚠️ Un témoin gelé a une durée de vie — et la péremption SCIENTIFIQUE n'est pas décidable.

    Mesuré le 2026-09-24 : le témoin cru sain porte un phénomène (« le bras ablaté fait mieux que
    l'intact ») qui est la forme EXACTE d'un résultat ÉTABLI DEPUIS dans le dépôt (P2.42). Le témoin
    n'a pas été mal choisi : il était sain au regard de ce qu'on savait au gel. Ce qui était propre le
    devient moins à mesure que le dépôt apprend, et cela vaut pour les QUATRE témoins.

    On calcule donc la moitié calculable — l'ÂGE — et on **déclare** l'autre (`_peremption` du
    roster). Et on ne bloque pas : refuser un roster sur un calendrier casserait un instrument qui
    marche pour une raison qui n'est **pas un fait sur ses témoins**.
    """
    p = T.peremption_du_roster()
    assert set(p) >= {"revu_le", "jours_depuis_la_revue", "revue_due", "gel_le_plus_ancien", "gels"}
    assert len(p["gels"]) == len(T.charger())
    assert p["gels"] == sorted(p["gels"], key=lambda g: -g["age_jours"])
    assert p["gel_le_plus_ancien"]["temoin"] == "EDR-RETAIN-COMPOSE-4204f8f"  # gel le 2026-08-04
    # Les deux issues, sur une date injectee (jamais l'horloge du jour, qui rendrait le test instable).
    assert T.peremption_du_roster("2026-09-24")["revue_due"] is False
    tardif = T.peremption_du_roster("2027-09-24")
    assert tardif["revue_due"] is True and tardif["jours_depuis_la_revue"] > 300
    # ⚠️ ET LE ROSTER RESTE CONFORME : la peremption ne BLOQUE rien.
    assert T.roster_conforme()[0] is True
    # Le chiffre est imprime a cote de ce que l'instrument rend, jamais dans un coin.
    T.main(["--lister"])
    sortie = capsys.readouterr().out
    assert "roster revu le" in sortie and "gel le plus ancien" in sortie
    for t in T.charger():
        assert f"gele {t['gele_le']}" in sortie


def test_racine_valide_rend_ses_DEUX_issues(tmp_path):
    """Un instrument dont la correction depend d'un etat ambiant NON DECLARE echoue au hasard."""
    ok, raison = T.racine_valide(T._ROOT)
    assert ok is True and "module et roster" in raison
    ok, raison = T.racine_valide(str(tmp_path))
    assert ok is False and "introuvable" in raison
    assert T.main(["--racine-valide", T._ROOT]) == 0
    assert T.main(["--racine-valide", str(tmp_path)]) == 2


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
    assert set(r) >= {"score", "statut", "detail", "plancher", "plancher_noop"}
    assert r["plancher"]["majorant_fausses_retrouvailles"] == 0
    # Le PLANCHER MESURE sur le temoin cru sain voyage dans la MEME structure que le score.
    assert r["plancher_noop"]["temoin"] == "LOCK-002-286f244"
    assert r["plancher_noop"]["n_recevables"] == 0
    # Le score ne porte que sur les temoins a DEFAUT : eux seuls font barriere.
    assert r["score"] == "0/3" and r["statut"] == "NULLE"


def test_une_phase_temoins_PASSEE_porte_quand_meme_son_plancher(extraits):
    textes, dossier = extraits
    critiques = {
        "S2-BLIND-CHAMPION-42e9357": _cas("E26-juste-sans-le-mot-corps")["critiques"],
        "EDR-GRAB-COST-1828371": _cas("GRAB-fait-c-sans-le-token")["critiques"],
    }
    jugements = {n: "OUI" for n in critiques}
    r = T.verdict_phase_temoins(dossier, critiques, jugements)
    assert r["score"] == "2/3", [d["statut"] for d in r["detail"]]
    assert r["plancher"]["majorant_fausses_retrouvailles"] == 0
    assert r["plancher_noop"]["n_recevables"] == 0


def test_une_phase_INDISCRIMINANTE_le_DIT_au_lieu_de_s_annuler(extraits):
    """Si le record cru sain produit autant de critiques recevables que les défectueux, l'instrument
    ne les distingue pas — et ça, c'est un VERDICT, pas un détail qu'on tait."""
    textes, dossier = extraits
    noop = T.par_nom("LOCK-002-286f244")
    beaucoup = [_crit(constat=f"constat distinct numero {i}", preuve=f"tools/x{i}.py:{i + 1}")
                for i in range(6)]
    critiques = {
        "S2-BLIND-CHAMPION-42e9357": _cas("E26-juste-sans-le-mot-corps")["critiques"],
        "EDR-GRAB-COST-1828371": _cas("GRAB-fait-c-sans-le-token")["critiques"],
        noop["nom"]: beaucoup,
    }
    r = T.verdict_phase_temoins(dossier, critiques, {n: "OUI" for n in critiques})
    assert r["plancher_noop"]["n_recevables"] == 6
    assert r["plancher_noop"]["discrimine"] is False
    assert "INDISCRIMINANT" in r["plancher_noop"]["verdict"]
    # ⚠️ Et la revue n'est PAS annulee pour autant : les deux defauts restent RETROUVES.
    assert r["score"] == "2/3"
    assert [d["statut"] for d in r["detail"] if d["genre"] == "noop"] == ["MESURE"]
    # Controle POSITIF du meme champ : un no-op silencieux DISCRIMINE.
    r2 = T.verdict_phase_temoins(dossier, {k: v for k, v in critiques.items() if k != noop["nom"]},
                                 {n: "OUI" for n in critiques})
    assert r2["plancher_noop"]["discrimine"] is True and r2["plancher_noop"]["verdict"] == "DISCRIMINE"


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


def _gabarits(js):
    """Les littéraux gabarits du script, grossièrement découpés — assez pour savoir ce qui y est interpolé."""
    return re.findall(r"`(?:[^`\\]|\\.)*`", js, re.S)


def test_chaque_prompt_qui_dit_CI_DESSOUS_interpole_vraiment_une_donnee():
    """CONTRE-EXEMPLE GELE : le workflow n'avait JAMAIS fait circuler ses propres données.

    Mesuré au premier lancement réel (2026-09-24) : le prompt du vérificateur disait « si un témoin
    du roster n'a pas sa relecture CI-DESSOUS » et « écris la liste de critiques de chaque
    relecture » — or `relectures` n'y était **jamais interpolé**. On lui demandait de relayer des
    critiques qu'on ne lui avait pas données. Le défaut a traversé six rondes, 87 tests et deux
    revues, parce que **les tests lisent le TEXTE du workflow** : aucun ne fait circuler une donnée.

    Un déictique renvoie à des DONNÉES, et les données passent par `JSON.stringify` — exiger une
    interpolation quelconque ne discriminait pas : `${ROSTER}` (un chemin) suffisait à faire passer
    un prompt qu'on venait de priver de ses relectures (mesuré sur le harnais de mutation).

    ⚠️ CE QUE CETTE GARDE NE VOIT PAS — et c'est la deuxième fois qu'on l'apprend : c'est un `grep`.
    Elle vérifie qu'une interpolation de données EXISTE dans le même gabarit, jamais qu'elle porte la
    BONNE donnée ; un renommage de variable la contourne, `JSON.stringify` est une convention qu'un
    refactor peut abandonner, et une donnée interpolée mais VIDE la passe.
    **Seule une exécution de bout en bout prouve qu'une donnée circule.** La seule vraie
    vérification de ce workflow reste de le lancer.
    """
    js = _lire(_WORKFLOW)
    vus = 0
    for gabarit in _gabarits(js):
        if re.search(r"ci-dessous|ci-dessus|plus bas|plus haut", gabarit, re.I):
            vus += 1
            assert "${JSON.stringify(" in gabarit, (
                f"un prompt renvoie à des données qu'il n'interpole pas : …{gabarit[:90]}…")
    assert vus >= 2, "aucun prompt déictique trouvé : la garde ne balaie rien"


def test_le_prompt_du_VERIFICATEUR_recoit_bien_les_relectures_et_les_jugements():
    """Le cas précis qui a rendu NUL le premier Step 4."""
    js = _lire(_WORKFLOW)
    bloc = [g for g in _gabarits(js) if "VERIFICATEUR" in g]
    assert len(bloc) == 1, "prompt du vérificateur introuvable ou dupliqué"
    bloc = bloc[0]
    for donnee in ("${JSON.stringify(relectures)}", "juge.jugements", "juge.calibration"):
        assert donnee in bloc, f"le vérificateur ne reçoit pas {donnee}"


def test_le_JUGE_ne_recoit_QUE_les_relectures_a_juger_pas_celle_du_noop():
    """Lui soumettre le no-op lui apprendrait qu'il existe ; la lui DONNER le lui apprendrait aussi."""
    js = _lire(_WORKFLOW)
    bloc = [g for g in _gabarits(js) if "Tu es le JUGE" in g]
    assert len(bloc) == 1
    assert "${JSON.stringify(relecturesJugees)}" in bloc[0]
    assert "JSON.stringify(relectures)}" not in bloc[0], (
        "le juge reçoit TOUTES les relectures : il identifie le no-op par différence")
    assert "--questions-du-juge" in bloc[0]
    assert "noop" not in bloc[0].lower(), "le prompt du juge nomme le genre qu'il ne doit pas connaître"
    assert "'Aiguillage'" in js, "la phase qui filtre les relectures a disparu"


def test_l_AIGUILLAGE_ne_peut_plus_echouer_en_SILENCE():
    """CONTRE-EXEMPLE GELE : au 2e Step 4 réel, l'aiguillage a rendu `{"fichiers": []}`.

    Le CLI marchait (3 fichiers, no-op exclu, exit 0) : c'est l'agent qui n'a rien relayé — et il
    était le seul de la chaîne réglé sur `effort: 'low'`, alors qu'il décide ce que le juge voit.
    Son mode d'échec, une liste vide, était **indiscernable d'un refus légitime** et faisait tomber
    toute la revue sans dire pourquoi.

    Trois propriétés, décidables sur le texte : il n'est plus au réglage le plus bas ; il rend la
    COMMANDE et la SORTIE BRUTE, que le script logge ; et les deux pannes opposées — n'avoir rien
    relayé (TRANSPORT) et n'avoir rien filtré (FUITE, le juge verrait le no-op) — portent des noms
    distincts.
    """
    js = _lire(_WORKFLOW)
    bloc = js.split("phase('Aiguillage')", 1)[1].split("phase('Juge')", 1)[0]
    # La garde lit le CODE, pas la prose : le commentaire qui EXPLIQUE la correction la déclenchait.
    bloc = "\n".join(l for l in bloc.splitlines() if not l.lstrip().startswith("//"))
    assert "effort: 'low'" not in bloc, (
        "l'aiguillage est au réglage le plus bas : c'est une garde contre une fuite, pas une corvée")
    for champ in ("commande", "sortie_brute"):
        assert f"{champ}: {{ type: 'string' }}" in bloc, f"l'aiguillage ne rend pas {champ}"
        assert f"'{champ}'" in bloc, f"{champ} n'est pas exigé par le schéma"
        assert f"aiguillage.{champ}" in bloc, f"le script ne LOGGE pas {champ} quand ça casse"
    assert "aiguillage-TRANSPORT" in bloc and "aiguillage-FUITE" in bloc, (
        "les deux pannes opposées portent encore le même nom")
    # Et le vérificateur RE-DERIVE l'aiguillage : une fuite ne serait plus silencieuse.
    verificateur = [g for g in _gabarits(js) if "VERIFICATEUR" in g][0]
    assert "--questions-du-juge" in verificateur and "aiguillage divergent" in verificateur


def test_questions_du_juge_OMET_le_noop_et_donne_le_defaut_des_autres():
    q = T.questions_du_juge()
    defauts = [t for t in T.charger() if t["genre"] == "defaut"]
    noop = T.par_nom("LOCK-002-286f244")
    assert len(q) == len(defauts) == 3
    assert {x["fichier"] for x in q} == {t["fichier"] for t in defauts}
    assert noop["fichier"] not in {x["fichier"] for x in q}
    assert all(x["defaut"] for x in q)
    # Le CLI n'imprime ni le fichier du no-op, ni son « AUCUN — record sain ».
    import io
    from contextlib import redirect_stdout
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        assert T.main(["--questions-du-juge"]) == 0
    sortie = tampon.getvalue()
    assert noop["fichier"] not in sortie and "record sain" not in sortie
    assert all(x["fichier"] in sortie for x in q)


def test_le_workflow_ancre_une_RACINE_ABSOLUE_et_refuse_si_le_module_n_y_est_pas():
    """CONTRE-EXEMPLE GELE : un agent a lancé le CLI depuis l'arbre principal, où le module n'existe
    pas, et n'a rapporté qu'`EXIT=2`. Tous les prompts employaient des chemins RELATIFS — un état
    ambiant non déclaré, dont la correction de l'instrument dépendait."""
    js = _lire(_WORKFLOW)
    assert "phase('Racine')" in js and "'Racine'" in js.split("phases:", 1)[1][:400]
    bloc = js.split("phase('Racine')", 1)[1].split("phase('Temoins')", 1)[0]
    assert "--racine-valide" in bloc and "git rev-parse --show-toplevel" in bloc
    assert "racine-invalide" in bloc, "aucune branche de refus au demarrage"
    for champ in ("commande", "sortie_brute"):
        assert f"ancrage.{champ}" in bloc, f"la panne de racine ne dit pas {champ}"
    # Plus AUCUNE invocation relative du CLI dans le corps du script (les commentaires exceptes).
    code = "\n".join(l for l in js.splitlines() if not l.lstrip().startswith("//"))
    relatives = re.findall(r"python\s+(?!\$\{racine\}/)(?!R/)tools/refutateur_temoins\.py", code)
    assert not relatives, f"{len(relatives)} invocation(s) encore relative(s) : {relatives[:3]}"


def test_le_workflow_fait_MESURER_le_noop_au_lieu_de_le_faire_BARRER():
    js = _lire(_WORKFLOW)
    assert "plancher_noop" in js
    assert "'plancher_noop'" in js.split("const VERIFICATION", 1)[1].split("\n}", 1)[0], (
        "le plancher du no-op n'est pas EXIGE du verificateur")
    # Le filtre d'echec accepte MESURE : un no-op bavard ne jette plus une revue qui a trouve.
    assert "v.statut !== 'MESURE'" in js
    assert "discrimine" in js and "INDISCRIMINANT" in js


def test_le_workflow_n_accepte_de_l_appelant_que_des_CHEMINS():
    js = _lire(_WORKFLOW)
    assert "args.fichiers" in js
    for fuite in ("args.temoins", "t.attendu", "temoin.attendu"):
        assert fuite not in js, f"le workflow accepte {fuite} de l'appelant"


def test_le_workflow_n_a_AUCUN_backtick_NU_dans_ses_litteraux_gabarits():
    """CONTRE-EXEMPLE GELE : le harnais a REFUSE de charger le script le 2026-09-24.

        Invalid workflow script: Script parse error: Unexpected token (116:62)
        ere ligne, TELLE QUELLE, dans le champ `plancher`. Un score sans son plancher es

    Un backtick de PROSE dans un littéral gabarit ferme le gabarit. Le livrable central de la tâche
    n'avait jamais été exécuté : les tests portaient sur le module Python et sur le TEXTE du
    workflow, aucun ne vérifiait qu'il est CHARGEABLE.

    ⚠️ `node --check` est MESURÉ INSUFFISANT — il rend 0 sur le fichier que le harnais refuse (les
    deux parseurs diffèrent), donc une garde qui l'appellerait serait décorative (classe E4).
    ⚠️ Et cette garde-ci ne voit qu'une propriété SYNTAXIQUE LOCALE : la passer ne garantit pas que
    le harnais accepte le script.
    """
    from tools import workflow_lint  # noqa: PLC0415

    source = _lire(_WORKFLOW)
    assert workflow_lint.backticks_nus(source) == [], (
        "backtick nu dans le workflow : le harnais refusera de le charger")

    # CONTRE-EXEMPLE : on ré-introduit EN MÉMOIRE le backtick exact de la ligne 116.
    casse = source.replace("dans le champ plancher.", "dans le champ `plancher`.")
    assert casse != source, "le contre-exemple ne casse RIEN : la garde ne prouverait rien"
    trouves = workflow_lint.backticks_nus(casse)
    assert trouves, "MUTATION NON TUEE : le backtick nu de la ligne 116 repasse"
    assert any(sig == "backtick-en-texte" for _, _, sig, _ in trouves)
    assert any(sig == "tagged-template" for _, _, sig, _ in trouves)


def test_le_balayeur_de_backticks_rend_ses_DEUX_issues_sur_des_sources_minimales():
    """Les deux issues sur une réponse connue, et pas seulement sur le fichier réel."""
    from tools import workflow_lint  # noqa: PLC0415

    sain = "const a = `texte ${x} et \\` echappe`\nconst b = 'un ` dans une chaine'\n// un ` en commentaire\n"
    assert workflow_lint.backticks_nus(sain) == [], workflow_lint.backticks_nus(sain)
    casse = "const a = `voir le champ `plancher` ici`\n"
    signatures = {sig for _, _, sig, _ in workflow_lint.backticks_nus(casse)}
    assert signatures == {"backtick-en-texte", "tagged-template"}
    assert workflow_lint.backticks_nus("const a = `jamais ferme\n")[-1][2] == "gabarit-non-ferme"
    assert workflow_lint.main([_WORKFLOW]) == 0


def test_TOUS_les_scripts_de_workflow_du_depot_sont_balayes_pas_seulement_celui_ci():
    """La garde porte sur le MÉCANISME, pas sur le fichier où il a mordu (règle du dépôt)."""
    from tools import workflow_lint  # noqa: PLC0415

    dossier = os.path.join(T._ROOT, ".claude", "workflows")
    scripts = [os.path.join(dossier, f) for f in sorted(os.listdir(dossier)) if f.endswith(".js")]
    assert scripts, "aucun script de workflow trouvé : la garde ne balaierait rien"
    assert workflow_lint.main(scripts) == 0


def test_le_workflow_ne_construit_aucun_monde_et_ne_prend_aucun_bail():
    js = _lire(_WORKFLOW)
    for interdit in ("hold(", "jobs.run", "FamineWorld", "kuzu"):
        assert interdit not in js, f"le workflow touche a {interdit} : une revue ne simule pas"


def test_aucune_declaration_CALIBRATED_de_ce_module_ne_pointe_vers_un_symbole_DISPARU():
    """CONTRE-EXEMPLE GELE : `tools/refutateur_temoins.py::verifier` a survécu quatre rondes à sa
    fonction.

    La refonte du barème (ronde 4) a scindé `verifier` en `recevabilite` et `verdict_temoin` ; la
    déclaration est restée, et le cliquet de calibration **l'abandonne en silence** — il ne dit ni
    « déclaration morte », ni « déclaration inutile ». J'ai donc cru l'instrument calibré alors que
    la clé ne résolvait rien. C'est la troisième cause d'un même silence, après la LANGUE du nom et
    le KIND du symbole (`^def` ne voit pas une classe).

    Cette garde ferme la cause du symbole RENOMMÉ, **pour mes fichiers seulement**. La généraliser à
    tout `CALIBRATED` est le vrai correctif — il appartient à la session qui reprend les motifs du
    cliquet, pas à cette tâche.

    ⚠️ Elle ne dit rien de l'inverse : une fonction qui affirme mais n'est **pas** déclarée reste
    invisible, et l'heuristique ne la détecte pas davantage.
    """
    import ast  # noqa: PLC0415

    source_tests = _lire(os.path.join(T._ROOT, "tests", "sandbox", "test_instrument_calibration.py"))
    arbre = ast.parse(source_tests)
    cles = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Assign) and any(
                getattr(c, "id", "") == "CALIBRATED" for c in noeud.targets):
            cles = [k.value for k in noeud.value.keys if isinstance(k, ast.Constant)]
            break
    assert cles, "CALIBRATED introuvable : le détecteur d'AST n'a rien lu"

    miens = [c for c in cles if c.startswith(("tools/refutateur_temoins.py::", "tools/workflow_lint.py::"))]
    assert miens, "aucune déclaration de ce module : la garde ne balaie rien"
    for cle in miens:
        chemin, symbole = cle.split("::", 1)
        module = ast.parse(_lire(os.path.join(T._ROOT, chemin)))
        definis = {n.name for n in ast.walk(module)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        assert symbole in definis, (
            f"déclaration MORTE : {cle} — le symbole n'existe plus. Le cliquet l'abandonne en "
            f"silence ; définis dans ce fichier : {sorted(definis)}")


def test_le_protocole_d_invocation_est_ecrit_dans_docs_reviews_README():
    txt = _lire(os.path.join(T._ROOT, "docs", "reviews", "README.md"))
    assert "Lancer une revue" in txt
    assert "tools/refutateur_temoins.py --extraire" in txt
    assert ".claude/workflows/refutateur.js" in txt
    assert "NUL" in txt
    assert "fichiers:" in txt and "temoins:" not in txt
    assert "--plancher" in txt, "le protocole doit imposer la publication du plancher"
