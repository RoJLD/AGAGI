"""P4.8 — `S2-REWARD-ABLATION` : le crédit in-world publié EFFACE le bassin DAgger de WARM-003
([[EDR-S2-CREDIT-RETENTION]] : ERODE, survie 36,0 -> 8,0, 12/12 seeds, dose 1999 TD/agent). La récompense
qu'il optimise est `Δénergie + curiosity_scale·surprise + novelty_scale/√count`
(`src/worlds/world_1_stoneage.py:1713`). Poursuit-il les termes INTRINSÈQUES plutôt que l'énergie ?

Règles SCELLÉES avant toute cellule : docs/preregistrations/S2-REWARD-ABLATION.json (design à cinq bras) puis
S2-REWARD-ABLATION-bis.json (design RÉDUIT à trois bras sur pré-vol MESURÉ, voir ci-dessous).
Même dispositif que P4.4 (`tools/evo_runs/s2_credit_retention.py`, réutilisé tel quel : phase 1 IMMORTELLE
2000 ticks à dose comptée, phase 2 MORTELLE 200 ticks à poids gelés), bassin DAgger cloné ×12, n = 12 seeds
(2026..2037, les mêmes que P4.4), unité de réplication = le seed. Trois bras appariés par seed :

    a_frozen     bassin gelé (le harnais transfère-t-il ? re-mesuré ICI, jamais importé)
    b_full       récompense COMPLÈTE (échelles du monde) = réplique EXACTE du bras (b) de P4.4 (contrôle)
    b_energy     Δénergie seule (curiosity_scale = 0, novelty_scale = 0)

⚠️ Pourquoi trois bras et pas cinq (smoke du 2026-09-14, E2 attrapée AVANT ~10 h de calcul) : sous le backend
torch in-world, `model.surprise` n'est JAMAIS écrit (seul le forward legacy numpy le pose,
`mamba_agent.py:824`) -- le terme de curiosité vaut 0 à chaque tick, et les bras « +curiosité » étaient
BIT-IDENTIQUES à leurs jumeaux sans (dW 1442,82 = 1442,82 sur 200 ticks). La récompense effective est
`Δénergie + nouveauté`. `preflight_curiosity_dead` le MESURE avant chaque run et REFUSE si la surprise se
réveille (le design à cinq bras du sceau original s'appliquerait alors).

Le SEAM est vérifié à réponse connue AVANT le run (`preflight_reward_seam`, publié dans le JSON) : à échelles
nulles la récompense passée au learner est EXACTEMENT Δénergie, et les termes se décomposent additivement.
`b_full` est mesuré sur le premier seed ; s'il est BIT-IDENTIQUE à la ligne P4.4 du même seed (âges, dose,
résurrections -- même code, même seed, même régime), les 11 autres seeds de `b_full` sont IMPORTÉS de
`results/s2_credit_retention.json` et publiés comme tels (`imported_from`) ; sinon ils sont mesurés.
SRA_FULL_ALL=1 force la mesure.

Usage : python tools/evo_runs/s2_reward_ablation.py   (env : SRA_SEEDS=12 SRA_TICKS_LEARN=2000
        SRA_TICKS_TEST=200 SRA_AGENTS=12 SRA_BUDGET_S=<sceau> SRA_OUT=results/s2_reward_ablation.json
        SRA_SMOKE=1 -> 1 seed, 200/100 ticks, fichier _smoke ; SRA_FULL_ALL=1 -> b_full mesuré partout)
"""
import json
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.cognitive_demand_inworld import _pinned_substrate  # noqa: E402
from tools.evo_runs.s2_credit_retention import (  # noqa: E402
    DELTA_MIN, DOSE_MIN, HARNESS_MIN, N_MIN, REGIME as REGIME_P44, SEEDS_DEFAULT, SIGN_MIN,
    _finite, _git_provenance, _save, _world, load_bassin, phase1_learn_immortal, phase2_survive_mortal)

PREREG = "S2-REWARD-ABLATION"
PREREG_BIS = "S2-REWARD-ABLATION-bis"       # design réduit à trois bras sur pré-vol MESURÉ (curiosité morte)
P44_RESULTS = os.path.join("results", "s2_credit_retention.json")
P44_FULL_ARM = "b_warm_credit"
ARMS = ("a_frozen", "b_full", "b_energy")
LEARNING_ARMS = ARMS[1:]
# (curiosity_scale, novelty_scale) : None = échelle du MONDE (publiée par `reward_defaults`), 0.0 = COUPÉ.
ARM_REWARD = {"b_full": (None, None), "b_energy": (0.0, 0.0)}
ARM_KEY = {"b_full": "full", "b_energy": "energy"}
_DEFAULTS_CACHE = {}


