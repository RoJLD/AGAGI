# -*- coding: utf-8 -*-
"""Les scripts de workflow (.claude/workflows/*.js) ne portent AUCUN caractère invisible.

Mesuré le 2026-09-26 par agagi-40 en lançant le Réfutateur : `.claude/workflows/refutateur.js` portait 6 sélecteurs de
variante U+FE0F (invisibles, collés après chaque « ⚠ ») et l'outil Workflow REFUSAIT le script — « script contains
control characters that would be hidden in the approval dialog » — par nom comme par chemin. Le Réfutateur, rôle
instancié de ROLES.md dont les prompts sont FIGÉS, était donc inlançable pour TOUTE session sur cette version du
harnais, et rien ne le disait : un fichier « figé » peut périmer par une contrainte du harnais qu'il ne connaît pas.

Le témoin : chaque script de workflow est lu octet par octet, et tout point de code de la liste ci-dessous (sélecteurs
de variante, largeurs nulles, BOM, trait d'union conditionnel, catégories Cc/Cf hors \\n \\r \\t) est nommé avec sa
position. Il ROUGIT sur une copie qui en porte un seul (contre-exemple ci-dessous) et passe sur le dépôt.
"""
import glob
import os
import unicodedata

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_WORKFLOWS = os.path.join(_ROOT, ".claude", "workflows")

# Points de code invisibles qui ne sont ni Cc ni Cf mais que le harnais cache dans son dialogue d'approbation.
_INVISIBLES = {0xFE0E, 0xFE0F, 0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x034F}


def invisibles(texte):
    """-> [(position, 'U+XXXX')] des caractères invisibles ; vide si le texte est sain.

    Le retour chariot est REFUSÉ lui aussi : l'outil Workflow lit les octets du disque et rejette tout caractère de
    contrôle, donc une extraction CRLF (core.autocrlf=true sous Windows) rend le script inlançable même quand le blob
    est sain — mesuré le 2026-09-26 après c0274ea9 (275 \\r). D'où `.gitattributes` (eol=lf) et cette lecture du DISQUE."""
    return [(i, f"U+{ord(c):04X}") for i, c in enumerate(texte)
            if ord(c) in _INVISIBLES or (unicodedata.category(c) in ("Cc", "Cf") and c not in "\n\t")]


def _scripts():
    return sorted(glob.glob(os.path.join(_WORKFLOWS, "*.js")))


def test_il_existe_au_moins_un_script_de_workflow_a_examiner():
    assert _scripts(), f"aucun script dans {_WORKFLOWS} : ce témoin ne mesurerait rien"


@pytest.mark.parametrize("chemin", _scripts(), ids=lambda p: os.path.basename(p))
def test_aucun_script_de_workflow_ne_porte_de_caractere_invisible(chemin):
    with open(chemin, "rb") as fh:                      # OCTETS du disque : c'est ce que l'outil Workflow lit
        texte = fh.read().decode("utf-8")               # (pas de traduction des fins de ligne : un \r reste un \r)
    trouves = invisibles(texte)
    assert not trouves, (
        f"{os.path.relpath(chemin, _ROOT)} porte {len(trouves)} caractère(s) invisible(s) {sorted(set(t[1] for t in trouves))} "
        f"(premières positions {[t[0] for t in trouves[:4]]}) : l'outil Workflow REFUSE un tel script, le rôle est inlançable"
    )


def test_le_temoin_ROUGIT_sur_un_selecteur_de_variante_seul():
    """Contre-exemple gelé : la forme exacte trouvée le 2026-09-26 (« ⚠ » suivi de U+FE0F) est détectée, et nommée."""
    sain = "// ⚠ attention\nconst x = 1;\n"
    assert invisibles(sain) == []
    malade = "// ⚠️ attention\nconst x = 1;\n"
    assert invisibles(malade) == [(4, "U+FE0F")]
    assert invisibles("a​b") == [(1, "U+200B")]
    assert invisibles("﻿debut") == [(0, "U+FEFF")]
    # Une extraction CRLF est refusée elle aussi (la forme du 2026-09-26 après c0274ea9) ; la tabulation passe.
    assert invisibles("ligne\r\nsuite\n") == [(5, "U+000D")]
    assert invisibles("a\tb\n") == []
