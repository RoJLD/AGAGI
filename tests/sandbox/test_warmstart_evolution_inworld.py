"""Tests WARM-001/WARM-002 — imitation BPTT récurrente + évolution in-world W-only + verdict partagé."""
import os, sys
import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _tiny_torch_pop(B=4, I=2, O=8, N=12, seed=0):
    """Construit un TorchPopulationModel minimal sur des agents jouets (Genome réel, petit N)."""
    torch = pytest.importorskip("torch")
    from src.seed_ai.mutation import Genome
    from src.agents.backend_torch import TorchPopulationModel
    rng = np.random.RandomState(seed)

    class _A:
        def __init__(self, g): self.genome = g
    agents = []
    for _ in range(B):
        W = (rng.randn(N, N) * 0.1).astype(np.float32)
        agents.append(_A(Genome(W, num_inputs=I, num_outputs=O)))
    return TorchPopulationModel(agents, lr=0.2)


def test_imitate_episode_bptt_reduces_loss_and_learns_separable_map():
    pytest.importorskip("torch")
    pop = _tiny_torch_pop(B=4, I=2, O=8, N=12, seed=1)
    rng = np.random.RandomState(2)
    # Tâche jouet séparable : le signe de obs[:,0] -> cible 0 (négatif) ou 3 (positif).
    T = 6
    obs_seq, tgt_seq = [], []
    for _ in range(T):
        s = rng.choice([-1.0, 1.0], size=4).astype(np.float32)
        obs = np.zeros((4, 2), dtype=np.float32); obs[:, 0] = s
        obs_seq.append(obs)
        tgt_seq.append(np.where(s > 0, 3, 0).astype(int))
    first = pop.imitate_episode_bptt(obs_seq, tgt_seq)
    for _ in range(60):
        last = pop.imitate_episode_bptt(obs_seq, tgt_seq)
    assert last < first, f"la perte d'imitation devrait décroître ({first:.3f} -> {last:.3f})"


def test_verdict_demand_marker_random_genome_is_neutral_and_wellformed():
    from tools.warmstart_evolution_inworld import verdict_demand_marker
    from src.agents.mamba_agent import MambaAgent
    g = MambaAgent().genome                         # génome aléatoire (non-suiveur)
    r = verdict_demand_marker(g, backend="mamba", seed=2026, K=2,
                              num_agents=4, max_ticks=20)
    assert set(r) >= {"ratio", "verdict", "n", "intact_survival", "ablated_survival"}
    assert r["verdict"] in ("PERCEPTION_DEMANDED", "NEUTRAL", "INCONCLUSIVE")


def test_run_inworld_evolution_smoke_returns_trend_and_best():
    from tools.warmstart_evolution_inworld import run_inworld_evolution
    from src.seed_ai.mutation import Genome
    out = run_inworld_evolution(seed=2026, generations=2, pop_size=6, survival_frac=0.34,
                                mut_power=0.2, max_ticks=15)
    assert len(out["trend"]) == 2
    assert isinstance(out["best_genome"], Genome)
    assert out["best_age"] >= 0


def test_mutate_w_only_changes_W_not_router():
    from tools.warmstart_evolution_inworld import _mutate_W_only
    from src.agents.mamba_agent import MambaAgent
    g = MambaAgent().genome
    W0 = g.W.copy()
    router0 = None if g.W_router is None else g.W_router.copy()
    _mutate_W_only(g, power=0.5, rng=np.random.RandomState(0))
    assert not np.allclose(g.W, W0), "W devrait changer"
    if router0 is not None:
        assert np.allclose(g.W_router, router0), "W_router ne doit PAS changer (comparaison propre au gradient)"


def test_collect_oracle_trajectory_shapes():
    from tools.warmstart_evolution_inworld import _collect_oracle_trajectory
    obs_seq, tgt_seq = _collect_oracle_trajectory(seed=2026, num_agents=4, max_ticks=8,
                                                  metab=0.75, cog=12.0)
    assert len(obs_seq) == len(tgt_seq) and len(obs_seq) >= 1
    assert obs_seq[0].shape[0] == 4 and obs_seq[0].shape[1] >= 14      # B=4, >= colonnes bit_a/bit_b
    assert tgt_seq[0].shape[0] == 4 and tgt_seq[0].max() < 8


