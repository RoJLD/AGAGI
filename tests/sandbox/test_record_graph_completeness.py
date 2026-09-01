"""Contre-exemples GELÉS de la COMPLÉTUDE du graphe de records — 122 arêtes étaient invisibles.

Mesuré le 2026-09-01. `parse_record` jette EN SILENCE toute clé de frontmatter absente de `_LIST_KEYS`
(branche `elif k in rec`). Conséquence : **122 arêtes déclarées n'entraient pas dans le graphe**, dont
`retracted_by`, `corrects`, `corrected_by`, `supersedes_mechanism_of` — c'est-à-dire **toutes les arêtes
de rétractation**. Un graphe de records qui ne lit pas ses rétractations ne peut pas signaler une
conclusion périmée, ce pour quoi il existe.

Plus embarrassant : `adopts` (77 occurrences) était ignoré alors que **CLAUDE.md prescrit explicitement**
d'ancrer un record par « gate: / tests: / adopts: ». L'outil ne connaissait pas une clé que le protocole
impose.

⚠️ Ce que le correctif NE fait PAS, mesuré dans les deux sens avant de l'écrire : il ne résorbe **aucun**
orphelin (0 sur 39). L'hypothèse « la dette d'orphelins est un artefact du parseur » était plausible et
FAUSSE — elle est notée ici pour qu'on ne la re-formule pas.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tools.check_record_links as C  # noqa: E402
from tools.consolidate_records import _LIST_KEYS, build_graph, scan_records  # noqa: E402

_RETRACTION = ("corrects", "corrected_by", "retracted_by", "supersedes_mechanism_of")


def _record(tmp_path, frontmatter):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True, exist_ok=True)
    (d / "999_Faux.md").write_text(f"---\n{frontmatter}\n---\n\n# corps\n", encoding="utf-8")
    return str(tmp_path)


def test_an_unread_edge_key_is_DETECTED(tmp_path):
    """⚠️ LE test. Une clé qui DÉCLARE une arête mais que le parseur ne lit pas doit être signalée —
    c'est le silence exact qui a coûté 122 arêtes."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ncle_inventee: [EDR-112]")
    non_lues = C.edge_key_silences(root)["non_lues"]
    assert any(k == "cle_inventee" for _, k in non_lues), (
        f"une clé d'arête non lue doit être détectée, or : {non_lues}")


def test_a_scalar_where_a_list_is_expected_is_DETECTED(tmp_path):
    """⚠️ La forme EXACTE trouvée sur EDR-164 à la seconde où les clés manquantes ont été branchées :
    `supersedes_mechanism_of: EDR-162` sans crochets. Le code itère alors la CHAÎNE et produit une arête
    PAR CARACTÈRE ('E','D','R','-','1','6','2') — 7 arêtes fantômes vers des nœuds inexistants."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\nsupersedes_mechanism_of: EDR-162")
    scal = C.edge_key_silences(root)["scalaires"]
    assert any(k == "supersedes_mechanism_of" for _, k, _ in scal), (
        f"une valeur scalaire là où une liste est attendue doit être détectée, or : {scal}")


def test_a_well_formed_record_triggers_NOTHING(tmp_path):
    """⚠️ SPÉCIFICITÉ — sans ce test, un détecteur qui signale TOUT passerait les deux précédents tout
    en étant inutilisable."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\nadopts: [EDR-112]\ntests: [SDR-G0]")
    r = C.edge_key_silences(root)
    assert r["non_lues"] == [] and r["scalaires"] == [], f"record bien formé signalé à tort : {r}"


def test_the_records_own_id_is_not_mistaken_for_an_edge(tmp_path):
    """DÉFAUT MESURÉ en écrivant le détecteur : `id: SDR-G0` a la FORME d'un identifiant de record, donc
    239 faux positifs. Les champs scalaires sont exclus via le SCHÉMA DÉCLARÉ (`_empty_record`) et non
    une liste écrite à la main, qui se serait désynchronisée à la première évolution du schéma."""
    root = _record(tmp_path, "id: EDR-999\ntype: EDR\ngate: G0\nverdict: EXIGE")
    assert C.edge_key_silences(root)["non_lues"] == []


def test_every_RETRACTION_edge_kind_stays_readable():
    """⚠️ La régression la plus grave possible : si quelqu'un rétrécit `_LIST_KEYS`, les rétractations
    redeviennent invisibles SANS que rien n'échoue. Ce test l'attrape."""
    for k in _RETRACTION:
        assert k in _LIST_KEYS, (
            f"« {k} » n'est plus lue : le graphe ne peut plus représenter une rétractation")


def test_the_real_graph_is_complete_and_coherent():
    """État gelé du dépôt : aucune arête déclarée n'est ignorée, aucune valeur mal formée, et le graphe
    porte bien ses arêtes de rétractation."""
    r = C.edge_key_silences()
    assert r["non_lues"] == [], f"arête(s) déclarée(s) mais jamais lue(s) : {r['non_lues']}"
    assert r["scalaires"] == [], f"valeur(s) scalaire(s) là où une liste est attendue : {r['scalaires']}"
    rels = {e["rel"] for e in build_graph(scan_records(C._ROOT))["edges"]}
    assert "RETRACTE_PAR" in rels and "CORRIGE" in rels, (
        f"le graphe ne porte plus d'arête de rétractation : {sorted(rels)}")
