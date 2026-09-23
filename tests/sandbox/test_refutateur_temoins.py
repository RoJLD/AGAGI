"""Temoins GELES du Refutateur : ils existent dans l'histoire git a leur SHA, la version gelee porte
ENCORE son defaut connu (signature / antisignature executables), et le bareme produit SES DEUX ISSUES
(revue ECRITE / revue NULLE) sur des textes a reponse connue -- plus une troisieme, INDECIDABLE.

Pourquoi une signature executable : la verification « a l'oeil » de la version d'un temoin n'est faite
qu'une fois, au moment de le geler. Si le SHA etait mal choisi (p.ex. la version DEJA RECTIFIEE d'un
record au lieu de celle qui porte le defaut nu), plus rien ne le dirait : le Refutateur validerait une
revue qui « retrouve » un defaut deja corrige dans le texte. `signature` / `antisignature` gelent ce
regard dans un test.

⚠️ QUATRE FRANCHISSEMENTS MESURES EN REVUE (2026-09-23), chacun gele ici en contre-exemple :
  1. la cle de reponse etait PUBLIEE dans le document que l'agent est somme de lire (REF), et le chemin
     du temoin portait son nom -> la phase mesurait la lecture d'un tableau, pas la discrimination ;
  2. une revue qui ne CONFIRME rien passait les quatre temoins : la regex etait cherchee dans toute la
     charge JSON, sonde comprise, et le token attendu figure dans le texte des temoins eux-memes ;
  3. le double bareme (Python / JS) avait DEJA diverge sur trois points -> le bareme vit ici, seul ;
  4. le roster gele n'etait pas contraignant : l'appelant passait les attendus au workflow.
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


def _texte(*critiques):
    return json.dumps(list(critiques), ensure_ascii=False)


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
    """Les deux issues de la garde du roster : un attendu vidé, ou le no-op seul, ne passent pas."""
    tem = T.charger()
    affaibli = [dict(t, attendu="") if t["genre"] == "defaut" else t for t in tem]
    assert T.roster_conforme(affaibli)[0] is False
    assert T.roster_conforme([t for t in tem if t["genre"] == "noop"])[0] is False
    doublon = [dict(tem[0]), dict(tem[1]), dict(tem[2]), dict(tem[3], nom=tem[0]["nom"])]
    assert T.roster_conforme(doublon)[0] is False


# --------------------------------------------------------------------------------------------- #
# Extraction ANONYME (franchissement 1)
# --------------------------------------------------------------------------------------------- #


def test_les_fichiers_d_extraction_sont_NEUTRES_et_decorreles_de_l_ordre_du_roster():
    tem = T.charger()
    for t in tem:
        assert re.fullmatch(r"temoin-\d+\.md", t["fichier"]), f"{t['nom']} : nom de fichier parlant"
        assert t["nom"] not in t["fichier"]
        for mot in ("sain", "noop", "defaut", "GRAB", "BLIND", "RETAIN", "LOCK"):
            assert mot.lower() not in t["fichier"].lower()
    ordre = [t["fichier"] for t in tem]
    attendu_naif = [f"temoin-{i}.md" for i in range(1, len(tem) + 1)]
    assert ordre != attendu_naif, (
        "les fichiers suivent l'ordre du roster : « le dernier est le no-op » redeviendrait devinable")


def test_le_nom_d_un_temoin_est_une_FORME_DERIVEE_et_non_un_libelle_libre():
    """LA garde. Le nom vaut `<identifiant du record>-<sha7>`, RECOMPUTE depuis `chemin` et `sha`.

    Pourquoi une forme POSITIVE plutot qu'une liste de mots interdits : la question qui compte est
    « ce nom divulgue-t-il le GENRE du temoin ? », et une liste noire n'y repond jamais -- elle repond
    « ce nom contient-il l'un de ces mots ». Mesure du 2026-09-23 : la liste de neuf mots a attrape
    `LOCK-002-sain` et a LAISSE PASSER `RETAIN-COMPOSE-pre-retractation`, qui annonce qu'une
    retractation a suivi, donc qu'un defaut est a trouver ; il n'a ete vu qu'A L'OEIL. Ajouter
    `retract*` aurait deplace le trou d'un cran. Un nom derive de l'IDENTITE (quel record, a quel SHA)
    ne peut structurellement rien dire de la QUALITE de ce qu'il nomme.

    ⚠️ CE QUE CETTE GARDE NE VOIT PAS : la FORME DU NOM, jamais le CONTENU du fichier extrait. Un
    record peut, a son SHA gele, annoncer sa propre faiblesse dans son titre ou sa prose et dire ainsi
    au relecteur ce qu'il doit trouver. Seule l'`antisignature` couvre un cas voisin et un seul (la
    marque de la CORRECTION est absente). « Le texte gele n'annonce pas son propre defaut » n'est ni
    mesure, ni decidable par motif : il reste a la charge de qui gele un temoin.
    """
    for t in T.charger():
        assert t["nom"] == T.nom_attendu(t), (
            f"nom hors forme : {t['nom']!r}, attendu {T.nom_attendu(t)!r}")
        assert re.fullmatch(r"[A-Za-z0-9.\-]+-[0-9a-f]{7}", t["nom"]), t["nom"]


def test_un_nom_renomme_A_LA_MAIN_est_REFUSE_et_rend_le_CLI_2(tmp_path):
    """CONTRE-EXEMPLE GELE : les deux issues de la forme, sur les deux noms reellement rencontres."""
    tem = T.charger()
    assert T.roster_conforme(tem)[0] is True  # controle INTACT avant toute mutation
    for libelle in ("LOCK-002-sain", "RETAIN-COMPOSE-pre-retractation", "temoin-4", ""):
        mute = [dict(t, nom=libelle) if t["genre"] == "noop" else t for t in tem]
        ok, raison = T.roster_conforme(mute)
        assert ok is False, f"un nom libre {libelle!r} passe la forme"
        assert "FORME" in raison or "collision" in raison
    # Le CLI refuse EN BLOC un roster hors forme : il rend 2 (indecidable), jamais 0 ni 1.
    f = tmp_path / "x.json"
    f.write_text("[]", encoding="utf-8")
    vrai_charger = T.charger
    T.charger = lambda: [dict(t, nom="LOCK-002-sain") if t["genre"] == "noop" else t
                         for t in vrai_charger()]
    try:
        assert T.main(["--verifier", "EDR-GRAB-COST-1828371", str(f)]) == 2
    finally:
        T.charger = vrai_charger
    assert T.main(["--verifier", "EDR-GRAB-COST-1828371", str(f)]) == 1  # roster rendu, revue NULLE


def test_plancher_secondaire_aucun_nom_ne_contient_un_mot_de_genre():
    """PLANCHER, pas la garde : conserve parce qu'il a reellement attrape `LOCK-002-sain`, et qu'un
    mot de genre glisse aussi dans un NOM DE FICHIER de record (que la forme, elle, recopie)."""
    declarent_le_genre = ("sain", "noop", "ok", "propre", "clean", "bug", "faux", "bon")
    for t in T.charger():
        for mot in declarent_le_genre:
            assert mot not in t["nom"].lower(), f"le nom {t['nom']} declare son genre"


@pytest.mark.parametrize("nom", [t["nom"] for t in T.charger()])
def test_la_version_gelee_porte_ENCORE_son_defaut_connu(nom, tmp_path):
    """Signature PRESENTE et antisignature ABSENTE : le regard « a l'oeil » du 2026-09-23, execute."""
    t = T.par_nom(nom)
    txt = _lire(T.extraire(t, str(tmp_path)))
    assert re.search(t["signature"], txt), (
        f"{nom} : la signature {t['signature']!r} est ABSENTE de {t['sha'][:9]}:{t['chemin']} — "
        "le SHA ne designe pas la version attendue")
    if t["antisignature"]:
        assert not re.search(t["antisignature"], txt), (
            f"{nom} : l'antisignature {t['antisignature']!r} est PRESENTE — la version gelee est deja "
            "corrigee, son defaut n'est plus a trouver")


