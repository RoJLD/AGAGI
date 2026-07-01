# tests/sandbox/test_substrate_ab_compositional.py
import pytest
import numpy as np

from tools.substrate_ab_compositional import compositional_reward


def test_compositional_reward_truth_table():
    """Récompense étape 2 = +1 SSI (Y correct ET X fait en S1), −1 sinon (les 4 cas)."""
    assert compositional_reward(move2=4, target_y=4, did_x=True) == 1.0    # X✓ Y✓
    assert compositional_reward(move2=4, target_y=4, did_x=False) == -1.0  # X✗ Y✓ : Y seul ne paie pas
    assert compositional_reward(move2=2, target_y=4, did_x=True) == -1.0   # X✓ Y✗
    assert compositional_reward(move2=2, target_y=4, did_x=False) == -1.0  # X✗ Y✗


@pytest.mark.slow
def test_compositional_ab_smoke():
    """Le banc A/B tourne pour les deux backends et renvoie un verdict structuré."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import compare
    res = compare(seeds=(0,), trials=30, n_agents=4)
    assert res["verdict"] in {"GRADIENT_GAGNE", "HEBBIEN_GAGNE", "NEUTRE"}
    assert res["per_seed"] and len(res["per_seed"]) == 1
    row = res["per_seed"][0]
    for k in ("legacy_delta", "torch_delta", "diff"):
        assert k in row


from tools.substrate_ab_compositional import _init_factor, _build_agents


def test_init_factor_anchor_is_one():
    """À num_nodes=172 (hidden=5), le facteur normalisé == 1.0 → normalized ≡ prod (dédup ancrage)."""
    assert _init_factor(172, "normalized") == 1.0
    assert _init_factor(172, "prod") == 1.0


def test_normalized_anchor_equals_prod_factor():
    """À l'ancrage (num_nodes=172, hidden=5), normalized et prod ont le MÊME facteur (1.0)
    → c'est l'invariant qui déclenche la déduplication dans sweep (pas de cellule en double)."""
    assert _init_factor(172, "normalized") == _init_factor(172, "prod") == 1.0
    # Hors ancrage, les facteurs DIVERGENT (pas de dédup) :
    assert _init_factor(187, "normalized") != _init_factor(187, "prod")


def test_init_factor_normalized_formula():
    """Facteur normalisé = sqrt(171/(N-1)) ; prod toujours 1.0 quelle que soit la taille."""
    assert _init_factor(267, "normalized") == pytest.approx(np.sqrt(171.0 / 266.0))
    assert _init_factor(187, "normalized") == pytest.approx(np.sqrt(171.0 / 186.0))
    assert _init_factor(267, "prod") == 1.0


def test_build_agents_size_mapping():
    """num_nodes contrôle la taille ; I/O restent fixes (59/108) ; hidden = num_nodes-167."""
    agents = _build_agents(3, 187, "prod")
    assert len(agents) == 3
    for a in agents:
        assert a.genome.num_nodes == 187
        assert a.genome.num_inputs == 59
        assert a.genome.num_outputs == 108


def test_build_agents_normalized_scales_W():
    """init normalisé multiplie W par sqrt(171/(N-1)) ; prod laisse W intact (même seed)."""
    np.random.seed(7)
    prod = _build_agents(2, 267, "prod")
    np.random.seed(7)
    norm = _build_agents(2, 267, "normalized")
    factor = np.sqrt(171.0 / 266.0)
    for p, q in zip(prod, norm):
        assert np.allclose(q.genome.W, p.genome.W * factor, atol=1e-5)


@pytest.mark.slow
def test_sweep_smoke():
    """sweep renvoie une cellule par (hidden,init) avec verdict structuré + courbe non vide."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import sweep
    res = sweep(hiddens=(5, 20), inits=("prod",), seeds=(0,), trials=20, n_agents=4)
    assert res["cells"] and len(res["cells"]) == 2
    for c in res["cells"]:
        assert c["verdict"] in {"GRADIENT_GAGNE", "HEBBIEN_GAGNE", "NEUTRE"}
        assert c["hidden"] in (5, 20) and c["init"] == "prod"
        assert c["per_seed"] and len(c["per_seed"]) == 1
    assert len(res["curve"]["legacy"]) == 2 and len(res["curve"]["torch"]) == 2
    assert all("median_hit_end" in p for p in res["curve"]["torch"])


