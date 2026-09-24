"""P2.108 — CONTRE-EXEMPLES GELÉS de la garde de copie des crochets.

Ce que ces cas protègent, et pourquoi ils existent avant le premier vert :

  (1) LE FAUX POSITIF QUI TUE LA GARDE. `core.autocrlf=true` sur cette machine : la copie déployée
      est en CRLF, le blob de git en LF, et un `diff` brut rend 46 lignes d'écart sur deux fichiers
      IDENTIQUES. Sans normalisation, ce cliquet crierait à CHAQUE commit de CHAQUE session sous
      Windows — et une garde qui crie toujours est une garde qu'on désarme. C'est le cas le plus
      important du fichier.
  (2) LE SENS GRAVE. Un worktree a écrit dans le crochet COMMUN une porte qui n'existe dans aucun
      commit (mesuré par la session PM). `core.hooksPath` valant un chemin ABSOLU, tous les
      worktrees exécutent ce fichier : du code non relu bloquait chaque session. Ce sens-là REFUSE.
  (3) LE SENS BÉNIN, qui ne doit PAS refuser. Une copie en retard n'est le crime de personne : c'est
      un `cp` oublié. Le distinguer de (2) demande de savoir si le contenu déployé a DÉJÀ EXISTÉ
      dans un commit — c'est toute la différence entre « recopie le fichier » et « quelqu'un a
      écrit du code que personne n'a lu ».
  (4) L'ABSENCE NE DEVIENT PAS UNE AFFIRMATION (porte 14). Sans contenu versionné NI contenu
      déployé, l'instrument rend `None` — « je ne sais pas » — jamais CONFORME.

⚠️ CE QUE CETTE GARDE NE PEUT PAS VOIR, et le cas qui le grave : elle est lancée PAR le pre-commit
déployé. Si celui-ci est absent, elle ne tourne pas du tout. L'absence du pre-commit est
structurellement indétectable de l'intérieur ; celle de tout AUTRE crochet ne l'est pas, et c'est
elle qui compte (un `commit-msg` manquant rouvre le trou de la fusion).

L'injection (`livre=`, `deploye=`, `anciennes=`) rend ces cas GRATUITS : aucun dépôt, aucun git.
"""
import json
import os
import subprocess
import sys

import pytest

_RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _RACINE not in sys.path:
    sys.path.insert(0, _RACINE)

from tools import check_hook_deployment as G  # noqa: E402

_CORPS = b"#!/bin/sh\necho porte 1\nexit 0\n"
_ANCIEN = b"#!/bin/sh\nexit 0\n"
_ETRANGER = b"#!/bin/sh\necho porte inventee par personne\nexit 1\n"


def _etat(livre, deploye, anciennes=frozenset()):
    return G.etat_un_crochet("pre-commit", None, livre=livre, deploye=deploye,
                             anciennes=set(anciennes))


# --------------------------------------------------------------------------------------------------
# 1. LE FAUX POSITIF QUI TUERAIT LA GARDE — deux fichiers IDENTIQUES à la fin de ligne près.
# --------------------------------------------------------------------------------------------------

def test_CRLF_contre_LF_est_CONFORME_sinon_la_garde_crie_a_chaque_commit():
    crlf = _CORPS.replace(b"\n", b"\r\n")
    assert crlf != _CORPS, "le cas ne mesure rien si les deux octets sont déjà égaux"
    assert _etat(_CORPS, crlf)["etat"] == G.CONFORME, (
        "la copie déployée en CRLF est vue DIVERGENTE de son blob en LF : sous Windows cette garde "
        "refuserait tous les commits de toutes les sessions, et serait désarmée le jour même")
    assert _etat(crlf, _CORPS)["etat"] == G.CONFORME, "la normalisation doit valoir dans les DEUX sens"


def test_une_ligne_vide_finale_ne_fait_pas_diverger():
    assert _etat(_CORPS, _CORPS + b"\n\n")["etat"] == G.CONFORME, (
        "une queue de fichier ne change pas le code exécuté ; la traiter comme une divergence "
        "rendrait la garde bruyante pour rien")


def test_un_CARACTERE_de_difference_fait_diverger():
    """CONTRÔLE POSITIF de la normalisation : elle doit tolérer les fins de ligne, PAS le contenu.
    Sans ce cas, une normalisation trop gourmande (tout l'espace, toute la casse) passerait les
    trois cas ci-dessus en restant aveugle à une vraie modification."""
    modifie = _CORPS.replace(b"porte 1", b"porte 2")
    assert _etat(_CORPS, modifie)["etat"] != G.CONFORME, (
        "une vraie modification du corps passe pour conforme : la normalisation efface le signal")


