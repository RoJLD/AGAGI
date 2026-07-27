"""Calibration du TRIAGE de rétro-audit (`tools/retro_audit_records.py`, classe E14).

Ce fichier existe parce que l'outil a ÉCHOUÉ sa calibration deux fois avant de la passer, et que les
deux échecs sont instructifs — ils sont figés ici pour ne plus pouvoir revenir silencieusement.

L'archétype est reconstruit en SYNTHÈSE plutôt que tiré de l'historique git : le test doit survivre à un
rebase, à un déplacement de fichier, et surtout à la correction du record d'origine (dont le bandeau
mentionne aujourd'hui le contrôle positif qui l'a réfuté — ce qui contaminait déjà la mesure).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.retro_audit_records import classify_record  # noqa: E402

# Reproduit la STRUCTURE ARGUMENTATIVE de WARM-002 avant correction : verdict nul, conclusion sur le
# MONDE, plancher avoué — et une mention d'« oracle » qui n'est qu'une VALEUR CITÉE d'un autre record.
_ARCHETYPE = """---
id: EDR-TEST-002
type: EDR
status: active
---

## Question
L'oracle S2-009 prouve que le monde EXIGE la perception, mais le crédit ne l'apprend pas.

## Méthode
Évolution W-only, fitness = survie, verdict marqueur (ablation within-subject) sur le génome final.

## Résultats
Repères : plancher no-perception ≈ 7 ; oracle intact ≈ 200 (S2-009).
Le meilleur génome évolué survit 5-10 ticks (= plancher) ; ratio 1.00 → NEUTRAL (n=12).

## Verdict
**`FLAT_FITNESS_LANDSCAPE`** — le paysage de fitness de survie est PLAT ; la sélection n'a aucun
gradient de fitness cognitif à escalader. Ratio ≈ 1.00 sur les 3 régimes.
"""

_SAIN = """---
id: EDR-TEST-003
type: EDR
status: active
---

## Question
Le banc sait-il produire un positif ?

## Méthode
Contrôle positif : oracle injecté, réponse connue 21x. Puis dose-réponse de fidélité.

## Résultats
Contrôle positif : ratio 22.22 (X_DEMANDED, n=12). Dose-réponse 9.0 -> 200.0, monotone.

## Verdict
**`LANDSCAPE_IS_NOT_FLAT`** — la fitness récompense la compétence partielle.
"""


def _score(tmp_path, contenu, nom="rec.md"):
    p = tmp_path / nom
    p.write_text(contenu, encoding="utf-8")
    return classify_record(str(p))


def test_archetype_scores_maximum_risk(tmp_path):
    """LE CAS QUI DÉCIDE. Si le triage ne sort pas l'archétype au risque maximal, il ne détecte pas
    le seul défaut dont la réponse est connue — et ne sert donc à rien."""
    r = _score(tmp_path, _ARCHETYPE)
    assert r["risque"] == 4, f"archétype non détecté : risque={r['risque']} ({r['motif']})"
    assert r["portee"] == "MONDE"


def test_cited_oracle_is_not_a_positive_control(tmp_path):
    """RÉGRESSION DES DEUX ÉCHECS DE CALIBRATION (2026-07-21).

    Échec 1 : « oracle » cherché dans TOUT le fichier → la mention en `## Question` (citation de
    cadrage) donnait un faux vert sur l'archétype. Même faute de portée que le bug substring du
    cliquet de calibration, commise le même jour dans l'outil censé la rattraper.
    Échec 2 : restreint aux sections de dispositif → « oracle intact ≈ 200 (S2-009) » en Résultats
    est une VALEUR DE RÉFÉRENCE CITÉE, pas un contrôle exécuté ; textuellement indiscernables.

    D'où la conception actuelle : la détection de contrôle positif est une INDICATION, jamais un
    score. Le score ne doit pas bouger même quand l'indication se déclenche à tort."""
    r = _score(tmp_path, _ARCHETYPE)
    assert r["mentionne_ctl"] is True, "l'indication doit bien se déclencher (le mot est présent)"
    assert r["risque"] == 4, "…mais elle NE DOIT PAS faire baisser le score : c'était le faux vert"


def test_positive_verdict_is_not_flagged(tmp_path):
    """SPÉCIFICITÉ : un record à verdict positif ne doit pas remonter. Sans ce bras, le triage
    pourrait signaler tout le corpus et rester « vert »."""
    assert _score(tmp_path, _SAIN)["risque"] == 0


def test_learner_scoped_null_ranks_below_world_scoped(tmp_path):
    """LA DISTINCTION QUI DÉCIDE DE TOUT : un négatif au plancher est LÉGITIME quand la conclusion
    porte sur l'apprenant (« le crédit n'apprend pas à froid » — rester au plancher EST le résultat),
    et INVALIDE quand elle porte sur le monde. Le triage doit ordonner dans ce sens."""
    apprenant = _ARCHETYPE.replace(
        "le paysage de fitness de survie est PLAT ; la sélection n'a aucun\ngradient de fitness "
        "cognitif à escalader.",
        "le crédit à froid n'apprend pas à utiliser la perception.")
    ra, rm = _score(tmp_path, apprenant, "a.md"), _score(tmp_path, _ARCHETYPE, "m.md")
    assert ra["risque"] < rm["risque"], (
        f"conclusion sur l'apprenant ({ra['risque']}) devrait passer SOUS celle sur le monde "
        f"({rm['risque']})")