def test_decode_auc_separable_signal():
    """Sur un signal linéairement séparable, l'AUC du décodeur ≈ 1."""
    import numpy as np
    from tools.substrate_ab_compositional import _decode_auc
    rng = np.random.RandomState(0)
    y = np.array([0, 1] * 60)                          # 120 samples, 2 classes équilibrées
    X = rng.randn(120, 4) + y[:, None] * 6.0           # signal fort corrélé à y
    auc = _decode_auc(X, y, min_per_class=8, seed=0)
    assert auc is not None and auc > 0.9


def test_decode_auc_pure_noise():
    """Sur du bruit indépendant de y, l'AUC ≈ 0.5 (pas de signal décodable)."""
    import numpy as np
    from tools.substrate_ab_compositional import _decode_auc
    rng = np.random.RandomState(1)
    y = np.array([0, 1] * 60)
    X = rng.randn(120, 4)                               # aucun lien avec y
    auc = _decode_auc(X, y, min_per_class=8, seed=0)
    assert auc is not None and 0.35 <= auc <= 0.65


def test_decode_auc_missing_class_returns_none():
    """Si une classe manque (ou < min_per_class), renvoie None (agent non qualifiant)."""
    import numpy as np
    from tools.substrate_ab_compositional import _decode_auc
    X = np.random.RandomState(2).randn(40, 4)
    y_one_class = np.zeros(40, dtype=int)              # une seule classe
    assert _decode_auc(X, y_one_class, min_per_class=8, seed=0) is None
    y_too_few = np.array([1] * 3 + [0] * 37)           # classe 1 < min_per_class
    assert _decode_auc(X, y_too_few, min_per_class=8, seed=0) is None


def test_read_state_legacy_shape():
    """_read_state(legacy) renvoie l'état récurrent batché (B, N) après un forward."""
    import numpy as np
    from src.agents.backend import make_population
    from tools.substrate_ab_compositional import _build_agents, _read_state
    np.random.seed(0)
    agents = _build_agents(4, 172, "prod")
    pop = make_population(agents, backend="legacy")
    obs = (np.random.RandomState(1).randn(4, agents[0].genome.num_inputs) * 0.5).astype(np.float32)
    pop.forward(obs)
    st = _read_state(pop, "legacy")
    assert st.shape == (4, 172)


@pytest.mark.slow
def test_read_state_torch_shape():
    """_read_state(torch) renvoie pop.H sous forme numpy (B, N)."""
    pytest.importorskip("torch")
    import numpy as np
    from src.agents.backend import make_population
    from tools.substrate_ab_compositional import _build_agents, _read_state
    np.random.seed(0)
    agents = _build_agents(4, 172, "prod")
    pop = make_population(agents, backend="torch")
    obs = (np.random.RandomState(1).randn(4, agents[0].genome.num_inputs) * 0.5).astype(np.float32)
    pop.forward(obs)
    st = _read_state(pop, "torch")
    assert st.shape == (4, 172)


@pytest.mark.slow
def test_memory_probe_smoke():
    """memory_probe renvoie un dict structuré ; le contrôle permutation est dans la bande chance (≈0.5)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import memory_probe
    res = memory_probe(seeds=(0,), n_agents=8, trials=60)
    assert res["verdict"] in {"MEMORY_PRESENT", "MEMORY_ABSENT", "ASYMÉTRIQUE"}
    assert "control_valid" in res
    assert res["cells"]
    for c in res["cells"]:
        assert c["backend"] in {"legacy", "torch"}
        for k in ("n_qualifying", "base_rate", "median_auc_s2", "median_auc_pre", "median_delta",
                  "median_auc_shuffled"):
            assert k in c
        # Le contrôle permutation (labels mélangés sur H_S2) est la vraie baseline chance :
        # H_pre est confondu (causalement amont de did_x) et ne constitue PAS un contrôle fiable.
        if c["median_auc_shuffled"] is not None:
            assert 0.3 <= c["median_auc_shuffled"] <= 0.7   # contrôle permutation dans la bande chance


def test_warmup_reward_rule():
    """Phase A (warmup) : reward = +1 si l'action == target_x (did_x), sinon −1. Pur."""
    from tools.substrate_ab_compositional import _warmup_reward
    assert _warmup_reward(move1=0, target_x=0) == 1.0
    assert _warmup_reward(move1=3, target_x=0) == -1.0
    assert _warmup_reward(move1=4, target_x=4) == 1.0