def test_run_bptt_imitation_warmstart_smoke_reduces_loss():
    pytest.importorskip("torch")
    from tools.warmstart_evolution_inworld import run_bptt_imitation_warmstart
    from src.seed_ai.mutation import Genome
    out = run_bptt_imitation_warmstart(seed=2026, num_agents=4, n_epochs=8,
                                       truncate_window=10, max_ticks=12)
    assert isinstance(out["learned_genome"], Genome)
    assert out["loss_trend"][-1] <= out["loss_trend"][0]


def test_collect_onpolicy_trajectory_shapes_and_mask():
    from tools.warmstart_evolution_inworld import _collect_onpolicy_trajectory
    from src.agents.mamba_agent import MambaAgent
    pytest.importorskip("torch")
    g = MambaAgent().genome
    obs_seq, tgt_seq, mask_seq = _collect_onpolicy_trajectory(g, seed=2026, num_agents=4, max_ticks=10)
    assert len(obs_seq) == len(tgt_seq) == len(mask_seq) >= 1
    assert obs_seq[0].shape == (4, obs_seq[0].shape[1]) and obs_seq[0].shape[1] >= 14
    assert tgt_seq[0].shape == (4,) and mask_seq[0].shape == (4,)
    assert set(np.unique(mask_seq[0])).issubset({0.0, 1.0})
    assert mask_seq[0].sum() == 4.0           # tous vivants au 1er tick


def test_imitate_episode_bptt_mask_all_ones_trains_and_zero_mask_noop():
    pytest.importorskip("torch")
    pop = _tiny_torch_pop(B=4, I=2, O=8, N=12, seed=3)
    rng = np.random.RandomState(4)
    obs_seq, tgt_seq = [], []
    for _ in range(5):
        s = rng.choice([-1.0, 1.0], size=4).astype(np.float32)
        o = np.zeros((4, 2), dtype=np.float32); o[:, 0] = s
        obs_seq.append(o); tgt_seq.append(np.where(s > 0, 3, 0).astype(int))
    ones = [np.ones(4, dtype=np.float32) for _ in range(5)]
    first = pop.imitate_episode_bptt(obs_seq, tgt_seq, mask_seq=ones)
    for _ in range(50):
        last = pop.imitate_episode_bptt(obs_seq, tgt_seq, mask_seq=ones)
    assert last < first, "masque tout-à-1 doit entraîner (perte décroît)"
    zeros = [np.zeros(4, dtype=np.float32) for _ in range(5)]
    lz = pop.imitate_episode_bptt(obs_seq, tgt_seq, mask_seq=zeros)
    assert lz <= 1e-6, "masque tout-à-0 -> perte nulle, pas d'exception"


def test_run_dagger_warmstart_smoke():
    from tools.warmstart_evolution_inworld import run_dagger_warmstart
    from src.seed_ai.mutation import Genome
    pytest.importorskip("torch")
    out = run_dagger_warmstart(seed=2026, rounds=2, epochs_per_round=6, lr=0.5,
                               num_agents=4, max_ticks=12, K=2)
    assert len(out["trend_onpolicy_acc"]) == 2
    assert len(out["trend_survival"]) == 2
    assert isinstance(out["final_genome"], Genome)
    assert set(out["final_verdict"]) >= {"ratio", "verdict", "intact_survival"}


def test_collect_diag_trajectory_oracle_is_long_and_masked():
    from tools.warmstart_evolution_inworld import _collect_diag_trajectory
    pytest.importorskip("torch")
    obs, tgt, mask, en = _collect_diag_trajectory("oracle", seed=2026, num_agents=4, max_ticks=60)
    assert len(obs) == len(tgt) == len(mask) == len(en) >= 1
    assert obs[0].shape[0] == 4 and obs[0].shape[1] >= 14
    assert set(np.unique(mask[0])).issubset({0.0, 1.0})
    alive0 = mask[0] > 0
    assert np.all(np.isfinite(en[0][alive0])), "énergie finie là où mask=1"
    # PLEINE LONGUEUR (raison d'être de ce collecteur) : si une mort survient, l'enregistrement
    # DOIT continuer au-delà — contrairement à _collect_oracle_trajectory qui tronque à la 1re mort.
    partiels = [k for k, m in enumerate(mask) if 0 < m.sum() < 4]
    if partiels:
        assert len(mask) > partiels[0] + 1, "doit enregistrer APRÈS la 1re mort (pas de troncature)"