def reward_defaults():
    """Les échelles par DÉFAUT du monde, lues sur une instance construite (une prémisse est une MESURE,
    E8 occ. 4) -- jamais recopiées de `world_1_stoneage.py:164/168`. Mis en cache (un monde par process)."""
    if not _DEFAULTS_CACHE:
        e = _world(0, 0)
        _DEFAULTS_CACHE.update(curiosity_scale=float(e.curiosity_scale), novelty_scale=float(e.novelty_scale))
        if hasattr(e, "memory_retriever"):
            e.memory_retriever.stop()
    return dict(_DEFAULTS_CACHE)


def effective_reward(arm):
    """Échelles EFFECTIVES d'un bras apprenant (None résolu sur le monde)."""
    cs, ns = ARM_REWARD[arm]
    d = reward_defaults()
    return {"curiosity_scale": d["curiosity_scale"] if cs is None else float(cs),
            "novelty_scale": d["novelty_scale"] if ns is None else float(ns)}


def _bassin_cohort(seed, num_agents):
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.harness import seed_at
    seed_at(seed, 0)
    bassin = load_bassin()
    agents = []
    for _ in range(int(num_agents)):
        a = MambaAgent()
        a.from_genome(bassin)
        agents.append(a)
    return agents


def first_tick_reward(seed, curiosity_scale, novelty_scale, num_agents=1):
    """La récompense PASSÉE AU LEARNER au premier tick d'un monde (`TorchPopulationModel.learn`
    intercepté, restauré en finally), avec ce qu'il faut pour la recomposer : Δénergie (énergie au
    moment de `learn` − énergie avant le tick ; `old_energies` est capturé au début du tick,
    `world_1_stoneage.py:1221`, et rien ne touche l'énergie avant hors l'aube, désactivée), la surprise
    du modèle au moment de `learn`, et le COMPTE de nouveauté utilisé pour chaque agent (rejoué dans
    l'ordre des agents : deux agents à inventaire identique ne reçoivent pas le même compte). Cohorte =
    clones du bassin DAgger."""
    from src.agents.backend_torch import TorchPopulationModel as _TPM
    from src.environments.stone_economy import state_signature
    if int(num_agents) <= 0:
        raise ValueError("first_tick_reward : num_agents <= 0 -- aucune récompense à capturer")
    cap = {}
    orig_learn = _TPM.learn

    def learn(self, rewards_batch, actions_batch=None):
        if "rewards" not in cap:
            e = cap["world"]
            cap["rewards"] = np.asarray(rewards_batch, dtype=np.float32).copy()
            cap["agent_ids"] = [id(a) for a in e.agents]
            cap["energy_at_learn"] = np.array([a["energy"] for a in e.agents], dtype=np.float32)
            cap["surprise"] = np.array([float(a["model"].surprise) for a in e.agents], dtype=np.float32)
            cap["signatures"] = [state_signature(a["inventory"]) for a in e.agents]
        return orig_learn(self, rewards_batch, actions_batch)

    _TPM.learn = learn
    try:
        with _pinned_substrate():
            agents = _bassin_cohort(seed, num_agents)
            e = _world(seed, 0, curiosity_scale=curiosity_scale, novelty_scale=novelty_scale)
            cap["world"] = e
            for a in agents:
                e.add_agent(a, energy=80.0)
            ids0 = [id(a) for a in e.agents]
            e0 = np.array([a["energy"] for a in e.agents], dtype=np.float32)
            counts0 = dict(e.novelty_counts)
            scales = {"curiosity_scale": float(e.curiosity_scale), "novelty_scale": float(e.novelty_scale)}
            e.step()
            if hasattr(e, "memory_retriever"):
                e.memory_retriever.stop()
    finally:
        _TPM.learn = orig_learn
    if "rewards" not in cap:
        raise RuntimeError("first_tick_reward : `learn` n'a pas été appelé au premier tick -- le crédit n'est pas branché")
    if cap["agent_ids"] != ids0:
        raise RuntimeError("first_tick_reward : la cohorte a changé pendant le tick 1 (mort intra-tick) -- Δénergie non appariable")
    counts = dict(counts0)
    novelty_count = []
    for sig in cap["signatures"]:
        counts[sig] = counts.get(sig, 0) + 1
        novelty_count.append(int(counts[sig]))
    return {"rewards": cap["rewards"], "delta_energy": cap["energy_at_learn"] - e0, "surprise": cap["surprise"],
            "novelty_count": novelty_count, **scales}