def test_extraire_ecrit_la_version_GELEE_sous_un_nom_ANONYME(tmp_path):
    grab = T.par_nom("EDR-GRAB-COST-1828371")
    p = T.extraire(grab, str(tmp_path))
    assert os.path.basename(p) == grab["fichier"]
    assert "GRAB" not in os.path.basename(p)
    txt = _lire(p)
    # La premisse fausse est ENONCEE, pas citee comme erreur passee : la rectification du 2026-09-09
    # (« RECTIFICATION », « le 3.0 n'a jamais eu cours ») n'est pas encore dans le texte.
    assert "forage_payoff = 3.0" in txt
    assert "RECTIFICATION" not in txt
    assert "grabber NOURRIT" in txt  # le titre d'origine, celui que la premisse fausse porte


def test_extraire_tous_rend_la_correspondance_a_l_appelant_et_n_ecrit_RIEN_qui_la_trahisse(tmp_path):
    correspondance = T.extraire_tous(str(tmp_path))
    assert set(correspondance) == {t["nom"] for t in T.charger()}
    ecrits = sorted(os.listdir(tmp_path))
    assert ecrits == sorted(t["fichier"] for t in T.charger()), (
        f"le repertoire extrait contient autre chose que les temoins anonymes : {ecrits}")
    # Le contenu d'un temoin PORTE son defaut (c'est le point) ; ce qui ne doit fuiter nulle part dans
    # le repertoire extrait, c'est la correspondance nom <-> fichier.
    for fichier in ecrits:
        contenu = _lire(os.path.join(tmp_path, fichier))
        for t in T.charger():
            assert t["nom"] not in contenu, f"{fichier} nomme le temoin {t['nom']}"
            assert t["defaut"] not in contenu


