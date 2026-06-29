# tests/sandbox/test_credit_assignment_gamma.py
import pytest


def test_td_gamma_default_is_09():
    """Non-régression : le défaut reste 0.9 (Actor-Critic TD historique)."""
    from src.agents.mamba_agent import MambaBatchModel
    assert MambaBatchModel.TD_GAMMA == 0.9


@pytest.mark.slow
def test_evp_gamma_propagates_to_td_update(monkeypatch):
    """EVP_GAMMA → MambaBatchModel.TD_GAMMA → γ effectivement reçu par td_error dans la boucle."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    monkeypatch.setenv("EVP_GAMMA", "0.99")
    import src.agents.mamba_agent as ma
    from src.graph_rag.async_logger import logger as async_logger
    from tools.evolve_ceiling_probe import run_evolution
    from main_curriculum import _acquire_shared_db

    seen = []
    real = ma.td_error

    def spy(reward, value, next_value, gamma=0.9):
        seen.append(gamma)
        return real(reward, value, next_value, gamma)

    monkeypatch.setattr(ma, "td_error", spy)
    async_logger.start()
    captured = None
    try:
        db = _acquire_shared_db()
        run_evolution("stoneage", k_eras=1, num_agents=8, max_ticks=40,
                      shared_db=db, preserve_dims=True, node_cap=512,
                      experiment_seed=0, select="elitist", n_carry=6,
                      tournament_size=3, pop_cap=40)
        captured = ma.MambaBatchModel.TD_GAMMA
    finally:
        async_logger.stop()
        ma.MambaBatchModel.TD_GAMMA = 0.9   # restaurer (attribut de classe GLOBAL)

    assert captured == 0.99                 # run_evolution a posé le knob depuis EVP_GAMMA
    assert seen, "td_error jamais appelé (l'update Actor-Critic différé n'a pas tourné)"
    assert all(g == 0.99 for g in seen), f"gamma non propagé : {sorted(set(seen))}"
