"""tools/g_fidelity_probe.py — Sonde de fidélité de g (NAS Axe 3, spec dream-offline, composant A).
go/no-go : g(H,a)→H' prédit-il les transitions latentes mieux que la baseline « pas de changement » ?
Si NON -> escalader vers g bilinéaire avant de bâtir Dyna. AUCUN changement du code cœur.

Deux mesures disponibles :
  collect_ratios     — obs synthétiques (artefact corrigé : round-robin + obs variables σ=0.3)
  collect_ratios_env — env grille 1-D réel (action→pos→obs couplé) : mesure CAUSALE de référence

Usage : GFP_SEEDS=0,1,2 python tools/g_fidelity_probe.py
        GFP_SEEDS=0,1,2 GFP_ENV=0 python tools/g_fidelity_probe.py  (mode synthétique)"""
import os
import sys
import math
import statistics as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from src.agents.mamba_agent import MambaAgent, MambaBatchModel

# --- Constantes env grille (bench-compatible) ---
_GRID_L = 7           # longueur de la grille 1-D
_T_WARN_PERIOD = 6    # période de télégraphe du danger
_N_MOVES = 3          # espace d'action : 0=gauche, 1=rester, 2=droite
_OBS_DIM = 2 * _GRID_L   # = 14 : one-hot(pos) ++ one-hot(danger)


def _obs_bench(pos: int, danger_cell) -> np.ndarray:
    """Obs 1-D grille : one-hot position (L) ++ one-hot danger télégraphié (L)."""
    o = np.zeros(_OBS_DIM, dtype=np.float32)
    o[pos] = 1.0
    if danger_cell is not None:
        o[_GRID_L + danger_cell] = 1.0
    return o


def transition_error(H_prev, g_delta, H_next):
    """(g_err, base_err) pour une transition latente. g_err = prédiction de g ; base_err = baseline."""
    H_prev = np.asarray(H_prev, dtype=np.float32)
    g_delta = np.asarray(g_delta, dtype=np.float32)
    H_next = np.asarray(H_next, dtype=np.float32)
    g_err = float(np.mean((H_prev + g_delta - H_next) ** 2))
    base_err = float(np.mean((H_prev - H_next) ** 2))
    return g_err, base_err


