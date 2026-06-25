"""Banc d'anticipation v3 (NAS Axe 3) : danger télégraphié 1-pas, FAIR test.

Le planificateur (PLAN_BIAS>0) est testé sur un env CONÇU pour récompenser l'anticipation.
Découple 'le plan marche' de 'le monde le récompense'. Déterministe, sans graph_rag.

Usage : AB_SEEDS=0,1,2 python tools/anticipation_bench.py
        AB_SEEDS=0,1,2 AB_STEPS=1200 python tools/anticipation_bench.py

==========================================================================
Fixes v1/v2 (conservés) :
  F1 — Gap temporel : pénalité −1 donnée au tick de la FRAPPE (t+1), pas au
       tick d'avertissement (t). Le crédit traverse un tick : un réactif
       1-pas ne peut pas relier signal(t) à punition(t+1).
  F2 — Espace d'action aligné : PLAN_A=3 avant création du modèle ; move=
       argmax(preds[:3]) sans %3. g apprend et le biais portent sur {0,1,2}.
  F3 — Budget de convergence : défaut 1000 steps.

Nouveautés v3 (FAIR test) :
  R1 — Respawn-on-death : quand l'agent est frappé il revient au centre
       (pos = L//2) au lieu de terminer l'épisode. L'épisode dure
       exactement `steps` ticks quoi qu'il arrive → g accumule du signal
       sur TOUTE la fenêtre.
  R2 — Métrique : danger-avoidance rate = dangers_avoided / dangers_faced.
       Un agent parfait → 1.0 ; un agent aléatoire → ≈0.5 (il reste sur
       place la moitié du temps face au danger). Métrique non-saturée et
       non-capée par la mort précoce.
  R3 — Warm-up diagnostique : `verbose=True` (activé par défaut dans main)
       affiche mean|G| en fin d'épisode pour vérifier que g a convergé.
  R4 — Bilan par danger : stats_str optionnel dans dict de sortie pour débogage.

Contraintes maintenues :
  - Déterministe par seed (np.random.seed).
  - PLAN_BIAS, PLAN_A, PLAN_LR restaurés dans finally.
  - API publique compatible : run_bench / compare avec mêmes clés.
  - Les deux bras (plan / réactif) partagent la même env/seed.
==========================================================================
"""
import os
import sys
import math
import statistics as st

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from src.agents.mamba_agent import MambaAgent, MambaBatchModel

L = 7                     # longueur de la grille 1-D
T_WARN_PERIOD = 6         # un danger est télégraphié tous les N ticks


def _obs(pos: int, danger_cell) -> np.ndarray:
    """Obs = one-hot position (L) ++ one-hot danger télégraphié (L)."""
    o = np.zeros(2 * L, dtype=np.float32)
    o[pos] = 1.0
    if danger_cell is not None:
        o[L + danger_cell] = 1.0
    return o