@pytest.mark.slow
def test_run_curriculum_warmup0_is_compositional():
    """warmup_trials=0 → phase A vide → run_curriculum exécute la phase B seule (plancher compo)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum
    r = run_curriculum("legacy", seed=0, warmup_trials=0, compo_trials=40, n_agents=4)
    # warmup vide → did_x de warmup non défini/neutre ; les clés existent et hit ∈ [0,1]
    for k in ("warmup_didx_end", "hit_start", "hit_end", "compo_didx_end", "delta"):
        assert k in r
    assert 0.0 <= r["hit_end"] <= 1.0
    assert r["warmup_didx_start"] == 0.0
    assert r["warmup_didx_end"] == 0.0


@pytest.mark.slow
def test_compare_curriculum_smoke():
    """compare_curriculum renvoie un verdict curriculum structuré + per_seed avec les trajectoires."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import compare_curriculum
    res = compare_curriculum(seeds=(0,), warmup_trials=40, compo_trials=40, n_agents=4)
    assert res["verdict_curriculum"] in {"DISCOVERY", "CREDIT", "WARMUP_FAILED", "AMBIGU"}
    assert res["per_seed"] and len(res["per_seed"]) == 1
    row = res["per_seed"][0]
    for k in ("legacy", "torch"):
        for kk in ("warmup_didx_end", "hit_end", "compo_didx_end"):
            assert kk in row[k]


def test_fade_weight_linear_decay():
    """fade_w = w0·(1−t/T) : plein à t=0, 0 à t=T, moitié à t=T/2 ; w0=0 → 0 partout (bascule dure)."""
    from tools.substrate_ab_compositional import _fade_weight
    assert _fade_weight(0, 100, 1.0) == 1.0
    assert _fade_weight(100, 100, 1.0) == 0.0
    assert _fade_weight(50, 100, 1.0) == 0.5
    assert _fade_weight(0, 100, 0.0) == 0.0
    assert _fade_weight(50, 100, 0.0) == 0.0


def test_p_y_given_x_conditional():
    """P(Y|X) = fraction de y_correct PARMI les trials où did_x ; None si aucun did_x."""
    import numpy as np
    from tools.substrate_ab_compositional import _p_y_given_x
    # did_x sur trials 0,1 ; y_correct sur 0 seulement → 1/2 = 0.5
    assert _p_y_given_x(np.array([True, False, True, True]),
                        np.array([True, True, False, False])) == 0.5
    # tous did_x, tous y → 1.0
    assert _p_y_given_x(np.array([True, True]), np.array([True, True])) == 1.0
    # aucun did_x → None
    assert _p_y_given_x(np.array([True, True]), np.array([False, False])) is None


@pytest.mark.slow
def test_run_curriculum_fade_keys_and_w0_zero():
    """run_curriculum_fade renvoie les clés (dont p_y_given_x_end) ; fade_w0=0 tourne sans erreur."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade
    r = run_curriculum_fade("legacy", seed=0, warmup_trials=10, compo_trials=40, n_agents=4, fade_w0=0.0)
    for k in ("warmup_didx_end", "hit_end", "compo_didx_end", "p_y_given_x_end", "y_rate_end", "delta"):
        assert k in r
    assert 0.0 <= r["hit_end"] <= 1.0
    assert (r["p_y_given_x_end"] is None) or (0.0 <= r["p_y_given_x_end"] <= 1.0)


@pytest.mark.slow
def test_compare_curriculum_fade_smoke():
    """compare_curriculum_fade renvoie un verdict_fade structuré + per_seed avec P(Y|X)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import compare_curriculum_fade
    res = compare_curriculum_fade(seeds=(0,), warmup_trials=40, compo_trials=40, n_agents=4)
    assert res["verdict_fade"] in {"CEILING_WAS_RETENTION", "CEILING_WAS_BINDING",
                                   "FADE_INEFFECTIVE", "AMBIGU"}
    assert res["per_seed"] and len(res["per_seed"]) == 1
    row = res["per_seed"][0]
    for arm in ("legacy", "torch"):
        for k in ("hit_end", "compo_didx_end", "p_y_given_x_end"):
            assert k in row[arm]


