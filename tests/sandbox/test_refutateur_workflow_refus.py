# -*- coding: utf-8 -*-
"""Le Réfutateur (.claude/workflows/refutateur.js) ne lit pas « aucun refus » comme un refus.

Mesuré le 2026-09-26 par agagi-40 (workflow wf_d1ad70bd, brouillon de P4.18) : le vérificateur a rendu
`"refus": "\\"\\""` — deux guillemets, pour « aucun refus » — et la ligne
`const refus = ((verif && verif.refus) || '').trim()` a lu cette chaîne NON VIDE comme un REFUS : la revue est sortie
NULLE alors que ses trois témoins à défaut étaient RETROUVÉS, le plancher mesuré et le juge calibré 5/5. Un nul de
TRANSPORT déguisé en nul de FOND, même famille qu'E4 (l'absence rendue comme une affirmation). Le correctif bfaea9c6
normalisait guillemets et espaces (`normaliserRefus`).

P2.133 (2026-09-26) — RÉCIDIVES le même soir, au synonyme suivant : « aucun » (run wf_c3134d3f-8dd), « (vide) Pas de
refus. Étape 1 : … » (run wf_f2e45bc7-b84), puis « (aucun refus) Roster conforme : … » (run wf_4c85e158-009). Une liste noire de mots recommence à chaque synonyme ; le correctif est
STRUCTUREL : la DÉCISION passe par le booléen `refuse` du schéma VERIFICATION, le MOTIF par un champ séparé `raison`, lu
seulement si `refuse` vaut true (`lireRefus`), et `normaliserRefus` disparaît. Un refus accompagné de résultats, ou un
`refuse` absent ou non booléen, est un état INCOHERENT NOMMÉ — jamais un nul de fond.

Les témoins exécutent le CODE RÉEL : `lireRefus` est extraite VERBATIM du script et lancée sous node — si quelqu'un la
retire ou la renomme, le témoin rougit ; si sa logique régresse, aussi. Le script entier n'est pas importé (c'est un
module de workflow : l'importer lancerait des agents).
"""
import json
import os
import re
import shutil
import subprocess

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCRIPT = os.path.join(_ROOT, ".claude", "workflows", "refutateur.js")


def _source():
    with open(_SCRIPT, encoding="utf-8") as fh:
        return fh.read()


def _lire_refus():
    m = re.search(r"^function lireRefus\(v\) \{\n.*?\n\}\n", _source(), re.S | re.M)
    assert m, "refutateur.js ne porte plus `function lireRefus(v)` : la décision de refus n'est plus structurée"
    return m.group(0)


