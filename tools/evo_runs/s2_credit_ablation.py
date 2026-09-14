"""P4.9 — `S2-CREDIT-ABLATION` : le crédit in-world publié EFFACE le bassin DAgger de WARM-003, à Δénergie
seule autant qu'à récompense complète ([[EDR-S2-REWARD-ABLATION]] : CREDIT_ERODE_SEUL, PLEIN ; survie
36,0 -> 8,0, 12/12 seeds). Le mur est le MÉCANISME de crédit (Actor-Critic TD(0) par tick + REINFORCE
épisodique k=8, lr 0,04). D'où vient l'érosion : du SIGNE du signal (avantage constant négatif sous critic
tanh saturé), du PAS (toute mise à jour à lr 0,04 détruit, signal ou pas), ou du TD par tick ?

Règle SCELLÉE avant toute cellule : docs/preregistrations/S2-CREDIT-ABLATION.json.
Même dispositif que P4.4 / P4.8 (`s2_credit_retention.py` : phase 1 IMMORTELLE 2000 ticks à dose comptée,
phase 2 MORTELLE 200 ticks à poids gelés ; bassin DAgger cloné ×12 ; n = 12 seeds 2026..2037 ; unité = seed).
Bras (b) déclinés sur le CRÉDIT par les seams de `tools/learning_events.count_learning_events` (calibrés
par EDR-CALIB-LEARNER) :

    a_frozen   bassin gelé (re-mesuré, jamais importé)
    b_full     crédit publié, récompense complète  = réplique EXACTE du bras (b) de P4.4 (importé sur
               réplication bit-identique du seed 2026, comme P4.8)
    b_zero     reward_scale = 0    : AUCUN signal — le critic dérive seul (erreur TD = γV' − V)
    b_neg      reward_scale = −1   : signal INVERSÉ — un avantage constant négatif devient positif
    b_lr       lr = 0,004          : même signal, pas 10× plus petit (E19)
    b_tdoff    td_enabled = False  : TD par tick coupé, REINFORCE épisodique seul

Les seams sont vérifiés à RÉPONSE CONNUE avant le run (`preflight_credit_seams`, publié dans le JSON) : ce qui
ATTEINT le learner d'ORIGINE sous chaque variante (récompenses toutes nulles ; négation bit-exacte au premier
tick ; TD jamais appelé mais épisodes vivants ; pas publié et mouvement moindre).

Usage : python tools/evo_runs/s2_credit_ablation.py   (env : SCA_SEEDS=12 SCA_TICKS_LEARN=2000
        SCA_TICKS_TEST=200 SCA_AGENTS=12 SCA_BUDGET_S=<sceau> SCA_OUT=results/s2_credit_ablation.json
        SCA_SMOKE=1 -> 1 seed, 200/100 ticks, fichier _smoke ; SCA_FULL_ALL=1 -> b_full mesuré partout)
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
    _finite, _git_provenance, _save, _world, immortal_refill, phase1_learn_immortal, phase2_survive_mortal)
from tools.evo_runs.s2_reward_ablation import P44_RESULTS, _bassin_cohort, p44_full_rows, replication_check  # noqa: E402
from tools.learning_events import count_learning_events  # noqa: E402

PREREG = "S2-CREDIT-ABLATION"
LR_LOW = 0.004
DOSE_EPISODIC_MIN = 100        # 250 épisodes attendus en 2000 ticks (k = 8) ; la moitié = bras qui a tourné
ARMS = ("a_frozen", "b_full", "b_zero", "b_neg", "b_lr", "b_tdoff")
LEARNING_ARMS = ARMS[1:]
ARM_CREDIT = {
    "b_full": {"reward_scale": 1.0, "td_enabled": True, "lr": None},      # chemin PUBLIÉ, bit-identique
    "b_zero": {"reward_scale": 0.0, "td_enabled": True, "lr": None},
    "b_neg": {"reward_scale": -1.0, "td_enabled": True, "lr": None},
    "b_lr": {"reward_scale": 1.0, "td_enabled": True, "lr": LR_LOW},
    "b_tdoff": {"reward_scale": 1.0, "td_enabled": False, "lr": None},
}
ARM_KEY = {"b_full": "full", "b_zero": "zero", "b_neg": "neg", "b_lr": "lr", "b_tdoff": "tdoff"}


def _learning_trace(seed, num_agents=4, ticks=32, reward_scale=1.0, td_enabled=True, lr=None):
    """Ce qui ATTEINT le learner d'ORIGINE sous une variante de `count_learning_events` : les originaux
    `learn` / `learn_episode` sont interceptés AVANT que count_learning_events ne les enveloppe (donc on
    voit les récompenses APRÈS mise à l'échelle, et rien du tout si le TD est coupé). Cohorte immortelle
    (même recette que la phase 1), clones du bassin. Renvoie les traces, le summary de dose et le pas
    EFFECTIF lu sur l'optimiseur SGD de la population (`self.opt`)."""
    from src.agents.backend_torch import TorchPopulationModel as _TPM
    if int(num_agents) <= 0 or int(ticks) <= 0:
        raise ValueError("_learning_trace : num_agents/ticks <= 0 -- rien à tracer")
    cap = {"td": [], "first_td": None, "ep": [], "lr": None}
    orig_learn, orig_episode = _TPM.learn, _TPM.learn_episode

    def _lr(self):
        if cap["lr"] is None:
            try:
                cap["lr"] = float(self.opt.param_groups[0]["lr"])
            except (AttributeError, IndexError, KeyError, TypeError):
                cap["lr"] = None

    def learn(self, rewards_batch, actions_batch=None):
        _lr(self)
        r = [float(x) for x in np.asarray(rewards_batch, dtype=np.float32).ravel()]
        if cap["first_td"] is None:
            cap["first_td"] = list(r)
        cap["td"].extend(r)
        return orig_learn(self, rewards_batch, actions_batch)

    def learn_episode(self, obs_seq, actions_seq, rewards, gamma=1.0, gate_last_only=True):
        _lr(self)
        cap["ep"].extend(float(x) for x in np.asarray(rewards, dtype=np.float32).ravel())
        return orig_episode(self, obs_seq, actions_seq, rewards, gamma=gamma, gate_last_only=gate_last_only)

    _TPM.learn, _TPM.learn_episode = learn, learn_episode
    try:
        with _pinned_substrate(), count_learning_events(reward_scale=reward_scale, td_enabled=td_enabled, lr=lr) as ev:
            agents = _bassin_cohort(seed, num_agents)
            e = _world(seed, 0)
            for a in agents:
                e.add_agent(a, energy=80.0)
            t = 0
            while e.agents and t < int(ticks):
                e.step()
                immortal_refill(e)
                t += 1
            if hasattr(e, "memory_retriever"):
                e.memory_retriever.stop()
        summary = ev.summary()
    finally:
        _TPM.learn, _TPM.learn_episode = orig_learn, orig_episode
    return {"td_rewards": cap["td"], "first_td_rewards": cap["first_td"] or [], "episode_rewards": cap["ep"],
            "summary": summary, "lr_effective": cap["lr"], "ticks_run": t,
            "variant": {"reward_scale": float(reward_scale), "td_enabled": bool(td_enabled), "lr": lr}}


def preflight_credit_seams(seed, num_agents=4, ticks=32):
    """Pré-vol à RÉPONSE CONNUE des quatre seams de crédit (question 2 du pré-vol : couper ce qu'on croit
    couper, et rien d'autre). Lève `PreflightError` si un seam ment ; renvoie la mesure publiée."""
    from tools.experiment_preflight import PreflightError
    full = _learning_trace(seed, num_agents=num_agents, ticks=ticks)
    zero = _learning_trace(seed, num_agents=num_agents, ticks=ticks, reward_scale=0.0)
    neg = _learning_trace(seed, num_agents=num_agents, ticks=ticks, reward_scale=-1.0)
    low = _learning_trace(seed, num_agents=num_agents, ticks=ticks, lr=LR_LOW)
    tdoff = _learning_trace(seed, num_agents=num_agents, ticks=ticks, td_enabled=False)
    checks = {
        "zero_all_rewards_null": (len(zero["td_rewards"]) >= 1 and all(r == 0.0 for r in zero["td_rewards"])
                                  and all(r == 0.0 for r in zero["episode_rewards"])),
        "zero_still_updates": zero["summary"]["td_updates"] >= 1,
        "neg_first_tick_exact_negation": (len(full["first_td_rewards"]) == int(num_agents)
                                          and neg["first_td_rewards"] == [-r for r in full["first_td_rewards"]]
                                          and any(r != 0.0 for r in full["first_td_rewards"])),
        "tdoff_td_never_called": tdoff["td_rewards"] == [] and tdoff["summary"]["td_updates"] == 0,
        "tdoff_episodes_alive": tdoff["summary"]["episode_updates"] >= 1 and tdoff["summary"]["dW_abs_sum"] > 0.0,
        "lr_published_and_lower": (low["lr_effective"] is not None and full["lr_effective"] is not None
                                   and abs(low["lr_effective"] - LR_LOW) < 1e-12 and low["lr_effective"] < full["lr_effective"]),
        "lr_moves_less": 0.0 < low["summary"]["dW_abs_sum"] < full["summary"]["dW_abs_sum"],
        "full_updates": full["summary"]["td_updates"] >= 1 and full["summary"]["dW_abs_sum"] > 0.0,
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise PreflightError(f"preflight_credit_seams : seam(s) en défaut {failed} -- l'ablation du crédit ne "
                             "coupe pas ce qu'elle déclare ; aucune cellule ne doit être lancée")
    return {"seed": int(seed), "num_agents": int(num_agents), "ticks": int(ticks), **checks,
            "tdoff_episode_updates": int(tdoff["summary"]["episode_updates"]),
            "lr_effective": {"full": full["lr_effective"], "lr": low["lr_effective"]},
            "dW_abs_sum": {"full": full["summary"]["dW_abs_sum"], "zero": zero["summary"]["dW_abs_sum"],
                           "neg": neg["summary"]["dW_abs_sum"], "lr": low["summary"]["dW_abs_sum"],
                           "tdoff": tdoff["summary"]["dW_abs_sum"]},
            "td_updates": {k: t["summary"]["td_updates"] for k, t in (("full", full), ("zero", zero), ("neg", neg), ("lr", low), ("tdoff", tdoff))},
            "first_td_rewards_full": full["first_td_rewards"]}


def run_arm(seed, arm, num_agents=12, ticks_learn=2000, ticks_test=200):
    """Un bras pour un seed : bassin cloné ×num_agents, phase 1 (sauf bras gelé) sous la variante de crédit
    du bras, phase 2 mortelle à poids gelés. Publie la variante déclarée."""
    if int(num_agents) <= 0 or int(ticks_learn) <= 0 or int(ticks_test) <= 0 or arm not in ARMS:
        raise ValueError(
            f"run_arm : argument degenere (num_agents={num_agents}, ticks_learn={ticks_learn}, "
            f"ticks_test={ticks_test}, arm={arm!r}) -- aucune mesure possible ; ne pas confondre avec une "
            "mesure nulle OBSERVEE.")
    agents = _bassin_cohort(seed, num_agents)
    credit = dict(ARM_CREDIT[arm]) if arm in ARM_CREDIT else None
    out = {"seed": int(seed), "arm": arm, "num_agents": int(num_agents), "ticks_learn": int(ticks_learn),
           "ticks_test": int(ticks_test), "lr": credit["lr"] if credit else None, "credit": credit}
    t0 = time.time()
    if credit:
        out["learning"] = phase1_learn_immortal(agents, seed, ticks_learn, lr=credit["lr"],
                                                reward_scale=credit["reward_scale"], td_enabled=credit["td_enabled"])
    else:
        out["learning"] = None
    out["survival"] = phase2_survive_mortal(agents, seed, ticks_test)
    out["elapsed_s"] = time.time() - t0
    return out


def _dose(arm, learning):
    """Dose d'un bras : mises à jour TD par agent ; pour le bras à TD coupé, les mises à jour ÉPISODIQUES."""
    return int(learning["episode_updates"]) if arm == "b_tdoff" else int(learning["td_updates"])


def _classify(d, sign_min, delta_min):
    pos, neg = sum(1 for x in d if x > 0), sum(1 for x in d if x < 0)
    med = float(np.median(d))
    if pos >= sign_min and med >= delta_min:
        return "ETENDU", pos, neg, med
    if neg >= sign_min and med <= -delta_min:
        return "ERODE", pos, neg, med
    return "NEUTRE", pos, neg, med


def credit_ablation_verdict(rows, harness_min=HARNESS_MIN, dose_min=DOSE_MIN, dose_episodic_min=DOSE_EPISODIC_MIN,
                            sign_min=SIGN_MIN, delta_min=DELTA_MIN, n_min=N_MIN):
    """Lecture de la règle scellée S2-CREDIT-ABLATION, branches dans l'ORDRE IMPOSÉ :
    1 INCOMPLET -> 2 INDETERMINE_HARNAIS -> 3 INDETERMINE_DOSE (TD < 1000 ; épisodique < 100 pour b_tdoff)
    -> 4 INDETERMINE_REPLICATION (b_full doit ÉRODER) -> 5 chaque bras classé ERODE / NEUTRE / ETENDU contre le
    bassin gelé (signe 10/12 ET ±5 ticks) -> 6 mécanisme : b_zero ERODE = PAS_OU_BRUIT (toute mise à jour à ce
    pas détruit, signal ou pas) ; sinon b_neg ERODE = SIGNAL_QUELCONQUE (tout signal non nul érode, quel que soit
    son signe) ; sinon SIGNE_NEGATIF (l'érosion exige le signe négatif du signal) — exhaustif. Lectures
    secondaires publiées : voie_td (b_tdoff ERODE = EPISODIQUE_SUFFIT, sinon TD_NECESSAIRE), pas (b_lr ERODE =
    DESTRUCTEUR_A_PETIT_PAS, sinon ATTENUE_A_PETIT_PAS), neg_etend (b_neg ETENDU), ratios Σ|ΔW| / Σ|ΔW|_full
    par bras (un NEUTRE à 10 % de mouvement se lit « pas assez bougé », pas « inoffensif »)."""
    S_KEYS = ("a", "full", "zero", "neg", "lr", "tdoff")
    L_KEYS = ("full", "zero", "neg", "lr", "tdoff")
    keys = [f"S_{k}" for k in S_KEYS] + [f"dose_{k}" for k in L_KEYS] + [f"dW_{k}" for k in L_KEYS]
    if not rows:
        raise ValueError("credit_ablation_verdict : aucune ligne -- aucun verdict n'est fabriqué")
    for r in rows:
        for k in keys:
            if k not in r or not _finite(r[k]):
                raise ValueError(f"credit_ablation_verdict : {k} absent ou non fini pour le seed {r.get('seed')}")
        if float(r["dW_full"]) <= 0.0:
            raise ValueError(f"credit_ablation_verdict : dW_full <= 0 pour le seed {r.get('seed')} -- le bras complet n'a pas bougé, harnais cassé")
    n = len(rows)
    S = {k: [float(r[f"S_{k}"]) for r in rows] for k in S_KEYS}
    dose = {k: [int(r[f"dose_{k}"]) for r in rows] for k in L_KEYS}
    out = {"n": n, "mecanisme": None, "voie_td": None, "pas": None, "neg_etend": None,
           "thresholds": {"harness_min": float(harness_min), "dose_min": int(dose_min),
                          "dose_episodic_min": int(dose_episodic_min), "sign_min": int(sign_min),
                          "delta_min": float(delta_min), "n_min": int(n_min)}}
    for k, v in S.items():
        out[f"S_{k}_median"] = float(np.median(v))
    for k, v in dose.items():
        out[f"dose_{k}_median"] = float(np.median(v))
    for k in L_KEYS:
        d = [b - a for a, b in zip(S["a"], S[k])]
        cls, pos, neg, med = _classify(d, sign_min, delta_min)
        out[f"d_{k}_median"] = med
        out[f"d_{k}_positive"] = f"{pos}/{n}"
        out[f"d_{k}_negative"] = f"{neg}/{n}"
        out[f"arm_{k}"] = cls
    out["dW_ratio_median"] = {k: float(np.median([float(r[f"dW_{k}"]) / float(r["dW_full"]) for r in rows]))
                              for k in ("zero", "neg", "lr", "tdoff")}
    if n < n_min:
        out.update(verdict="INCOMPLET", why=f"{n} seeds < {n_min} : reprise, aucune lecture")
        return out
    if out["S_a_median"] < harness_min:
        out.update(verdict="INDETERMINE_HARNAIS",
                   why=f"S_a mediane {out['S_a_median']:.1f} < {harness_min} : le bassin ne transfere pas ici")
        return out
    low = [k for k in ("full", "zero", "neg", "lr") if out[f"dose_{k}_median"] < dose_min]
    if out["dose_tdoff_median"] < dose_episodic_min:
        low.append("tdoff")
    if low:
        out.update(verdict="INDETERMINE_DOSE",
                   why="dose insuffisante (le credit ne s'est pas applique, E2) : %s" % ", ".join(
                       f"dose_{k} mediane {out[f'dose_{k}_median']:.0f}" for k in low))
        return out
    if out["arm_full"] != "ERODE":
        out.update(verdict="INDETERMINE_REPLICATION",
                   why=(f"d_full mediane {out['d_full_median']:+.1f}, signe -{out['d_full_negative']} : le credit complet "
                        f"n'erode pas ici (P4.4/P4.8 : -28,25, 12/12) -- rien a ablater"))
        return out
    if out["arm_zero"] == "ERODE":
        out["mecanisme"] = "PAS_OU_BRUIT"
    elif out["arm_neg"] == "ERODE":
        out["mecanisme"] = "SIGNAL_QUELCONQUE"
    else:
        out["mecanisme"] = "SIGNE_NEGATIF"
    out["neg_etend"] = out["arm_neg"] == "ETENDU"
    out["voie_td"] = "EPISODIQUE_SUFFIT" if out["arm_tdoff"] == "ERODE" else "TD_NECESSAIRE"
    out["pas"] = "DESTRUCTEUR_A_PETIT_PAS" if out["arm_lr"] == "ERODE" else "ATTENUE_A_PETIT_PAS"
    out.update(verdict="LU",
               why=(f"zero {out['arm_zero']} ({out['d_zero_median']:+.1f}, dW {out['dW_ratio_median']['zero']:.2f}x) ; "
                    f"neg {out['arm_neg']} ({out['d_neg_median']:+.1f}, dW {out['dW_ratio_median']['neg']:.2f}x) -> "
                    f"mecanisme {out['mecanisme']} ; tdoff {out['arm_tdoff']} ({out['d_tdoff_median']:+.1f}, "
                    f"dW {out['dW_ratio_median']['tdoff']:.2f}x) -> {out['voie_td']} ; lr {out['arm_lr']} "
                    f"({out['d_lr_median']:+.1f}, dW {out['dW_ratio_median']['lr']:.2f}x) -> {out['pas']}"))
    return out


def main():
    from src.paths import results_file
    from tools.cost_guard import project_cost
    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.jobs.run import hold
    from tools.preregister import verify

    smoke = os.environ.get("SCA_SMOKE") == "1"
    full_all = os.environ.get("SCA_FULL_ALL") == "1"
    n = 1 if smoke else int(os.environ.get("SCA_SEEDS", "12"))
    ticks_learn = 200 if smoke else int(os.environ.get("SCA_TICKS_LEARN", "2000"))
    ticks_test = 100 if smoke else int(os.environ.get("SCA_TICKS_TEST", "200"))
    agents = int(os.environ.get("SCA_AGENTS", "12"))
    out = os.environ.get("SCA_OUT") or str(results_file("s2_credit_ablation" + ("_smoke" if smoke else "") + ".json"))
    out = out if os.path.isabs(out) else os.path.join(_ROOT, out)
    seeds = list(SEEDS_DEFAULT[:n])

    rule = verify(PREREG)
    budget_s = float(os.environ.get("SCA_BUDGET_S") or rule["budget_s"])
    print(f"[preregistration] {PREREG} : sceau VERIFIE ({len(rule['discrimination'])} branches, budget {budget_s / 3600:.2f} h)", flush=True)
    design = declare_design(
        question=rule["question"],
        replication_unit="seed (une cohorte de %d clones du bassin par bras, un monde par seed ; 6 bras appariés)" % agents,
        n_independent=n,
        links={"seams_credit": "measured", "dose_de_credit": "measured", "mouvement_dW": "measured",
               "resurrections": "measured", "survie_mortelle_poids_geles": "measured",
               "bassin_transfere_S_a": "measured", "replication_b_full": "measured"},
        cost_estimate=rule["plafond"], control_family=assert_control_family(cells=n, alpha_family=0.05))
    data = (json.load(open(out, encoding="utf-8")) if os.path.exists(out) else
            {"preregistration": [PREREG], "design": design, "provenance": _git_provenance(),
             "regime": dict(REGIME_P44, arms_credit=ARM_CREDIT, lr_low=LR_LOW),
             "params": {"seeds": seeds, "ticks_learn": ticks_learn, "ticks_test": ticks_test, "agents": agents,
                        "budget_s": budget_s, "smoke": smoke, "full_all": full_all},
             "arms": {arm: {} for arm in ARMS}, "cost": {}, "preflight": None, "replication": None})
    t_start = time.time()
    with hold("kuzu", owner="s2-credit-ablation" + ("-smoke" if smoke else ""), ttl_s=max(3600.0, budget_s * 2)):
        if data.get("preflight") is None:
            data["preflight"] = preflight_credit_seams(seeds[0], num_agents=4, ticks=32)     # lève si un seam ment
            data["regime"]["lr_published"] = data["preflight"]["lr_effective"]["full"]      # lu sur l'optimiseur
            _save(out, data)
            p = data["preflight"]
            print(f"[preflight] seams OK : lr {p['lr_effective']} ; dW {{{', '.join(f'{k} {v:.0f}' for k, v in p['dW_abs_sum'].items())}}} ; "
                  f"tdoff episodes {p['tdoff_episode_updates']}", flush=True)
        if "unit_s" not in data["cost"]:
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
                        row["credit"] = dict(ARM_CREDIT["b_full"])
                        data["arms"]["b_full"][s] = row
                unit_proj = unit_s - data["cost"]["unit_b_full_s"]
            else:
                unit_proj = unit_s
            _save(out, data)                   # AVANT la garde : un run REFUSÉ garde sa mesure
            data["cost"]["projected_s"] = project_cost(unit_proj, n_units=n, budget_s=budget_s,
                                                       label="s2-credit-ablation (unité = un seed, %d bras)" % (
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
                print(f"[{arm:8s} seed {s}] S {r['survival']['survival_median']:6.1f} (censures {r['survival']['censored']}) "
                      f"| TD {lrn.get('td_updates', 0):4d} ep {lrn.get('episode_updates', 0):3d} dW {lrn.get('dW_abs_sum', 0.0):8.0f} "
                      f"resur {lrn.get('resurrections', 0):3d} | {r['elapsed_s']:.0f}s", flush=True)
    rows = []
    for s in seeds:
        got = {arm: data["arms"][arm].get(str(s)) for arm in ARMS}
        if not all(got.values()):
            continue
        row = {"seed": s, "S_a": got["a_frozen"]["survival"]["survival_median"]}
        for arm in LEARNING_ARMS:
            k = ARM_KEY[arm]
            lrn = got[arm]["learning"]
            row[f"S_{k}"] = got[arm]["survival"]["survival_median"]
            row[f"dose_{k}"] = _dose(arm, lrn)
            row[f"dW_{k}"] = float(lrn["dW_abs_sum"])
            row[f"resurrections_{k}"] = lrn["resurrections"]
            row[f"imported_{k}"] = bool(got[arm].get("imported_from"))
        rows.append(row)
    data["rows"] = rows
    data["verdict"] = credit_ablation_verdict(rows) if rows else {"verdict": "INCOMPLET", "n": 0}
    data["cost"]["elapsed_total_s"] = time.time() - t_start
    _save(out, data)
    v = data["verdict"]
    print(f"\n=== P4.9 S2-CREDIT-ABLATION — n={v.get('n')} : {v.get('verdict')} | mecanisme {v.get('mecanisme')} | "
          f"voie_td {v.get('voie_td')} | pas {v.get('pas')}\n{v.get('why', '')}\n-> {out}")
    return data


if __name__ == "__main__":
    main()
