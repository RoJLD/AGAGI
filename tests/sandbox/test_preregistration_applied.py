"""Cliquet : le record MESURE-t-il la DV que sa règle scellée EXIGE ? (classe E11, occurrence 4)

Le sceau de `preregister.py` prouve que la RÈGLE n'a pas bougé ; il ne dit rien sur la FIDÉLITÉ de son
application. EDR-EVO-019 l'a démontré : règle « le plafond doit RÉDUIRE `|logit|` médian », record qui
substitue une réduction de FAN-IN — sceau intact, mot « logit » absent du record.

⚠️ Ces tests vérifient surtout que le cliquet **ÉCHOUE quand il le doit**. Un cliquet qui n'a jamais vu
un cas positif est une vérification vide (classe E4).
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tools.check_preregistration_applied as C  # noqa: E402


def _mk(tmp_path, rule, record_text, name="EVO-999"):
    pre = tmp_path / "preregistrations"; pre.mkdir(exist_ok=True)
    edr = tmp_path / "EDR"; edr.mkdir(exist_ok=True)
    (pre / f"{name}.json").write_text(json.dumps({"name": name, "rule": rule, "seal": "x"}),
                                      encoding="utf-8")
    (edr / f"{name}_Un_Record.md").write_text(record_text, encoding="utf-8")
    C._PREREG, C._EDR = str(pre), str(edr)
    return C.scan()


def test_substituted_dv_is_DETECTED(tmp_path):
    """⚠️ CONTRE-EXEMPLE GELÉ — la configuration EXACTE d'EDR-EVO-019 avant correction.

    La règle exige `|logit|` médian ; le record ne parle que de fan-in. Le sceau serait intact et
    l'ancienne garde ne verrait rien."""
    rule = {"controle_de_manipulation_OBLIGATOIRE":
            "(b) le plafond doit REDUIRE |logit| median par rapport au bras volume-seul."}
    record = ("## Controles de manipulation\n\nLe plafond ramene le fan-in de 10.05 a 2.92. "
              "Les deux conditions exigees sont satisfaites.\n")
    problems = _mk(tmp_path, rule, record)
    assert problems, "la DV substituee doit etre DETECTEE — sinon le cliquet est une verification vide"
    assert "logit" in " ".join(problems[0][2]).lower()


def test_record_that_measures_the_sealed_dv_passes(tmp_path):
    """SPÉCIFICITÉ : un record qui mesure bien la grandeur scellée ne doit pas être signalé."""
    rule = {"controle_de_manipulation_OBLIGATOIRE": "le plafond doit REDUIRE |logit| median"}
    record = "Le |logit| median passe de 10.2 a 0.5 dans le bras traite.\n"
    assert _mk(tmp_path, rule, record) == []


def test_backticked_quantity_is_also_required(tmp_path):
    """Les grandeurs citees entre backticks comptent autant que les motifs |x|."""
    rule = {"dv_primaire": "taux de bascule de `measure_decision_saliency` sur la sous-tache la plus haute"}
    assert _mk(tmp_path, rule, "On rapporte le taux de lecteurs.\n"), "grandeur backtickee non exigee"
    assert _mk(tmp_path, rule, "measure_decision_saliency donne 0.982.\n") == []


def test_generic_tokens_do_not_create_false_positives(tmp_path):
    """La garde ne doit pas exiger des termes generiques (`raw`, `n`, `seed`) — sinon elle crie tout le
    temps et on cesse de la lire, ce qui la rend equivalente a une garde absente."""
    rule = {"dv_primaire": "le `raw` median par `seed`, sur `n` bras"}
    assert _mk(tmp_path, rule, "Resultats par bras.\n") == []


def test_repository_preregistrations_are_all_applied():
    """Cliquet sur le depot REEL : chaque regle scellee doit etre mesuree dans son record."""
    import importlib
    importlib.reload(C)
    problems = C.scan()
    assert not problems, f"DV scellees non mesurees : {problems}"