def test_collect_diag_trajectory_rejects_unknown_driver():
    from tools.warmstart_evolution_inworld import _collect_diag_trajectory
    with pytest.raises(ValueError):
        _collect_diag_trajectory("oracel", seed=2026, num_agents=2, max_ticks=3)


def test_collect_diag_trajectory_genome_runs():
    from tools.warmstart_evolution_inworld import _collect_diag_trajectory
    from src.agents.mamba_agent import MambaAgent
    pytest.importorskip("torch")
    g = MambaAgent().genome
    obs, tgt, mask, en = _collect_diag_trajectory("genome", genome=g, seed=2026,
                                                 num_agents=4, max_ticks=15)
    assert len(obs) >= 1 and obs[0].shape[0] == 4
    assert mask[0].sum() == 4.0


def test_bins_and_accuracy_binned_random_genome_is_chance():
    from tools.warmstart_evolution_inworld import (_collect_diag_trajectory, bins_by_tick,
                                                   accuracy_binned)
    from src.agents.mamba_agent import MambaAgent
    pytest.importorskip("torch")
    obs, tgt, mask, en = _collect_diag_trajectory("oracle", seed=2026, num_agents=4, max_ticks=30)
    edges = [0, 10, 1000]
    bids = bins_by_tick(mask, edges)
    assert len(bids) == len(mask) and bids[0].shape == (4,)
    res = accuracy_binned(MambaAgent().genome, obs, tgt, mask, bids, n_bins=2, num_agents=4)
    assert len(res) == 2
    peupled = [r for r in res if r["n"] > 0]
    assert peupled, "au moins un bin peuplé"
    for r in peupled:
        assert 0.0 <= r["acc"] <= 1.0
    # contrôle négatif : un génome aléatoire ne doit pas être excellent partout
    assert min(r["acc"] for r in peupled) < 0.9


def test_bins_by_energy_maps_nan_to_minus_one():
    from tools.warmstart_evolution_inworld import bins_by_energy
    en = [np.array([10.0, 50.0, np.nan, 95.0], dtype=np.float32)]
    b = bins_by_energy(en, [0, 40, 80, 101])
    assert b[0].tolist() == [0, 1, -1, 2]


def test_run_coverage_precision_diagnostic_smoke(tmp_path):
    from tools.warmstart_evolution_inworld import run_coverage_precision_diagnostic
    pytest.importorskip("torch")
    out = run_coverage_precision_diagnostic(seed=2026, rounds=1, epochs_per_round=4, lr=0.5,
                                            num_agents=4, max_ticks=12, K=2,
                                            genome_path=str(tmp_path / "g.npz"))
    assert "coverage" in out and "precision" in out and "verdict" in out
    assert isinstance(out["coverage"], list) and isinstance(out["precision"], list)


def test_measure_action_pipeline_wellformed():
    from tools.warmstart_evolution_inworld import measure_action_pipeline
    from src.agents.mamba_agent import MambaAgent
    pytest.importorskip("torch")
    r = measure_action_pipeline(MambaAgent().genome, seed=2026, num_agents=4, max_ticks=12)
    assert set(r) >= {"n", "acc_raw", "acc_applied", "flip_rate", "ticks"}
    assert r["n"] > 0 and r["ticks"] > 0
    for k in ("acc_raw", "acc_applied", "flip_rate"):
        assert 0.0 <= r[k] <= 1.0, f"{k} hors [0,1]"


