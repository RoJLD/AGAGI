"""Garde EXÉCUTABLE de la classe E11 du registre des erreurs — « choix d'analyse post-hoc ».

E11 était, avec E13, la seule classe marquée **garde : AUCUNE** (backlog P3.1). Sa forme : arrêter un
seuil, une partition ou un critère APRÈS avoir vu les données, ce qui rend n'importe quel résultat
atteignable. La discipline manuelle (écrire la règle dans le record avant le run) a été tenue sur EVO-005
et EVO-006, mais rien ne l'ATTESTAIT — un lecteur ne peut pas distinguer une règle écrite avant d'une
règle écrite après, et l'auteur non plus, six mois plus tard.

`tools/preregister.py` scelle la règle ; ces tests vérifient que le sceau tient ses deux promesses, et
surtout qu'il **échoue** quand il le doit (une garde qui ne peut pas échouer est la classe E4).
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.preregister import (  # noqa: E402
    preregister, verify, PreregistrationConflict, PreregistrationTampered)

_RULE = {"dv": "raw", "seuil": 0.5, "claim": "existence"}


def test_roundtrip_seals_and_returns_the_rule(tmp_path):
    """Cas nominal : ce qui est scellé est relu à l'identique."""
    preregister("X", _RULE, _dir=str(tmp_path))
    assert verify("X", _dir=str(tmp_path)) == _RULE


def test_reregistering_the_same_rule_is_idempotent(tmp_path):
    """Ré-enregistrer À L'IDENTIQUE ne doit pas gêner (un script relancé ne doit pas exploser)."""
    preregister("X", _RULE, _dir=str(tmp_path))
    preregister("X", dict(_RULE), _dir=str(tmp_path))
    assert verify("X", _dir=str(tmp_path)) == _RULE


def test_changing_the_rule_under_the_same_name_is_REFUSED(tmp_path):
    """⚠️ LE CŒUR DE LA GARDE. Changer la règle après coup sous le même nom doit être IMPOSSIBLE.
    Sinon la pré-inscription n'est qu'un commentaire : on la réécrirait en voyant les résultats."""
    preregister("X", _RULE, _dir=str(tmp_path))
    with pytest.raises(PreregistrationConflict):
        preregister("X", {**_RULE, "seuil": 0.3}, _dir=str(tmp_path))
    assert verify("X", _dir=str(tmp_path))["seuil"] == 0.5, "la règle d'origine doit SURVIVRE à la tentative"


def test_hand_editing_the_file_is_DETECTED(tmp_path):
    """L'autre voie de contournement : éditer le JSON à la main. Le sceau doit la détecter."""
    p = preregister("X", _RULE, _dir=str(tmp_path))
    with open(p, encoding="utf-8") as f:
        payload = json.load(f)
    payload["rule"]["seuil"] = 0.3                      # falsification silencieuse
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    with pytest.raises(PreregistrationTampered):
        verify("X", _dir=str(tmp_path))


def test_missing_preregistration_is_an_ERROR_not_a_default(tmp_path):
    """Absence de règle = échec BRUYANT. Un défaut silencieux ferait exactement ce que la classe décrit :
    laisser le critère se décider plus tard."""
    with pytest.raises(FileNotFoundError):
        verify("jamais-enregistre", _dir=str(tmp_path))


def test_the_repository_preregistrations_are_all_intact():
    """Cliquet sur le dépôt RÉEL : toute règle scellée sous `docs/preregistrations/` doit encore
    correspondre à son sceau. C'est ce test qui transforme la garde en régression permanente — si
    quelqu'un retouche une règle d'un record déjà gravé, la suite tombe."""
    from tools.preregister import _DIR
    if not os.path.isdir(_DIR):
        pytest.skip("aucune pré-inscription dans ce dépôt")
    names = [f[:-5] for f in sorted(os.listdir(_DIR)) if f.endswith(".json")]
    assert names, "le répertoire existe mais est VIDE — vérification creuse (classe E4)"
    for n in names:
        verify(n)                                        # lève si retouché


# --- E11 occurrence 3 (2026-08-04) : les branches doivent couvrir le CONTINUUM ------------------------
# Née d'un ECHEC de cette garde meme. EDR-EVO-019 avait scelle « >= 3/12 » et « 0/12 » ; le resultat est
# tombe a **1/12**, dans le TROU entre les deux. Le sceau protegeait le SEUIL, pas l'EXHAUSTIVITE.
from tools.preregister import IncompleteDiscrimination  # noqa: E402

_GAPPED = {"dv": "taux", "discrimination": {">= 3/12": "confirme", "0/12": "refute"}}


def test_gapped_discrimination_is_REFUSED(tmp_path):
    """⚠️ LE CŒUR DE LA NOUVELLE GARDE. Des branches « >= 3 » et « 0 » laissent 1 et 2 sans lecture —
    exactement la latitude post-hoc que la pré-inscription existe pour supprimer."""
    with pytest.raises(IncompleteDiscrimination):
        preregister("gap", _GAPPED, _dir=str(tmp_path))


def test_catchall_branch_makes_it_acceptable(tmp_path):
    rule = {**_GAPPED, "discrimination": {**_GAPPED["discrimination"],
                                          "sinon (1 ou 2 seeds)": "observation isolee, non elevee"}}
    preregister("ok", rule, _dir=str(tmp_path))
    assert verify("ok", _dir=str(tmp_path))["discrimination"]


def test_continuous_reading_rule_also_accepted(tmp_path):
    """L'autre forme valable : decrire la lecture sur TOUTE l'echelle plutot que par branches."""
    rule = {**_GAPPED, "regle_de_lecture_continue": "verdict = f(taux) : Fisher vs baseline, p<0.05 requis"}
    preregister("cont", rule, _dir=str(tmp_path))
    assert verify("cont", _dir=str(tmp_path))


def test_rule_without_discrimination_is_untouched(tmp_path):
    """La garde ne doit pas gener une regle qui ne declare aucune branche (pas de faux positif)."""
    preregister("nodisc", {"dv": "taux", "seuil": 0.5}, _dir=str(tmp_path))
    assert verify("nodisc", _dir=str(tmp_path))["seuil"] == 0.5
