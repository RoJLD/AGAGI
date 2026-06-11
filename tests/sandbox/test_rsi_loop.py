"""Boucle RSI (#8) câblée mais NON armée (EDR 044/051)."""
import pytest

from src.metaprog.rsi_loop import (
    Proposal, TemplateProposer, LLMProposer, WorldDemandProposer,
    evaluate_proposal, rsi_step, rsi_demand_step, ALLOWED_KINDS,
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
    # Une proposition hors périmètre (ni activation ni world_demand) est refusée.
    bad = Proposal(kind="world_rule", name="x", code="import numpy as np\ndef f(x):\n    return x\n")
    ok, reason = evaluate_proposal(bad)
    assert not ok and "perimetre" in reason


def test_world_demand_proposer_cycles_validated_demands():
    # Le générateur dirigé de DEMANDES propose les demandes du catalogue (047/045/050).
    p = WorldDemandProposer()
    names = {p.propose({}).name for _ in range(3)}
    assert names == {"lewis_2ref", "referential_pressure", "speaker_reciprocity"}
    prop = WorldDemandProposer().propose({})
    assert prop.kind == "world_demand" and isinstance(prop.params, dict) and prop.params


def test_rsi_demand_step_measures_and_returns_best():
    # La boucle de demandes MESURE via le callback injecté et renvoie le score (seam world-agnostique).
    seen = []

    def fake_measure(proposal):
        score = {"lewis_2ref": 0.033}.get(proposal.name, 0.0)   # re-decouvre 047 comme gagnant
        seen.append(proposal.name)
        return score, f"MI={score}"

    proposal, score, detail = rsi_demand_step({}, fake_measure)
    assert proposal.kind == "world_demand"
    assert seen and isinstance(score, float)


def test_perimeter_rejects_unsafe_code():
    # Même kind="activation", le gate AST refuse le code dangereux (defense EDR 035).
    evil = Proposal(kind="activation", name="evil",
                    code="import os\ndef f(x):\n    os.system('echo x')\n    return x\n")
    ok, reason = evaluate_proposal(evil)
    assert not ok


def test_perimeter_is_activation_and_world_demand():
    # Périmètre élargi (EDR 051) : activation (sandbox) + world_demand (le vrai levier).
    assert ALLOWED_KINDS == {"activation", "world_demand"}
