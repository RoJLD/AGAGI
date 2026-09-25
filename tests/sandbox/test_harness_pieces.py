# -*- coding: utf-8 -*-
"""Calibration de `src/seed_ai/harness_pieces.py` (ADR-004 §2.2, ADR-005) : le registre a les 13 lignes
attendues (11 du spec + 2 d'ADR-005), les statuts sont ceux scellés par le contrôleur, `check_pieces_registry`
refuse une pièce inconnue (KeyError) et une pièce non payée (ValueError, `in_repo_today` commence par
"absent") ; et REF-HARNESS-PIECES.md ne peut pas dériver du code (un test rend le .md depuis PIECES)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_learner import Piece  # noqa: E402
from src.seed_ai.harness_pieces import PIECES, PIECE_STATUS, check_pieces_registry  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_REF_PIECES_PATH = os.path.join(_REPO_ROOT, "docs", "REF", "REF-HARNESS-PIECES.md")

_EXPECTED_NAMES = {
    "bilinear", "recurrent_state", "bptt_credit", "td_critic", "condition_gate",
    "warm_start_prior", "neuromod_plasticity", "frozen_llm_backbone",
    "state_noise_regulator", "curiosity_intrinsic", "targeted_variation",
    "eligibility_trace_credit", "time_constant_modulation",
}
_SOLIDITY = {"solide", "moyenne", "faible", "aucune"}
_STATUSES = {"R1", "R2", "attend", "hors_v1", "hors_registre"}


def test_registry_has_the_thirteen_pieces_with_statuses_sealed_by_the_controller():
    assert set(PIECES) == _EXPECTED_NAMES
    assert set(PIECE_STATUS) == _EXPECTED_NAMES
    assert PIECE_STATUS["bilinear"] == "R1" and PIECE_STATUS["recurrent_state"] == "R1"
    assert PIECE_STATUS["bptt_credit"] == "R2"
    assert PIECE_STATUS["state_noise_regulator"] == "hors_v1"
    assert PIECE_STATUS["curiosity_intrinsic"] == "hors_registre"
    for name in ("td_critic", "condition_gate", "warm_start_prior", "neuromod_plasticity",
                 "frozen_llm_backbone", "targeted_variation", "eligibility_trace_credit",
                 "time_constant_modulation"):
        assert PIECE_STATUS[name] == "attend", name
    for name, p in PIECES.items():
        assert isinstance(p, Piece), name
        assert p.name == name, name
        assert p.analogue_solidity in _SOLIDITY, name
        assert p.without, name  # dict non vide : la variante "sans" DOIT exister


def test_registry_refuses_a_learner_citing_an_unknown_or_absent_piece():
    class L:
        name = "x"
        pieces = (Piece("phlogiston", "", "", "aucune", None, "", {"x": True}, True, None, "absent"),)

    with pytest.raises(KeyError, match="phlogiston"):
        check_pieces_registry([L()])

    class M:
        name = "y"
        pieces = (PIECES["frozen_llm_backbone"],)

    with pytest.raises(ValueError, match="absent"):
        check_pieces_registry([M()])

    class N:
        name = "z"
        pieces = (PIECES["time_constant_modulation"],)

    with pytest.raises(ValueError, match="absent"):
        check_pieces_registry([N()])

    class Ok:
        name = "ok"
        pieces = (PIECES["bilinear"], PIECES["recurrent_state"])

    check_pieces_registry([Ok()])   # ne lève pas : deux pièces R1, toutes deux payées


def test_bilinear_sham_and_connectome_learner_without_dicts_are_exact():
    """Ces trois dicts sont consommés TELS QUELS par la tâche 9 (ConnectomeLearner.pieces) : un
    écart silencieux ici casserait (L4) VACUOUS_PIECE sans qu'aucun test de CE fichier ne le voie."""
    assert PIECES["bilinear"].matched_sham == {"bilinear_sham": True}
    assert PIECES["bilinear"].without == {"bilinear": False}
    assert PIECES["recurrent_state"].without == {"feedforward": True}
    assert PIECES["bptt_credit"].without == {"truncate": True}


def test_every_row_declares_a_valid_solidity_and_a_valid_status():
    for name, p in PIECES.items():
        assert p.analogue_solidity in _SOLIDITY, f"{name} : solidité {p.analogue_solidity!r} hors {_SOLIDITY}"
    for name, status in PIECE_STATUS.items():
        assert status in _STATUSES, f"{name} : statut {status!r} hors {_STATUSES}"


def _render_expected_rows():
    """Rendu MINIMAL (nom + statut) depuis les données du registre — pas une copie du .md, un GABARIT
    dont chaque champ doit apparaître dans le fichier publié. Empêche le code et la doc de diverger :
    si un nom ou un statut change ici sans que le .md suive, ce test rougit."""
    return [(name, PIECE_STATUS[name]) for name in PIECES]


def test_ref_harness_pieces_doc_matches_the_registry():
    assert os.path.isfile(_REF_PIECES_PATH), "docs/REF/REF-HARNESS-PIECES.md manquant"
    with open(_REF_PIECES_PATH, encoding="utf-8") as fh:
        content = fh.read()
    assert "id: REF-HARNESS-PIECES" in content
    assert "type: REF" in content
    for name, status in _render_expected_rows():
        assert name in content, f"pièce {name!r} absente de REF-HARNESS-PIECES.md"
        assert status in content, f"statut {status!r} (pièce {name!r}) absent de REF-HARNESS-PIECES.md"
