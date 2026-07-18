import numpy as np
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent


def _fresh_world(cognitive_demand, cog_gain=6.0, base_metabolism=1.0):
    env = Biosphere3D()
    env.benchmark_mode = True
    env.night_enabled = False
    env.current_era = 10_000
    env.config.cognitive_demand = cognitive_demand
    env.config.cog_gain = cog_gain
    env.config.base_metabolism = base_metabolism
    env.config.forage_payoff = 0.0            # neutralise la chasse (mode ON : corps insuffisant)
    return env


def test_off_mode_is_non_regressive():
    # OFF : pas d'attribut de signal exploité, l'énergie décroît par métabolisme comme avant (pas de cog_gain)
    env = _fresh_world(cognitive_demand=False, base_metabolism=1.0)
    a = MambaAgent(); env.add_agent(a, energy=50.0)
    e0 = env.agents[0]["energy"]
    env.step()
    assert env.agents[0]["energy"] < e0        # métabolisme draine, aucun cog_gain injecté


def test_off_mode_legacy_fruit_income_still_fires():
    # OFF : la voie de revenu corporel LÉGACY (fruit en inventaire, +20) doit toujours payer ->
    # preuve que le gating cognitive_demand ne fuit pas et ne bloque rien en mode OFF.
    env = _fresh_world(cognitive_demand=False, base_metabolism=0.01)
    a = MambaAgent(); env.add_agent(a, energy=50.0)
    ag = env.agents[0]
    ag["x"] = -1                                # hors grille -> déterministe (aucun treasure/prey/worm collision)
    ag["inventory"] = [{"type": "Fruit", "weight": 1.0}]
    ag["energy"] = 50.0
    env._resolve_biology(ag, action=0, logits=np.zeros(120))
    assert ag["energy"] > 50.0                  # la voie fruit (+20, min plafonné 100) a bien payé
    assert not any(isinstance(it, dict) and it.get("type") == "Fruit" for it in ag["inventory"])  # fruit consommé


def test_on_mode_rewards_signal_matched_direction():
    # ON : forcer le signal, appeler _resolve_biology avec l'action == direction correcte -> +cog_gain net
    env = _fresh_world(cognitive_demand=True, cog_gain=6.0, base_metabolism=0.1)
    a = MambaAgent(); env.add_agent(a, energy=50.0)
    ag = env.agents[0]
    ag["_cog_sig"] = (1.0, 1.0)                 # dir = 2*(1>0)+(1>0) = 3
    ag["energy"] = 50.0
    env._resolve_biology(ag, action=3, logits=np.zeros(120))   # action correcte
    correct_e = ag["energy"]
    ag["energy"] = 50.0
    env._resolve_biology(ag, action=0, logits=np.zeros(120))   # action fausse
    wrong_e = ag["energy"]
    assert correct_e > wrong_e                  # matcher le signal paie l'énergie
    assert correct_e - wrong_e >= 5.0           # ~cog_gain (6.0) de différentiel


def test_on_mode_signal_in_obs_columns_12_13():
    # ON : le signal est PAR-AGENT, présent dans l'obs (colonnes bit_a=12, bit_b=13) de CHAQUE agent
    env = _fresh_world(cognitive_demand=True)
    for _ in range(3):
        env.add_agent(MambaAgent(), energy=50.0)
    sigs = [(1.0, 1.0), (-1.0, 1.0), (1.0, -1.0)]
    for a, s in zip(env.agents, sigs):
        a["_cog_sig"] = s
    obs = env.get_batch_observations()
    for i, s in enumerate(sigs):
        assert obs[i, 12] == s[0]                # bit_a de CET agent
        assert obs[i, 13] == s[1]                # bit_b de CET agent
