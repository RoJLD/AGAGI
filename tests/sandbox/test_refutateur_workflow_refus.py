# -*- coding: utf-8 -*-
"""Le Réfutateur (.claude/workflows/refutateur.js) ne lit pas « aucun refus » comme un refus.

Mesuré le 2026-09-26 par agagi-40 (workflow wf_d1ad70bd, brouillon de P4.18) : le vérificateur a rendu
`"refus": "\\"\\""` — deux guillemets, pour « aucun refus » — et la ligne
`const refus = ((verif && verif.refus) || '').trim()` a lu cette chaîne NON VIDE comme un REFUS : la revue est sortie
NULLE alors que ses trois témoins à défaut étaient RETROUVÉS, le plancher mesuré et le juge calibré 5/5. Un nul de
TRANSPORT déguisé en nul de FOND, même famille qu'E4 (l'absence rendue comme une affirmation).

Le témoin exécute le CODE RÉEL : la fonction `normaliserRefus` est extraite VERBATIM du script et lancée sous node —
si quelqu'un la retire ou la renomme, le témoin rougit ; si sa logique régresse, aussi. Le script entier n'est pas
importé (c'est un module de workflow : l'importer lancerait des agents).
"""
import json
import os
import re
import shutil
import subprocess

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCRIPT = os.path.join(_ROOT, ".claude", "workflows", "refutateur.js")


def _fonction():
    with open(_SCRIPT, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r"^function normaliserRefus\(x\) \{\n.*?\n\}\n", src, re.S | re.M)
    assert m, "refutateur.js ne porte plus `function normaliserRefus(x)` : le refus n'est plus normalisé"
    assert "const refus = normaliserRefus(verif && verif.refus)" in src, "la fonction existe mais n'est plus APPELÉE"
    return m.group(0)


def _sous_node(cas):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node absent : le code réel du workflow ne peut pas être exécuté ici")
    # Sous `node -` (script lu sur stdin), process.argv vaut [node, '-', <arg>] : le cas est en position 2.
    programme = _fonction() + "\nconst cas = JSON.parse(process.argv[2]);\n" \
        "process.stdout.write(JSON.stringify(cas.map(c => normaliserRefus(c))));\n"
    r = subprocess.run([node, "-", json.dumps(cas)], input=programme, capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_deux_guillemets_ou_du_vide_ne_sont_PAS_un_refus():
    """Contre-exemple gelé : la forme exacte du 2026-09-26 ('""'), et ses voisines."""
    assert _sous_node(['""', "''", "", "   ", '" "', None]) == ["", "", "", "", "", ""]


def test_un_vrai_refus_RESTE_un_refus():
    assert _sous_node(["juge non calibre", '  roster incomplet  ', '"vrai refus"']) == \
        ["juge non calibre", "roster incomplet", '"vrai refus"']