# --- Levier binding par le SIGNAL : punir Y-sans-X (EDR 126 suite) ---

def test_compositional_reward_penalized_penalty0_equals_baseline():
    """À penalty=0, la récompense pénalisée == compositional_reward (les 4 cas) : le baseline
    reproduit EXACTEMENT EDR 126 (garantie structurelle de la dose-réponse)."""
    from tools.substrate_ab_compositional import compositional_reward_penalized as pen, compositional_reward as base
    for move2, did_x in [(4, True), (4, False), (2, True), (2, False)]:
        assert pen(move2, 4, did_x, 0.0) == base(move2, 4, did_x)


def test_compositional_reward_penalized_makes_y_without_x_harsher_than_silence():
    """penalty>0 : Y-sans-X (−1−p) est PLUS punitif que le silence ¬Y (−1) → pression DIFFÉRENTIELLE
    forçant le conditionnement. Y&X reste +1 (le seul chemin payant)."""
    from tools.substrate_ab_compositional import compositional_reward_penalized as pen
    assert pen(move2=4, target_y=4, did_x=True, y_without_x_penalty=1.0) == 1.0     # Y&X : inchangé
    assert pen(move2=4, target_y=4, did_x=False, y_without_x_penalty=1.0) == -2.0   # Y&¬X : surpuni
    assert pen(move2=2, target_y=4, did_x=False, y_without_x_penalty=1.0) == -1.0   # ¬Y : silence
    # l'ordre est ce qui compte : silence (−1) STRICTEMENT préféré à Y-sans-X (−2)
    assert pen(4, 4, False, 1.0) < pen(2, 4, False, 1.0)


def test_p_y_given_not_x_conditional():
    """P(Y|¬X) = fraction de y_correct parmi les trials ¬did_x (dénominateur du binding_gap).
    None si aucun ¬did_x."""
    import numpy as np
    from tools.substrate_ab_compositional import _p_y_given_not_x
    # did_x = [T,F,F,T], y_correct=[T,T,F,T] → parmi ¬X (idx 1,2) : y=[T,F] → 0.5
    assert _p_y_given_not_x(np.array([True, True, False, True]),
                            np.array([True, False, False, True])) == 0.5
    assert _p_y_given_not_x(np.array([True, True]), np.array([False, False])) == 1.0  # tous ¬X, tous Y
    assert _p_y_given_not_x(np.array([True, True]), np.array([True, True])) is None   # aucun ¬X


@pytest.mark.slow
def test_run_curriculum_fade_penalty_keys_and_gap():
    """run_curriculum_fade accepte y_without_x_penalty et renvoie p_y_given_not_x_end + binding_gap_end
    (= P(Y|X) − P(Y|¬X)) ; penalty=0 tourne comme le baseline."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade
    r = run_curriculum_fade("torch", seed=0, warmup_trials=10, compo_trials=40, n_agents=4,
                            fade_w0=1.0, y_without_x_penalty=1.0)
    for k in ("p_y_given_x_end", "p_y_given_not_x_end", "binding_gap_end", "y_rate_end"):
        assert k in r
    # gap défini ssi les deux conditionnels existent
    if r["p_y_given_x_end"] is not None and r["p_y_given_not_x_end"] is not None:
        assert abs(r["binding_gap_end"] - (r["p_y_given_x_end"] - r["p_y_given_not_x_end"])) < 1e-9


@pytest.mark.slow
def test_sweep_binding_penalty_smoke():
    """sweep_binding_penalty renvoie une ligne par (penalty, backend) avec le gap de binding."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import sweep_binding_penalty
    res = sweep_binding_penalty(seeds=(0,), penalties=(0.0, 1.0), warmup_trials=30,
                                compo_trials=30, n_agents=4)
    assert res["rows"]
    for row in res["rows"]:
        for k in ("penalty", "backend", "seed", "p_y_given_x_end", "p_y_given_not_x_end",
                  "binding_gap_end", "y_rate_end", "hit_end"):
            assert k in row


# --- Levier 2 : GATING archi did_x -> logit Y (EDR 126 suite, chantier binding-gate) ---

