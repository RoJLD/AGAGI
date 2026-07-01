"""A/B de learnabilité COMPOSITIONNELLE du substrat (means→ends) — porte de décision torch-prod.

Question : un substrat `torch` (autograd) apprend-il une contingence 2-étapes — faire X en S1
(récompense IMMÉDIATE nulle) puis Y en S2 récompensé SEULEMENT si X a été fait — que le substrat
`legacy` (hebbien/Actor-Critic TD numpy, ~5 cachés) NE peut pas ? C'est l'apex craft→chasse en
miniature. `obs_B` n'encode PAS `did_X` -> l'agent doit le MÉMORISER (récurrence) = vraie composition.

Réutilise le backend abstrait (`make_population`, ADR-003) + `compute_ab_verdict` de `substrate_ab`
SANS les modifier. PORTÉE : micro-tâche, PAS une preuve de transfert apex en prod.

Usage : python tools/substrate_ab_compositional.py   (env: SABC_SEEDS, SABC_TRIALS, SABC_AGENTS)
"""
import os
import sys

import numpy as np
import statistics
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from tools.substrate_ab import compute_ab_verdict, _MOVE


def compositional_reward(move2: int, target_y: int, did_x: bool) -> float:
    """Récompense d'étape 2 : +1 SSI l'action Y est correcte ET X a été fait en S1, sinon −1.
    PURE et testable. C'est ce qui rend la tâche COMPOSITIONNELLE (Y ne paie que via X)."""
    return 1.0 if (move2 == target_y and did_x) else -1.0


def compositional_reward_penalized(move2: int, target_y: int, did_x: bool,
                                   y_without_x_penalty: float = 0.0) -> float:
    """Récompense d'étape 2 avec SURCOÛT sur Y-sans-X (levier binding par le signal, suite EDR 126).
    Y&X → +1 (seul chemin payant) ; Y&¬X → −1 − penalty (PLUS punitif que le silence) ; ¬Y → −1.
    penalty=0 ≡ compositional_reward EXACTEMENT (baseline EDR 126). Le baseline actuel donne le MÊME
    −1 à « Y-sans-X » et au silence → aucune pression DIFFÉRENTIELLE pour conditionner Y sur X ;
    penalty>0 rend le silence strictement préférable à Y-sans-X → force P(Y|¬X)→0. PUR."""
    if move2 == target_y:
        return 1.0 if did_x else (-1.0 - y_without_x_penalty)
    return -1.0


def _init_factor(num_nodes: int, init_scale: str) -> float:
    """Facteur d'échelle d'init des poids. `normalized` = sqrt(171/(N-1)) → maintient la variance
    d'excitation (Σ_{k≠j} H_k W_kj ∝ (N-1)·Var(W)) ≈ invariante à N, calibrée sur N_ref=172.
    À N=172 → 1.0 (anchor identique à prod). `prod` → 1.0 (init MambaAgent intact). PUR."""
    if init_scale == "normalized":
        return float(np.sqrt(171.0 / (num_nodes - 1)))
    return 1.0


def _build_agents(n_agents: int, num_nodes: int, init_scale: str) -> list:
    """Construit n_agents MambaAgent à `num_nodes` (hidden = num_nodes-167, I/O fixes 59/108),
    puis applique l'échelle d'init au niveau GÉNOME (backend-agnostique : legacy et torch lisent
    le même W). Le caller seed np.random avant d'appeler (déterminisme)."""
    agents = [MambaAgent(num_nodes=num_nodes) for _ in range(n_agents)]
    factor = _init_factor(num_nodes, init_scale)
    if factor != 1.0:
        for a in agents:
            a.genome.W = (a.genome.W * factor).astype(np.float32)
    return agents


