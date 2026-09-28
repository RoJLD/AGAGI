# -*- coding: utf-8 -*-
"""Frontmatter partagé : lecteur STRICT pour l'index (P2.87), extraction identique pour parse_record (porte 1)."""
import glob
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import frontmatter as F  # noqa: E402
from tools import consolidate_records as CR  # noqa: E402


def test_sans_bloc_rend_None():
    assert F.bloc_frontmatter("# Titre\n") is None
    assert F.lire_frontmatter("# Titre\n") is None
    assert F.lire_frontmatter("---\nid: X\nsans fermeture\n") is None     # bloc non fermé = pas de bloc


def test_bloc_vide_rend_un_dict_vide_et_la_position_de_fin():
    t = "---\n---\n# Titre\n"
    bloc, fin = F.bloc_frontmatter(t)
    assert bloc == "" and t[fin:] == "# Titre\n"
    assert F.lire_frontmatter(t) == {}


def test_bloc_lu_tel_quel():
    t = "---\nid: EDR-1\ntitle: \"Un titre : avec deux-points\"\ntests: [SDR-G1]\n---\ncorps\n"
    assert F.lire_frontmatter(t) == {"id": "EDR-1", "title": "Un titre : avec deux-points", "tests": ["SDR-G1"]}
    assert t[F.bloc_frontmatter(t)[1]:] == "corps\n"


@pytest.mark.parametrize("bloc, exc", [
    ("title: [a, b\n", yaml.YAMLError),                 # YAML cassé
    ("date: 2026-13-45\n", ValueError),                 # date impossible : PyYAML lève ValueError, pas YAMLError
    ("- a\n- b\n", TypeError),                          # racine non-dict
])
def test_le_lecteur_strict_LEVE(bloc, exc):
    with pytest.raises(exc):
        F.lire_frontmatter("---\n" + bloc + "---\n")


def test_normaliser_crlf():
    assert F.normaliser("a\r\nb\rc") == "a\nb\nc"


def _parse_record_d_origine(path):
    """Copie GELÉE de l'extraction de parse_record avant le 2026-09-26 : le témoin d'équivalence la compare au code
    courant sur les records RÉELS. Ne pas « corriger » cette copie : c'est la référence."""
    name = os.path.basename(path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    rec = CR._empty_record(os.path.relpath(path, CR._ROOT).replace(os.sep, "/"))
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            try:
                meta = yaml.safe_load(text[3:end]) or {}
            except yaml.YAMLError:
                meta = {}
            for k, v in meta.items():
                if k in CR._LIST_KEYS:
                    rec[k] = list(v) if v else []
                elif k in rec:
                    rec[k] = v
            if rec["id"]:
                rec["linked"] = True
                return rec
    m = CR._EDR_NAME.match(name)
    if m:
        rec["id"] = f"EDR-{int(m.group(1)):03d}{m.group(2)}"
        rec["type"] = "EDR"
        rec["title"] = name[m.end(2) + 1:-3].replace("_", " ")
        return rec
    return None


def _issue(fonction, chemin):
    """Valeur rendue, ou TYPE de l'exception levée : l'équivalence porte aussi sur les échecs."""
    try:
        return ("rendu", fonction(chemin))
    except Exception as exc:                                    # noqa: BLE001
        return ("leve", type(exc).__name__)


# Revue du pas 1 (I6) : les 335 records réels commencent tous par « ---\n » et se ferment proprement, donc le témoin
# ci-dessous ne voyait que ce chemin — trois mutants de bloc_frontmatter qui CHANGENT le comportement (ouverture
# stricte, fermeture stricte, bloc non fermé lu comme tout le texte) y survivaient. Chaque bord est ici un fichier.
_CAS_LIMITES = [
    "---\nid: EDR-900\ntitle: t\n---\ncorps\n",           # nominal
    "--- \nid: EDR-901\n---\n",                            # espace après l'ouverture
    "---id: EDR-902\n---\n",                               # rien entre l'ouverture et le YAML
    "---\nid: EDR-903\n----\n",                            # fermeture à quatre tirets
    "---\nid: EDR-904\n---",                               # fermeture en fin de fichier, sans saut de ligne
    "---\nid: EDR-905\nsans fermeture\n",                  # bloc non fermé, YAML invalide s'il était lu
    "---\nid: EDR-999\ntitle: jamais ferme\n",            # bloc non fermé, YAML VALIDE : lu, il changerait l'id
    "---\n---\n# corps\n",                                 # bloc vide
    "---\r\nid: EDR-906\r\n---\r\n",                       # CRLF
    "﻿---\nid: EDR-907\n---\n",                       # BOM devant l'ouverture
    "---\nid: EDR-908\n---\n---\nid: autre\n---\n",        # deux blocs : le premier seul
    "---\ntitle: [x\n---\n",                               # YAML cassé : repli sur le nom
    "---\n- a\n- b\n---\n",                                # racine non-dict
    "# pas de bloc\n",                                     # repli sur le nom
]


@pytest.mark.parametrize("i, texte", list(enumerate(_CAS_LIMITES)))
def test_parse_record_INCHANGE_sur_des_cas_LIMITES(tmp_path, i, texte):
    p = tmp_path / f"9{i:02d}_cas_limite.md"
    p.write_bytes(texte.encode("utf-8"))                    # octets exacts : write_text traduirait \n sous Windows
    assert _issue(CR.parse_record, str(p)) == _issue(_parse_record_d_origine, str(p)), repr(texte)


def test_parse_record_INCHANGE_sur_les_records_reels(capsys):
    """Porte 1 : l'extraction du bloc a changé de module, pas de comportement. Tous les records réels."""
    chemins = sorted(p for d in ("EDR", "ADR", "REF", "SDR")
                     for p in glob.glob(os.path.join(CR._ROOT, "docs", d, "*.md")))
    assert len(chemins) > 300, "contrôle : le motif doit voir les records réels"
    for p in chemins:
        assert CR.parse_record(p) == _parse_record_d_origine(p), p
