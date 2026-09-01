"""Calibration de la PORTE du graphe AGI-Taxonomy — `tools/check_agi_taxonomy.validate_edge`.

Contre-exemple GELÉ (revue adversariale du 2026-09-01). L'ancienne règle (`check_agi_taxonomy.py`
avant durcissement) acceptait `functional_aliasing == 'pass'` SEUL et n'exigeait `specificity_control`
que dans la branche `'n/a'`. Une 3e arête aurait donc été gravée à un standard de preuve STRICTEMENT
INFÉRIEUR à celui des deux arêtes déjà gravées :

  - Le bras PRINCIPAL d'une arête de demande est arithmétiquement FORCÉ : une fois l'entrée nécessaire
    ablatée, l'agent ne peut pas dépasser 1/K, donc `X_DEMANDED` tombe mécaniquement dès que le bras
    intact est vivant. Ce bras ne peut PAS produire l'issue négative -> il ne prouve rien (motif du
    pré-vol : « un contrôle qui ne peut pas échouer ne prouve rien »).
  - Le seul bras dont l'issue négative est RÉELLEMENT atteignable est le contrôle de demande
    (`specificity_control` : NO-COORD pour language->perception, PRESENT pour memory->perception —
    même ablation, information redondante disponible ailleurs). Preuve directe que l'alternative
    existe : l'itération 1 de MEM-PERCEPTION a ÉCHOUÉ ce contrôle (ratio 4.329) et a dû être corrigée.

Ces tests sont PUREMENT NUMÉRIQUES (aucun entraînement, aucun monde, aucun bail `kuzu`) : ils testent
la LOGIQUE de la porte sur des arêtes synthétiques, plus la non-régression sur les arêtes RÉELLES
lues depuis `data/agi_taxonomy/demands.json`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.check_agi_taxonomy import validate_edge, validate_graph  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA = os.path.join(_ROOT, "data", "agi_taxonomy")
_IDS = {"perception", "memory", "language", "generalization"}
# Record réel : `validate_edge` vérifie son existence sur disque, une preuve fictive doit donc pointer
# un fichier qui existe pour que le test isole bien la règle visée (et pas la règle `record`).
_REAL_RECORD = "docs/EDR/S2-001_Within_Subject_Perception_Ablation_Is_The_Sound_Demand_Marker.md"


def _load(name):
    with open(os.path.join(_DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def _edge(**evidence_over):
    """Arête synthétique conforme sur TOUS les autres axes (verdict, n, record, ids). Chaque test
    n'écrase que le champ dont il éprouve la règle."""
    ev = {"ablation_verdict": "X_DEMANDED", "ratio": 2.4, "n": 12, "record": _REAL_RECORD}
    ev.update(evidence_over)
    return {"capability": "memory", "prerequisite": "perception", "strength": "hard", "evidence": ev}


# --------------------------------------------------------------------------------------------------
# 1. LE CONTRE-EXEMPLE GELÉ — le trou réel de la porte
# --------------------------------------------------------------------------------------------------

def test_gate_REFUSES_aliasing_pass_without_specificity_control():
    """⚠️ Le cas qui compte. C'est EXACTEMENT la configuration que l'ancienne règle acceptait
    (`check_agi_taxonomy.py:64-72` avant durcissement : branche `fa == 'pass'` -> `pass  # ok`), et
    donc exactement le standard inférieur qui aurait été appliqué à la 3e arête : garde d'aliasing
    verte, AUCUN contrôle de demande. Sans `specificity_control`, l'arête ne repose que sur son bras
    arithmétiquement forcé — une affirmation invérifiable, pas une mesure."""
    v = validate_edge(_edge(functional_aliasing="pass"), _IDS)
    assert any("specificity_control" in x for x in v), (
        "l'arête sans contrôle de demande DOIT être refusée, même avec functional_aliasing='pass'")


def test_gate_REFUSES_aliasing_pass_with_FAILED_specificity_control():
    """Variante mesurée du même trou : le contrôle a été LANCÉ et a ÉCHOUÉ (cas réel de l'itération 1
    de MEM-PERCEPTION). Un échec explicite ne doit pas être moins bloquant qu'une absence."""
    v = validate_edge(_edge(functional_aliasing="pass", specificity_control="fail"), _IDS)
    assert any("specificity_control" in x for x in v)


def test_gate_accepts_aliasing_pass_WITH_specificity_control():
    """Contrôle positif de la règle précédente : la porte n'est pas devenue un refus systématique."""
    assert validate_edge(_edge(functional_aliasing="pass", specificity_control="pass"), _IDS) == []


# --------------------------------------------------------------------------------------------------
# 2. `n/a` NE COUVRE QU'UNE ABLATION D'ENTRÉE
# --------------------------------------------------------------------------------------------------