def test_extraire_leve_sur_un_temoin_dont_le_SHA_ne_porte_pas_le_chemin(tmp_path):
    faux = dict(T.par_nom("EDR-GRAB-COST-1828371"), nom="FAUX", chemin="docs/EDR/_inexistant_.md")
    with pytest.raises(RuntimeError):
        T.extraire(faux, str(tmp_path))


# --------------------------------------------------------------------------------------------- #
# `verifier` : seule une critique CONFIRMEE retrouve un temoin (franchissement 2)
# --------------------------------------------------------------------------------------------- #


def test_verifier_accepte_un_constat_CONFIRME_et_refuse_son_absence():
    grab = T.par_nom("EDR-GRAB-COST-1828371")
    trouve = _crit(constat="la valeur forage_payoff citee n'est publiee par aucun bloc regime",
                   preuve="results/…json : pas de cle forage_payoff", sonde="python tools/check_regime_claims.py")
    assert T.verifier(grab, _texte(trouve)) is True
    assert T.verifier(grab, _texte(_crit(constat="rien a signaler", preuve="—"))) is False
    assert T.verifier(grab, "") is False


def test_une_critique_NON_CONFIRMEE_ne_retrouve_PAS_un_temoin():
    """CONTRE-EXEMPLE GELE (revue du 2026-09-23) : une revue qui ne confirme rien passait les 4 temoins."""
    grab = T.par_nom("EDR-GRAB-COST-1828371")
    non_confirmee = _crit(verdict="non confirmé", sonde="grep forage_payoff",
                          constat="forage_payoff semble cite", preuve="ligne 14")
    assert T.verifier(grab, _texte(non_confirmee)) is False
    hors = _crit(verdict="hors périmètre", constat="forage_payoff", preuve="forage_payoff")
    assert T.verifier(grab, _texte(hors)) is False


def test_le_token_present_dans_la_SEULE_sonde_ne_retrouve_PAS_un_temoin():
    """CONTRE-EXEMPLE GELE : le token attendu figure dans le texte des temoins eux-memes (section
    « ce qui n'est pas mesure »). Une revue qui RECOPIE la commande passait le temoin."""
    grab = T.par_nom("EDR-GRAB-COST-1828371")
    sonde_seule = _crit(sonde="grep -n forage_payoff docs/EDR/…md", constat="le regime est publie",
                        preuve="aucune discordance")
    assert T.verifier(grab, _texte(sonde_seule)) is False


def test_verifier_sur_les_trois_defauts_reconnait_le_bon_constat_et_rejette_la_revue_creuse():
    connus = {
        "EDR-GRAB-COST-1828371": "forage_payoff = 3.0 cite, absent du bloc regime du results",
        "S2-BLIND-CHAMPION-42e9357": "make_blind annule aussi W[0:10], donc le CORPS ; le drain tombe de 46 %",
        "EDR-RETAIN-COMPOSE-4204f8f": "nul comparatif sous gradient, le pas lr=0.02 n'est pas balaye (E19)",
    }
    creuse = _crit(constat="Le record est clair, bien ecrit, la conclusion est prudente.",
                   preuve="lecture integrale", sonde="cat du record")
    for nom, constat in connus.items():
        t = T.par_nom(nom)
        assert T.verifier(t, _texte(_crit(constat=constat, preuve="fichier:ligne"))) is True, nom
        assert T.verifier(t, _texte(creuse)) is False, f"{nom} : une revue CREUSE passe le temoin"