# --------------------------------------------------------------------------------------------------
# 2. LES DEUX SENS DE LA DIVERGENCE — et un seul refuse.
# --------------------------------------------------------------------------------------------------

def test_une_copie_EN_RETARD_est_PERIME_et_ne_bloque_pas():
    e = _etat(_CORPS, _ANCIEN, anciennes={G.norme(_ANCIEN)})
    assert e["etat"] == G.PERIME, e
    assert G.PERIME not in G._BLOQUANTS, (
        "bloquer sur un `cp` oublié arrêterait toute la flotte sur un fichier partagé, et le commit "
        "qui MET À JOUR un crochet est dans cet état par construction : il ne pourrait plus passer")


def test_une_copie_JAMAIS_COMMITTEE_est_INCONNU_et_BLOQUE():
    e = _etat(_CORPS, _ETRANGER, anciennes={G.norme(_ANCIEN)})
    assert e["etat"] == G.INCONNU, e
    assert G.INCONNU in G._BLOQUANTS, (
        "c'est l'occurrence RÉELLE mesurée par le PM : du code que personne n'a relu tournait chez "
        "toutes les sessions. Si elle ne bloque pas, cette garde ne sert à rien")


def test_PERIME_et_INCONNU_ne_different_QUE_par_l_historique():
    """La seule chose qui sépare « recopie le fichier » de « quelqu'un a écrit du code non relu »
    est de savoir si le contenu déployé a DÉJÀ EXISTÉ. Ce cas le prouve : mêmes octets, deux
    verdicts, selon que l'historique le contient ou non. Si `revisions_connues` rendait tout, ou
    rendait vide, l'un des deux diagnostics deviendrait inatteignable."""
    octets = _ANCIEN
    avec = _etat(_CORPS, octets, anciennes={G.norme(octets)})["etat"]
    sans = _etat(_CORPS, octets, anciennes=set())["etat"]
    assert (avec, sans) == (G.PERIME, G.INCONNU), (avec, sans)


def test_un_crochet_versionne_NON_DEPLOYE_est_ABSENT_et_BLOQUE():
    e = _etat(_CORPS, None)
    assert e["etat"] == G.ABSENT and G.ABSENT in G._BLOQUANTS, e


def test_un_crochet_DEPLOYE_SANS_SOURCE_est_ORPHELIN_et_BLOQUE():
    e = _etat(None, _ETRANGER)
    assert e["etat"] == G.ORPHELIN and G.ORPHELIN in G._BLOQUANTS, e


# --------------------------------------------------------------------------------------------------
# 3. L'ABSENCE NE DEVIENT PAS UNE AFFIRMATION (porte 14, biais dominant du dépôt).
# --------------------------------------------------------------------------------------------------

def test_ni_versionne_ni_deploye_rend_NONE_jamais_CONFORME():
    assert _etat(None, None) is None, (
        "sans rien à comparer, l'instrument doit dire « je ne sais pas ». Rendre CONFORME ferait "
        "d'une absence une affirmation de fond — la forme (a) du biais mesuré dans ce dépôt")
    assert G.norme(None) is None, "une absence normalisée reste une absence, pas un contenu vide"


def test_un_perimetre_VIDE_refuse_au_lieu_de_passer(tmp_path, monkeypatch):
    """Aucun crochet versionné = l'inventaire est cassé ou le dépôt a perdu ses crochets. Les deux
    se corrigent ; aucun ne se tait. Un `exit 0` ici serait un vert qui ne mesure rien."""
    monkeypatch.setattr(G, "crochets_versionnes", lambda: [])
    monkeypatch.setattr(G, "repertoire_deploye", lambda: str(tmp_path))
    assert G.main([]) == 1


def test_hors_depot_la_garde_se_TAIT_et_le_DIT(monkeypatch, capsys):
    """Les cliquets tournent aussi sur un EXPORT temporaire (technique de commit par index de ce
    dépôt), où il n'y a pas de `.git`. La garde ne peut rien juger là : elle sort 0 en l'ÉCRIVANT,
    plutôt que d'inventer un verdict dans un sens ou dans l'autre."""
    monkeypatch.setattr(G, "repertoire_deploye", lambda: None)
    assert G.main([]) == 0
    assert "rien à juger" in capsys.readouterr().out


# --------------------------------------------------------------------------------------------------
# 4. MESURE SUR LE DÉPÔT RÉEL — la garde doit rendre un état DÉFINI, et le vert doit être expliqué.
# --------------------------------------------------------------------------------------------------

def test_le_depot_reel_rend_un_etat_defini_pour_chaque_crochet():
    dossier = G.repertoire_deploye()
    if dossier is None:
        pytest.skip("hors dépôt git : rien à mesurer")
    mesures = G.etats(dossier)
    assert mesures, "le dépôt versionne des crochets : un inventaire vide serait un défaut du scan"
    for nom, e in mesures.items():
        assert e["etat"] in (G.CONFORME, G.PERIME, G.INCONNU, G.ABSENT, G.ORPHELIN), (nom, e)
        assert e["detail"], f"{nom} : un état sans motif n'est pas actionnable"