def _sous_node(cas):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node absent : le code réel du workflow ne peut pas être exécuté ici")
    # Sous `node -` (script lu sur stdin), process.argv vaut [node, '-', <arg>] : le cas est en position 2. Le JSON
    # passe en ASCII (json.dumps échappe « néant ») : aucune page de code ne peut le mutiler en route.
    programme = _lire_refus() + "\nconst cas = JSON.parse(process.argv[2]);\n" \
        "process.stdout.write(JSON.stringify(cas.map(c => lireRefus(c))));\n"
    r = subprocess.run([node, "-", json.dumps(cas)], input=programme, capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


_RENDUS = {"a": {"statut": "RETROUVE"}}          # un témoin rendu : le vérificateur est allé au bout
_SANS_REFUS = {"etat": "SANS_REFUS", "raison": ""}


def test_deux_guillemets_ou_du_vide_ne_sont_PAS_un_refus():
    """Contre-exemple gelé de bfaea9c6 (la forme exacte du 2026-09-26, '""'), et ses voisines — sous le contrat
    STRUCTUREL : quand refuse vaut false, la raison n'est même pas lue."""
    formes = ['""', "''", "", "   ", '" "']
    assert _sous_node([{"refuse": False, "raison": t, "resultats": _RENDUS} for t in formes]) == \
        [_SANS_REFUS] * len(formes)


def test_P2_133_aucun_none_neant_ne_sont_JAMAIS_un_refus_quand_refuse_vaut_false():
    """LE CONTRE-EXEMPLE GELÉ de P2.133 : « aucun » (run wf_c3134d3f-8dd), « (vide) Pas de refus. Étape 1 : … » (run
    wf_f2e45bc7-b84) et « (aucun refus) Roster conforme : … » (run wf_4c85e158-009) — trois formes RÉELLES du même
    soir, relevées par agagi-40 —, puis les synonymes suivants."""
    formes = ("aucun", "(vide) Pas de refus. Étape 1 : roster conforme",
              "(aucun refus) Roster conforme : 3 défauts et 1 no-op", "none", "néant")
    assert _sous_node([{"refuse": False, "raison": t, "resultats": _RENDUS} for t in formes]) == \
        [_SANS_REFUS] * len(formes)


def test_P2_133_un_VRAI_refus_reste_un_refus_et_son_motif_est_lu():
    """Spécificité : le booléen ne désarme pas le refus — refuse vaut true, resultats vide, le motif est rendu ; un
    motif vide devient « sans raison », jamais un texte vide pris pour un motif."""
    assert _sous_node([{"refuse": True, "raison": "juge non calibre", "resultats": {}},
                       {"refuse": True, "raison": "   ", "resultats": {}}]) == \
        [{"etat": "REFUS", "raison": "juge non calibre"}, {"etat": "REFUS", "raison": "refus sans raison donnee"}]


def test_P2_133_un_refus_AVEC_resultats_ou_sans_booleen_est_INCOHERENT_jamais_un_nul_de_fond():
    """Un refus accompagné de résultats contredit le prompt (« refuse: true … resultats vide ») ; un refuse absent — la
    FORME EXACTE des runs du 2026-09-26, antérieure au champ, qui portait le texte dans `refus` — ou non booléen ne
    décide rien. Chacun est NOMMÉ INCOHERENT, avec sa raison, au lieu de devenir un nul de fond."""
    rendus = _sous_node([{"refuse": True, "raison": "aucun", "resultats": _RENDUS},
                         {"refus": "aucun", "resultats": _RENDUS},
                         {"refus": "(aucun refus) Roster conforme : 3 défauts et 1 no-op", "resultats": _RENDUS},
                         {"refuse": "false", "raison": "", "resultats": _RENDUS},
                         None])
    assert [r["etat"] for r in rendus] == ["INCOHERENT"] * 5
    assert "resultats VIDE" in rendus[0]["raison"] and "absent ou non booleen" in rendus[1]["raison"]


def test_P2_133_le_booleen_est_EXIGE_ANNONCE_et_LU_avant_tout_verdict_et_la_liste_noire_a_DISPARU():
    """La forme du correctif, lue dans le script : le schéma exige refuse et porte raison, le prompt figé dit ce qu'ils
    signifient, la décision passe par lireRefus, l'état INCOHERENT est rendu AVANT la branche qui déclare une revue
    NULLE — et normaliserRefus n'existe plus (la clause de fermeture de P2.133)."""
    src = _source()
    bloc = src.split("const VERIFICATION", 1)[1].split("\n}", 1)[0]
    assert "refuse: { type: 'boolean' }" in bloc and "raison: { type: 'string' }" in bloc
    assert "required: ['refuse'," in bloc and "refus: {" not in bloc
    assert "refuse est un BOOLEEN" in src and "REFUSE (refuse: true" in src
    assert "const lecture = lireRefus(verif)" in src
    assert "normaliserRefus" not in src, "la normalisation du texte libre (liste noire) est revenue"
    # « revue NULLE » apparaît déjà sur les branches de démarrage : l'ordre se juge contre la branche nulle de la
    # VÉRIFICATION elle-même (celle qui lit refus), pas contre la première occurrence du mot — un motif validé sur le
    # mauvais corpus, attrapé en calibrant ce témoin.
    assert src.index("if (lecture.etat === 'INCOHERENT')") < src.index("if (refus || !Object.keys(resultats).length")