@pytest.mark.slow
def test_run_curriculum_fade_gated_none_keys():
    """gate_mode='none' : mêmes clés que le fade + gate_mode ; tourne sans erreur (≈ baseline)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=20, compo_trials=40, n_agents=4,
                                  gate_mode="none")
    for k in ("p_y_given_x_end", "p_y_given_not_x_end", "binding_gap_end", "y_rate_end", "gate_mode"):
        assert k in r
    assert r["gate_mode"] == "none"


@pytest.mark.slow
def test_gated_oracle_opens_binding_gap():
    """CONTRÔLE POSITIF : le gate ORACLE (biais câblé ±selon did_x VRAI sur le logit Y) DOIT ouvrir
    un gap de binding large (P(Y|X)≫P(Y|¬X)) → valide que l'instrument détecte le binding quand il
    existe, et que la tâche est solvable par routage did_x→Y."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=60, compo_trials=120, n_agents=6,
                                  gate_mode="oracle", oracle_bias=8.0)
    # biais ±8 domine les logits → move2=Y quasi ssi did_x → gap franchement positif
    assert r["binding_gap_end"] is not None and r["binding_gap_end"] > 0.5


@pytest.mark.slow
def test_gated_learned_runs_and_returns_gap():
    """gate_mode='learned' : le gate entraînable (REINFORCE sur H_S2) tourne et renvoie un gap ∈ [-1,1]."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=40, compo_trials=60, n_agents=4,
                                  gate_mode="learned", gate_lr=0.05)
    assert r["gate_mode"] == "learned"
    assert (r["binding_gap_end"] is None) or (-1.0 <= r["binding_gap_end"] <= 1.0)


def test_gated_invalid_mode_raises():
    """Un gate_mode inconnu lève ValueError (garde-fou explicite)."""
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    with pytest.raises(ValueError):
        run_curriculum_fade_gated("torch", gate_mode="bogus", warmup_trials=1, compo_trials=1, n_agents=2)


@pytest.mark.slow
def test_compare_gate_modes_smoke():
    """compare_gate_modes renvoie un verdict + per_mode avec gap per-seed (expose la bimodalité)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import compare_gate_modes
    res = compare_gate_modes(seeds=(0,), modes=("none", "oracle"), warmup_trials=30, compo_trials=30,
                             n_agents=4)
    assert res["verdict"] in {"GATE_BINDS", "GATE_COLLAPSES", "GATE_INTERMITTENT", "AMBIGU"}
    for mode in ("none", "oracle"):
        for k in ("gap_median", "gap_per_seed", "n_bind", "n_seeds"):
            assert k in res["per_mode"][mode]


# --- Levier 3 : crédit/optimisation du gate (entropy + éligibilité) — fiabiliser le binding (EDR 129 suite) ---

@pytest.mark.slow
def test_gated_learned_entropy_and_eligibility_run():
    """Le gate learned accepte entropy_coef (anti-collapse) et elig_lambda (trace) et tourne."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=30, compo_trials=40, n_agents=4,
                                  gate_mode="learned", entropy_coef=0.05, elig_lambda=0.5)
    assert r["gate_mode"] == "learned"
    assert r["entropy_coef"] == 0.05 and r["elig_lambda"] == 0.5
    assert (r["binding_gap_end"] is None) or (-1.0 <= r["binding_gap_end"] <= 1.0)


def test_gated_entropy_default_zero_is_baseline_reinforce():
    """Par défaut entropy_coef=0 et elig_lambda=0 → REINFORCE nu (baseline EDR 129, rétrocompat)."""
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    import inspect
    sig = inspect.signature(run_curriculum_fade_gated)
    assert sig.parameters["entropy_coef"].default == 0.0
    assert sig.parameters["elig_lambda"].default == 0.0


@pytest.mark.slow
def test_sweep_gate_reliability_smoke():
    """sweep_gate_reliability : n_bind/n_seeds par config d'optimisation (fiabilité du binding)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import sweep_gate_reliability
    res = sweep_gate_reliability(seeds=(0, 1), configs=({"entropy_coef": 0.0}, {"entropy_coef": 0.05}),
                                 warmup_trials=30, compo_trials=30, n_agents=4)
    assert res["rows"]
    for row in res["rows"]:
        for k in ("config", "n_bind", "n_seeds", "gap_median", "gap_per_seed"):
            assert k in row


# --- Diagnostic collapse (suite EDR 130) : prédicteurs bind vs collapse ---