def _sign_p(k: int, n: int) -> float:
    if n <= 0:
        return 1.0
    khi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(khi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def _mean_G_norm(m: MambaBatchModel) -> float:
    """Norme L1 moyenne de G_batch — indicateur de convergence de g."""
    return float(np.mean(np.abs(m.G_batch)))


def run_bench(plan_bias: float, seeds, steps: int = 1000,
              verbose: bool = False) -> dict:
    """Lance le banc d'anticipation v3 avec respawn et danger-avoidance rate.

    Paramètres
    ----------
    plan_bias : float   PLAN_BIAS pendant le run (0 = réactif, >0 = planificateur)
    seeds     : list    graines numpy à tester
    steps     : int     nombre total de ticks par épisode (défaut 1000)
    verbose   : bool    si True, affiche mean|G| final par seed

    Retourne
    --------
    dict avec :
      "avoidance_mean"  : float   moyenne du danger-avoidance rate sur les seeds
      "per_seed"        : list    [{"seed": s, "avoidance": r,
                                    "avoided": k, "faced": n,
                                    "mean_G": g}]
    """
    per_seed = []
    for seed in seeds:
        np.random.seed(seed)
        a = MambaAgent()
        a.genome.organ_genes = np.array([True, False])   # organe planificateur actif

        # Sauvegarder et patcher les flags de classe
        prev_bias = MambaBatchModel.PLAN_BIAS
        prev_plan_a = MambaBatchModel.PLAN_A
        prev_plan_lr = MambaBatchModel.PLAN_LR
        MambaBatchModel.PLAN_BIAS = plan_bias
        MambaBatchModel.PLAN_A = 3    # F2 : g et biais portent sur {0,1,2}
        MambaBatchModel.PLAN_LR = 0.1  # LR plus agressif pour convergence dans le budget
        try:
            m = MambaBatchModel([a])
            pos = L // 2
            pending_danger = None   # case mortelle au prochain tick
            dangers_faced = 0
            dangers_avoided = 0

            for t in range(steps):
                # --- Vérifier la frappe du tick précédent (F1 : gap temporel) ---
                strike_cell = pending_danger
                pending_danger = None

                if strike_cell is not None:
                    # Le danger frappe CE tick (t = tick d'avertissement + 1)
                    dangers_faced += 1
                    if pos == strike_cell:
                        # L'agent s'est fait toucher : pénalité −1, puis RESPAWN (R1)
                        obs_death = _obs(pos, None)[None, :]
                        preds_death, _ = m.forward(obs_death)
                        move_death = int(np.argmax(preds_death[0, :3]))
                        m.compute_policy_gradient(
                            np.array([-1.0], dtype=np.float32),
                            [{"move": move_death, "grab": 0, "rub": 0}])
                        # R1 : respawn au centre — l'épisode CONTINUE
                        pos = L // 2
                    else:
                        # L'agent a évité le danger (R2 : incrémenter avoided)
                        dangers_avoided += 1

                # --- Tick normal : avertissement potentiel ---
                warn = (t % T_WARN_PERIOD == 0)
                telegraph = pos if warn else None   # visible dans l'obs (même case que l'agent)
                obs = _obs(pos, telegraph)[None, :]
                preds, _ = m.forward(obs)
                move = int(np.argmax(preds[0, :3]))   # 0=gauche, 1=rester, 2=droite
                new_pos = min(L - 1, max(0, pos + (move - 1)))

                # F1 : récompense neutre au tick d'avertissement (+0.1)
                reward = 0.1
                m.compute_policy_gradient(
                    np.array([reward], dtype=np.float32),
                    [{"move": move, "grab": 0, "rub": 0}])

                if warn:
                    pending_danger = pos   # frappe programmée au tick t+1 sur la pos ACTUELLE

                pos = new_pos

            # R3 : mesurer mean|G| après le run complet
            mean_g = _mean_G_norm(m)
            avoidance = (dangers_avoided / dangers_faced) if dangers_faced > 0 else 0.0
            if verbose:
                print(f"  seed={seed} avoided={dangers_avoided}/{dangers_faced} "
                      f"avoidance={avoidance:.3f} mean|G|={mean_g:.4f}")
            per_seed.append({
                "seed": int(seed),
                "avoidance": float(avoidance),
                "avoided": int(dangers_avoided),
                "faced": int(dangers_faced),
                "mean_G": float(mean_g),
            })
        finally:
            # Restaurer TOUS les flags modifiés (contrainte hard)
            MambaBatchModel.PLAN_BIAS = prev_bias
            MambaBatchModel.PLAN_A = prev_plan_a
            MambaBatchModel.PLAN_LR = prev_plan_lr

    avoidances = [r["avoidance"] for r in per_seed]
    return {
        "avoidance_mean": float(st.mean(avoidances)) if avoidances else 0.0,
        # Clé de compatibilité v2 (survival_mean) — identique à avoidance_mean
        "survival_mean": float(st.mean(avoidances)) if avoidances else 0.0,
        "per_seed": per_seed,
    }


def compare(seeds, steps: int = 1000, verbose: bool = False) -> dict:
    """Compare le bras planificateur vs le bras réactif sur les mêmes seeds (pairé).

    Retourne
    --------
    dict avec : verdict, median_ratio, sign_p, n_favorable, n, ratios
    Verdict : PLAN_GAGNE si médiane > 1.05 ET majorité favorable ;
              PLAN_PERD si médiane < 0.95 ; sinon NEUTRE.
    """
    ratios = []
    for seed in seeds:
        plan = run_bench(0.5, [seed], steps, verbose=verbose)["avoidance_mean"]
        react = run_bench(0.0, [seed], steps, verbose=verbose)["avoidance_mean"]
        ratios.append(plan / max(react, 1e-6))
    eff = [r for r in ratios if r != 1.0]
    n_fav = sum(1 for r in ratios if r > 1.0)
    p = _sign_p(sum(1 for r in eff if r > 1.0), len(eff))
    med = st.median(ratios) if ratios else 1.0
    verdict = "PLAN_GAGNE" if (med > 1.05 and 2 * n_fav > len(ratios)) else \
              ("PLAN_PERD" if med < 0.95 else "NEUTRE")
    return {"verdict": verdict, "median_ratio": float(med), "sign_p": float(p),
            "n_favorable": int(n_fav), "n": len(ratios), "ratios": ratios}


def main():
    seeds = [int(s) for s in os.environ.get("AB_SEEDS", "0,1,2,3,4,5,6,7").split(",")
             if s.strip()]
    steps = int(os.environ.get("AB_STEPS", "1000"))
    print(f"=== Anticipation Bench v3 : seeds={seeds} steps={steps} ===")
    print("--- Bras planificateur (PLAN_BIAS=0.5) ---")
    plan_out = run_bench(0.5, seeds, steps, verbose=True)
    print(f"avoidance_mean (plan)  = {plan_out['avoidance_mean']:.4f}")
    mean_g_vals = [r["mean_G"] for r in plan_out["per_seed"]]
    print(f"mean|G| moyen (plan)   = {st.mean(mean_g_vals):.6f}  "
          f"(convergence indicator; 0 = g n'a pas appris)")
    print("--- Bras réactif (PLAN_BIAS=0.0) ---")
    react_out = run_bench(0.0, seeds, steps, verbose=True)
    print(f"avoidance_mean (react) = {react_out['avoidance_mean']:.4f}")
    print("--- Verdict pairé ---")
    out = compare(seeds, steps, verbose=False)
    print(f"VERDICT={out['verdict']} median_ratio={out['median_ratio']:.3f} "
          f"n_fav={out['n_favorable']}/{out['n']} sign_p={out['sign_p']:.3f}")
    return out


if __name__ == "__main__":
    main()
