"""Contrat de neutralisation de la memoire ambiante dans robust_evaluate (verrou repro Dev #3).

Le memory_retriever async (demarre par Biosphere3D.__init__) doit etre stop()+clear() AVANT la boucle
sim, sinon les obs (slots memoire 51-55) sont timing-dependantes (le worker lit un KuzuDB partage qui
grossit) -> robust_evaluate non reproductible meme a seed fixe. Le test de repro existant
(test_harness.test_robust_evaluate_reproducible_with_seed) ne le capte PAS : en conditions de test
(DB vide, max_ticks tres court < intervalle de poll 0.5s) la memoire renvoie des zeros deterministes.

Ce banc verifie le CONTRAT directement via un env-espion : rapide, deterministe, independant de l'etat
KuzuDB. Il echoue sur le code qui ne fait que stop() APRES la boucle (jamais clear, et trop tard)."""
from src.seed_ai.robust_hof import robust_evaluate
from src.agents.mamba_agent import MambaAgent


class _SpyRetriever:
    def __init__(self):
        self.stopped = False
        self.cleared = False

    def stop(self):
        self.stopped = True

    def clear(self):
        self.cleared = True


class _FakeEnv:
    """Env minimal : enregistre si le cache memoire a ete vide AVANT le premier step()."""
    instances = []

    def __init__(self, config):
        self.memory_retriever = _SpyRetriever()
        self.agents = []
        self.dead_agents = []
        self.current_era = 0
        self.cleared_before_first_step = None
        _FakeEnv.instances.append(self)

    def add_agent(self, agent, energy=80.0):
        self.agents.append(agent)

    def step(self):
        if self.cleared_before_first_step is None:
            self.cleared_before_first_step = self.memory_retriever.cleared
        self.agents = []  # termine la boucle apres un seul pas


def test_robust_evaluate_neutralizes_ambient_memory_before_sim(monkeypatch):
    monkeypatch.setattr("src.worlds.world_1_stoneage.Biosphere3D", _FakeEnv)
    _FakeEnv.instances.clear()
    robust_evaluate(None, MambaAgent().genome, K=1, num_agents=2, max_ticks=5, seed=1)
    env = _FakeEnv.instances[-1]
    assert env.memory_retriever.stopped is True, "le retriever doit etre stoppe"
    assert env.memory_retriever.cleared is True, "le cache memoire doit etre vide (clear)"
    assert env.cleared_before_first_step is True, "stop()+clear() doit preceder le premier step() (sinon obs timing-dependantes)"
