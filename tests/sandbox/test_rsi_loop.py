"""Boucle RSI (#8) câblée mais NON armée (EDR 044)."""
import pytest

from src.metaprog.rsi_loop import (
    Proposal, TemplateProposer, LLMProposer, evaluate_proposal, rsi_step, ALLOWED_KINDS,
)


def test_template_proposer_proposals_are_valid():
    # Le générateur sûr (défaut) produit des activations qui passent la validation.
    p = TemplateProposer()
    for _ in range(3):
        proposal = p.propose({"trend": {"direction": "plateau"}})
        ok, reason = evaluate_proposal(proposal)
        assert ok, f"{proposal.name}: {reason}"


def test_llm_proposer_is_not_armed():
    # Le SEAM du #8 lève NotImplementedError tant qu'il n'est pas armé.
    with pytest.raises(NotImplementedError):
        LLMProposer().propose({})


def test_rsi_step_falls_back_when_llm_unarmed():
    # Avec LLMProposer non armé, la boucle retombe sur le gabarit et fonctionne quand même.
    proposal, ok, reason = rsi_step({"trend": {"direction": "plateau"}}, proposer=LLMProposer())
    assert ok, reason
    assert "repli" in proposal.rationale


def test_perimeter_rejects_out_of_scope():
    # Une proposition hors périmètre (pas une activation) est refusée.
    bad = Proposal(kind="world_rule", name="x", code="import numpy as np\ndef f(x):\n    return x\n")
    ok, reason = evaluate_proposal(bad)
    assert not ok and "perimetre" in reason


def test_perimeter_rejects_unsafe_code():
    # Même kind="activation", le gate AST refuse le code dangereux (defense EDR 035).
    evil = Proposal(kind="activation", name="evil",
                    code="import os\ndef f(x):\n    os.system('echo x')\n    return x\n")
    ok, reason = evaluate_proposal(evil)
    assert not ok


def test_activation_is_the_minimal_perimeter():
    assert ALLOWED_KINDS == {"activation"}   # on commence borné (le pouce, pas la main)