def _ticks_reward_trace(seed, curiosity_scale, novelty_scale, num_agents, ticks, refill_below=30.0,
                        refill_to=80.0, hp_refill_below=50.0):
    """Trace des récompenses passées au learner sur `ticks` ticks et surprise maximale vue au moment de
    chaque `learn`. Cohorte IMMORTELLE (même recette que phase1_learn_immortal : le pré-vol mesure sous le
    RÉGIME du run -- une cohorte mortelle de 4 agents meurt avant le tick 26 et tronque la trace).
    Sert au pré-vol « curiosité morte »."""
    from src.agents.backend_torch import TorchPopulationModel as _TPM
    cap = {"rewards": [], "max_abs_surprise": 0.0, "learn_calls": 0}
    orig_learn = _TPM.learn

    def learn(self, rewards_batch, actions_batch=None):
        e = cap["world"]
        cap["learn_calls"] += 1
        cap["rewards"].extend(float(x) for x in np.asarray(rewards_batch, dtype=np.float32).ravel())
        s = max((abs(float(a["model"].surprise)) for a in e.agents), default=0.0)
        cap["max_abs_surprise"] = max(cap["max_abs_surprise"], s)
        return orig_learn(self, rewards_batch, actions_batch)

    _TPM.learn = learn
    try:
        with _pinned_substrate():
            agents = _bassin_cohort(seed, num_agents)
            e = _world(seed, 0, curiosity_scale=curiosity_scale, novelty_scale=novelty_scale)
            cap["world"] = e
            for a in agents:
                e.add_agent(a, energy=80.0)
            t = 0
            while e.agents and t < int(ticks):
                e.step()
                for a in e.agents:
                    if a["energy"] < refill_below:
                        a["energy"] = refill_to
                    if a["hp"] < hp_refill_below:
                        a["hp"] = 100.0 + float(getattr(a["model"], "phenotype_hp_bonus", 0.0))
                dead = list(getattr(e, "dead_agents", []))
                for a in dead:
                    a["energy"] = refill_to
                    a["hp"] = 100.0 + float(getattr(a["model"], "phenotype_hp_bonus", 0.0))
                    e.agents.append(a)
                if dead:
                    e.dead_agents.clear()
                t += 1
            if hasattr(e, "memory_retriever"):
                e.memory_retriever.stop()
    finally:
        _TPM.learn = orig_learn
    return {"rewards": cap["rewards"], "max_abs_surprise": float(cap["max_abs_surprise"]),
            "learn_calls": int(cap["learn_calls"]), "ticks_run": t, "curiosity_scale": float(e.curiosity_scale)}


def preflight_curiosity_dead(seed, num_agents=4, ticks=50):
    """Pré-vol MESURÉ (E2) : le terme de curiosité est-il STRUCTURELLEMENT NUL sous le backend torch ?
    Deux mondes au même seed, curiosity_scale 0 vs défaut : surprise max vue par le learner == 0 ET traces
    de récompense bit-identiques. Lève sinon (le design à trois bras serait faux : reprendre le sceau
    original à cinq bras). Renvoie la mesure publiée dans le JSON."""
    from tools.experiment_preflight import PreflightError
    d = reward_defaults()
    off = _ticks_reward_trace(seed, 0.0, None, num_agents, ticks)
    on = _ticks_reward_trace(seed, None, None, num_agents, ticks)
    max_s = max(off["max_abs_surprise"], on["max_abs_surprise"])
    identical = off["rewards"] == on["rewards"] and off["learn_calls"] == on["learn_calls"]
    if max_s != 0.0 or not identical:
        raise PreflightError(
            f"preflight_curiosity_dead : la curiosité est VIVANTE (surprise max {max_s:.3g}, traces "
            f"{'identiques' if identical else 'DIFFERENTES'} a curiosity_scale 0 vs {d['curiosity_scale']}) -- "
            "le design a trois bras suppose un terme nul ; appliquer le sceau original a cinq bras.")
    return {"seed": int(seed), "num_agents": int(num_agents), "ticks": int(ticks), "learn_calls": on["learn_calls"],
            "max_abs_surprise": max_s, "rewards_identical_curiosity_0_vs_default": bool(identical),
            "curiosity_scale_default": d["curiosity_scale"], "n_rewards_compared": len(on["rewards"])}