def test_probe_free_channels_wellformed():
    """La sonde des canaux LIBRES doit être bornée et cohérente (grab_on_frac = fraction de logits > 0)."""
    from tools.warmstart_evolution_inworld import _probe_free_channels, _collect_oracle_trajectory
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    pytest.importorskip("torch")
    obs, tgt = _collect_oracle_trajectory(2026, 4, 12, 0.75, 12.0)
    pop = TorchPopulationModel([MambaAgent() for _ in range(4)], lr=0.5)
    p = _probe_free_channels(pop, obs, tgt)
    assert set(p) == {"grab", "rub", "grab_on_frac", "move_acc"}
    assert 0.0 <= p["grab_on_frac"] <= 1.0 and 0.0 <= p["move_acc"] <= 1.0
    assert np.isfinite(p["grab"]) and np.isfinite(p["rub"])


def test_probe_free_channels_is_read_only():
    """La sonde ne doit PAS entraîner : W identique avant/après (sinon elle contamine la mesure)."""
    from tools.warmstart_evolution_inworld import _probe_free_channels, _collect_oracle_trajectory
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    pytest.importorskip("torch")
    obs, tgt = _collect_oracle_trajectory(2026, 4, 12, 0.75, 12.0)
    agents = [MambaAgent() for _ in range(4)]
    pop = TorchPopulationModel(agents, lr=0.5)
    before = agents[0].genome.W.copy()
    _probe_free_channels(pop, obs, tgt)
    assert np.array_equal(before, agents[0].genome.W), "la sonde a modifié les poids"


def test_run_grab_drift_diagnostic_smoke():
    """Les deux bras doivent tracer les MÊMES epochs, partir du MÊME point (init partagée) et
    sonder DANS le round 0 (c'est ce qui sépare durée vs données on-policy)."""
    from tools.warmstart_evolution_inworld import run_grab_drift_diagnostic
    pytest.importorskip("torch")
    out = run_grab_drift_diagnostic(seed=2026, rounds=2, epochs_per_round=4, lr=0.5,
                                    num_agents=4, max_ticks=12, probe_every=2)
    assert set(out) == {"dagger", "oracle_only"}
    for arm, tr in out.items():
        assert tr[0]["round"] == -1 and tr[0]["epoch"] == 0, f"{arm}: pas de point pré-gradient"
        assert [p["epoch"] for p in tr] == [0, 2, 4, 6, 8], f"{arm}: grille d'epochs inattendue"
        assert sum(1 for p in tr if p["round"] == 0) >= 2, f"{arm}: pas de sonde DANS le round 0"
    # init partagée -> le point pré-gradient est identique entre bras (contrôle apparié)
    assert out["dagger"][0]["grab"] == pytest.approx(out["oracle_only"][0]["grab"])


def test_probe_by_agent_shapes_and_mean_matches_population():
    """La vue par agent doit renvoyer des vecteurs (B,) et sa moyenne doit reproduire EXACTEMENT la
    vue agrégée — c'est ce qui garantit que la seule différence est l'unité d'analyse (EDR-WARM-006)."""
    from tools.warmstart_evolution_inworld import (_probe_free_channels,
                                                   _probe_free_channels_by_agent,
                                                   _collect_oracle_trajectory)
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    pytest.importorskip("torch")
    obs, tgt = _collect_oracle_trajectory(2026, 4, 12, 0.75, 12.0)
    pop = TorchPopulationModel([MambaAgent() for _ in range(4)], lr=0.5)
    pa = _probe_free_channels_by_agent(pop, obs, tgt)
    agg = _probe_free_channels(pop, obs, tgt)
    for k, v in pa.items():
        assert v.shape == (4,), f"{k} n'est pas un vecteur par agent"
        assert agg[k] == pytest.approx(float(np.mean(v)))
    assert np.all(pa["grab_on_frac"] >= 0.0) and np.all(pa["grab_on_frac"] <= 1.0)


