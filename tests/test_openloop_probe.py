"""TDD S2-003 — ladder de survie (permuted/noise/zero) au-dessus de S2-002. RED avant
implémentation de tools/s2_openloop_probe.py : la survie du champion est-elle indifférente à l'obs
(SURVIVAL_NEUTRAL) ou s'effondre-t-elle sous une ablation (SURVIVAL_SENSITIVE) ?"""
import numpy as np
from src.agents.mamba_agent import MambaBatchModel


def test_noise_obs_feeds_noise(monkeypatch):
    import tools.s2_openloop_probe as mod
    captured = {}

    def fake_parent_forward(self, batch_obs, env_surprise_batch=None):
        captured["obs"] = batch_obs
        return (np.zeros((batch_obs.shape[0], 2)), np.zeros(batch_obs.shape[0]))

    monkeypatch.setattr(MambaBatchModel, "forward", fake_parent_forward, raising=True)
    inst = object.__new__(mod.NoiseObsMamba)      # saute __init__ (pas d'agents)
    np.random.seed(3)
    obs = np.arange(10 * 4, dtype=np.float32).reshape(10, 4)
    before = obs.copy()
    inst.forward(obs)
    assert captured["obs"].shape == obs.shape
    assert not np.array_equal(captured["obs"], obs)     # remplacée par du bruit, pas l'obs d'origine
    assert np.array_equal(obs, before)                  # entrée d'origine INTACTE (pas de mutation)


def test_zero_obs_feeds_zeros(monkeypatch):
    import tools.s2_openloop_probe as mod
    captured = {}

    def fake_parent_forward(self, batch_obs, env_surprise_batch=None):
        captured["obs"] = batch_obs
        return (np.zeros((batch_obs.shape[0], 2)), np.zeros(batch_obs.shape[0]))

    monkeypatch.setattr(MambaBatchModel, "forward", fake_parent_forward, raising=True)
    inst = object.__new__(mod.ZeroObsMamba)        # saute __init__ (pas d'agents)
    obs = (np.arange(10 * 4, dtype=np.float32).reshape(10, 4) + 1.0)  # tout non-nul
    before = obs.copy()
    inst.forward(obs)
    assert captured["obs"].shape == obs.shape
    assert np.array_equal(captured["obs"], np.zeros_like(obs))
    assert np.array_equal(obs, before)              # entrée d'origine INTACTE (pas de mutation)