def preflight_reward_seam(seed, num_agents=4):
    """Pré-vol (question 2 : « le chemin qu'on croit couper est-il le seul ? ») à RÉPONSE CONNUE : quatre
    mondes au même seed, identiques jusqu'à la récompense, doivent vérifier
        r_energy = Δénergie ; r_cur − r_energy = c·surprise ; r_nov − r_energy = n/√count ;
        r_full = r_energy + c·surprise + n/√count
    au bruit flottant près, ET r_full ≠ r_energy (l'ablation change quelque chose, E2). Lève sinon.
    Renvoie la décomposition publiée dans le JSON du run."""
    from src.environments.stone_economy import novelty_bonus
    from tools.experiment_preflight import PreflightError, assert_ablation_changes_something
    d = reward_defaults()
    full = first_tick_reward(seed, None, None, num_agents=num_agents)
    energy = first_tick_reward(seed, 0.0, 0.0, num_agents=num_agents)
    cur = first_tick_reward(seed, None, 0.0, num_agents=num_agents)
    nov = first_tick_reward(seed, 0.0, None, num_agents=num_agents)
    for other in (energy, cur, nov):
        if (not np.allclose(other["delta_energy"], full["delta_energy"], atol=1e-6)
                or not np.allclose(other["surprise"], full["surprise"], atol=1e-6)
                or other["novelty_count"] != full["novelty_count"]):
            raise PreflightError("preflight_reward_seam : les quatre mondes DIVERGENT avant la récompense "
                                 "(Δénergie, surprise ou comptes différents) -- le seed n'apparie pas les bras")
    cur_term = np.float32(d["curiosity_scale"]) * full["surprise"]
    nov_term = np.array([novelty_bonus(c, d["novelty_scale"]) for c in full["novelty_count"]], dtype=np.float32)
    residuals = {
        "energy_vs_delta": energy["rewards"] - energy["delta_energy"],
        "curiosity_term": cur["rewards"] - energy["rewards"] - cur_term,
        "novelty_term": nov["rewards"] - energy["rewards"] - nov_term,
        "additivity_full": full["rewards"] - energy["rewards"] - cur_term - nov_term,
    }
    max_abs = max(float(np.max(np.abs(r))) for r in residuals.values())
    if not np.isfinite(max_abs) or max_abs > 1e-3:
        worst = max(residuals, key=lambda k: float(np.max(np.abs(residuals[k]))))
        raise PreflightError(f"preflight_reward_seam : la récompense ne se décompose PAS comme déclaré "
                             f"(résidu max {max_abs:.3g} sur {worst}) -- le seam ne coupe pas ce qu'on croit")
    assert_ablation_changes_something(full["rewards"].tolist(), energy["rewards"].tolist(),
                                      label="ablation des termes intrinsèques (tick 1)")
    intrinsic = float(np.sum(np.abs(cur_term)) + np.sum(np.abs(nov_term)))
    extrinsic = float(np.sum(np.abs(energy["delta_energy"])))
    return {"seed": int(seed), "num_agents": int(num_agents), "reward_defaults": d,
            "max_abs_residual": max_abs, "residuals_max_abs": {k: float(np.max(np.abs(v))) for k, v in residuals.items()},
            "intrinsic_share_full": intrinsic / (intrinsic + extrinsic) if (intrinsic + extrinsic) > 0 else None,
            "r_full": full["rewards"].tolist(), "r_energy": energy["rewards"].tolist(),
            "delta_energy": full["delta_energy"].tolist(), "surprise": full["surprise"].tolist(),
            "novelty_count": full["novelty_count"]}