def test_probe_by_agent_detects_divergence():
    """Contrôle négatif de l'unité d'analyse : 12 agents frais ont des grab DISTINCTS (W est (B,N,N)).
    Si ce test échouait, la moyenne de population serait légitime et WARM-006 n'aurait pas lieu d'être."""
    from tools.warmstart_evolution_inworld import (_probe_free_channels_by_agent,
                                                   _collect_oracle_trajectory)
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    from src.seed_ai.harness import seed_at
    pytest.importorskip("torch")
    obs, tgt = _collect_oracle_trajectory(2026, 12, 12, 0.75, 12.0)
    seed_at(2026, 1)
    pop = TorchPopulationModel([MambaAgent() for _ in range(12)], lr=0.5)
    g = _probe_free_channels_by_agent(pop, obs, tgt)["grab"]
    assert g.std() > 0.1, f"agents non divergents (std={g.std():.4f})"


def test_grab_off_ablation_forces_channel_below_world_threshold():
    """L'ablation grab_off doit mettre le canal 24 SOUS le seuil d'exécution du monde (logit > 0),
    sans toucher aux 8 canaux de mouvement. Sans cette garantie l'ablation ne prouverait rien."""
    from tools.warmstart_evolution_inworld import _torch_survival_eras, _GRAB_NODE_T
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    pytest.importorskip("torch")
    captured = {}

    class _Probe(TorchPopulationModel):
        def forward(self, batch_obs, env_surprise_batch=None):
            logits, extra = super().forward(batch_obs, env_surprise_batch)
            if getattr(logits, "ndim", 0) == 2 and logits.size:
                logits[:, _GRAB_NODE_T] = -1.0
                captured["moves"] = logits[:, :8].copy()
                captured["grab"] = logits[:, _GRAB_NODE_T].copy()
            return logits, extra

    pop = _Probe([MambaAgent() for _ in range(4)], lr=0.0)
    pop.forward(np.zeros((4, pop.I), dtype=np.float32))
    assert np.all(captured["grab"] < 0.0), "grab pas forcé sous le seuil"
    assert captured["moves"].shape == (4, 8)
    # et la variante grab_off doit produire K ères exploitables
    eras = _torch_survival_eras(MambaAgent().genome, True, 2026, 2, 4, 10, 0.75, 12.0,
                                ablate_kind="grab_off")
    assert len(eras) == 2 and all(e >= 0 for e in eras)


def test_run_grab_incidence_and_ablation_smoke(tmp_path):
    from tools.warmstart_evolution_inworld import run_grab_incidence_and_ablation
    pytest.importorskip("torch")
    out = run_grab_incidence_and_ablation(seeds=(2026,), rounds=1, epochs_per_round=2, num_agents=4,
                                          max_ticks=10, K=2, n_probe=2,
                                          out_path=str(tmp_path / "w7.json"))
    recs = out["seeds"]["2026"]["agents"]
    assert len(recs) == 2
    for r in recs:
        assert {"birth_grab", "final_grab", "surv_intact", "surv_grab_off", "ratio"} <= set(r)
        assert r["K"] == 2 and 0 <= r["eras_improved"] <= 2


def test_forward_logits_alias_recurrent_state():
    """VÉRITÉ-TERRAIN du bug attrapé en revue WARM-007 : `forward` renvoie une VUE de H, donc écrire
    dans logits mute l'état récurrent. Ce test DOCUMENTE le piège ; si le backend cessait d'aliaser,
    il échouerait et signalerait que le découplage de `_DecoupledTorchPop` est devenu inutile."""
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    from tools.warmstart_evolution_inworld import _GRAB_NODE_T
    pytest.importorskip("torch")
    pop = TorchPopulationModel([MambaAgent() for _ in range(4)], lr=0.0)
    logits, _ = pop.forward(np.zeros((4, pop.I), dtype=np.float32))
    node = pop.N - pop.O + _GRAB_NODE_T
    assert np.shares_memory(logits, pop.H.numpy()), "plus d'aliasing : revoir _DecoupledTorchPop"
    logits[:, _GRAB_NODE_T] = -1.0
    assert float(pop.H[0, node]) == pytest.approx(-1.0)