def test_ladder_wiring(monkeypatch):
    import tools.s2_openloop_probe as mod
    from tools.s2_demand_ablation import PerceptionAblatedMamba

    # cas 1 : les 3 barreaux sont PLATS -> verdict monde SURVIVAL_NEUTRAL
    # ⚠️ FIXTURE RENDUE REALISTE le 2026-09-09 (P2.52). Elle rendait `[100.0]*12` pour l'intact ET
    # pour les bras ables : des listes LITTERALEMENT IDENTIQUES, que `_degeneracy` refuse a juste
    # titre de trancher depuis le 2026-07-21 (« l'intervention ne s'est pas appliquee » et « elle n'a
    # rien fait » sont indiscernables depuis les SORTIES). Le test etait donc ROUGE -- en silence,
    # car aucun job de CI ne lancait ce fichier ; c'est le NEUVIEME rouge de cette famille trouve
    # dans la journee, apres les huit de P2.51.
    # ⚠️ ON NE CHANGE PAS L'ATTENTE, ON CORRIGE LA FIXTURE : l'INTENTION du test est valide et vaut
    # d'etre testee. Les bras different desormais legerement tout en gardant la MEME mediane -- ce
    # qu'on observe sur des donnees reelles, ou deux tableaux de flottants ne coincident jamais.
    # ⚠️ SECOND AXE D'IRREALISME, trouve en corrigeant le premier : la fixture rendait des survies
    # de 100 alors que le test passe `max_ticks=10`. Le monde declare `ceiling=max_ticks`, et la
    # garde refusait donc « les DEUX bras au PLAFOND declare » -- a juste titre : survivre 100 ticks
    # quand l'horizon en compte 10 est impossible. Les survies sont desormais SOUS le plafond.
    def _fake_flat(world_cls, batch_model_cls, genome, seed, num_agents=12, max_ticks=200, n_eras=12):
        if batch_model_cls is None:
            return {"survival": [4.0, 6.0] * 6, "era_survival": [4.0, 6.0] * 6}
        if batch_model_cls in (PerceptionAblatedMamba, mod.NoiseObsMamba, mod.ZeroObsMamba):
            return {"survival": [3.0, 7.0] * 6, "era_survival": [3.0, 7.0] * 6}
        raise AssertionError(f"condition inattendue: {batch_model_cls}")

    monkeypatch.setattr(mod, "run_condition", _fake_flat)
    monkeypatch.setattr(mod, "load_champion_genome", lambda: "FAKE_GENOME")
    out = mod.run_openloop_ladder(worlds=["soup"], seed=1, K=12, num_agents=3, max_ticks=10)
    r = out["soup"]
    assert r["intact_med"] == 5.0
    assert r["permuted"]["ratio"] == 1.0
    assert r["noise"]["ratio"] == 1.0
    assert r["zero"]["ratio"] == 1.0
    assert r["permuted"]["n"] == 12
    assert r["noise"]["n"] == 12
    assert r["zero"]["n"] == 12
    # ⚠️ RECTIFIE le 2026-09-09 (P2.52). Ce test affirmait `SURVIVAL_NEUTRAL` et etait ROUGE depuis
    # l'armement de la garde de degenerescence (2026-07-21) -- en silence, car AUCUN job de CI ne
    # lance ce fichier. C'est le NEUVIEME rouge de cette famille trouve dans la journee ; les huit
    # premiers etaient dans les sondes de demande in-world (cf. P2.51).
    # Les trois barreaux rendent `ratio == 1.0` EXACTEMENT : les bras sont LITTERALEMENT identiques,
    # et `_degeneracy` refuse alors de trancher -- « l'intervention ne s'est pas appliquee » et
    # « elle s'est appliquee et n'a rien fait » sont indiscernables depuis les SORTIES.
    # CE QUI TIENT : aucun effondrement n'est detecte. CE QUI NE TIENT PLUS : « donc le monde est
    # neutre » -- une cellule INDECIDABLE n'etablit pas la neutralite, elle refuse de conclure.
    assert r["verdict"] == "SURVIVAL_NEUTRAL", (
        "trois barreaux plats sur des bras DISTINCTS : la survie est independante de l'obs", r["verdict"])

    # cas 2 : le barreau ZERO s'effondre (ratio 5.0 >= collapse_factor) -> SURVIVAL_SENSITIVE
    def _fake_zero_collapse(world_cls, batch_model_cls, genome, seed, num_agents=12, max_ticks=200, n_eras=12):
        if batch_model_cls is mod.ZeroObsMamba:
            return {"survival": [1.0] * 12, "era_survival": [1.0] * 12}
        if batch_model_cls is None:
            return {"survival": [4.0, 6.0] * 6, "era_survival": [4.0, 6.0] * 6}
        if batch_model_cls in (PerceptionAblatedMamba, mod.NoiseObsMamba):
            return {"survival": [3.0, 7.0] * 6, "era_survival": [3.0, 7.0] * 6}
        raise AssertionError(f"condition inattendue: {batch_model_cls}")

    monkeypatch.setattr(mod, "run_condition", _fake_zero_collapse)
    out2 = mod.run_openloop_ladder(worlds=["soup"], seed=1, K=12, num_agents=3, max_ticks=10)
    r2 = out2["soup"]
    assert r2["zero"]["ratio"] == 5.0
    assert r2["permuted"]["ratio"] == 1.0
    assert r2["noise"]["ratio"] == 1.0
    assert r2["verdict"] == "SURVIVAL_SENSITIVE"