def run_arm(seed, arm, num_agents=12, ticks_learn=2000, ticks_test=200):
    """Un bras pour un seed : bassin cloné ×num_agents, phase 1 (sauf bras gelé) avec les échelles du
    bras, phase 2 mortelle à poids gelés. Publie les échelles EFFECTIVES et déclarées."""
    if int(num_agents) <= 0 or int(ticks_learn) <= 0 or int(ticks_test) <= 0 or arm not in ARMS:
        raise ValueError(
            f"run_arm : argument degenere (num_agents={num_agents}, ticks_learn={ticks_learn}, "
            f"ticks_test={ticks_test}, arm={arm!r}) -- aucune mesure possible ; ne pas confondre avec une "
            "mesure nulle OBSERVEE.")
    reward = effective_reward(arm) if arm in ARM_REWARD else None      # AVANT seed_at : construit un monde
    agents = _bassin_cohort(seed, num_agents)
    out = {"seed": int(seed), "arm": arm, "num_agents": int(num_agents), "ticks_learn": int(ticks_learn),
           "ticks_test": int(ticks_test), "lr": None, "reward": reward,
           "reward_declared": list(ARM_REWARD[arm]) if arm in ARM_REWARD else None}
    t0 = time.time()
    if arm in ARM_REWARD:
        cs, ns = ARM_REWARD[arm]
        out["learning"] = phase1_learn_immortal(agents, seed, ticks_learn, curiosity_scale=cs, novelty_scale=ns)
    else:
        out["learning"] = None
    out["survival"] = phase2_survive_mortal(agents, seed, ticks_test)
    out["elapsed_s"] = time.time() - t0
    return out


def _load_p44():
    with open(os.path.join(_ROOT, P44_RESULTS), encoding="utf-8") as fh:
        return json.load(fh)


def replication_check(row, seed):
    """`row` (bras `b_full` mesuré ICI) est-il BIT-IDENTIQUE à la ligne P4.4 du même seed (bras
    `b_warm_credit` : âges, dose TD, résurrections, mêmes paramètres) ? KeyError si P4.4 n'a pas ce seed."""
    p44 = _load_p44()
    ref = p44["arms"][P44_FULL_ARM][str(int(seed))]
    p44_ages, ages = list(ref["survival"]["ages"]), list(row["survival"]["ages"])
    same_params = all(ref[k] == row[k] for k in ("num_agents", "ticks_learn", "ticks_test"))
    lrn_ref, lrn = ref["learning"] or {}, row["learning"] or {}
    same_dose = (lrn_ref.get("td_updates") == lrn.get("td_updates")
                 and lrn_ref.get("resurrections") == lrn.get("resurrections"))
    identical = bool(same_params and same_dose and p44_ages == ages)
    reason = ("bit-identique" if identical else
              "parametres differents" if not same_params else
              "dose ou resurrections differentes" if not same_dose else "ages differents")
    return {"seed": int(seed), "identical": identical, "reason": reason, "p44_ages": p44_ages, "measured_ages": ages,
            "p44_S": ref["survival"]["survival_median"], "measured_S": row["survival"]["survival_median"],
            "p44_dW_abs_sum": lrn_ref.get("dW_abs_sum"), "measured_dW_abs_sum": lrn.get("dW_abs_sum"),
            "p44_git_sha": (p44.get("provenance") or {}).get("git_sha")}


def p44_full_rows(replication_identical):
    """Les lignes `b_warm_credit` de P4.4, re-typées `b_full` et marquées `imported_from` -- IMPORTABLES
    SEULEMENT si la réplication bit-identique du premier seed est constatée. Refuse sinon."""
    if not replication_identical:
        raise ValueError("p44_full_rows : import REFUSE -- la replication bit-identique de b_full n'est pas "
                         "constatee ; mesurer le bras sur chaque seed")
    p44 = _load_p44()
    sha = (p44.get("provenance") or {}).get("git_sha")
    rows = {}
    for s, r in p44["arms"][P44_FULL_ARM].items():
        rows[s] = {"seed": int(s), "arm": "b_full", "num_agents": r["num_agents"], "ticks_learn": r["ticks_learn"],
                   "ticks_test": r["ticks_test"], "lr": r.get("lr"),
                   "reward": {"curiosity_scale": None, "novelty_scale": None},     # P4.4 ne les publiait pas
                   "reward_declared": [None, None], "learning": r["learning"], "survival": r["survival"],
                   "elapsed_s": r["elapsed_s"], "imported_from": P44_RESULTS, "imported_git_sha": sha}
    return rows


def _classify(d, sign_min, delta_min):
    pos, neg = sum(1 for x in d if x > 0), sum(1 for x in d if x < 0)
    med = float(np.median(d))
    if pos >= sign_min and med >= delta_min:
        return "ETENDU", pos, neg, med
    if neg >= sign_min and med <= -delta_min:
        return "ERODE", pos, neg, med
    return "NEUTRE", pos, neg, med