def test_grab_off_ablation_does_not_touch_recurrent_state():
    """Le correctif : clamper le grab ne doit PLUS muter H (sinon l'ablation est deux interventions,
    dont une d'amplitude colinéaire au taux de grab — le confond qui a invalidé la 1re passe)."""
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    from tools.warmstart_evolution_inworld import _GRAB_NODE_T
    pytest.importorskip("torch")

    class _Decoupled(TorchPopulationModel):
        def forward(self, batch_obs, env_surprise_batch=None):
            logits, extra = super().forward(batch_obs, env_surprise_batch)
            if getattr(logits, "ndim", 0) == 2 and logits.size:
                logits = logits.copy()
            return logits, extra

    class _GrabOff(_Decoupled):
        def forward(self, batch_obs, env_surprise_batch=None):
            logits, extra = super().forward(batch_obs, env_surprise_batch)
            if getattr(logits, "ndim", 0) == 2 and logits.size:
                logits[:, _GRAB_NODE_T] = -1.0
            return logits, extra

    pop = _GrabOff([MambaAgent() for _ in range(4)], lr=0.0)
    logits, _ = pop.forward(np.zeros((4, pop.I), dtype=np.float32))
    node = pop.N - pop.O + _GRAB_NODE_T
    assert not np.shares_memory(logits, pop.H.numpy()), "logits encore aliasé sur H"
    assert np.all(logits[:, _GRAB_NODE_T] < 0.0), "grab pas clampé"
    assert float(pop.H[0, node]) != pytest.approx(-1.0), "H muté : l'ablation perturbe l'état"


def test_grab_off_is_exact_noop_for_never_grabbing_genome():
    """Contrôle négatif STRICT (restreint par la revue aux agents qui ne grabbent JAMAIS) : si le génome
    ne grab pas, l'ablation doit être un no-op EXACT — survies identiques ère par ère. Toute dérive
    résiduelle signalerait que l'ablation agit par un autre canal que le geste."""
    from tools.warmstart_evolution_inworld import (_torch_survival_eras, measure_inworld_grab_rate)
    from src.seed_ai.mutation import Genome
    pytest.importorskip("torch")
    p = "results/warm007_genomes/seed2026_agent06.npz"       # gi = 0.000 (jamais de grab)
    if not os.path.exists(p):
        pytest.skip("génomes WARM-007 absents")
    d = np.load(p, allow_pickle=False)
    g = Genome(d["W"], int(d["num_inputs"]), int(d["num_outputs"]))
    assert measure_inworld_grab_rate(g, seed=2026, K=1, num_agents=12, max_ticks=60) == 0.0
    a = _torch_survival_eras(g, False, 2026, 2, 12, 60, 0.75, 12.0, ablate_kind="grab_off")
    b = _torch_survival_eras(g, True, 2026, 2, 12, 60, 0.75, 12.0, ablate_kind="grab_off")
    assert a == b, f"no-op attendu, obtenu intact={a} ablate={b}"


def test_run_aux_off_validation_smoke(tmp_path):
    """Les deux bras doivent être appariés (même init) et rapporter gi + move_acc par agent."""
    from tools.warmstart_evolution_inworld import run_aux_off_validation
    pytest.importorskip("torch")
    out = run_aux_off_validation(seeds=(2026,), epochs=3, num_agents=4, max_ticks=12, gi_ticks=8,
                                 weights=(0.0, 1.0), out_path=str(tmp_path / "w8.json"))
    arms = out["seeds"]["2026"]
    assert set(arms) == {"0.0", "1.0"}
    for w, recs in arms.items():
        assert len(recs) == 4
        for r in recs:
            assert 0.0 <= r["gi"] <= 1.0 and 0.0 <= r["move_acc"] <= 1.0