@pytest.mark.slow
def test_capture_probe_adds_early_diagnostics():
    """capture_probe=True ajoute did_x_auc_early ; les métriques de fenêtre précoce sont toujours là."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=30, compo_trials=40, n_agents=6,
                                  gate_mode="learned", capture_probe=True)
    for k in ("binding_gap_start", "y_rate_start", "did_x_auc_early"):
        assert k in r
    assert (r["did_x_auc_early"] is None) or (0.0 <= r["did_x_auc_early"] <= 1.0)
    assert 0.0 <= r["y_rate_start"] <= 1.0


def test_capture_probe_off_by_default():
    """Sans capture_probe, pas de clé did_x_auc_early (coût sklearn évité par défaut)."""
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    import inspect
    assert inspect.signature(run_curriculum_fade_gated).parameters["capture_probe"].default is False


@pytest.mark.slow
def test_probe_collapse_predictors_smoke():
    """probe_collapse_predictors : rows per-seed + prédicteurs (moyenne bind vs collapse)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import probe_collapse_predictors
    res = probe_collapse_predictors(seeds=(0, 1), warmup_trials=30, compo_trials=40, n_agents=4)
    assert res["n_seeds"] == 2 and res["rows"]
    for k in ("did_x_auc_early", "y_rate_start", "binding_gap_start"):
        assert k in res["predictors"]
        for stat in ("bind_mean", "collapse_mean", "separation"):
            assert stat in res["predictors"][k]
    for row in res["rows"]:
        for k in ("seed", "bound", "binding_gap_end", "did_x_auc_early", "y_rate_start"):
            assert k in row


# --- Warm-start du gate (test causal path-dependence, suite EDR 131) ---

def test_gated_warmstart_default_zero_is_baseline():
    """Par défaut gate_warmstart_trials=0 → aucun pré-entraînement (rétrocompat EDR 129/131)."""
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    import inspect
    assert inspect.signature(run_curriculum_fade_gated).parameters["gate_warmstart_trials"].default == 0


def test_gated_warmstart_runs_and_reports_trials():
    """gate_warmstart_trials>0 pré-entraîne le gate à imiter l'oracle depuis H_S2 puis tourne ;
    le nombre de trials de warm-start est reporté dans la sortie."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=30, compo_trials=40, n_agents=4,
                                  gate_mode="learned", gate_warmstart_trials=20)
    assert r["gate_warmstart_trials"] == 20
    assert (r["binding_gap_end"] is None) or (-1.0 <= r["binding_gap_end"] <= 1.0)


def test_gated_warmstart_ignored_when_not_learned():
    """Le warm-start ne s'applique qu'au gate learned : none/oracle tournent sans erreur avec le param."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=20, compo_trials=20, n_agents=4,
                                  gate_mode="none", gate_warmstart_trials=20)
    assert r["gate_mode"] == "none"
    assert r["gate_warmstart_trials"] == 20


def test_gated_freeze_after_warmstart_default_false():
    """Par défaut freeze_gate_after_warmstart=False → gate plastique en phase B (rétrocompat)."""
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    import inspect
    p = inspect.signature(run_curriculum_fade_gated).parameters["freeze_gate_after_warmstart"]
    assert p.default is False


def test_gated_freeze_after_warmstart_runs():
    """freeze_gate_after_warmstart=True : le gate warm-starté n'est plus mis à jour en phase B, tourne."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=30, compo_trials=40, n_agents=4,
                                  gate_mode="learned", gate_warmstart_trials=30,
                                  freeze_gate_after_warmstart=True)
    assert r["freeze_gate_after_warmstart"] is True
    assert (r["binding_gap_end"] is None) or (-1.0 <= r["binding_gap_end"] <= 1.0)


def test_capture_gate_bias_off_by_default():
    """Sans capture_gate_bias, pas de clés de biais du gate (coût évité)."""
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    import inspect
    assert inspect.signature(run_curriculum_fade_gated).parameters["capture_gate_bias"].default is False


def test_capture_gate_bias_reports_conditional_bias():
    """capture_gate_bias=True : biais MOYEN du gate en phase B, séparé did_x vs ¬did_x.
    Sur un gate warm-starté à imiter l'oracle (+8/−8), le biais sur did_x doit être > celui sur ¬did_x
    (marge de conditionnement) — c'est l'instrument qui distingue sous-ajustement de marge vs offset."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=1, warmup_trials=30, compo_trials=40, n_agents=4,
                                  gate_mode="learned", gate_warmstart_trials=60,
                                  freeze_gate_after_warmstart=True, capture_gate_bias=True)
    for k in ("gate_bias_didx_end", "gate_bias_notdidx_end", "gate_bias_margin_end"):
        assert k in r
    # marge = biais(did_x) − biais(¬did_x) ; cohérence interne
    if r["gate_bias_margin_end"] is not None:
        assert abs(r["gate_bias_margin_end"]
                   - (r["gate_bias_didx_end"] - r["gate_bias_notdidx_end"])) < 1e-4