def test_gate_REFUSES_na_aliasing_on_a_SUBSTRATE_ablation():
    """`functional_aliasing='n/a'` n'est légitime que pour une ablation d'ENTRÉE (rien n'est écrit
    dans le substrat, il n'y a pas de fuite à garder). Couper dans le SUBSTRAT peut dégrader du calcul
    hors-demande : la garde CALIB-ALIAS doit alors être mesurée `pass`, jamais déclarée sans objet."""
    e = _edge(functional_aliasing="n/a", specificity_control="pass", ablation_target="substrate")
    v = validate_edge(e, _IDS)
    assert any("functional_aliasing" in x and "substrate" in x for x in v)


def test_gate_accepts_a_well_formed_SUBSTRATE_edge():
    """Contrôle positif : une ablation de substrat correctement gardée (aliasing mesuré `pass` ET
    contrôle de demande `pass`) passe. La règle interdit le `n/a`, pas l'ablation de substrat."""
    e = _edge(functional_aliasing="pass", specificity_control="pass", ablation_target="substrate")
    assert validate_edge(e, _IDS) == []


def test_gate_accepts_na_aliasing_on_an_INPUT_ablation():
    """Le chemin des 2 arêtes gravées, rendu explicite."""
    e = _edge(functional_aliasing="n/a", specificity_control="pass", ablation_target="input")
    assert validate_edge(e, _IDS) == []


def test_absent_ablation_target_defaults_to_input():
    """Compatibilité légataire : `ablation_target` absent == 'input'. Les 2 arêtes déjà gravées ne
    portent pas le champ et ablatent bien l'entrée (cf. `tools/memory_perception_demand_probe.py:21`
    « ablation d'entrée, pas d'écriture substrat -> pas de fuite à garder »)."""
    assert validate_edge(_edge(functional_aliasing="n/a", specificity_control="pass"), _IDS) == []


def test_gate_REFUSES_an_unknown_ablation_target():
    """Un `ablation_target` inconnu ne doit pas silencieusement retomber sur le défaut permissif."""
    e = _edge(functional_aliasing="n/a", specificity_control="pass", ablation_target="ablatuff")
    v = validate_edge(e, _IDS)
    assert any("ablation_target" in x for x in v)


# --------------------------------------------------------------------------------------------------
# 3. NON-RÉGRESSION — les 2 arêtes RÉELLES survivent au durcissement
# --------------------------------------------------------------------------------------------------

def test_the_two_REAL_edges_remain_valid_after_hardening():
    """Test de non-régression OBLIGATOIRE : durcir la porte ne doit invalider AUCUNE arête gravée.
    Les valeurs sont LUES sur disque, jamais recopiées — un futur changement de `demands.json` doit
    repasser par ici."""
    demands = _load("demands.json")
    assert len(demands) == 2, "le graphe livré porte exactement 2 arêtes mesurées"
    for e in demands:
        lbl = f"{e['capability']}->{e['prerequisite']}"
        assert validate_edge(e, _IDS) == [], f"arête gravée invalidée par le durcissement : {lbl}"


def test_the_shipped_graph_still_validates_end_to_end():
    """Même non-régression au niveau graphe (nœuds + arêtes), comme le cliquet l'exécute."""
    assert validate_graph(_load("capabilities.json"), _load("demands.json")) == []


def test_the_two_REAL_edges_are_exactly_the_expected_ones():
    """Ancre la précondition vérifiée par la revue : les 2 arêtes portent DÉJÀ `specificity_control`
    `pass` (avec `functional_aliasing` `n/a`) — c'est pourquoi le durcissement est gratuit pour elles.
    Si cette assertion casse, la non-régression ci-dessus ne teste plus ce qu'elle prétend tester."""
    seen = {(e["capability"], e["prerequisite"]): e["evidence"] for e in _load("demands.json")}
    assert set(seen) == {("language", "perception"), ("memory", "perception")}
    for ev in seen.values():
        assert ev["ablation_verdict"] == "X_DEMANDED"
        assert ev["n"] == 12
        assert ev["functional_aliasing"] == "n/a"
        assert ev["specificity_control"] == "pass"
        assert ev.get("ablation_target", "input") == "input"


# --------------------------------------------------------------------------------------------------
# 4. SPÉCIFICITÉ DE LA PORTE — le durcissement n'a pas avalé les autres règles
# --------------------------------------------------------------------------------------------------

def test_other_rules_still_fire_independently():
    """No-op EXACT sur les règles voisines : n_floor, verdict et record échouent toujours SEULS,
    sur une arête par ailleurs conforme à la nouvelle règle de spécificité."""
    ok = {"functional_aliasing": "pass", "specificity_control": "pass"}
    assert any("n=" in x for x in validate_edge(_edge(n=8, **ok), _IDS))
    assert any("X_DEMANDED" in x for x in validate_edge(_edge(ablation_verdict="INCONCLUSIVE", **ok), _IDS))
    assert any("record" in x for x in validate_edge(_edge(record="docs/EDR/NOPE.md", **ok), _IDS))
    assert any("functional_aliasing" in x for x in validate_edge(_edge(functional_aliasing="fail",
                                                                      specificity_control="pass"), _IDS))