def reward_ablation_verdict(rows, harness_min=HARNESS_MIN, dose_min=DOSE_MIN, sign_min=SIGN_MIN,
                            delta_min=DELTA_MIN, n_min=N_MIN):
    """Lecture de la règle scellée S2-REWARD-ABLATION(-bis), branches dans l'ORDRE IMPOSÉ :
    1 INCOMPLET -> 2 INDETERMINE_HARNAIS -> 3 INDETERMINE_DOSE -> 4 INDETERMINE_REPLICATION (la récompense
    complète doit ÉRODER ici comme dans P4.4) -> 5 chaque bras apprenant classé ERODE / NEUTRE / ETENDU
    contre le bassin gelé (signe 10/12 ET ±5 ticks) -> 6a `b_energy` non ERODE = RECOMPENSE_MAL_ALIGNEE
    (terme NOUVEAUTE : seul terme intrinsèque vivant sous torch) ; 6b `b_energy` ERODE = CREDIT_ERODE_SEUL
    (ATTENUE si Δénergie seule érode MOINS que la récompense complète, 10/12 et +5 ; sinon PLEIN).
    `rows` : une ligne par seed avec S_a, S_full, S_energy, dose_full, dose_energy. Toute entrée absente
    ou non finie LÈVE."""
    keys = ("S_a", "S_full", "S_energy", "dose_full", "dose_energy")
    if not rows:
        raise ValueError("reward_ablation_verdict : aucune ligne -- aucun verdict n'est fabriqué")
    for r in rows:
        for k in keys:
            if k not in r or not _finite(r[k]):
                raise ValueError(f"reward_ablation_verdict : {k} absent ou non fini pour le seed {r.get('seed')}")
    n = len(rows)
    S = {k: [float(r[f"S_{k}"]) for r in rows] for k in ("a", "full", "energy")}
    dose = {k: [int(r[f"dose_{k}"]) for r in rows] for k in ("full", "energy")}
    out = {"n": n, "thresholds": {"harness_min": float(harness_min), "dose_min": int(dose_min),
                                  "sign_min": int(sign_min), "delta_min": float(delta_min), "n_min": int(n_min)},
           "terme": None, "attenuation": None}
    for k, v in S.items():
        out[f"S_{k}_median"] = float(np.median(v))
    for k, v in dose.items():
        out[f"dose_{k}_median"] = float(np.median(v))
    for k in ("full", "energy"):
        d = [b - a for a, b in zip(S["a"], S[k])]
        cls, pos, neg, med = _classify(d, sign_min, delta_min)
        out[f"d_{k}_median"] = med
        out[f"d_{k}_positive"] = f"{pos}/{n}"
        out[f"d_{k}_negative"] = f"{neg}/{n}"
        out[f"arm_{k}"] = cls
    d_ef = [e - f for e, f in zip(S["energy"], S["full"])]
    att_cls, att_pos, _, att_med = _classify(d_ef, sign_min, delta_min)
    out["d_energy_vs_full_median"] = att_med
    out["d_energy_vs_full_positive"] = f"{att_pos}/{n}"
    if n < n_min:
        out.update(verdict="INCOMPLET", why=f"{n} seeds < {n_min} : reprise, aucune lecture")
        return out
    if out["S_a_median"] < harness_min:
        out.update(verdict="INDETERMINE_HARNAIS",
                   why=f"S_a mediane {out['S_a_median']:.1f} < {harness_min} : le bassin ne transfere pas ici")
        return out
    low = [k for k in ("full", "energy") if out[f"dose_{k}_median"] < dose_min]
    if low:
        out.update(verdict="INDETERMINE_DOSE",
                   why="dose sous %d (le credit ne s'est pas applique, E2) : %s" % (
                       dose_min, ", ".join(f"dose_{k} mediane {out[f'dose_{k}_median']:.0f}" for k in low)))
        return out
    if out["arm_full"] != "ERODE":
        out.update(verdict="INDETERMINE_REPLICATION",
                   why=(f"d_full mediane {out['d_full_median']:+.1f}, signe -{out['d_full_negative']} : la recompense "
                        f"complete n'erode pas ici (P4.4 : -28,25, 12/12) -- rien a ablater"))
        return out
    if out["arm_energy"] != "ERODE":
        out["terme"] = "NOUVEAUTE"          # seul terme intrinsèque VIVANT sous torch (preflight_curiosity_dead)
        out.update(verdict="RECOMPENSE_MAL_ALIGNEE",
                   why=(f"Δenergie seule : {out['arm_energy']} (d_energy mediane {out['d_energy_median']:+.1f}, "
                        f"signe +{out['d_energy_positive']}/-{out['d_energy_negative']}) ; complete ERODE "
                        f"({out['d_full_median']:+.1f}, -{out['d_full_negative']}) -> l'erosion EXIGE la nouveaute"))
        return out
    out["attenuation"] = "ATTENUE" if att_cls == "ETENDU" else "PLEIN"
    out.update(verdict="CREDIT_ERODE_SEUL",
               why=(f"Δenergie seule ERODE (d_energy mediane {out['d_energy_median']:+.1f}, signe -{out['d_energy_negative']}) ; "
                    f"vs complete {att_med:+.1f} (+{att_pos}/{n}) -> {out['attenuation']}"))
    return out