@pytest.mark.slow
def test_sweep_gate_warmstart_smoke():
    """sweep_gate_warmstart : n_bind/n_seeds par niveau de warm-start (test causal path-dependence)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import sweep_gate_warmstart
    res = sweep_gate_warmstart(seeds=(0, 1), warmstart_levels=(0, 20),
                               warmup_trials=30, compo_trials=30, n_agents=4)
    assert res["rows"] and "verdict" in res
    for row in res["rows"]:
        for k in ("warmstart", "n_bind", "n_seeds", "gap_median", "gap_per_seed"):
            assert k in row


# --- Readout non-linéaire du gate (test de l'actionnable migration, suite EDR 132) ---

def test_gate_hidden_default_zero_is_linear():
    """Par défaut gate_hidden=0 → gate LINÉAIRE (rétrocompat EDR 129-132)."""
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    import inspect
    assert inspect.signature(run_curriculum_fade_gated).parameters["gate_hidden"].default == 0


def test_gate_mlp_runs_and_reports_hidden():
    """gate_hidden>0 : le gate devient un MLP (H_S2 → tanh → biais Y), tourne, reporte gate_hidden."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=30, compo_trials=40, n_agents=4,
                                  gate_mode="learned", gate_hidden=8)
    assert r["gate_hidden"] == 8
    assert (r["binding_gap_end"] is None) or (-1.0 <= r["binding_gap_end"] <= 1.0)


def test_gate_mlp_composes_with_warmstart_and_bias_capture():
    """Le MLP compose avec warm-start (régression MSE vers oracle) et capture_gate_bias."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=1, warmup_trials=30, compo_trials=40, n_agents=4,
                                  gate_mode="learned", gate_hidden=8, gate_warmstart_trials=40,
                                  capture_gate_bias=True)
    assert r["gate_hidden"] == 8
    for k in ("gate_bias_didx_end", "gate_bias_notdidx_end", "gate_bias_margin_end"):
        assert k in r


def test_capture_probe_adds_late_auc():
    """capture_probe expose aussi did_x_auc_late (séparabilité TARDIVE que lit le gate) — contrôle
    bassin-d'optim vs features-tardives-pauvres (suite revue EDR 133)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=30, compo_trials=40, n_agents=6,
                                  gate_mode="learned", capture_probe=True)
    assert "did_x_auc_late" in r
    assert (r["did_x_auc_late"] is None) or (0.0 <= r["did_x_auc_late"] <= 1.0)