def test_la_baseline_ne_gele_que_des_etats_BLOQUANTS():
    """Une baseline qui tolère CONFORME ou PERIME ne gèlerait rien : elle donnerait l'illusion
    d'une dette suivie. Seuls les trois états refusés peuvent y figurer."""
    for nom, etat in G.baseline().items():
        assert etat in G._BLOQUANTS, (
            f"{nom} : geler « {etat} » n'a aucun effet, cet état ne bloque pas. Une baseline qui "
            "contient des états non bloquants se lit comme une dette suivie alors qu'elle est vide")


def test_la_baseline_est_du_JSON_d_objet_et_se_relit():
    if not os.path.isfile(G._BASELINE):
        pytest.skip("aucune baseline : rien à relire")
    with open(G._BASELINE, encoding="utf-8") as fh:
        brut = json.load(fh)
    assert isinstance(brut, dict), "la baseline est un objet {nom: état}"


# --------------------------------------------------------------------------------------------------
# 5. GARDE DE LA GARDE — le cliquet est-il BRANCHÉ, et son chiffre publié se recompute-t-il ?
# --------------------------------------------------------------------------------------------------

def test_le_cliquet_est_branche_sur_le_hook():
    with open(os.path.join(_RACINE, "tools", "hooks", "pre-commit"), encoding="utf-8") as fh:
        hook = fh.read()
    assert "check_hook_deployment.py" in hook, (
        "un cliquet non branché est une règle documentée sans application exécutable (classe E10) : "
        "c'est la faute que ce dépôt a vue récidiver plusieurs fois")


def test_le_nombre_de_portes_annonce_dans_CLAUDE_md_se_RECOMPUTE():
    """Le contrôle est celui de la session PM, repris tel quel : compter les cliquets LANCÉS par le
    hook et le confronter à la balise. ⚠️ Il calcule les deux sens — le test anti-dérive existant ne
    voyait que « hook − déclarées », donc une porte PERDUE à la fusion restait invisible."""
    import re
    with open(os.path.join(_RACINE, "tools", "hooks", "pre-commit"), encoding="utf-8") as fh:
        hook = fh.read()
    lances = set(re.findall(r"python tools/(check_[a-z0-9_]+)\.py", hook))
    with open(os.path.join(_RACINE, "CLAUDE.md"), encoding="utf-8") as fh:
        claude = fh.read()
    m = re.search(r"count:portes_hook=(\d+)", claude)
    assert m, "CLAUDE.md doit porter la balise count:portes_hook"
    assert len(lances) == int(m.group(1)), (
        f"CLAUDE.md annonce {m.group(1)} gardes, le hook en lance {len(lances)} : "
        f"{sorted(lances)}. Recompute : "
        "grep -oE 'python tools/check_[a-z0-9_]+\\.py' tools/hooks/pre-commit | sort -u | wc -l")


def test_git_hash_object_n_est_PAS_utilise_pour_comparer():
    """Pourquoi ce cas existe : comparer par `git hash-object` serait plus court et FAUX ici — le
    hash porte les octets bruts, donc CRLF != LF, et on retomberait exactement sur le faux positif
    du cas 1. La comparaison doit passer par `norme`."""
    with open(os.path.join(_RACINE, "tools", "check_hook_deployment.py"), encoding="utf-8") as fh:
        src = fh.read()
    corps = src.split("def etat_un_crochet", 1)[1]
    assert "hash-object" not in corps, (
        "la comparaison est revenue à un hash d'octets bruts : sous `core.autocrlf=true` elle "
        "déclarerait divergents deux fichiers identiques")


def test_le_cliquet_lance_depuis_un_AUTRE_repertoire_juge_le_MEME_depot():
    """Le hook tourne avec un cwd arbitraire (et, dans la technique de commit par index de ce dépôt,
    depuis un export temporaire). Si le cliquet résolvait ses chemins depuis le cwd, il jugerait un
    autre dépôt — ou aucun — en silence."""
    r = subprocess.run([sys.executable, os.path.join(_RACINE, "tools", "check_hook_deployment.py")],
                       capture_output=True, cwd=os.path.dirname(_RACINE),
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    sortie = (r.stdout + r.stderr).decode("utf-8", "replace")
    assert "crochets :" in sortie, f"le cliquet n'a rien jugé depuis un autre cwd :\n{sortie}"
    assert "rien à juger" not in sortie, (
        f"lancé depuis le parent du dépôt, le cliquet se croit hors dépôt :\n{sortie}")