def _sign_p(k: int, n: int) -> float:
    if n <= 0:
        return 1.0
    khi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(khi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def fidelity_verdict(ratios) -> dict:
    """ratios[i] = g_err/base_err par transition. g UTILE = ratio < 1 (g bat la baseline)."""
    ratios = [float(r) for r in ratios]
    n = len(ratios)
    if n == 0:
        return {"median_ratio": 1.0, "n_favorable": 0, "n": 0, "sign_p": 1.0, "verdict": "NEUTRE"}
    med = st.median(ratios)
    n_fav = sum(1 for r in ratios if r < 1.0)            # favorable = g meilleur
    eff = [r for r in ratios if r != 1.0]
    sign_p = _sign_p(sum(1 for r in eff if r < 1.0), len(eff))
    if med < 0.95 and 2 * n_fav > n:
        verdict = "G_FIDELE"
    elif med > 1.05:
        verdict = "G_INUTILE"
    else:
        verdict = "NEUTRE"
    return {"median_ratio": float(med), "n_favorable": int(n_fav), "n": int(n),
            "sign_p": float(sign_p), "verdict": verdict}


def collect_ratios(seed: int, warmup: int = 300, measure: int = 300):
    """Boucle pilotée : exercice en round-robin des PLAN_A actions (diversité d'actions),
    obs non-nulles variables (régime non-trivial), g apprend en ligne (PLAN_BIAS>0).
    Enregistre g_err/base_err par transition (action RÉELLEMENT jouée à ce tick).
    Restaure les flags en finally.
    Retourne aussi action_abs_by_action : dict action -> list |G[a]| moyens pour diagnostic."""
    rng = np.random.default_rng(seed)
    a = MambaAgent()
    a.genome.organ_genes = np.array([True, False])          # organe planificateur actif (g se met à jour)
    prev_bias, prev_a, prev_lr = (MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_A, MambaBatchModel.PLAN_LR)
    MambaBatchModel.PLAN_BIAS = 0.5
    MambaBatchModel.PLAN_LR = 0.1
    ratios = []
    action_abs_by_action: dict = {a_idx: [] for a_idx in range(MambaBatchModel.PLAN_A)}
    try:
        m = MambaBatchModel([a])
        n_in = a.genome.num_inputs
        n_actions = MambaBatchModel.PLAN_A
        map_idx = m.mappings[0]
        prev_hrec = None
        prev_move = None
        for t in range(warmup + measure):
            # FIX 2 — obs non-nulles VARIABLES par tick (régime non-trivial, déterministe par seed)
            obs = rng.standard_normal((1, n_in)).astype(np.float32) * 0.3
            preds, _ = m.forward(obs)
            # FIX 1 — round-robin des actions pour exercer les 8 colonnes de G
            move = int(t % n_actions)
            # H_rec courant en ordre nœud (capturé par forward, avant le rêve)
            cur_hrec = m.H_rec_batch[0, map_idx].copy()
            if t >= warmup and prev_hrec is not None and prev_move is not None:
                g_delta = m.G_batch[0][:, map_idx][prev_move]    # colonne de l'action JOUÉE au tick précédent
                g_err, base_err = transition_error(prev_hrec, g_delta, cur_hrec)
                # FIX 3 — seuil relevé : ignorer les transitions de très faible amplitude
                if base_err > 0.01:
                    ratios.append(g_err / base_err)
            # Diagnostic diversité : mean|G[a]| pour l'action jouée à ce tick
            g_col = m.G_batch[0][:, map_idx][move]               # (N_i,)
            action_abs_by_action[move].append(float(np.mean(np.abs(g_col))))
            # apprentissage en ligne de g (transition différée) : nécessite compute_policy_gradient
            m.compute_policy_gradient(np.array([0.1], dtype=np.float32),
                                      [{"move": move, "grab": 0, "rub": 0}])
            prev_hrec, prev_move = cur_hrec, move
    finally:
        MambaBatchModel.PLAN_BIAS, MambaBatchModel.PLAN_A, MambaBatchModel.PLAN_LR = prev_bias, prev_a, prev_lr
    return ratios, action_abs_by_action


def run_probe(seeds, warmup: int = 300, measure: int = 300) -> dict:
    """Agrège collect_ratios sur plusieurs seeds. Retourne le verdict + diagnostics action."""
    all_ratios = []
    # accumulate mean|G[a]| per action across seeds
    n_actions = MambaBatchModel.PLAN_A
    action_abs_accum: dict = {a_idx: [] for a_idx in range(n_actions)}
    for s in seeds:
        ratios, action_abs = collect_ratios(int(s), warmup, measure)
        all_ratios.extend(ratios)
        for a_idx in range(n_actions):
            action_abs_accum[a_idx].extend(action_abs[a_idx])
    result = fidelity_verdict(all_ratios)
    result["mean_G_abs_by_action"] = {
        a_idx: float(np.mean(vals)) if vals else 0.0
        for a_idx, vals in action_abs_accum.items()
    }
    return result


def collect_ratios_env(seed: int, warmup: int = 300, measure: int = 300):
    """Mesure de fidélité de g dans un env où les ACTIONS ONT DE VRAIES CONSEQUENCES.

    Env : grille 1-D de longueur L=7 (bench-compatible).
    - obs = one-hot(pos) ++ one-hot(danger_telegraph) — 14 dimensions
    - move ∈ {0=gauche, 1=rester, 2=droite} change réellement la position
    - Donc : action → pos' → obs' : le lien action→next-obs EST présent par construction.

    Couverture des actions : round-robin sur {0,1,2} (force G[0..2] tous entraînés et mesurés).
    PLAN_A=3 (aligne g sur l'espace d'action réel du bench).
    Restaure PLAN_BIAS/PLAN_A/PLAN_LR en finally.

    Retourne
    --------
    ratios              : list[float]   g_err/base_err par transition (base_err > 0.01 filtrée)
    action_abs_by_action: dict          action -> list mean|G[a]| (preuve de diversité)
    """
    np.random.seed(seed)   # reproductibilité du réseau (MambaAgent utilise np.random)
    # Agent dimensionné pour l'obs du bench (14 entrées)
    a = MambaAgent(num_inputs=_OBS_DIM, num_outputs=108, num_nodes=172)
    a.genome.organ_genes = np.array([True, False])          # organe planificateur actif

    prev_bias = MambaBatchModel.PLAN_BIAS
    prev_plan_a = MambaBatchModel.PLAN_A
    prev_plan_lr = MambaBatchModel.PLAN_LR
    MambaBatchModel.PLAN_BIAS = 0.5
    MambaBatchModel.PLAN_A = _N_MOVES     # 3 : aligne g sur l'espace action réel
    MambaBatchModel.PLAN_LR = 0.1
    # Seuil adapté aux obs one-hot (amplitude ~10× plus faible qu'obs gaussiennes σ=0.3)
    _BASE_ERR_THRESH = 1e-4
    ratios = []
    action_abs_by_action: dict = {a_idx: [] for a_idx in range(_N_MOVES)}
    try:
        m = MambaBatchModel([a])
        map_idx = m.mappings[0]

        # État env : déterministe via seed numpy
        pos = _GRID_L // 2
        pending_danger = None

        prev_hrec = None
        prev_move = None

        for t in range(warmup + measure):
            # --- Résoudre la frappe du tick précédent (gap temporel F1 du bench) ---
            strike_cell = pending_danger
            pending_danger = None
            if strike_cell is not None:
                if pos == strike_cell:
                    # Respawn au centre (comme bench R1)
                    pos = _GRID_L // 2

            # --- Construire l'obs depuis l'état réel de l'env ---
            warn = (t % _T_WARN_PERIOD == 0)
            telegraph = pos if warn else None
            obs = _obs_bench(pos, telegraph)[None, :]    # (1, 14)

            # --- Forward ---
            preds, _ = m.forward(obs)

            # --- Action : round-robin pour couvrir toutes les colonnes de G ---
            move = int(t % _N_MOVES)

            # --- Capturer H_rec APRÈS forward (latent pré-rêve) ---
            cur_hrec = m.H_rec_batch[0, map_idx].copy()

            # --- Mesurer fidélité APRÈS warmup ---
            if t >= warmup and prev_hrec is not None and prev_move is not None:
                g_delta = m.G_batch[0][:, map_idx][prev_move]    # colonne de l'action jouée t-1
                g_err, base_err = transition_error(prev_hrec, g_delta, cur_hrec)
                if base_err > _BASE_ERR_THRESH:
                    ratios.append(g_err / base_err)

            # --- Diagnostic mean|G[a]| pour l'action jouée ---
            g_col = m.G_batch[0][:, map_idx][move]
            action_abs_by_action[move].append(float(np.mean(np.abs(g_col))))

            # --- Apprentissage en ligne de g via policy_gradient ---
            reward = 0.1 if (strike_cell is None or pos != strike_cell) else -1.0
            m.compute_policy_gradient(
                np.array([reward], dtype=np.float32),
                [{"move": move, "grab": 0, "rub": 0}])

            # --- Appliquer le mouvement dans l'env ---
            new_pos = min(_GRID_L - 1, max(0, pos + (move - 1)))
            if warn:
                # Telegraph : danger frappe au prochain tick sur la pos ACTUELLE
                pending_danger = pos
            pos = new_pos

            prev_hrec, prev_move = cur_hrec, move
    finally:
        MambaBatchModel.PLAN_BIAS = prev_bias
        MambaBatchModel.PLAN_A = prev_plan_a
        MambaBatchModel.PLAN_LR = prev_plan_lr
    return ratios, action_abs_by_action


def run_probe_env(seeds, warmup: int = 300, measure: int = 300) -> dict:
    """Agrège collect_ratios_env sur plusieurs seeds. Mesure CAUSALE (env réel)."""
    all_ratios = []
    action_abs_accum: dict = {a_idx: [] for a_idx in range(_N_MOVES)}
    for s in seeds:
        ratios, action_abs = collect_ratios_env(int(s), warmup, measure)
        all_ratios.extend(ratios)
        for a_idx in range(_N_MOVES):
            action_abs_accum[a_idx].extend(action_abs[a_idx])
    result = fidelity_verdict(all_ratios)
    result["mean_G_abs_by_action"] = {
        a_idx: float(np.mean(vals)) if vals else 0.0
        for a_idx, vals in action_abs_accum.items()
    }
    return result



def collect_ratios_stoneage(seed, num_agents=30, warmup=150, measure=150, genome=None, benchmark=False):
    """Collecte les ratios g_err/base_err sur observations REELLES du monde stoneage.

    Approche : num_agents agents libres dans Biosphere3D. Apres warmup ticks, on mesure
    pour chaque agent vivant la fidelite de g(H(t-1), action(t-1)) vers H(t).

    Attributs requis sur ag["model"] apres step() :
      - H_prev     : (1, N) latent mis a jour
      - planner_G  : (PLAN_A, N_i) colonnes g par action
      - _td        : dict avec "act" -> {"move": int, ...}

    Si ces attributs sont absents, log un warning et retourne liste vide + note NEEDS_CONTEXT.

    Restaure PLAN_BIAS/PLAN_LR en finally. AUCUN changement du code de production.
    """
    import logging
    log = logging.getLogger("AGIseed.GFP.stoneage")

    # Sauvegarder et regler les flags
    prev_bias = MambaBatchModel.PLAN_BIAS
    prev_lr = MambaBatchModel.PLAN_LR
    # PLAN_A non modifie : on garde la valeur par defaut (8)
    MambaBatchModel.PLAN_BIAS = 0.5
    MambaBatchModel.PLAN_LR = 0.1

    ratios = []
    n_transitions = 0
    action_abs_by_action = {a_idx: [] for a_idx in range(MambaBatchModel.PLAN_A)}
    needs_context = False
    context_note = ""

    try:
        from src.environments.config import WorldConfig
        from src.seed_ai.harness import SeedManager
        from src.worlds.world_1_stoneage import Biosphere3D
        from src.graph_rag.async_logger import logger as async_logger

        cfg = WorldConfig()
        cfg.base_metabolism = 0.25
        cfg.forage_payoff = 3.0

        # Agents avec planificateur actif. genome fourni -> CHAMPION competent (leve le blocueur
        # n=0 : les agents frais meurent ~15 ticks < warmup, aucune transition mesurable ; un
        # champion survit 66+ au sweet-spot EDR-129 -> g a le temps d'apprendre et d'etre mesure).
        agents_list = []
        for _ in range(num_agents):
            a = MambaAgent()
            if genome is not None:
                a.from_genome(genome)
            a.genome.organ_genes = np.array([True, False])   # planner ON (apres from_genome)
            agents_list.append(a)

        # Determinisme
        SeedManager(seed).seed_boundary(0)

        env = Biosphere3D(cfg)
        if benchmark:
            # cohorte fixe (pas de repro -> le planner n'est pas dilue par des rejetons sans g,
            # cf. caveat 'clone() ne propage pas planner_G') + regime EDR-129 (nuit OFF, scaffolds OFF).
            env.benchmark_mode = True
            env.night_enabled = False
            env.current_era = 10_000
        for a in agents_list:
            env.add_agent(a, energy=80.0)

        # KuzuDB async_logger = goulot (écriture par tick) et INUTILE pour une mesure de fidélité.
        # En benchmark (champion), on le SAUTE -> step() marche sans (cf. cross_world_transfer) et le
        # run passe de minutes à secondes. Chemin par défaut (agents frais) inchangé (le démarre).
        _use_logger = not benchmark
        if _use_logger:
            async_logger.start()

        # prev_H par agent_id : H(t-1) et action(t-1)
        prev_state = {}  # agent_id -> {"H": np.ndarray (N,), "move": int, "G_col": np.ndarray}

        for t in range(warmup + measure):
            env.step()

            for ag in env.agents:
                model = ag["model"]
                agent_id = ag.get("id", id(model))

                # Verifier H_prev
                if not hasattr(model, "H_prev") or model.H_prev is None:
                    if not needs_context:
                        log.warning("H_prev absent sur ag %s - NEEDS_CONTEXT", agent_id)
                        needs_context = True
                        context_note = "H_prev absent"
                    continue

                cur_H = np.asarray(model.H_prev[0], dtype=np.float32)

                # Verifier _td et action
                td = getattr(model, "_td", None)
                move = -1
                if td is not None and td.get("act") is not None:
                    move = int(td["act"].get("move", -1))

                # Verifier planner_G
                G = getattr(model, "planner_G", None)
                g_col = None
                if G is not None and move >= 0 and move < G.shape[0]:
                    g_col = G[move]
                    action_abs_by_action.setdefault(move, []).append(float(np.mean(np.abs(g_col))))
                elif G is None and not needs_context:
                    log.warning("planner_G absent sur ag %s (PLAN_BIAS=%.1f) - NEEDS_CONTEXT",
                                agent_id, MambaBatchModel.PLAN_BIAS)
                    needs_context = True
                    context_note = "planner_G absent"

                # Mesure de fidelite : seulement apres warmup et si prev disponible
                if t >= warmup and agent_id in prev_state and g_col is not None:
                    ps = prev_state[agent_id]
                    if ps.get("G_col") is not None:
                        g_err, base_err = transition_error(ps["H"], ps["G_col"], cur_H)
                        if base_err > 0.01:
                            ratios.append(g_err / base_err)
                            n_transitions += 1

                # Memoriser l'etat courant pour le tick suivant
                prev_state[agent_id] = {
                    "H": cur_H.copy(),
                    "move": move,
                    "G_col": g_col.copy() if g_col is not None else None,
                }

            # Nettoyer les agents morts de prev_state pour eviter les faux positifs
            alive_ids = {ag.get("id", id(ag["model"])) for ag in env.agents}
            for dead_id in list(prev_state.keys()):
                if dead_id not in alive_ids:
                    del prev_state[dead_id]

        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()

    finally:
        MambaBatchModel.PLAN_BIAS = prev_bias
        MambaBatchModel.PLAN_LR = prev_lr
        if not benchmark:
            try:
                from src.graph_rag.async_logger import logger as async_logger
                async_logger.stop()
            except Exception:
                pass

    result = {
        "ratios": ratios,
        "n_transitions": n_transitions,
        "action_abs_by_action": action_abs_by_action,
    }
    if needs_context:
        result["needs_context"] = context_note
    return result


def run_probe_stoneage(seeds, warmup=150, measure=150, num_agents=30, genome=None, benchmark=False) -> dict:
    """Agrege collect_ratios_stoneage sur plusieurs seeds. Retourne le verdict + diagnostics.
    genome fourni -> cohorte de champions (leve le blocueur n=0) ; benchmark -> cohorte fixe."""
    all_ratios = []
    action_abs_accum = {a_idx: [] for a_idx in range(MambaBatchModel.PLAN_A)}
    total_transitions = 0
    notes = []

    for s in seeds:
        res = collect_ratios_stoneage(int(s), num_agents=num_agents, warmup=warmup, measure=measure,
                                      genome=genome, benchmark=benchmark)
        all_ratios.extend(res["ratios"])
        total_transitions += res["n_transitions"]
        for a_idx, vals in res["action_abs_by_action"].items():
            action_abs_accum.setdefault(a_idx, []).extend(vals)
        if "needs_context" in res:
            notes.append(res["needs_context"])

    result = fidelity_verdict(all_ratios)
    result["mean_G_abs_by_action"] = {
        a_idx: float(np.mean(vals)) if vals else 0.0
        for a_idx, vals in action_abs_accum.items()
    }
    result["n_transitions"] = total_transitions
    if notes:
        result["needs_context"] = notes[0]
    return result


def main():
    seeds = [int(s) for s in os.environ.get("GFP_SEEDS", "0,1,2,3,4,5,6,7").split(",") if s.strip()]
    warmup = int(os.environ.get("GFP_WARMUP", "300"))
    measure = int(os.environ.get("GFP_MEASURE", "300"))
    mode = os.environ.get("GFP_MODE", "").strip().lower()
    use_env = os.environ.get("GFP_ENV", "1").strip() not in ("0", "false", "False")

    if mode == "stoneage":
        num_agents = int(os.environ.get("GFP_NUM_AGENTS", "30"))
        # GFP_HOF -> injecte un CHAMPION competent (leve le blocueur n=0 ; cohorte fixe par defaut).
        genome = None
        hof = os.environ.get("GFP_HOF", "").strip()
        benchmark = os.environ.get("GFP_BENCHMARK", "1" if hof else "0").strip() not in ("0", "false", "False")
        if hof:
            import importlib
            from src.seed_ai import persistence
            os.environ["HOF_PATH"] = hof
            importlib.reload(persistence)
            _v, entries = persistence.load_hall_of_fame()
            if not entries:
                raise RuntimeError(f"HoF vide : {hof}")
            genome = entries[0].genome
            print(f"[champion] {hof} (dims {genome.num_inputs}/{genome.num_outputs}), benchmark={benchmark}")
        print(f"=== g-fidelity probe STONEAGE (Biosphere3D, obs reelles) seeds={seeds} ===")
        out = run_probe_stoneage(seeds, warmup=warmup, measure=measure, num_agents=num_agents,
                                 genome=genome, benchmark=benchmark)
    elif use_env:
        print(f"=== g-fidelity probe ENV (grille 1-D, action->obs couple) seeds={seeds} ===")
        out = run_probe_env(seeds, warmup, measure)
    else:
        print(f"=== g-fidelity probe SYNTHÉTIQUE seeds={seeds} ===")
        out = run_probe(seeds, warmup, measure)

    print(f"VERDICT={out['verdict']} median_ratio={out['median_ratio']:.3f} "
          f"n_fav={out['n_favorable']}/{out['n']} sign_p={out['sign_p']:.3f}")
    g_abs = out.get("mean_G_abs_by_action", {})
    if g_abs:
        vals_str = " ".join(f"G[{a}]={v:.4f}" for a, v in sorted(g_abs.items()))
        print(f"ACTION_DIVERSITY mean|G[a]|: {vals_str}")
    return out


if __name__ == "__main__":
    main()