@pytest.mark.slow
def test_sweep_gate_readout_smoke():
    """sweep_gate_readout : n_bind/gap/marge par niveau gate_hidden (test readout non-linéaire)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import sweep_gate_readout
    res = sweep_gate_readout(seeds=(0, 1), hidden_levels=(0, 8),
                             warmup_trials=30, compo_trials=30, n_agents=4)
    assert res["rows"] and "verdict" in res
    for row in res["rows"]:
        for k in ("gate_hidden", "n_bind", "n_seeds", "gap_median", "per_seed", "bound_seeds"):
            assert k in row


# --- Anti-saturation-Y de la politique de base (verrou résiduel EDR 133 = bassin d'optim) ---

def test_apply_y_saturation_penalty_coef0_is_identity():
    """coef=0 → récompense inchangée (rétrocompat garantie)."""
    from tools.substrate_ab_compositional import _apply_y_saturation_penalty
    r = np.array([1.0, -1.0, 1.0, -1.0], dtype=np.float32)
    move2 = np.array([4, 0, 4, 1])
    out = _apply_y_saturation_penalty(r, move2, target_y=4, coef=0.0, y_target=0.5)
    assert np.allclose(out, r)


def test_apply_y_saturation_penalty_only_when_marginal_exceeds_target():
    """Sous la cible → identité ; au-dessus → seuls les Y-pickers pénalisés de coef*(y_rate−cible)."""
    from tools.substrate_ab_compositional import _apply_y_saturation_penalty
    r = np.array([1.0, 1.0, 1.0, -1.0], dtype=np.float32)
    move2 = np.array([4, 4, 4, 0])              # y_rate = 3/4 = 0.75
    # cible 0.8 > 0.75 → pas de pénalité
    out_lo = _apply_y_saturation_penalty(r, move2, target_y=4, coef=2.0, y_target=0.8)
    assert np.allclose(out_lo, r)
    # cible 0.25 < 0.75 → excess 0.5, pénalité 2.0*0.5=1.0 sur les 3 Y-pickers, pas le non-Y
    out_hi = _apply_y_saturation_penalty(r, move2, target_y=4, coef=2.0, y_target=0.25)
    assert np.allclose(out_hi, np.array([0.0, 0.0, 0.0, -1.0], dtype=np.float32))


def test_gated_y_saturation_default_zero_is_baseline():
    """Par défaut y_saturation_penalty=0 → régime EDR 129-133 inchangé."""
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    import inspect
    p = inspect.signature(run_curriculum_fade_gated).parameters["y_saturation_penalty"]
    assert p.default == 0.0


def test_gated_y_saturation_runs_and_reports():
    """y_saturation_penalty>0 tourne et est reporté ; y_rate_end reste borné."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=30, compo_trials=40, n_agents=4,
                                  gate_mode="learned", y_saturation_penalty=1.5, y_saturation_target=0.5)
    assert r["y_saturation_penalty"] == 1.5
    assert 0.0 <= r["y_rate_end"] <= 1.0


@pytest.mark.slow
def test_sweep_y_saturation_smoke():
    """sweep_y_saturation : n_bind + y_rate par coef de pénalité anti-saturation."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import sweep_y_saturation
    res = sweep_y_saturation(seeds=(0, 1), penalties=(0.0, 1.0),
                             warmup_trials=30, compo_trials=30, n_agents=4)
    assert res["rows"] and "verdict" in res
    for row in res["rows"]:
        for k in ("penalty", "n_bind", "n_seeds", "gap_median", "y_rate_start_median", "per_seed"):
            assert k in row


def test_y_saturation_scope_default_both_and_invalid_raises():
    """Défaut y_saturation_scope='both' (base+gate, rétrocompat) ; valeur inconnue → ValueError."""
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    import inspect
    assert inspect.signature(run_curriculum_fade_gated).parameters["y_saturation_scope"].default == "both"
    with pytest.raises(ValueError):
        run_curriculum_fade_gated("torch", seed=0, warmup_trials=5, compo_trials=5, n_agents=3,
                                  gate_mode="learned", y_saturation_scope="bogus")


def test_y_saturation_scope_base_lets_gate_see_raw_reward():
    """scope='base' tourne (le gate lit la reward brute, seule pop.learn est pénalisée) — décompose
    le locus base vs gate (revue EDR 134)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade_gated
    r = run_curriculum_fade_gated("torch", seed=0, warmup_trials=30, compo_trials=40, n_agents=4,
                                  gate_mode="learned", y_saturation_penalty=3.0, y_saturation_scope="base")
    assert r["y_saturation_scope"] == "base"
    assert (r["binding_gap_end"] is None) or (-1.0 <= r["binding_gap_end"] <= 1.0)


@pytest.mark.slow
def test_sweep_y_saturation_per_seed_carries_real_metrics():
    """Le per_seed remonte P(Y|X)/hit_end/y_rate_end (anti-artefact du gap) — revue EDR 134."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import sweep_y_saturation
    res = sweep_y_saturation(seeds=(0, 1), penalties=(0.0, 3.0),
                             warmup_trials=30, compo_trials=30, n_agents=4)
    for row in res["rows"]:
        assert "hit_end_median" in row
        for cell in row["per_seed"]:
            for k in ("seed", "gap", "p_y_given_x", "p_y_given_not_x", "hit_end", "y_rate_end"):
                assert k in cell
