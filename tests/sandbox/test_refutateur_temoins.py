"""Temoins GELES du Refutateur : ils existent dans l'histoire git a leur SHA, la version gelee porte
ENCORE son defaut connu (signature / antisignature executables), les regex compilent, et `verifier`
produit SES DEUX ISSUES (revue ECRITE / revue NULLE) sur des textes a reponse connue.

Pourquoi une signature executable : la verification « a l'oeil » de la version d'un temoin n'est faite
qu'une fois, au moment de le geler. Si le SHA etait mal choisi (p.ex. la version DEJA RECTIFIEE d'un
record au lieu de celle qui porte le defaut nu), plus rien ne le dirait : le Refutateur validerait une
revue qui « retrouve » un defaut deja corrige dans le texte. `signature` / `antisignature` gelent ce
regard dans un test.
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


# --------------------------------------------------------------------------------------------- #
# Les temoins eux-memes
# --------------------------------------------------------------------------------------------- #


def test_trois_temoins_a_defaut_et_un_noop_tous_presents_dans_git():
    tem = T.charger()
    assert sum(1 for t in tem if t["genre"] == "defaut") == 3
    assert sum(1 for t in tem if t["genre"] == "noop") == 1
    assert len({t["nom"] for t in tem}) == len(tem), "noms de temoins en collision"
    for t in tem:
        assert re.fullmatch(r"[0-9a-f]{40}", t["sha"]), t
        p = subprocess.run(["git", "cat-file", "-e", f"{t['sha']}:{t['chemin']}"],
                           cwd=T._ROOT, capture_output=True)
        assert p.returncode == 0, f"{t['nom']} : {t['sha']}:{t['chemin']} absent de git"
        re.compile(t["attendu"] or ".")
        re.compile(t["signature"])
        re.compile(t["antisignature"] or ".")


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


def test_extraire_ecrit_la_version_GELEE_et_le_temoin_GRAB_COST_porte_encore_la_valeur_fausse(tmp_path):
    grab = T.par_nom("GRAB-COST-v09-08")
    p = T.extraire(grab, str(tmp_path))
    assert os.path.basename(p) == "GRAB-COST-v09-08.md"
    txt = _lire(p)
    # La premisse fausse est ENONCEE, pas citee comme erreur passee : la rectification du 2026-09-09
    # (« RECTIFICATION », « le 3.0 n'a jamais eu cours ») n'est pas encore dans le texte.
    assert "forage_payoff = 3.0" in txt
    assert "RECTIFICATION" not in txt
    assert "grabber NOURRIT" in txt  # le titre d'origine, celui que la premisse fausse porte


def test_extraire_leve_sur_un_temoin_dont_le_SHA_ne_porte_pas_le_chemin(tmp_path):
    faux = dict(T.par_nom("GRAB-COST-v09-08"), nom="FAUX", chemin="docs/EDR/_inexistant_.md")
    with pytest.raises(RuntimeError):
        T.extraire(faux, str(tmp_path))


# --------------------------------------------------------------------------------------------- #
# `verifier` est un instrument : ses deux issues sur des textes a reponse connue
# --------------------------------------------------------------------------------------------- #


def test_verifier_accepte_le_defaut_nomme_et_refuse_son_absence():
    grab = T.par_nom("GRAB-COST-v09-08")
    assert T.verifier(grab, "P2 : la valeur forage_payoff citee n'est publiee par aucun bloc regime") is True
    assert T.verifier(grab, "aucune critique") is False
    assert T.verifier(grab, "") is False


def test_verifier_sur_les_trois_defauts_reconnait_le_bon_texte_et_rejette_la_revue_creuse():
    connus = {
        "GRAB-COST-v09-08": "P2 DELEGUE : forage_payoff = 3.0 cite, absent du bloc regime du results",
        "S2-BLIND-v1": "P8 : make_blind annule aussi W[0:10], donc le CORPS ; le drain tombe de 46 %",
        "RETAIN-COMPOSE-pre-retractation": "P3 : nul comparatif sous gradient, le pas lr=0.02 n'est pas balaye (E19)",
    }
    creux = "Le record est clair, bien ecrit, les tableaux sont lisibles et la conclusion est prudente."
    for nom, texte in connus.items():
        t = T.par_nom(nom)
        assert T.verifier(t, texte) is True, nom
        assert T.verifier(t, creux) is False, f"{nom} : une revue CREUSE passe le temoin"


def test_verifier_du_noop_tolere_une_critique_et_refuse_deux():
    noop = T.par_nom("LOCK-002-sain")
    assert T.verifier(noop, "[]") is True
    assert T.verifier(noop, '[{"a": 1}]') is True
    assert T.verifier(noop, '[{"a": 1}, {"b": 2}]') is False
    # Un texte VIDE n'est pas un silence de revue : c'est une absence de mesure -> revue NULLE.
    assert T.verifier(noop, "") is False
    assert T.verifier(noop, "   \n ") is False
    # Quand les critiques portent un verdict, seules les CONFIRMEES comptent (meme regle que le workflow).
    deux_non_confirmees = json.dumps([{"verdict": "non confirme"}, {"verdict": "hors perimetre"}])
    assert T.verifier(noop, deux_non_confirmees) is True
    deux_confirmees = json.dumps([{"verdict": "confirme"}, {"verdict": "confirme"}])
    assert T.verifier(noop, deux_confirmees) is False


def test_main_rend_0_quand_le_defaut_est_retrouve_et_1_sinon(tmp_path, capsys):
    """Les deux issues du CLI, sur fichiers reels."""
    assert T.main(["--extraire", str(tmp_path)]) == 0
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".md")]) == len(T.charger())
    bon = tmp_path / "critiques_ok.txt"
    bon.write_text("P2 : forage_payoff non publie", encoding="utf-8")
    mauvais = tmp_path / "critiques_vides.txt"
    mauvais.write_text("rien a signaler", encoding="utf-8")
    assert T.main(["--verifier", "GRAB-COST-v09-08", str(bon)]) == 0
    assert T.main(["--verifier", "GRAB-COST-v09-08", str(mauvais)]) == 1
    sortie = capsys.readouterr().out
    assert "NULLE" in sortie


def test_main_rend_2_sur_un_temoin_inconnu(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("peu importe", encoding="utf-8")
    assert T.main(["--verifier", "TEMOIN-QUI-N-EXISTE-PAS", str(f)]) == 2


# --------------------------------------------------------------------------------------------- #
# Le REF et le workflow : forme, et coherence avec les temoins
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


def test_le_REF_dit_pour_CHAQUE_prompt_s_il_DELEGUE_a_une_porte_ou_s_il_JUGE():
    txt = _lire(_REF)
    lignes = [l for l in txt.splitlines() if re.match(r"\|\s*P\d+\s*\|", l)]
    assert len(lignes) == 10
    for l in lignes:
        assert ("DÉLÈGUE" in l) or ("JUGE" in l), f"role non declare : {l[:60]}"
    delegue = [l for l in lignes if "DÉLÈGUE" in l]
    assert delegue, "aucun prompt ne delegue : les portes 19/20/22 seraient refaites a la main"
    assert len(delegue) < len(lignes), "tout deleguer : le Refutateur ne jugerait plus rien"
    # Un prompt qui DELEGUE nomme la porte qu'il lance.
    for l in delegue:
        assert re.search(r"tools/check_\w+\.py", l), f"DÉLÈGUE sans porte nommee : {l[:80]}"


def test_le_REF_nomme_les_quatre_temoins_et_aucun_chiffre_de_porte_en_dur():
    txt = _lire(_REF)
    for t in T.charger():
        assert t["nom"] in txt, f"temoin {t['nom']} absent du REF"
    # Regle du controleur : le REF ne recopie AUCUN compte rendu par une porte (ils se periment).
    interdits = [r"\b300 records\b", r"\b74 (records|citent)\b", r"\b18 chemins\b", r"\b232 records\b",
                 r"\b8 nus\b", r"\b29 scell", r"\b104/105\b"]
    for motif in interdits:
        assert not re.search(motif, txt), f"chiffre de porte recopie dans le REF : {motif}"


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
