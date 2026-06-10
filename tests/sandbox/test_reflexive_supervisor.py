"""Supervisor réflexif (EDR 036) : décision sur la TENDANCE multi-ères, pas le snapshot."""
from src.graph_rag.reflexive_supervisor import compute_trend, reflexive_decision, read_recent_scores


def test_plateau_low_triggers_famine():
    # Scores stagnants ET bas -> famine cognitive (déclenche la métaprog).
    trend = compute_trend([0.50, 0.51, 0.50, 0.49, 0.50, 0.51])
    assert trend["direction"] == "plateau"
    d = reflexive_decision(trend)
    assert d["famine"] is True


def test_plateau_high_no_famine():
    # Stagnant mais HAUT (>=0.95) -> pas de famine (rien à réparer).
    trend = compute_trend([0.96, 0.97, 0.96, 0.97, 0.96])
    assert trend["direction"] == "plateau"
    assert reflexive_decision(trend)["famine"] is False


def test_improving_stays_course():
    # Tendance à la hausse -> rester le cap, pas de famine ni de boost.
    trend = compute_trend([0.40, 0.50, 0.60, 0.70, 0.80])
    assert trend["direction"] == "improving"
    d = reflexive_decision(trend)
    assert not d["famine"] and not d["mutation_boost"]


def test_declining_boosts_mutation():
    # Déclin multi-ères -> ↑ exploration (ce qu'un snapshot myope manquait).
    trend = compute_trend([0.80, 0.70, 0.60, 0.50, 0.40])
    assert trend["direction"] == "declining"
    assert reflexive_decision(trend)["mutation_boost"] is True


def test_read_recent_scores_handles_no_db():
    assert read_recent_scores(None) == []


def test_trend_needs_history():
    # Moins de 3 points -> direction inconnue (pas de décision hâtive).
    assert compute_trend([0.5])["direction"] == "unknown"