def test_verifier_du_noop_tolere_une_critique_CONFIRMEE_et_refuse_deux():
    noop = T.par_nom("LOCK-002-286f244")
    assert T.verifier(noop, "[]") is True
    assert T.verifier(noop, _texte(_crit(constat="un doute"))) is True
    assert T.verifier(noop, _texte(_crit(constat="a"), _crit(constat="b"))) is False
    # Deux critiques NON confirmees ne sont pas deux fausses alarmes : le plancher compte les confirmees.
    assert T.verifier(noop, _texte(_crit(verdict="non confirmé"), _crit(verdict="hors périmètre"))) is True
    # Un texte VIDE n'est pas un silence de revue : c'est une absence de mesure -> revue NULLE.
    assert T.verifier(noop, "") is False
    assert T.verifier(noop, "   \n ") is False


def test_verifier_leve_FormatInvalide_sur_un_texte_illisible_ou_une_critique_sans_verdict():
    """INDECIDABLE n'est pas NULLE : un bug de serialisation ne doit pas devenir un verdict de fond."""
    grab = T.par_nom("EDR-GRAB-COST-1828371")
    for illisible in ("P2 : forage_payoff non publie", "{\"critiques\": []}", "[1, 2]", "[[]]"):
        with pytest.raises(T.FormatInvalide):
            T.verifier(grab, illisible)
    # Comptage PARTIEL : c'est exactement la divergence Python/JS mesuree en revue.
    partiel = json.dumps([{"verdict": "confirme"}, {"constat": "x"}])
    with pytest.raises(T.FormatInvalide):
        T.verifier(grab, partiel)
    with pytest.raises(T.FormatInvalide):
        T.verifier(T.par_nom("LOCK-002-286f244"), partiel)


def test_main_rend_0_puis_1_puis_2_les_trois_issues(tmp_path, capsys):
    assert T.main(["--extraire", str(tmp_path)]) == 0
    assert sorted(os.listdir(tmp_path)) == sorted(t["fichier"] for t in T.charger())
    bon = tmp_path / "ok.json"
    bon.write_text(_texte(_crit(constat="forage_payoff non publie", preuve="results:regime")), encoding="utf-8")
    nul = tmp_path / "nul.json"
    nul.write_text(_texte(_crit(constat="rien a signaler")), encoding="utf-8")
    illisible = tmp_path / "illisible.txt"
    illisible.write_text("rien a signaler", encoding="utf-8")
    assert T.main(["--verifier", "EDR-GRAB-COST-1828371", str(bon)]) == 0
    assert T.main(["--verifier", "EDR-GRAB-COST-1828371", str(nul)]) == 1
    assert T.main(["--verifier", "EDR-GRAB-COST-1828371", str(illisible)]) == 2
    sortie = capsys.readouterr().out
    assert "NULLE" in sortie and "INDÉCIDABLE" in sortie


def test_main_rend_2_sur_un_temoin_inconnu(tmp_path):
    f = tmp_path / "x.json"
    f.write_text("[]", encoding="utf-8")
    assert T.main(["--verifier", "TEMOIN-QUI-N-EXISTE-PAS", str(f)]) == 2


# --------------------------------------------------------------------------------------------- #
# Le REF : forme, roles, et AUCUNE cle de reponse (franchissement 1)
# --------------------------------------------------------------------------------------------- #


def test_le_REF_est_un_record_et_fige_dix_prompts():
    txt = _lire(_REF)
    assert txt.startswith("---\n")
    entete = txt.split("---", 2)[1]
    assert "id: REF-REVUE-ADVERSARIALE" in entete
    assert "type: REF" in entete
    assert "status: active" in entete
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
    assert delegue, "aucun prompt ne delegue : les portes seraient refaites a la main"
    assert len(delegue) < len(lignes), "tout deleguer : le Refutateur ne jugerait plus rien"
    for l in delegue:
        portes = re.findall(r"tools/check_\w+\.py", l)
        assert portes, f"DÉLÈGUE sans porte nommee : {l[:80]}"
        for porte in portes:
            assert os.path.exists(os.path.join(T._ROOT, porte)), (
                f"le REF delegue a {porte}, qui n'existe pas")