def _decode_auc(X, y, *, min_per_class: int = 8, seed: int = 0):
    """ROC-AUC d'une régression logistique linéaire décodant y depuis X (split train/test stratifié
    70/30, StandardScaler). Renvoie None si une classe a < min_per_class échantillons (agent non
    qualifiant). Mesure la décodabilité LINÉAIRE de y (pur, testable sans backend)."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y).astype(int)
    n0 = int(np.sum(y == 0))
    n1 = int(np.sum(y == 1))
    if n0 < min_per_class or n1 < min_per_class:
        return None
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, stratify=y, random_state=seed)
    if len(np.unique(y_tr)) < 2 or len(np.unique(y_te)) < 2:
        return None
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    clf.fit(X_tr, y_tr)
    proba = clf.predict_proba(X_te)[:, 1]
    return float(roc_auc_score(y_te, proba))


def _read_state(pop, backend: str):
    """Lit l'état récurrent batché (B, N) du backend (LECTURE SEULE, ne modifie rien).
    legacy -> MambaBatchModel.H_prev_batch ; torch -> TorchPopulationModel.H."""
    if backend == "torch":
        return pop.H.detach().cpu().numpy().copy()
    return np.asarray(pop._model.H_prev_batch, dtype=np.float64).copy()


def run_compositional(backend: str, seed: int = 0, trials: int = 100, n_agents: int = 8,
                      target_x: int = 0, target_y: int = 4,
                      num_nodes: int = 172, init_scale: str = "prod") -> dict:
    """Entraîne une pop sur la tâche 2-étapes. Renvoie le taux d'essais PLEINEMENT corrects
    (X-puis-Y) début vs fin (delta = apprentissage compositionnel)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    agents = _build_agents(n_agents, num_nodes, init_scale)
    pop = make_population(agents, backend=backend)
    rng = np.random.RandomState(seed + 1)
    n_in = agents[0].genome.num_inputs
    obs_a = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)   # état S1 (motif fixe)
    obs_b = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)   # état S2 (motif distinct)
    zeros = np.zeros(n_agents, dtype=np.float32)

    full = []
    for _ in range(trials):
        # Étape 1 (S1) : émettre X, récompense différée (0). La récurrence retient l'état.
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        pop.learn(zeros, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])
        # Étape 2 (S2) : émettre Y, récompensé SSI X fait en S1 (obs_b n'encode pas did_x).
        preds2, _ = pop.forward(obs_b)
        move2 = np.asarray(preds2)[:, :_MOVE].argmax(axis=1)
        reward2 = np.array([compositional_reward(int(move2[i]), target_y, bool(did_x[i]))
                            for i in range(n_agents)], dtype=np.float32)
        pop.learn(reward2, [{"move": int(m), "grab": 0, "rub": 0} for m in move2])
        full.append(float(np.mean((move2 == target_y) & did_x)))   # essai pleinement correct

    q = max(1, trials // 4)
    hit_start, hit_end = float(np.mean(full[:q])), float(np.mean(full[-q:]))
    return {"backend": backend, "seed": int(seed), "trials": trials, "n_agents": n_agents,
            "hit_start": hit_start, "hit_end": hit_end, "delta": hit_end - hit_start}


def _warmup_reward(move1: int, target_x: int) -> float:
    """Phase A : récompense DENSE directe sur l'action X de S1. +1 si did_x, −1 sinon. PURE."""
    return 1.0 if move1 == target_x else -1.0


def _fade_weight(t: int, total: int, w0: float) -> float:
    """Poids de maintien de X en phase B : décroissance LINÉAIRE w0·(1−t/total) (plein à t=0, 0 à
    t=total). w0=0 → 0 partout (≡ bascule dure). PUR."""
    if total <= 0 or w0 == 0.0:
        return 0.0
    return float(w0 * (1.0 - t / total))


def _p_y_given_x(y_correct, did_x):
    """P(Y correct | X fait) = fraction de y_correct PARMI les trials où did_x est vrai.
    None si aucun did_x (conditionnel indéfini). MESURE directe du binding (pas d'inférence). PUR."""
    y_correct = np.asarray(y_correct, dtype=bool)
    did_x = np.asarray(did_x, dtype=bool)
    n = int(np.sum(did_x))
    if n == 0:
        return None
    return float(np.sum(y_correct & did_x) / n)


def _p_y_given_not_x(y_correct, did_x):
    """P(Y correct | X NON fait) = fraction de y_correct PARMI les trials ¬did_x. None si aucun ¬did_x.
    C'est le DÉNOMINATEUR du binding : le gap P(Y|X) − P(Y|¬X) distingue le CONDITIONNEMENT (gap>0)
    de la montée des marginales (gap≈0, EDR 126) et de la suppression triviale (les deux ≈0). PUR."""
    y_correct = np.asarray(y_correct, dtype=bool)
    not_x = ~np.asarray(did_x, dtype=bool)
    n = int(np.sum(not_x))
    if n == 0:
        return None
    return float(np.sum(y_correct & not_x) / n)


def run_curriculum(backend: str, seed: int = 0, warmup_trials: int = 150, compo_trials: int = 250,
                   n_agents: int = 8, target_x: int = 0, target_y: int = 4) -> dict:
    """Curriculum 2 phases (bascule dure). Phase A : enseigner X (reward dense did_x, S1 seul).
    Phase B : compositionnel pur (S1 reward 0, S2 reward Y|X). Trace l'efficacité (warmup did_x),
    le hit compositionnel (phase B) et la rétention de X en phase B. warmup_trials=0 → phase B seule."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    agents = _build_agents(n_agents, 172, "prod")
    pop = make_population(agents, backend=backend)
    rng = np.random.RandomState(seed + 1)
    n_in = agents[0].genome.num_inputs
    obs_a = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)    # S1 fixe (partagé A/B)
    obs_b = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)    # S2 fixe

    # --- Phase A : warmup dense sur X (S1 seul) ---
    warm = []
    for _ in range(warmup_trials):
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        reward = np.array([_warmup_reward(int(m), target_x) for m in move1], dtype=np.float32)
        pop.learn(reward, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])
        warm.append(float(np.mean(did_x)))
    qa = max(1, warmup_trials // 4) if warmup_trials else 0
    warmup_didx_start = float(np.mean(warm[:qa])) if qa else 0.0
    warmup_didx_end = float(np.mean(warm[-qa:])) if qa else 0.0

    # --- Phase B : compositionnel pur (bascule dure) ---
    hit, bx = [], []
    zeros = np.zeros(n_agents, dtype=np.float32)
    for _ in range(compo_trials):
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        pop.learn(zeros, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])   # S1 différé (0)
        preds2, _ = pop.forward(obs_b)
        move2 = np.asarray(preds2)[:, :_MOVE].argmax(axis=1)
        reward2 = np.array([compositional_reward(int(move2[i]), target_y, bool(did_x[i]))
                            for i in range(n_agents)], dtype=np.float32)
        pop.learn(reward2, [{"move": int(m), "grab": 0, "rub": 0} for m in move2])
        hit.append(float(np.mean((move2 == target_y) & did_x)))
        bx.append(float(np.mean(did_x)))
    qb = max(1, compo_trials // 4) if compo_trials else 0
    hit_start = float(np.mean(hit[:qb])) if qb else 0.0
    hit_end = float(np.mean(hit[-qb:])) if qb else 0.0
    compo_didx_start = float(np.mean(bx[:qb])) if qb else 0.0
    compo_didx_end = float(np.mean(bx[-qb:])) if qb else 0.0
    return {"backend": backend, "seed": int(seed), "warmup_trials": warmup_trials,
            "compo_trials": compo_trials, "n_agents": n_agents,
            "warmup_didx_start": warmup_didx_start, "warmup_didx_end": warmup_didx_end,
            "hit_start": hit_start, "hit_end": hit_end,
            "compo_didx_start": compo_didx_start, "compo_didx_end": compo_didx_end,
            "delta": hit_end - hit_start}


def run_curriculum_fade(backend: str, seed: int = 0, warmup_trials: int = 150, compo_trials: int = 250,
                        n_agents: int = 8, target_x: int = 0, target_y: int = 4,
                        fade_w0: float = 1.0, y_without_x_penalty: float = 0.0) -> dict:
    """Curriculum à FADE. Phase A : enseigner X (dense). Phase B : S1 reward = fade_w·warmup_reward
    (fade_w décroît linéairement de fade_w0 à 0) → maintient X au lieu de le laisser décliner ;
    S2 reward = compositionnel PÉNALISÉ (surcoût y_without_x_penalty sur Y-sans-X → force le
    conditionnement, levier binding par le signal, EDR 126). Mesure le joint `hit`, la rétention
    `compo_didx`, P(Y|X) ET P(Y|¬X) → binding_gap. fade_w0=0 ≡ bascule dure ; penalty=0 ≡ EDR 126."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    agents = _build_agents(n_agents, 172, "prod")
    pop = make_population(agents, backend=backend)
    rng = np.random.RandomState(seed + 1)
    n_in = agents[0].genome.num_inputs
    obs_a = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)
    obs_b = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)

    # --- Phase A : warmup dense sur X (S1 seul) ---
    warm = []
    for _ in range(warmup_trials):
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        warm.append(float(np.mean(move1 == target_x)))
        reward = np.array([_warmup_reward(int(m), target_x) for m in move1], dtype=np.float32)
        pop.learn(reward, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])
    qa = max(1, warmup_trials // 4) if warmup_trials else 0
    warmup_didx_end = float(np.mean(warm[-qa:])) if qa else 0.0

    # --- Phase B : compositionnel + fade linéaire du maintien de X ---
    hit, bx, yc = [], [], []
    for t in range(compo_trials):
        fade_w = _fade_weight(t, compo_trials, fade_w0)
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        s1_reward = np.array([fade_w * _warmup_reward(int(m), target_x) for m in move1], dtype=np.float32)
        pop.learn(s1_reward, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])
        preds2, _ = pop.forward(obs_b)
        move2 = np.asarray(preds2)[:, :_MOVE].argmax(axis=1)
        y_correct = (move2 == target_y)
        reward2 = np.array([compositional_reward_penalized(int(move2[i]), target_y, bool(did_x[i]),
                                                           y_without_x_penalty)
                            for i in range(n_agents)], dtype=np.float32)
        pop.learn(reward2, [{"move": int(m), "grab": 0, "rub": 0} for m in move2])
        hit.append(float(np.mean(y_correct & did_x)))
        bx.append(did_x)
        yc.append(y_correct)
    qb = max(1, compo_trials // 4) if compo_trials else 0
    hit_start = float(np.mean(hit[:qb])) if qb else 0.0
    hit_end = float(np.mean(hit[-qb:])) if qb else 0.0
    didx_end = np.concatenate(bx[-qb:]) if qb else np.array([], dtype=bool)
    didx_start = np.concatenate(bx[:qb]) if qb else np.array([], dtype=bool)
    yc_end = np.concatenate(yc[-qb:]) if qb else np.array([], dtype=bool)
    yc_start = np.concatenate(yc[:qb]) if qb else np.array([], dtype=bool)
    compo_didx_start = float(np.mean(didx_start)) if didx_start.size else 0.0
    compo_didx_end = float(np.mean(didx_end)) if didx_end.size else 0.0
    p_yx_end = _p_y_given_x(yc_end, didx_end)
    p_ynotx_end = _p_y_given_not_x(yc_end, didx_end)
    binding_gap_end = (p_yx_end - p_ynotx_end) if (p_yx_end is not None and p_ynotx_end is not None) else None
    return {"backend": backend, "seed": int(seed), "warmup_trials": warmup_trials,
            "compo_trials": compo_trials, "fade_w0": fade_w0,
            "y_without_x_penalty": float(y_without_x_penalty), "n_agents": n_agents,
            "warmup_didx_end": warmup_didx_end,
            "hit_start": hit_start, "hit_end": hit_end,
            "compo_didx_start": compo_didx_start, "compo_didx_end": compo_didx_end,
            "p_y_given_x_start": _p_y_given_x(yc_start, didx_start),
            "p_y_given_x_end": p_yx_end,
            "p_y_given_not_x_end": p_ynotx_end,
            "binding_gap_end": binding_gap_end,
            "y_rate_end": float(np.mean(yc_end)) if yc_end.size else 0.0,
            "delta": hit_end - hit_start}


def run_curriculum_fade_gated(backend: str, seed: int = 0, warmup_trials: int = 150,
                              compo_trials: int = 250, n_agents: int = 8, target_x: int = 0,
                              target_y: int = 4, fade_w0: float = 1.0, gate_mode: str = "none",
                              oracle_bias: float = 8.0, gate_lr: float = 0.05,
                              y_without_x_penalty: float = 0.0, entropy_coef: float = 0.0,
                              elig_lambda: float = 0.0, gate_warmstart_trials: int = 0,
                              freeze_gate_after_warmstart: bool = False,
                              capture_probe: bool = False, capture_gate_bias: bool = False) -> dict:
    """LEVIER 2 (gating archi, suite EDR 126/128) : curriculum à fade + GATE sur le logit Y en phase B.
    L'action Y est échantillonnée d'un softmax sur les logits de mouvement (règle commune aux 3 modes
    → comparaison équitable ; `none` doit reproduire le baseline EDR 126/128).
    gate_mode :
      - "none"    : aucun gate (biais Y = 0) ≡ baseline (sert de contrôle négatif).
      - "oracle"  : biais CÂBLÉ ±oracle_bias au logit Y selon did_x VRAI → force le conditionnement à
                    la décision (CONTRÔLE POSITIF : plafond du binding, valide l'instrument).
      - "learned" : gate LINÉAIRE entraînable biais_Y = w·H_S2 + b, entraîné par REINFORCE sur reward2
                    (avantage = reward − baseline glissant). Teste si le substrat APPREND à router did_x
                    (décodable de H_S2, EDR 120) vers le logit Y quand on lui donne la STRUCTURE.
    LEVIER 3 (crédit/optimisation du gate learned, fiabiliser vs collapse always-Y d'EDR 129) :
      - entropy_coef>0 : bonus d'entropie sur la politique (anti-collapse, exploration).
      - elig_lambda>0 : trace d'éligibilité sur le gradient du gate (trace=λ·trace+grad). λ=0 → Adam nu.
    Les deux valent 0 par défaut → REINFORCE nu = baseline gating (rétrocompat garantie).
    WARM-START (test causal path-dependence, suite EDR 131) :
      - gate_warmstart_trials>0 : AVANT la phase B, pré-entraîne le gate (population GELÉE, forward sans
        learn) à IMITER l'oracle depuis H_S2 — régression `gate_bias → oracle_bias·(2·did_x−1)` par MSE.
        Le gate entre alors en phase B en conditionnant DÉJÀ (au lieu de partir de 0 et tomber dans le
        bassin always-Y). Si ça rescape les collapsés d'EDR 129 (7/10 → ~10/10), la path-dependence
        précoce (EDR 131) est confirmée CAUSALEMENT. =0 par défaut → rétrocompat EDR 129/131.
      - freeze_gate_after_warmstart : GÈLE le gate warm-starté en phase B (aucun update REINFORCE) →
        isole si le collapse = ÉROSION du routage par la récompense jointe (gate gelé binde) vs
        NOYAGE par les base-logits de la population (gate gelé collapse aussi). Contrôle du mécanisme.
      - capture_gate_bias : reporte le biais RÉEL du gate en fin de phase B, séparé did_x vs ¬did_x
        (gate_bias_didx_end / _notdidx_end / _margin_end). Distingue les modes d'échec : MARGE faible
        (readout ne sépare pas) vs OFFSET élevé aux deux (le gate booste Y partout → always-Y).
    Mesure binding_gap = P(Y|X) − P(Y|¬X) en fin de phase B."""
    if gate_mode not in ("none", "oracle", "learned"):
        raise ValueError(f"gate_mode inconnu : {gate_mode!r} (attendu none/oracle/learned)")
    import torch
    np.random.seed(seed)
    torch.manual_seed(seed)
    agents = _build_agents(n_agents, 172, "prod")
    pop = make_population(agents, backend=backend)
    rng = np.random.RandomState(seed + 1)
    n_in = agents[0].genome.num_inputs
    obs_a = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)
    obs_b = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)

    # --- Phase A : warmup dense sur X (S1 seul), identique au fade ---
    warm = []
    for _ in range(warmup_trials):
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        warm.append(float(np.mean(move1 == target_x)))
        reward = np.array([_warmup_reward(int(m), target_x) for m in move1], dtype=np.float32)
        pop.learn(reward, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])
    qa = max(1, warmup_trials // 4) if warmup_trials else 0
    warmup_didx_end = float(np.mean(warm[-qa:])) if qa else 0.0

    # --- Gate appris : params + optim (créés seulement pour learned) ---
    gate_w = gate_b = optim = None
    trace_w = trace_b = None
    baseline_ret = 0.0
    if gate_mode == "learned":
        state_dim = _read_state(pop, backend).shape[1]
        gate_w = torch.zeros(state_dim, requires_grad=True)
        gate_b = torch.zeros(1, requires_grad=True)
        optim = torch.optim.Adam([gate_w, gate_b], lr=gate_lr)
        trace_w = torch.zeros(state_dim)   # trace d'éligibilité (levier 3) sur le gradient
        trace_b = torch.zeros(1)

    # --- Warm-start (test causal EDR 131) : pré-entraîner le gate à imiter l'oracle depuis H_S2 ---
    # Population GELÉE (forward sans learn) : on seed UNIQUEMENT le routage did_x→biais_Y, sans laisser
    # la politique dériver. Régression MSE de gate_bias vers la cible oracle ±oracle_bias.
    # NB : on RÉUTILISE `optim` (pas un 2e Adam) → l'état des moments est continu warm-start→phase B ;
    # un optimizer neuf en phase B donnerait un pas plein-lr au trial 1 sur un gate déjà placé (choc).
    if gate_mode == "learned" and gate_warmstart_trials > 0:
        for _ in range(gate_warmstart_trials):
            preds1_ws, _ = pop.forward(obs_a)
            move1_ws = np.asarray(preds1_ws)[:, :_MOVE].argmax(axis=1)
            did_x_ws = (move1_ws == target_x)
            pop.forward(obs_b)                                   # avance l'état vers H_S2 (comme phase B)
            h_s2_ws = torch.tensor(_read_state(pop, backend), dtype=torch.float32)
            gate_bias_ws = h_s2_ws @ gate_w + gate_b
            target_ws = torch.tensor(oracle_bias * (2.0 * did_x_ws - 1.0), dtype=torch.float32)
            ws_loss = ((gate_bias_ws - target_ws) ** 2).mean()
            optim.zero_grad(); ws_loss.backward(); optim.step()

    # --- Phase B : compositionnel + fade + gate sur le logit Y ---
    hit, bx, yc = [], [], []
    probe_H, probe_dx = [], []          # diagnostic précoce (H_S2, did_x) sur la 1re moitié
    gbias = []                          # biais réel du gate par trial (mécanisme : marge vs offset)
    probe_cut = compo_trials // 2
    for t in range(compo_trials):
        fade_w = _fade_weight(t, compo_trials, fade_w0)
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        s1_reward = np.array([fade_w * _warmup_reward(int(m), target_x) for m in move1], dtype=np.float32)
        pop.learn(s1_reward, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])

        preds2, _ = pop.forward(obs_b)
        base_logits = torch.tensor(np.asarray(preds2)[:, :_MOVE], dtype=torch.float32)  # (B, _MOVE)
        gate_bias = None
        if gate_mode == "oracle":
            add = torch.tensor(oracle_bias * (2.0 * did_x - 1.0), dtype=torch.float32)   # (B,)
            base_logits = base_logits.clone(); base_logits[:, target_y] = base_logits[:, target_y] + add
        elif gate_mode == "learned":
            state_np = _read_state(pop, backend)                                          # (B, N)
            h_s2 = torch.tensor(state_np, dtype=torch.float32)
            gate_bias = h_s2 @ gate_w + gate_b                                            # (B,)
            base_logits = base_logits.clone(); base_logits[:, target_y] = base_logits[:, target_y] + gate_bias
            if capture_probe and t < probe_cut:      # décodabilité did_x de H_S2 (avant que le gate route)
                probe_H.append(state_np.copy()); probe_dx.append(did_x.copy())
            if capture_gate_bias:                     # biais réel appliqué au logit Y (par agent, ce trial)
                gbias.append(gate_bias.detach().cpu().numpy().copy())

        probs = torch.softmax(base_logits.detach(), dim=1)
        move2 = torch.multinomial(probs, 1).squeeze(1).cpu().numpy()                      # échantillonné
        y_correct = (move2 == target_y)
        reward2 = np.array([compositional_reward_penalized(int(move2[i]), target_y, bool(did_x[i]),
                                                           y_without_x_penalty)
                            for i in range(n_agents)], dtype=np.float32)
        pop.learn(reward2, [{"move": int(m), "grab": 0, "rub": 0} for m in move2])

        gate_frozen = (gate_warmstart_trials > 0 and freeze_gate_after_warmstart)
        if gate_mode == "learned" and not gate_frozen:
            idx = torch.arange(n_agents)
            log_probs = torch.log_softmax(base_logits, dim=1)                              # (B, _MOVE)
            logp = log_probs[idx, torch.as_tensor(move2)]                                  # (B,)
            adv = torch.tensor(reward2, dtype=torch.float32) - baseline_ret
            # LEVIER 3a : bonus d'entropie (anti-collapse always-Y ; exploration)
            entropy = -(torch.softmax(base_logits, dim=1) * log_probs).sum(dim=1)          # (B,)
            loss = -(logp * adv).mean() - entropy_coef * entropy.mean()
            optim.zero_grad(); loss.backward()
            # LEVIER 3b : trace d'éligibilité sur le gradient (λ=0 → Adam nu = baseline EDR 129/gating)
            if elig_lambda > 0.0:
                trace_w.mul_(elig_lambda).add_(gate_w.grad); gate_w.grad = trace_w.clone()
                trace_b.mul_(elig_lambda).add_(gate_b.grad); gate_b.grad = trace_b.clone()
            optim.step()
            baseline_ret = 0.9 * baseline_ret + 0.1 * float(np.mean(reward2))

        hit.append(float(np.mean(y_correct & did_x)))
        bx.append(did_x)
        yc.append(y_correct)

    qb = max(1, compo_trials // 4) if compo_trials else 0
    hit_end = float(np.mean(hit[-qb:])) if qb else 0.0
    didx_end = np.concatenate(bx[-qb:]) if qb else np.array([], dtype=bool)
    yc_end = np.concatenate(yc[-qb:]) if qb else np.array([], dtype=bool)
    compo_didx_end = float(np.mean(didx_end)) if didx_end.size else 0.0
    p_yx = _p_y_given_x(yc_end, didx_end)
    p_ynx = _p_y_given_not_x(yc_end, didx_end)
    gap = (p_yx - p_ynx) if (p_yx is not None and p_ynx is not None) else None
    # Fenêtre PRÉCOCE (1er quart) : la trajectoire early prédit-elle le collapse ?
    didx_start = np.concatenate(bx[:qb]) if qb else np.array([], dtype=bool)
    yc_start = np.concatenate(yc[:qb]) if qb else np.array([], dtype=bool)
    p_yx_s = _p_y_given_x(yc_start, didx_start)
    p_ynx_s = _p_y_given_not_x(yc_start, didx_start)
    gap_start = (p_yx_s - p_ynx_s) if (p_yx_s is not None and p_ynx_s is not None) else None
    out = {"backend": backend, "seed": int(seed), "gate_mode": gate_mode,
           "warmup_trials": warmup_trials, "compo_trials": compo_trials, "fade_w0": fade_w0,
           "oracle_bias": float(oracle_bias), "gate_lr": float(gate_lr),
           "y_without_x_penalty": float(y_without_x_penalty),
           "entropy_coef": float(entropy_coef), "elig_lambda": float(elig_lambda),
           "gate_warmstart_trials": int(gate_warmstart_trials),
           "freeze_gate_after_warmstart": bool(freeze_gate_after_warmstart), "n_agents": n_agents,
           "warmup_didx_end": warmup_didx_end, "hit_end": hit_end,
           "compo_didx_end": compo_didx_end, "p_y_given_x_end": p_yx,
           "p_y_given_not_x_end": p_ynx, "binding_gap_end": gap,
           "y_rate_end": float(np.mean(yc_end)) if yc_end.size else 0.0,
           "binding_gap_start": gap_start,
           "y_rate_start": float(np.mean(yc_start)) if yc_start.size else 0.0}
    if capture_probe:
        # Décodabilité de did_x depuis H_S2 précoce (pooled agents×trials) : la mémoire encode-t-elle
        # did_x proprement chez ce seed ? (hypothèse REPRÉSENTATION du collapse)
        if probe_H:
            X = np.concatenate(probe_H, axis=0)
            y = np.concatenate(probe_dx, axis=0).astype(int)
            out["did_x_auc_early"] = _decode_auc(X, y, min_per_class=8, seed=seed)
        else:
            out["did_x_auc_early"] = None
    if capture_gate_bias:
        # Biais RÉEL appliqué au logit Y en fin de phase B (dernier quart), séparé did_x vs ¬did_x.
        # Distingue les mécanismes d'échec du gate : MARGE (biais_didx − biais_¬didx) faible = le readout
        # ne sépare pas ; OFFSET élevé aux deux = le gate booste Y partout (always-Y malgré la marge).
        b_didx = b_notdidx = margin = None
        if gbias and qb:
            gb_end = np.concatenate(gbias[-qb:], axis=0)          # (agents×trials,)
            mask = didx_end
            if mask.size == gb_end.size:
                if mask.any():
                    b_didx = float(gb_end[mask].mean())
                if (~mask).any():
                    b_notdidx = float(gb_end[~mask].mean())
                if b_didx is not None and b_notdidx is not None:
                    margin = b_didx - b_notdidx
        out["gate_bias_didx_end"] = b_didx
        out["gate_bias_notdidx_end"] = b_notdidx
        out["gate_bias_margin_end"] = margin
    return out


def probe_collapse_predictors(seeds=tuple(range(10)), fade_w0: float = 0.0,
                              y_without_x_penalty: float = 2.0, warmup_trials: int = 150,
                              compo_trials: int = 250, n_agents: int = 8, bind_thresh: float = 0.30) -> dict:
    """DIAGNOSTIC (suite EDR 130) : POURQUOI certains seeds collapsent-ils en always-Y (plafond 7/10) ?
    Pour chaque seed : gate learned (régime incitatif) + capture PRÉCOCE — did_x_auc_early
    (décodabilité de did_x depuis H_S2 = hypothèse REPRÉSENTATION), y_rate_start / binding_gap_start
    (trajectoire du 1er quart = hypothèse POLITIQUE PRÉCOCE) — corrélés à l'issue finale bind/collapse.
    Rapporte, par prédicteur, la moyenne du groupe BINDEUR vs COLLAPSÉ : celui dont l'écart est net
    tranche l'hypothèse (représentation vs entrée précoce du bassin always-Y). Diagnostic, pas verdict."""
    rows = []
    for s in seeds:
        r = run_curriculum_fade_gated("torch", seed=s, gate_mode="learned", fade_w0=fade_w0,
                                      y_without_x_penalty=y_without_x_penalty, warmup_trials=warmup_trials,
                                      compo_trials=compo_trials, n_agents=n_agents, capture_probe=True)
        bound = (r["binding_gap_end"] is not None and r["binding_gap_end"] > bind_thresh)
        rows.append({"seed": int(s), "bound": bound, "binding_gap_end": r["binding_gap_end"],
                     "did_x_auc_early": r["did_x_auc_early"], "y_rate_start": r["y_rate_start"],
                     "binding_gap_start": r["binding_gap_start"]})

    def _grp(key, want):
        vals = [row[key] for row in rows if row["bound"] == want and row[key] is not None]
        return (sum(vals) / len(vals)) if vals else None

    predictors = {}
    for key in ("did_x_auc_early", "y_rate_start", "binding_gap_start"):
        bm, cm = _grp(key, True), _grp(key, False)
        sep = abs(bm - cm) if (bm is not None and cm is not None) else None
        predictors[key] = {"bind_mean": bm, "collapse_mean": cm, "separation": sep}
    return {"n_bind": sum(1 for r in rows if r["bound"]), "n_seeds": len(rows),
            "predictors": predictors, "rows": rows}


def compare_gate_modes(seeds=(0, 1, 2, 3, 4), modes=("none", "learned", "oracle"),
                       fade_w0: float = 0.0, y_without_x_penalty: float = 2.0,
                       warmup_trials: int = 150, compo_trials: int = 250, n_agents: int = 8,
                       bind_thresh: float = 0.30) -> dict:
    """LEVIER 2 (gating) — compare none / learned / oracle sur le binding_gap (suite EDR 126/128).
    Défauts = régime où CONDITIONNER est optimal (fade0.0 → ¬X fréquent ; penalty=2 → silence −1 >
    Y-sans-X −3), sans quoi always-Y est optimal et le gate collapse trivialement.
    Expose le gap PER-SEED (le gate appris est BIMODAL : binde ou collapse en always-Y) — la médiane
    seule masque le signal. `n_bind` = nb de seeds avec gap > bind_thresh.
    Verdict (bras learned vs none/oracle) :
    - GATE_BINDS : learned n_bind ≥ majorité ET oracle gap médian > 0.5 (plafond) ET none gap méd < 0.2.
    - GATE_COLLAPSES : learned n_bind = 0 (toujours always-Y ou pas de routage).
    - GATE_INTERMITTENT : learned binde sur certains seeds mais < majorité.
    Seuils heuristiques ; verdict final lu par l'humain sur la distribution per-seed."""
    per_mode = {}
    for mode in modes:
        cells = [run_curriculum_fade_gated("torch", seed=s, gate_mode=mode, fade_w0=fade_w0,
                                           y_without_x_penalty=y_without_x_penalty,
                                           warmup_trials=warmup_trials, compo_trials=compo_trials,
                                           n_agents=n_agents) for s in seeds]
        gaps = [c["binding_gap_end"] for c in cells if c["binding_gap_end"] is not None]
        pyx_vals = [c["p_y_given_x_end"] for c in cells if c["p_y_given_x_end"] is not None]
        per_mode[mode] = {
            "gap_median": statistics.median(gaps) if gaps else None,
            "gap_per_seed": gaps,
            "n_bind": sum(1 for g in gaps if g > bind_thresh),
            "n_seeds": len(gaps),
            "p_y_given_x_median": statistics.median(pyx_vals) if pyx_vals else None,
            "y_rate_median": statistics.median([c["y_rate_end"] for c in cells])}

    verdict = "AMBIGU"
    if "learned" in per_mode:
        lb = per_mode["learned"]["n_bind"]
        ln = per_mode["learned"]["n_seeds"]
        none_gap = per_mode.get("none", {}).get("gap_median")
        oracle_gap = per_mode.get("oracle", {}).get("gap_median")
        if lb == 0:
            verdict = "GATE_COLLAPSES"
        elif (lb * 2 >= ln and (oracle_gap is None or oracle_gap > 0.5)
              and (none_gap is None or none_gap < 0.2)):
            verdict = "GATE_BINDS"
        else:
            verdict = "GATE_INTERMITTENT"
    return {"verdict": verdict, "bind_thresh": bind_thresh, "fade_w0": fade_w0,
            "y_without_x_penalty": y_without_x_penalty, "per_mode": per_mode}


def sweep_gate_reliability(seeds=tuple(range(10)), configs=None, fade_w0: float = 0.0,
                           y_without_x_penalty: float = 2.0, warmup_trials: int = 150,
                           compo_trials: int = 250, n_agents: int = 8, bind_thresh: float = 0.30) -> dict:
    """LEVIER 3 — FIABILITÉ du gate learned sous interventions crédit/optimisation (suite EDR 129).
    EDR 129 : le gate binde ~7/10 seeds mais collapse en always-Y sur le reste. Question : entropy
    (anti-collapse) et/ou éligibilité fiabilisent-ils (n_bind ↑ vers n_seeds) ?
    `configs` = liste de dicts d'overrides passés à run_curriculum_fade_gated (gate_mode='learned'),
    ex. {'entropy_coef':0.05} ; défaut = {baseline, entropy, elig, both}. Régime = conditionnement
    optimal (fade0.0/pen2, cf. EDR 129). Rapporte n_bind/n_seeds par config (la FIABILITÉ, pas juste
    la médiane). Verdict : RELIABILITY_IMPROVED si un config atteint n_bind ≥ baseline+2 sur 10 seeds ;
    NO_IMPROVEMENT sinon (les collapses sont irréductibles à ces leviers). Seuils heuristiques."""
    if configs is None:
        configs = ({"entropy_coef": 0.0, "elig_lambda": 0.0},   # baseline REINFORCE (= EDR 129)
                   {"entropy_coef": 0.05, "elig_lambda": 0.0},   # entropie
                   {"entropy_coef": 0.0, "elig_lambda": 0.7},    # éligibilité
                   {"entropy_coef": 0.05, "elig_lambda": 0.7})   # les deux
    rows = []
    for cfg in configs:
        cells = [run_curriculum_fade_gated("torch", seed=s, gate_mode="learned", fade_w0=fade_w0,
                                           y_without_x_penalty=y_without_x_penalty,
                                           warmup_trials=warmup_trials, compo_trials=compo_trials,
                                           n_agents=n_agents, **cfg) for s in seeds]
        gaps = [c["binding_gap_end"] for c in cells if c["binding_gap_end"] is not None]
        rows.append({"config": dict(cfg), "n_bind": sum(1 for g in gaps if g > bind_thresh),
                     "n_seeds": len(gaps), "gap_median": statistics.median(gaps) if gaps else None,
                     "gap_per_seed": gaps})
    base = next((r for r in rows if r["config"].get("entropy_coef", 0.0) == 0.0
                 and r["config"].get("elig_lambda", 0.0) == 0.0), None)
    base_bind = base["n_bind"] if base else None
    best = max((r["n_bind"] for r in rows), default=0)
    if base_bind is not None and best >= base_bind + 2:
        verdict = "RELIABILITY_IMPROVED"
    elif base_bind is not None:
        verdict = "NO_IMPROVEMENT"
    else:
        verdict = "AMBIGU"
    return {"verdict": verdict, "bind_thresh": bind_thresh, "base_n_bind": base_bind,
            "best_n_bind": best, "rows": rows}


def sweep_gate_warmstart(seeds=tuple(range(10)), warmstart_levels=(0, 100), fade_w0: float = 0.0,
                         y_without_x_penalty: float = 2.0, warmup_trials: int = 150,
                         compo_trials: int = 250, n_agents: int = 8, oracle_bias: float = 8.0,
                         bind_thresh: float = 0.30) -> dict:
    """TEST CAUSAL de la path-dependence précoce (EDR 131) via WARM-START du gate.
    EDR 129 : le gate learned binde ~7/10, collapse en always-Y sur le reste. EDR 131 (corrélationnel) :
    les collapsés saturent always-Y dès le 1er quart, AVANT que le gate n'apprenne à router — did_x
    reste pourtant décodable (AUC~0.9) chez tous. Intervention : pré-entraîner le gate à imiter l'oracle
    depuis H_S2 (warmstart>0) → il entre en phase B en conditionnant déjà. Si les collapsés sont RESCAPÉS
    (n_bind ↑), la path-dependence est la CAUSE (pas la représentation) → recette de fiabilité concrète.
    Régime = conditionnement optimal (fade0.0/pen2, cf. EDR 129). Rapporte n_bind/n_seeds ET le gap
    per-seed par niveau (le rescue se lit sur les seeds AUPARAVANT collapsés). Verdict :
    - RESCUE : un niveau warmstart>0 atteint n_bind ≥ baseline+2 sur 10 seeds.
    - PARTIAL_RESCUE : le meilleur niveau atteint exactement baseline+1 (un seul collapsé basculé).
    - NO_RESCUE : aucun niveau ne dépasse baseline (collapse irréductible au warm-start du gate).
    Seuils heuristiques ; le rescue per-seed (quels seeds basculent) est lu par l'humain."""
    rows = []
    for ws in warmstart_levels:
        cells = [run_curriculum_fade_gated("torch", seed=s, gate_mode="learned", fade_w0=fade_w0,
                                           y_without_x_penalty=y_without_x_penalty,
                                           warmup_trials=warmup_trials, compo_trials=compo_trials,
                                           n_agents=n_agents, oracle_bias=oracle_bias,
                                           gate_warmstart_trials=ws) for s in seeds]
        gaps_by_seed = [(int(s), c["binding_gap_end"]) for s, c in zip(seeds, cells)]
        gaps = [g for _, g in gaps_by_seed if g is not None]
        bound_seeds = [s for s, g in gaps_by_seed if g is not None and g > bind_thresh]
        rows.append({"warmstart": int(ws), "n_bind": len(bound_seeds), "n_seeds": len(gaps),
                     "gap_median": statistics.median(gaps) if gaps else None,
                     "gap_per_seed": gaps_by_seed, "bound_seeds": bound_seeds})
    base = next((r for r in rows if r["warmstart"] == 0), None)
    base_bind = base["n_bind"] if base else None
    best = max((r["n_bind"] for r in rows if r["warmstart"] > 0), default=0)
    if base_bind is not None and best >= base_bind + 2:
        verdict = "RESCUE"
    elif base_bind is not None and best == base_bind + 1:
        verdict = "PARTIAL_RESCUE"
    elif base_bind is not None:
        verdict = "NO_RESCUE"
    else:
        verdict = "AMBIGU"
    return {"verdict": verdict, "bind_thresh": bind_thresh, "base_n_bind": base_bind,
            "best_n_bind": best, "rows": rows}


def compare_curriculum_fade(seeds=(0, 1, 2, 3, 4), warmup_trials: int = 150, compo_trials: int = 250,
                            n_agents: int = 8, fade_w0: float = 1.0) -> dict:
    """A/B apparié legacy vs torch du curriculum à fade. Verdict_fade :
    FADE_INEFFECTIVE si torch compo_didx_end médian ≤ 0.40 (le fade n'a PAS maintenu X → garde-fou) ;
    CEILING_WAS_RETENTION si torch hit_end médian > 0.35 ET p_y_given_x_end médian > 0.70 ;
    CEILING_WAS_BINDING si X maintenu (compo_didx_end > 0.60) MAIS hit_end ≤ 0.35 / p_y_given_x ≤ 0.70 ;
    sinon AMBIGU. Seuils heuristiques (verdict final lu par l'humain sur les chiffres)."""
    rows = []
    for s in seeds:
        leg = run_curriculum_fade("legacy", seed=s, warmup_trials=warmup_trials,
                                  compo_trials=compo_trials, n_agents=n_agents, fade_w0=fade_w0)
        tor = run_curriculum_fade("torch", seed=s, warmup_trials=warmup_trials,
                                  compo_trials=compo_trials, n_agents=n_agents, fade_w0=fade_w0)
        rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                     "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})

    def _med(arm, key):
        vals = [r[arm][key] for r in rows if r[arm][key] is not None]
        return statistics.median(vals) if vals else None

    tor_didx = _med("torch", "compo_didx_end")
    tor_hit = _med("torch", "hit_end")
    tor_pyx = _med("torch", "p_y_given_x_end")
    if tor_didx is None or tor_didx <= 0.40:
        verdict_f = "FADE_INEFFECTIVE"
    elif tor_hit is not None and tor_hit > 0.35 and tor_pyx is not None and tor_pyx > 0.70:
        verdict_f = "CEILING_WAS_RETENTION"
    elif tor_didx > 0.60 and (tor_hit is None or tor_hit <= 0.35 or tor_pyx is None or tor_pyx <= 0.70):
        verdict_f = "CEILING_WAS_BINDING"
    else:
        verdict_f = "AMBIGU"
    return {**compute_ab_verdict(rows), "verdict_fade": verdict_f,
            "summary": {"torch_compo_didx_end": tor_didx, "torch_hit_end": tor_hit,
                        "torch_p_y_given_x_end": tor_pyx,
                        "legacy_hit_end": _med("legacy", "hit_end"),
                        "legacy_p_y_given_x_end": _med("legacy", "p_y_given_x_end")},
            "per_seed": rows}


def sweep_binding_penalty(seeds=(0, 1, 2, 3, 4), penalties=(0.0, 0.5, 1.0, 2.0),
                          backends=("torch", "legacy"), warmup_trials: int = 150,
                          compo_trials: int = 250, n_agents: int = 8, fade_w0: float = 1.0) -> dict:
    """Dose-réponse du LEVIER BINDING PAR LE SIGNAL (punir Y-sans-X, suite EDR 126).
    Pour chaque (penalty, backend, seed) : curriculum à fade (X maintenu) + surcoût y_without_x_penalty
    sur Y-sans-X. Mesure le GAP de binding = P(Y|X) − P(Y|¬X) à la fin.
    Verdict (sur le bras torch, celui qui apprend), penalty=0 = baseline EDR 126 (Y⊥did_x, gap≈0) :
    - BINDING_FORCED : le gap médian s'OUVRE avec la pénalité (max-penalty > 0.30 ET > baseline+0.15)
      SANS suppression (P(Y|X) reste > 0.40) → le signal SUFFIT à forcer le conditionnement.
    - SUPPRESSION : y_rate s'effondre (P(Y|X) médian < 0.20 au max-penalty) → l'agent fait taire Y
      au lieu de le conditionner (échec trivial que le gap seul masquerait).
    - SIGNAL_INSUFFICIENT : le gap reste ≈0 (max-penalty ≤ baseline+0.15) → punir ne binde pas,
      le verrou est un MÉCANISME (archi/crédit), pas le signal.
    Seuils heuristiques ; verdict final lu par l'humain sur la courbe dose-réponse."""
    rows = []
    for pen in penalties:
        for backend in backends:
            for s in seeds:
                r = run_curriculum_fade(backend, seed=s, warmup_trials=warmup_trials,
                                        compo_trials=compo_trials, n_agents=n_agents,
                                        fade_w0=fade_w0, y_without_x_penalty=pen)
                rows.append({"penalty": float(pen), "backend": backend, "seed": int(s),
                             "p_y_given_x_end": r["p_y_given_x_end"],
                             "p_y_given_not_x_end": r["p_y_given_not_x_end"],
                             "binding_gap_end": r["binding_gap_end"],
                             "y_rate_end": r["y_rate_end"], "hit_end": r["hit_end"],
                             "compo_didx_end": r["compo_didx_end"]})

    def _cell_med(pen, backend, key):
        vals = [r[key] for r in rows if r["penalty"] == pen and r["backend"] == backend
                and r[key] is not None]
        return statistics.median(vals) if vals else None

    cells = {}
    for pen in penalties:
        for backend in backends:
            cells[f"{backend}_p{pen}"] = {
                "gap": _cell_med(pen, backend, "binding_gap_end"),
                "p_y_given_x": _cell_med(pen, backend, "p_y_given_x_end"),
                "p_y_given_not_x": _cell_med(pen, backend, "p_y_given_not_x_end"),
                "y_rate": _cell_med(pen, backend, "y_rate_end"),
                "hit": _cell_med(pen, backend, "hit_end")}

    verdict = "AMBIGU"
    if "torch" in backends:
        pmax = max(penalties)
        base_gap = _cell_med(0.0, "torch", "binding_gap_end") if 0.0 in penalties else None
        max_gap = _cell_med(pmax, "torch", "binding_gap_end")
        max_pyx = _cell_med(pmax, "torch", "p_y_given_x_end")
        if max_pyx is not None and max_pyx < 0.20:
            verdict = "SUPPRESSION"
        elif (max_gap is not None and max_gap > 0.30
              and (base_gap is None or max_gap > base_gap + 0.15)
              and max_pyx is not None and max_pyx > 0.40):
            verdict = "BINDING_FORCED"
        elif max_gap is not None and (base_gap is not None and max_gap <= base_gap + 0.15):
            verdict = "SIGNAL_INSUFFICIENT"
    return {"verdict": verdict, "penalties": list(penalties), "backends": list(backends),
            "cells": cells, "rows": rows}


def compare_curriculum(seeds=(0, 1, 2, 3, 4), warmup_trials: int = 150,
                       compo_trials: int = 250, n_agents: int = 8) -> dict:
    """A/B apparié legacy vs torch du curriculum. Verdict_curriculum :
    WARMUP_FAILED si did_x ne monte pas en warmup (médiane warmup_didx_end ≤ 0.30 sur un bras) ;
    DISCOVERY si warmup réussit ET hit_end médian décolle (> 0.30) sur ≥1 bras ;
    CREDIT si warmup réussit MAIS hit_end médian reste planché (≤ 0.15) sur les DEUX bras ;
    sinon AMBIGU. Seuils heuristiques (le verdict final est lu par l'humain sur les chiffres)."""
    rows = []
    for s in seeds:
        leg = run_curriculum("legacy", seed=s, warmup_trials=warmup_trials,
                             compo_trials=compo_trials, n_agents=n_agents)
        tor = run_curriculum("torch", seed=s, warmup_trials=warmup_trials,
                             compo_trials=compo_trials, n_agents=n_agents)
        rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                     "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})

    def _med(arm, key):
        return statistics.median([r[arm][key] for r in rows])

    leg_warm, tor_warm = _med("legacy", "warmup_didx_end"), _med("torch", "warmup_didx_end")
    leg_hit, tor_hit = _med("legacy", "hit_end"), _med("torch", "hit_end")
    warmup_ok = (leg_warm > 0.30) and (tor_warm > 0.30)
    if not warmup_ok:
        verdict_c = "WARMUP_FAILED"
    elif leg_hit > 0.30 or tor_hit > 0.30:
        verdict_c = "DISCOVERY"
    elif leg_hit <= 0.15 and tor_hit <= 0.15:
        verdict_c = "CREDIT"
    else:
        verdict_c = "AMBIGU"
    return {**compute_ab_verdict(rows), "verdict_curriculum": verdict_c,
            "summary": {"legacy_warmup_didx_end": leg_warm, "torch_warmup_didx_end": tor_warm,
                        "legacy_hit_end": leg_hit, "torch_hit_end": tor_hit},
            "per_seed": rows}


def _probe_one(backend: str, seed: int, n_agents: int, trials: int, num_nodes: int, target_x: int):
    """Collecte (H_pre, H_S2, did_x) par agent SANS apprentissage, puis décode per-agent.
    obs_a VARIÉ par trial (fait varier did_x), obs_b FIXE (S2 n'encode pas did_x)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    agents = _build_agents(n_agents, num_nodes, "prod")
    pop = make_population(agents, backend=backend)
    I = agents[0].genome.num_inputs
    rng = np.random.RandomState(seed + 1)
    obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)         # S2 fixe
    pre_buf = [[] for _ in range(n_agents)]
    s2_buf = [[] for _ in range(n_agents)]
    didx_buf = [[] for _ in range(n_agents)]
    for _ in range(trials):
        H_pre = _read_state(pop, backend)                             # état AVANT S1
        obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)     # S1 VARIÉ
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        pop.forward(obs_b)                                            # S2 -> met à jour l'état
        H_s2 = _read_state(pop, backend)
        for i in range(n_agents):
            pre_buf[i].append(H_pre[i, I:])
            s2_buf[i].append(H_s2[i, I:])
            didx_buf[i].append(bool(did_x[i]))
    auc_s2, auc_pre, auc_shuffled, base = [], [], [], []
    for i in range(n_agents):
        y = np.array(didx_buf[i], dtype=int)
        base.append(float(np.mean(y)))
        X_s2 = np.array(s2_buf[i])
        y_perm = np.random.RandomState(seed * 1000 + i).permutation(y)
        a2 = _decode_auc(X_s2, y, seed=seed)
        ap = _decode_auc(np.array(pre_buf[i]), y, seed=seed)
        ash = _decode_auc(X_s2, y_perm, seed=seed)
        if a2 is not None:
            auc_s2.append(a2)
        if ap is not None:
            auc_pre.append(ap)
        if ash is not None:
            auc_shuffled.append(ash)
    med_s2 = statistics.median(auc_s2) if auc_s2 else None
    med_pre = statistics.median(auc_pre) if auc_pre else None
    med_delta = (med_s2 - med_pre) if (med_s2 is not None and med_pre is not None) else None
    med_shuf = statistics.median(auc_shuffled) if auc_shuffled else None
    return {"backend": backend, "seed": int(seed), "n_qualifying": len(auc_s2),
            "base_rate": float(np.mean(base)), "median_auc_s2": med_s2,
            "median_auc_pre": med_pre, "median_delta": med_delta,
            "median_auc_shuffled": med_shuf,
            "per_agent_auc_s2": auc_s2, "per_agent_auc_pre": auc_pre,
            "per_agent_auc_shuffled": auc_shuffled}


def memory_probe(seeds=(0, 1, 2), n_agents: int = 16, trials: int = 300,
                 num_nodes: int = 172, target_x: int = 0) -> dict:
    """Sonde la décodabilité linéaire de did_x depuis H_S2 (mémoire) vs H_pre (diagnostic),
    per-agent, par backend. Verdict : MEMORY_PRESENT si AUC_S2 médian >0.6 sur les DEUX backends
    ET control_valid (contrôle permutation dans la bande chance) ; MEMORY_ABSENT si AUC_S2 ≈0.5
    (≤0.55) sur les deux ; sinon ASYMÉTRIQUE."""
    cells = []
    for backend in ("legacy", "torch"):
        for s in seeds:
            cells.append(_probe_one(backend, s, n_agents, trials, num_nodes, target_x))

    def _agg(backend):
        vals_s2 = [c["median_auc_s2"] for c in cells if c["backend"] == backend and c["median_auc_s2"] is not None]
        vals_d = [c["median_delta"] for c in cells if c["backend"] == backend and c["median_delta"] is not None]
        vals_shuf = [c["median_auc_shuffled"] for c in cells if c["backend"] == backend and c["median_auc_shuffled"] is not None]
        return (statistics.median(vals_s2) if vals_s2 else None,
                statistics.median(vals_d) if vals_d else None,
                statistics.median(vals_shuf) if vals_shuf else None)

    leg_s2, leg_d, leg_shuf = _agg("legacy")
    tor_s2, tor_d, tor_shuf = _agg("torch")

    def _in_chance(v):
        return v is not None and 0.40 <= v <= 0.60

    control_valid = _in_chance(leg_shuf) and _in_chance(tor_shuf)

    # Verdict gate sur le contrôle permutation (pas le delta H_pre, qui est confondu car
    # H_pre est causalement en amont de did_x et peut être élevé sans encoder did_x).
    def _carries(s2):
        return (s2 is not None and s2 > 0.6)

    def _absent(s2):
        return (s2 is not None and s2 <= 0.55)

    if control_valid and _carries(leg_s2) and _carries(tor_s2):
        verdict = "MEMORY_PRESENT"
    elif _absent(leg_s2) and _absent(tor_s2):
        verdict = "MEMORY_ABSENT"
    else:
        verdict = "ASYMÉTRIQUE"

    return {"cells": cells, "verdict": verdict, "control_valid": control_valid,
            "summary": {"legacy_auc_s2": leg_s2, "legacy_delta": leg_d,
                        "torch_auc_s2": tor_s2, "torch_delta": tor_d,
                        "legacy_auc_shuffled": leg_shuf, "torch_auc_shuffled": tor_shuf}}


def sweep(hiddens=(5, 20, 50, 100), inits=("prod", "normalized"),
          seeds=(0, 1, 2, 3, 4), trials: int = 250, n_agents: int = 8) -> dict:
    """Grille A/B legacy↔torch par cellule (hidden, init). Déduplique normalized@5 == prod@5
    (même facteur 1.0). Renvoie {cells, curve} ; curve = hit_end médian par taille et backend
    (lecture décisive A/B/C). Jamais de scalaire nu : per_seed conservé par cellule."""
    cells = []
    curve = {"legacy": [], "torch": []}
    seen = set()
    for hidden in hiddens:
        num_nodes = 167 + hidden
        for init in inits:
            factor = round(_init_factor(num_nodes, init), 6)
            key = (hidden, factor)            # dédup : normalized@anchor (factor 1.0) == prod
            if key in seen:
                continue
            seen.add(key)
            rows = []
            for s in seeds:
                leg = run_compositional("legacy", seed=s, trials=trials, n_agents=n_agents,
                                        num_nodes=num_nodes, init_scale=init)
                tor = run_compositional("torch", seed=s, trials=trials, n_agents=n_agents,
                                        num_nodes=num_nodes, init_scale=init)
                rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                             "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})
            verdict = compute_ab_verdict(rows)
            cells.append({"hidden": hidden, "init": init, **verdict, "per_seed": rows})
            curve["legacy"].append({"hidden": hidden, "init": init,
                                    "median_hit_end": statistics.median([r["legacy"]["hit_end"] for r in rows]),
                                    "median_delta": statistics.median([r["legacy_delta"] for r in rows])})
            curve["torch"].append({"hidden": hidden, "init": init,
                                   "median_hit_end": statistics.median([r["torch"]["hit_end"] for r in rows]),
                                   "median_delta": statistics.median([r["torch_delta"] for r in rows])})
    return {"cells": cells, "curve": curve}


def compare(seeds=(0, 1, 2, 3, 4), trials: int = 100, n_agents: int = 8) -> dict:
    """A/B apparié legacy vs torch par seed -> verdict de learnabilité compositionnelle."""
    rows = []
    for s in seeds:
        leg = run_compositional("legacy", seed=s, trials=trials, n_agents=n_agents)
        tor = run_compositional("torch", seed=s, trials=trials, n_agents=n_agents)
        rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                     "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})
    return {**compute_ab_verdict(rows), "per_seed": rows}


def main():
    hiddens = [int(h) for h in os.environ.get("SABC_HIDDENS", "5,20,50,100").split(",") if h.strip()]
    inits = [x.strip() for x in os.environ.get("SABC_INITS", "prod,normalized").split(",") if x.strip()]
    seeds = [int(s) for s in os.environ.get("SABC_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    trials = int(os.environ.get("SABC_TRIALS", "250"))
    n_agents = int(os.environ.get("SABC_AGENTS", "8"))
    res = sweep(hiddens=hiddens, inits=inits, seeds=seeds, trials=trials, n_agents=n_agents)
    print("CELLS (hidden x init -> verdict, median diff, hit_end medians):")
    for c, lp, tp in zip(res["cells"], res["curve"]["legacy"], res["curve"]["torch"]):
        print(f"  hidden={c['hidden']:>3} init={c['init']:<10} verdict={c['verdict']:<14} "
              f"median_diff={c['median_diff']:+.3f} sign_p={c['sign_p']:.3f} "
              f"legacy_hit_end={lp['median_hit_end']:.3f} torch_hit_end={tp['median_hit_end']:.3f}")
    print("CURVE legacy:", [(p["hidden"], p["init"], round(p["median_hit_end"], 3)) for p in res["curve"]["legacy"]])
    print("CURVE torch :", [(p["hidden"], p["init"], round(p["median_hit_end"], 3)) for p in res["curve"]["torch"]])
    out = os.environ.get("SABC_OUT")
    if out:
        import json
        with open(out, "w") as f:
            json.dump(res, f, indent=2)
        print(f"WROTE {out}")
    return res


def main_memory_probe():
    seeds = [int(s) for s in os.environ.get("SABC_MP_SEEDS", "0,1,2").split(",") if s.strip()]
    n_agents = int(os.environ.get("SABC_MP_AGENTS", "16"))
    trials = int(os.environ.get("SABC_MP_TRIALS", "300"))
    res = memory_probe(seeds=tuple(seeds), n_agents=n_agents, trials=trials)
    print(f"VERDICT={res['verdict']}  summary={res['summary']}")
    print(f"control_valid={res['control_valid']}  "
          f"legacy_auc_shuffled={res['summary'].get('legacy_auc_shuffled')}  "
          f"torch_auc_shuffled={res['summary'].get('torch_auc_shuffled')}")
    print("CELLS (backend x seed -> n_qual, base_rate, AUC_s2, AUC_pre, delta, AUC_shuf):")
    for c in res["cells"]:
        def _f(x):
            return f"{x:.3f}" if x is not None else "  NA "
        print(f"  {c['backend']:<6} seed={c['seed']} n_qual={c['n_qualifying']:>2} "
              f"base={c['base_rate']:.3f} AUC_s2={_f(c['median_auc_s2'])} "
              f"AUC_pre={_f(c['median_auc_pre'])} delta={_f(c['median_delta'])} "
              f"AUC_shuf={_f(c['median_auc_shuffled'])}")
    out = os.environ.get("SABC_MP_OUT")
    if out:
        import json
        with open(out, "w") as f:
            json.dump(res, f, indent=2)
        print(f"WROTE {out}")
    return res


def main_curriculum():
    seeds = [int(s) for s in os.environ.get("SABC_CU_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    warmup = int(os.environ.get("SABC_CU_WARMUP", "150"))
    compo = int(os.environ.get("SABC_CU_COMPO", "250"))
    n_agents = int(os.environ.get("SABC_CU_AGENTS", "8"))
    res = compare_curriculum(seeds=tuple(seeds), warmup_trials=warmup,
                             compo_trials=compo, n_agents=n_agents)
    print(f"VERDICT_CURRICULUM={res['verdict_curriculum']}  summary={res['summary']}")
    print("PER-SEED (warmup_didx_end -> hit_end ; compo_didx retention):")
    for r in res["per_seed"]:
        for arm in ("legacy", "torch"):
            a = r[arm]
            print(f"  seed={r['seed']} {arm:<6} warmup_didx={a['warmup_didx_end']:.3f} "
                  f"hit_end={a['hit_end']:.3f} compo_didx {a['compo_didx_start']:.3f}->{a['compo_didx_end']:.3f}")
    out = os.environ.get("SABC_CU_OUT")
    if out:
        import json
        with open(out, "w") as f:
            json.dump(res, f, indent=2)
        print(f"WROTE {out}")
    return res


def main_curriculum_fade():
    seeds = [int(s) for s in os.environ.get("SABC_CF_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    warmup = int(os.environ.get("SABC_CF_WARMUP", "150"))
    compo = int(os.environ.get("SABC_CF_COMPO", "250"))
    n_agents = int(os.environ.get("SABC_CF_AGENTS", "8"))
    fade_w0 = float(os.environ.get("SABC_CF_W0", "1.0"))
    res = compare_curriculum_fade(seeds=tuple(seeds), warmup_trials=warmup, compo_trials=compo,
                                  n_agents=n_agents, fade_w0=fade_w0)
    print(f"VERDICT_FADE={res['verdict_fade']} (w0={fade_w0})  summary={res['summary']}")
    print("PER-SEED (compo_didx_end ; hit_end ; P(Y|X)_end) :")
    for r in res["per_seed"]:
        for arm in ("legacy", "torch"):
            a = r[arm]
            pyx = a["p_y_given_x_end"]
            pyx_s = f"{pyx:.3f}" if pyx is not None else " None"
            print(f"  seed={r['seed']} {arm:<6} didx_end={a['compo_didx_end']:.3f} "
                  f"hit_end={a['hit_end']:.3f} P(Y|X)={pyx_s} y_rate={a['y_rate_end']:.3f}")
    out = os.environ.get("SABC_CF_OUT")
    if out:
        import json
        with open(out, "w") as f:
            json.dump(res, f, indent=2)
        print(f"WROTE {out}")
    return res


if __name__ == "__main__":
    import sys as _sys
    if "--memory-probe" in _sys.argv:
        main_memory_probe()
    elif "--curriculum-fade" in _sys.argv:
        main_curriculum_fade()
    elif "--curriculum" in _sys.argv:
        main_curriculum()
    else:
        main()
