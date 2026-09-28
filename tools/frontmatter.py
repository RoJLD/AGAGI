# -*- coding: utf-8 -*-
"""Frontmatter YAML en tête d'un `.md` — l'extraction partagée par `tools/consolidate_records.py` (porte 1) et
`tools/pm/index_artefacts.py` (P2.87, spec 2026-09-26).

Import de PyYAML PARESSEUX : un processus sans PyYAML sait encore dire qu'un fichier N'A PAS de frontmatter, et
seul un fichier qui EN A devient illisible (« pyyaml_absent »). `lire_frontmatter` est STRICT — il lève au lieu de
tolérer, parce que l'index doit NOMMER un frontmatter cassé ; `parse_record` garde, lui, sa propre tolérance.
"""


def normaliser(texte):
    return texte.replace("\r\n", "\n").replace("\r", "\n")


def bloc_frontmatter(texte):
    """`(bloc YAML brut, position juste après la ligne fermante)`, ou `None` sans bloc.

    Règle de `parse_record` depuis sa création : le texte COMMENCE par `---` et un `\\n---` le ferme. Le texte doit
    être normalisé en `\\n` (`normaliser`)."""
    if not texte.startswith("---"):
        return None
    fin = texte.find("\n---", 3)
    if fin == -1:
        return None
    apres = texte.find("\n", fin + 4)
    return texte[3:fin], (len(texte) if apres == -1 else apres + 1)


def lire_frontmatter(texte):
    """`dict` (vide pour un bloc vide) ou `None` sans bloc. LÈVE : `yaml.YAMLError` (YAML invalide), `ValueError`
    (date impossible, ex. `2026-13-45`), `TypeError` (racine non-dict), `ImportError` (PyYAML absent)."""
    b = bloc_frontmatter(texte)
    if b is None:
        return None
    import yaml
    meta = yaml.safe_load(b[0])
    if meta is None:
        return {}
    if not isinstance(meta, dict):
        raise TypeError(f"frontmatter de type {type(meta).__name__}")
    return meta
