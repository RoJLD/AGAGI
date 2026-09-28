# -*- coding: utf-8 -*-
"""Le smoke docker de la CI, étape de l'index (P2.87), confronté à des réponses CONNUES : un contrôle qui ne peut pas
échouer ne prouve rien (CLAUDE.md, question 1 ; classe E1). Revue du pas 2 (I1) : il restait vert avec un bloc
`artefacts` refusé, à null, ou vide. Les deux `python3 -c` sont EXTRAITS du workflow tel qu'il est commité — jamais
recopiés ici — et lancés sur des fichiers écrits sous tmp_path. EXEMPTION DÉCLARÉE de la garde de bail : aucun monde."""
import json
import os
import re
import subprocess
import sys

import pytest

_LEASE_GUARD_EXEMPT = True
_CI = os.path.join(os.path.dirname(__file__), "..", "..", ".github", "workflows", "ci.yml")


def _controle(fichier):
    """Le code du `python3 -c` qui lit `fichier` dans l'étape smoke du workflow."""
    for ligne in open(_CI, encoding="utf-8").read().splitlines():
        if f"open('{fichier}'" in ligne:
            m = re.search(r'python3 -c "(.*)" \|\| \{', ligne)
            assert m, ligne[:120]
            return m.group(1)
    raise AssertionError(f"aucun contrôle ne lit {fichier} dans {_CI}")


def _rc(tmp_path, fichier, doc):
    (tmp_path / fichier).write_text(json.dumps(doc), encoding="utf-8")
    return subprocess.run([sys.executable, "-c", _controle(fichier)], cwd=tmp_path, capture_output=True,
                          text=True, encoding="utf-8").returncode


_SAIN = {"schema": "index_v1", "familles": [{"nom": "record", "indexes": 304, "illisibles": []}],
         "artefacts": [{"famille": "record", "chemin": "docs/EDR/1.md"}], "hors_familles": None}
_ABSENT = {**_SAIN, "dates": None,
           "aveugle": ["dates : DATES_GIT.json introuvable à /app/data/pm/DATES_GIT.json -- écrivain jamais passé"]}
_PRESENT = {**_SAIN, "aveugle": [], "dates": {"generated_at": 1.0, "age_s": 12.0, "head": "abc", "historique": "tronque"}}
_REFUS_ARTEFACTS = {"artefacts": None,
                    "aveugle_en_plus": ["artefacts : bloc refusé par le modèle de la route (x) -- servi à null"]}


def _avec(base, **k):
    doc = json.loads(json.dumps(base))
    en_plus = k.pop("aveugle_en_plus", [])
    doc.update(k)
    doc["aveugle"] = doc.get("aveugle", []) + en_plus
    return doc


@pytest.mark.parametrize("fichier, doc, attendu", [
    ("index_absent.json", _ABSENT, 0),
    ("index_absent.json", _avec(_ABSENT, **_REFUS_ARTEFACTS), 1),
    ("index_absent.json", _avec(_ABSENT, artefacts=[]), 1),
    ("index_absent.json", _avec(_ABSENT, aveugle_en_plus=["index: RuntimeError: x"]), 1),
    ("index_present.json", _PRESENT, 0),
    ("index_present.json", _avec(_PRESENT, **_REFUS_ARTEFACTS), 1),
    ("index_present.json", _avec(_PRESENT, familles=None,
                                 aveugle_en_plus=["familles : bloc refusé par le modèle de la route (x)"]), 1),
    ("index_present.json", _avec(_PRESENT, dates=None), 1),
])
def test_le_smoke_de_l_index_produit_les_DEUX_issues(tmp_path, fichier, doc, attendu):
    assert _rc(tmp_path, fichier, doc) == attendu