def main():
    from src.paths import results_file
    from tools.cost_guard import project_cost
    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.jobs.run import hold
    from tools.preregister import verify

    smoke = os.environ.get("SRA_SMOKE") == "1"
    full_all = os.environ.get("SRA_FULL_ALL") == "1"
    n = 1 if smoke else int(os.environ.get("SRA_SEEDS", "12"))
    ticks_learn = 200 if smoke else int(os.environ.get("SRA_TICKS_LEARN", "2000"))
    ticks_test = 100 if smoke else int(os.environ.get("SRA_TICKS_TEST", "200"))
    agents = int(os.environ.get("SRA_AGENTS", "12"))
    out = os.environ.get("SRA_OUT") or str(results_file("s2_reward_ablation" + ("_smoke" if smoke else "") + ".json"))
    out = out if os.path.isabs(out) else os.path.join(_ROOT, out)
    seeds = list(SEEDS_DEFAULT[:n])

    rule = verify(PREREG)                      # design original (cinq bras) : reste lisible, jamais retouché
    rule_bis = verify(PREREG_BIS)              # design RÉDUIT à trois bras sur pré-vol mesuré ; porte le budget
    budget_s = float(os.environ.get("SRA_BUDGET_S") or rule_bis["budget_s"])
    print(f"[preregistration] {PREREG} + {PREREG_BIS} : sceaux VERIFIES ({len(rule_bis['discrimination'])} branches, "
          f"budget {budget_s / 3600:.2f} h)", flush=True)
    design = declare_design(
        question=rule_bis["question"],
        replication_unit="seed (une cohorte de %d clones du bassin par bras, un monde par seed ; 3 bras appariés)" % agents,
        n_independent=n,
        links={"seam_recompense": "measured", "curiosite_morte": "measured", "dose_de_credit": "measured",
               "resurrections": "measured", "survie_mortelle_poids_geles": "measured",
               "bassin_transfere_S_a": "measured", "replication_b_full": "measured"},
        cost_estimate=rule_bis["plafond"], control_family=assert_control_family(cells=n, alpha_family=0.05))
    defaults = reward_defaults()
    regime = dict(REGIME_P44, reward_defaults=defaults,
                  arms_reward_declared={a: list(v) for a, v in ARM_REWARD.items()},
                  arms_reward_effective={a: effective_reward(a) for a in ARM_REWARD})
    data = (json.load(open(out, encoding="utf-8")) if os.path.exists(out) else
            {"preregistration": [PREREG, PREREG_BIS], "design": design, "provenance": _git_provenance(),
             "regime": regime,
             "params": {"seeds": seeds, "ticks_learn": ticks_learn, "ticks_test": ticks_test, "agents": agents,
                        "budget_s": budget_s, "smoke": smoke, "full_all": full_all},
             "arms": {arm: {} for arm in ARMS}, "cost": {}, "preflight": None, "replication": None})
    t_start = time.time()
    with hold("kuzu", owner="s2-reward-ablation" + ("-smoke" if smoke else ""), ttl_s=max(3600.0, budget_s * 2)):
        if data.get("preflight") is None:
            seam = preflight_reward_seam(seeds[0], num_agents=4)               # lève si le seam ment
            dead = preflight_curiosity_dead(seeds[0], num_agents=4, ticks=50)  # lève si la curiosité vit
            data["preflight"] = {"seam": seam, "curiosity_dead": dead}
            _save(out, data)
            print(f"[preflight] seam OK : residu max {seam['max_abs_residual']:.2e}, part intrinseque au tick 1 "
                  f"{seam['intrinsic_share_full']:.2f} ; curiosite MORTE sur {dead['ticks']} ticks "
                  f"(surprise max {dead['max_abs_surprise']:.3g}, {dead['n_rewards_compared']} recompenses identiques)", flush=True)
        if "unit_s" not in data["cost"]:
            # Unité = UN SEED COMPLET (trois bras), chaque bras MESURÉ (leçon P4.4 : 675 s/seed contre 136
            # extrapolés d'un smoke -- E12 sur le coût). Sauvé AVANT la garde.
            unit_s = 0.0
            for arm in ARMS:
                if str(seeds[0]) not in data["arms"][arm]:
                    data["arms"][arm][str(seeds[0])] = run_arm(seeds[0], arm, num_agents=agents,
                                                               ticks_learn=ticks_learn, ticks_test=ticks_test)
                    _save(out, data)
                r = data["arms"][arm][str(seeds[0])]
                data["cost"][f"unit_{arm}_s"] = r["elapsed_s"]
                unit_s += r["elapsed_s"]
                if arm == "b_full":
                    try:
                        data["replication"] = replication_check(r, seeds[0])
                    except KeyError:
                        data["replication"] = {"seed": seeds[0], "identical": False, "reason": "seed absent de P4.4"}
                    _save(out, data)
                    print(f"[replication] b_full seed {seeds[0]} vs P4.4 : {data['replication']['reason']}", flush=True)
            data["cost"]["unit_s"] = unit_s
            _save(out, data)
            import_full = bool(data["replication"]["identical"]) and not full_all and not smoke
            data["cost"]["b_full_imported"] = import_full
            if import_full:
                for s, row in p44_full_rows(True).items():
                    if s in [str(x) for x in seeds] and s not in data["arms"]["b_full"]:
                        row["reward_established_by_replication"] = defaults
                        data["arms"]["b_full"][s] = row
                unit_proj = unit_s - data["cost"]["unit_b_full_s"]
            else:
                unit_proj = unit_s
            _save(out, data)                   # AVANT la garde : un run REFUSÉ garde sa mesure
            data["cost"]["projected_s"] = project_cost(unit_proj, n_units=n, budget_s=budget_s,
                                                       label="s2-reward-ablation (unité = un seed, %d bras)" % (
                                                           len(ARMS) - (1 if import_full else 0)))
            _save(out, data)
            print(f"[cost] unité (seed complet, {len(ARMS)} bras) {unit_s:.1f}s ; projeté {data['cost']['projected_s'] / 60:.0f} min "
                  f"(budget {budget_s / 60:.0f} min ; b_full {'IMPORTE' if import_full else 'MESURE'})", flush=True)
        for s in seeds:
            for arm in ARMS:
                if str(s) in data["arms"][arm]:
                    continue
                r = run_arm(s, arm, num_agents=agents, ticks_learn=ticks_learn, ticks_test=ticks_test)
                data["arms"][arm][str(s)] = r
                _save(out, data)
                lrn = r["learning"] or {}
                print(f"[{arm:10s} seed {s}] S {r['survival']['survival_median']:6.1f} (censures {r['survival']['censored']}) "
                      f"| TD {lrn.get('td_updates', 0):4d} resur {lrn.get('resurrections', 0):3d} | {r['elapsed_s']:.0f}s", flush=True)
    rows = []
    for s in seeds:
        got = {arm: data["arms"][arm].get(str(s)) for arm in ARMS}
        if not all(got.values()):
            continue
        row = {"seed": s, "S_a": got["a_frozen"]["survival"]["survival_median"]}
        for arm in LEARNING_ARMS:
            k = ARM_KEY[arm]
            row[f"S_{k}"] = got[arm]["survival"]["survival_median"]
            row[f"dose_{k}"] = got[arm]["learning"]["td_updates"]
            row[f"resurrections_{k}"] = got[arm]["learning"]["resurrections"]
            row[f"imported_{k}"] = bool(got[arm].get("imported_from"))
        rows.append(row)
    data["rows"] = rows
    data["verdict"] = reward_ablation_verdict(rows) if rows else {"verdict": "INCOMPLET", "n": 0}
    data["cost"]["elapsed_total_s"] = time.time() - t_start
    _save(out, data)
    v = data["verdict"]
    print(f"\n=== P4.8 S2-REWARD-ABLATION — n={v.get('n')} : {v.get('verdict')} | terme {v.get('terme')} | "
          f"attenuation {v.get('attenuation')}\n{v.get('why', '')}\n-> {out}")
    return data


if __name__ == "__main__":
    main()