def test_aux_off_weight_drives_grab_logit_down():
    """Vérité-terrain du correctif sur le CANAL (indépendamment de l'in-world) : à init et données
    identiques, la BCE auxiliaire doit pousser le logit grab plus bas que le bras sans elle."""
    from tools.warmstart_evolution_inworld import (_collect_oracle_trajectory,
                                                   _probe_free_channels_by_agent)
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    from src.seed_ai.harness import seed_at
    pytest.importorskip("torch")
    obs, tgt = _collect_oracle_trajectory(2026, 4, 20, 0.75, 12.0)
    mask = [np.ones(len(t), dtype=np.float32) for t in tgt]
    res = {}
    for w in (0.0, 1.0):
        seed_at(2026, 1)
        pop = TorchPopulationModel([MambaAgent() for _ in range(4)], lr=0.5)
        for _ in range(60):
            pop.imitate_episode_bptt(obs, tgt, truncate_window=25, mask_seq=mask, aux_off_weight=w)
        res[w] = float(np.mean(_probe_free_channels_by_agent(pop, obs, tgt)["grab"]))
    assert res[1.0] < res[0.0], f"aux_off inefficace : {res[1.0]:.3f} >= {res[0.0]:.3f}"


def test_aux_off_hinge_has_zero_gradient_below_margin():
    """La charnière doit avoir un gradient EXACTEMENT nul sur un nœud déjà conforme — c'est tout l'intérêt
    vs la BCE, dont le gradient résiduel (0.269 à la borne tanh) perturbait le tronc récurrent partagé."""
    import torch
    import torch.nn.functional as F
    pytest.importorskip("torch")
    margin = 0.2
    for x0, attendu_nul in ((-0.9, True), (-0.5, True), (-0.1, False), (0.5, False)):
        x = torch.tensor([x0], requires_grad=True)
        F.relu(x + margin).sum().backward()
        g = float(x.grad.item())
        assert (g == 0.0) == attendu_nul, f"x={x0} gradient={g} (attendu nul={attendu_nul})"
        # la BCE, elle, garde un gradient partout > 0 : contraste documenté
        y = torch.tensor([x0], requires_grad=True)
        F.binary_cross_entropy_with_logits(y, torch.zeros(1)).backward()
        assert float(y.grad.item()) > 0.0


def test_assert_aux_off_safe_blocks_craft_and_throw_and_explore():
    """La garde runtime doit refuser les 3 configurations où aux_off casse ou est contourné."""
    from tools.warmstart_evolution_inworld import assert_aux_off_safe

    class _Cfg:
        craft_level = 0

    class _Env:
        def __init__(self):
            self.config = _Cfg()
            self.torch_throw_gate = False
            self.explore_eps = 0.0

    e = _Env()
    assert assert_aux_off_safe(e) is True                      # config sûre
    e.config.craft_level = 1
    with pytest.raises(AssertionError, match="craft_level"):
        assert_aux_off_safe(e)
    e.config.craft_level = 0
    e.torch_throw_gate = True
    with pytest.raises(AssertionError, match="torch_throw_gate"):
        assert_aux_off_safe(e)
    e.torch_throw_gate = False
    e.explore_eps = 0.15
    with pytest.raises(AssertionError, match="explore_eps"):
        assert_aux_off_safe(e)


def test_cognitive_demand_flag_reaches_the_world():
    """Le régime doit être PARAMÉTRABLE et atteindre réellement la config du monde. Sans ce flag, le banc
    évalue toujours sous `cognitive_demand=True`, qui COUPE les revenus d'inventaire (fruit +20,
    world_1_stoneage:743-745) en laissant la taxe de portage : l'inventaire y est un coût pur PAR
    CONSTRUCTION, ce qui rend « grab nuit » quasi-tautologique (EDR-WARM-008)."""
    from tools.warmstart_evolution_inworld import _torch_survival_eras
    from src.agents.mamba_agent import MambaAgent
    import src.worlds.world_1_stoneage as w
    pytest.importorskip("torch")
    vus = []
    _orig = w.Biosphere3D

    class _Spy(_orig):
        def step(self, *a, **k):
            vus.append(bool(getattr(self.config, "cognitive_demand", False)))
            return super().step(*a, **k)

    w.Biosphere3D = _Spy
    try:
        for regime in (True, False):
            vus.clear()
            _torch_survival_eras(MambaAgent().genome, False, 2026, 1, 4, 6, 0.75, 12.0,
                                 cognitive_demand=regime)
            assert vus and all(v is regime for v in vus), f"régime {regime} non transmis au monde"
    finally:
        w.Biosphere3D = _orig
