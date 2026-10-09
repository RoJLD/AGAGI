import pytest
from src.metaprog.sociologist_rsi import SociologistRSILoop


def test_sociologist_trend_detection():
    loop = SociologistRSILoop(stagnation_threshold=0.1)

    # 1. Progression claire
    scores_up = [10.0, 11.0, 12.0, 15.0, 18.0, 20.0]
    trend_up = loop.analyze_campaign_trend(scores_up)
    assert trend_up["direction"] == "PROGRESSION"
    assert not trend_up["needs_intervention"]

    # 2. Plateau / Stagnation
    scores_flat = [10.0, 10.1, 9.9, 10.0, 10.0, 10.1]
    trend_flat = loop.analyze_campaign_trend(scores_flat)
    assert trend_flat["direction"] == "STAGNATION"
    assert trend_flat["needs_intervention"]

    # 3. Régression
    scores_down = [20.0, 18.0, 15.0, 12.0, 8.0, 5.0]
    trend_down = loop.analyze_campaign_trend(scores_down)
    assert trend_down["direction"] == "REGRESSION"
    assert trend_down["needs_intervention"]


def test_sociologist_rsi_closed_loop():
    loop = SociologistRSILoop(stagnation_threshold=0.05)
    stagnant_campaign = [12.0, 12.1, 12.0, 11.9, 12.0, 12.1]

    proposal, ok, reason = loop.trigger_auto_improvement(stagnant_campaign, use_llm=False)

    assert proposal is not None
    assert proposal.kind in {"activation", "world_demand"}
    assert ok is True, f"La proposition du catalogue template doit être validée en sandbox : {reason}"
    assert len(loop.history) == 1
    assert loop.history[0]["proposal_name"] == proposal.name