def test_le_recapitulatif_du_REF_se_derive_du_TABLEAU_et_non_de_la_memoire():
    """Le compte vivant (« DÉLÈGUENT : P2, P3, P9 ») doit dire ce que le tableau dit."""
    txt = _lire(_REF)
    du_tableau = {"DÉLÈGUE": [], "JUGE": []}
    for l in _lignes_prompts():
        pid = re.match(r"\|\s*(P\d+)\s*\|", l).group(1)
        du_tableau["DÉLÈGUE" if "DÉLÈGUE" in l else "JUGE"].append(pid)
    for role, ids in du_tableau.items():
        ligne = re.search(rf"\*\*{role}NT\*\*\s*:\s*([^—\n]+)", txt)
        assert ligne, f"recapitulatif {role}NT absent du REF"
        annonces = re.findall(r"P\d+", ligne.group(1))
        assert annonces == ids, f"{role}NT annonce {annonces}, le tableau dit {ids}"


def test_le_REF_ne_publie_AUCUNE_cle_de_reponse():
    """Ce que l'agent de revue lit ne doit contenir ni les attendus, ni les defauts, ni les genres."""
    txt = _lire(_REF)
    roster = _lire(T._JSON)
    for t in T.charger():
        assert t["nom"] in txt, f"temoin {t['nom']} absent du REF"
        if t["attendu"]:
            assert t["attendu"] not in txt, f"regex `attendu` de {t['nom']} PUBLIEE dans le REF"
            # Controle POSITIF du motif de recherche : la regex EST trouvable la ou elle vit (le roster,
            # ou elle est serialisee avec ses echappements). Sans lui, « absent du REF » ne prouverait rien.
            assert json.dumps(t["attendu"], ensure_ascii=False)[1:-1] in roster
        assert t["defaut"] not in txt, f"enonce du defaut de {t['nom']} PUBLIE dans le REF"
    # Le token le plus specifique des trois defauts : s'il reparait dans le REF, la cle est de retour.
    assert "forage_payoff" not in txt
    assert "forage_payoff" in roster
    # Aucun tableau temoin -> attendu.
    assert not re.search(r"\|\s*`?(GRAB-COST|S2-BLIND|RETAIN-COMPOSE|LOCK-002)", txt)


def test_le_REF_ne_recopie_aucun_chiffre_de_porte_en_dur():
    txt = _lire(_REF)
    interdits = [r"\b300 records\b", r"\b74 (records|citent)\b", r"\b18 chemins\b", r"\b232 records\b",
                 r"\b8 nus\b", r"\b29 scell", r"\b104/105\b"]
    for motif in interdits:
        assert not re.search(motif, txt), f"chiffre de porte recopie dans le REF : {motif}"


# --------------------------------------------------------------------------------------------- #
# Le workflow : il ne juge plus rien (franchissements 3 et 4)
# --------------------------------------------------------------------------------------------- #


def test_le_workflow_a_son_meta_et_ne_cite_que_des_prompts_du_REF():
    js = _lire(_WORKFLOW)
    assert "export const meta = {" in js
    bloc = js.split("export const meta = {", 1)[1].split("\n}", 1)[0]
    for champ in ("name:", "description:", "phases:"):
        assert champ in bloc, f"meta sans {champ}"
    assert "'refutateur'" in bloc or '"refutateur"' in bloc
    ref_txt = _lire(_REF)
    for pid in re.findall(r"'(P\d+)'", js):
        assert re.search(rf"\|\s*{pid}\s*\|", ref_txt), f"{pid} cite par le workflow, absent du REF"
    assert "docs/REF/REF-REVUE-ADVERSARIALE.md" in js
    assert "docs/reviews/" in js


def test_le_workflow_ne_contient_AUCUN_bareme_et_fait_lancer_le_CLI_python():
    """Le bareme vit en UN seul endroit. Les deux implementations avaient DEJA diverge (3 points)."""
    js = _lire(_WORKFLOW)
    for interdit in ("function retrouve", "new RegExp", "genre === 'noop'", 'genre === "noop"'):
        assert interdit not in js, f"le workflow rejuge : {interdit}"
    assert "tools/refutateur_temoins.py --verifier" in js
    assert "tools/refutateur_temoins.json" in js
    assert "'Verification'" in js or '"Verification"' in js


def test_le_workflow_n_accepte_de_l_appelant_que_des_CHEMINS():
    """Le gel n'est contraignant que si l'appelant ne peut pas le contourner."""
    js = _lire(_WORKFLOW)
    assert "args.fichiers" in js
    for fuite in ("args.temoins", "t.attendu", "temoin.attendu"):
        assert fuite not in js, f"le workflow accepte {fuite} de l'appelant : le roster gele est contournable"


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
    assert "fichiers:" in txt and "temoins:" not in txt, "le README passerait encore le roster en argument"
