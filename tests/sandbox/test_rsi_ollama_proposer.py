"""
tests/sandbox/test_rsi_ollama_proposer.py — Test de l'armement OllamaProposer (#8 RSI).
Vérifie :
1. Le repli gracieux et sécurisé sur TemplateProposer si Ollama est injoignable.
2. Le respect absolu de la frontière ALLOWED_DEMAND_PARAMS (aucun dépassement de bornes).
3. Le parsing strict des réponses JSON et le sandboxing.
"""
import pytest
from src.metaprog.rsi_loop import (
    OllamaProposer,
    Proposal,
    evaluate_proposal,
    rsi_step,
    ALLOWED_DEMAND_PARAMS,
    sanitize_demand_params
)


def test_ollama_proposer_graceful_fallback():
    """Vérifie que la boucle retombe sur une proposition valide si le serveur LLM est hors-ligne."""
    context = {"trend": {"direction": "up"}, "recent": []}
    # Connexion à un port inexistant pour forcer le repli
    proposer = OllamaProposer(host="http://localhost:65530", timeout=0.1)

    proposal, ok, reason = rsi_step(context, proposer=proposer)
    assert ok is True
    assert proposal.kind in ("activation", "world_demand")
    assert "repli" in proposal.rationale


def test_sanitize_demand_params_safety_frontier():
    """Vérifie que toute tentative d'injection de paramètre arbitraire est neutralisée."""
    raw_params = {
        "lewis": True,
        "referential_scale": 1.5,
        "speaker_reward": 999.0,  # Dépasse la borne max (20.0) -> doit être clampé
        "unauthorized_code_exec": "import os; os.system('echo hacked')",  # Doit être purement rejeté
        "random_param": 42
    }

    clean = sanitize_demand_params(raw_params)

    assert "unauthorized_code_exec" not in clean
    assert "random_param" not in clean
    assert clean["lewis"] is True
    assert clean["referential_scale"] == 1.5
    assert clean["speaker_reward"] == 20.0  # Clampé à la borne haute


def test_evaluate_world_demand_proposal():
    """Vérifie la validation de la proposition world_demand."""
    valid_prop = Proposal(
        kind="world_demand",
        name="test_demand",
        params={"lewis": True, "referential_scale": 1.0}
    )
    ok, reason = evaluate_proposal(valid_prop)
    assert ok is True

    invalid_prop = Proposal(
        kind="world_demand",
        name="test_invalid",
        params={"illegal_key": 10.0}
    )
    ok, reason = evaluate_proposal(invalid_prop)
    assert ok is False
