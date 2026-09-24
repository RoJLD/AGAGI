"""P4.16 — `S2-CREDIT-ABLATION-2` : [[EDR-S2-CREDIT-ABLATION]] a établi que l'érosion du bassin DAgger par le crédit
publié EXIGE un signal non nul, IGNORE son signe, n'est pas proportionnelle au mouvement des poids, et que la voie
ÉPISODIQUE seule (REINFORCE k = 8, `learn_episode`) suffit. Seconde passe, trois questions :

    b_tdonly   épisodique COUPÉ, TD par tick seul      -> le TD seul détruit-il AUSSI (deux destructeurs) ?
    b_const    retour CONSTANT +1 sur les deux voies    -> signal non nul, contenu nul : l'opérateur détruit-il
                                                          quel que soit le contenu (dérive de politique) ?
    b_eplr     épisodique seul à pas 0,004              -> la voie épisodique détruit-elle encore à petit pas ?

Règle SCELLÉE avant toute cellule : docs/preregistrations/S2-CREDIT-ABLATION-2.json.
Même dispositif que P4.4 / P4.8 / P4.9 (`s2_credit_retention.py` : phase 1 IMMORTELLE 2000 ticks à dose comptée,
phase 2 MORTELLE 200 ticks à poids gelés ; bassin DAgger cloné ×12 ; n = 12 seeds 2026..2037 ; unité = seed ;
`a_frozen` re-mesuré, `b_full` importé de P4.4 sur réplication bit-identique du seed 2026).

⚠️ Les deux seams NEUFS (`episode_enabled`, `reward_const`) vivent ICI (`credit_variant`), PAS dans
`tools/learning_events.py` (en cours d'édition par une autre session le 2026-09-22) : ils s'empilent SOUS
`count_learning_events` (qui compte et applique `reward_scale` / `td_enabled` / `lr`) et sont vérifiés à réponse
connue sur ce qui ATTEINT le learner d'ORIGINE (`_learning_trace_2`, `preflight_credit_seams_2`), avec un no-op
EXACT contre la trace de P4.9. À replier dans `count_learning_events` quand le fichier sera libre (backlog).

Usage : python tools/evo_runs/s2_credit_ablation_2.py   (env : SCA2_SEEDS=12 SCA2_TICKS_LEARN=2000
        SCA2_TICKS_TEST=200 SCA2_AGENTS=12 SCA2_BUDGET_S=<sceau> SCA2_OUT=results/s2_credit_ablation_2.json
        SCA2_SMOKE=1 -> 1 seed, 200/100 ticks, fichier _smoke ; SCA2_FULL_ALL=1 -> b_full mesuré partout)
"""
import contextlib
import datetime as _dt
import json
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.cognitive_demand_inworld import _pinned_substrate  # noqa: E402
from tools.evo_runs.s2_credit_ablation import DOSE_EPISODIC_MIN, LR_LOW, _classify, _learning_trace  # noqa: E402
from tools.evo_runs.s2_credit_retention import (  # noqa: E402
    DELTA_MIN, DOSE_MIN, HARNESS_MIN, N_MIN, REGIME as REGIME_P44, SEEDS_DEFAULT, SIGN_MIN,
    _finite, _git_provenance, _save, _world, immortal_refill, phase1_learn_immortal, phase2_survive_mortal)
from tools.evo_runs.s2_reward_ablation import P44_RESULTS, _bassin_cohort, p44_full_rows, replication_check  # noqa: E402
from tools.learning_events import count_learning_events  # noqa: E402

PREREG = "S2-CREDIT-ABLATION-2"
ARMS = ("a_frozen", "b_full", "b_tdonly", "b_const", "b_eplr")
LEARNING_ARMS = ARMS[1:]
_BASE = {"reward_scale": 1.0, "td_enabled": True, "lr": None, "episode_enabled": True, "reward_const": None}
ARM_CREDIT = {
    "b_full": dict(_BASE),                                    # chemin PUBLIÉ, bit-identique
    "b_tdonly": dict(_BASE, episode_enabled=False),
    "b_const": dict(_BASE, reward_const=1.0),
    "b_eplr": dict(_BASE, td_enabled=False, lr=LR_LOW),
}
ARM_KEY = {"b_full": "full", "b_tdonly": "tdonly", "b_const": "const", "b_eplr": "eplr"}


@contextlib.contextmanager
def credit_variant(episode_enabled=True, reward_const=None):
    """Deux seams sur la population torch, restaurés en `finally`. Défauts = AUCUN patch (bit-identique par
    construction). `episode_enabled=False` : `learn_episode` rend None sans toucher au modèle (le compteur de
    `count_learning_events`, posé PAR-DESSUS, compte l'appel et aucune mise à jour). `reward_const=c` : les
    récompenses passées à `learn` ET `learn_episode` sont remplacées par un tableau constant de même forme —
    signal non nul, contenu nul. S'empile SOUS `count_learning_events` : entrer ce contexte AVANT lui."""
    from src.agents.backend_torch import TorchPopulationModel as _TPM
    if episode_enabled and reward_const is None:
        yield
        return
    orig_learn, orig_episode = _TPM.learn, _TPM.learn_episode
    const = None if reward_const is None else np.float32(reward_const)

    def _const_like(x):
        return np.full_like(np.asarray(x, dtype=np.float32), const)

    def learn(self, rewards_batch, actions_batch=None):
        if const is not None:
            rewards_batch = _const_like(rewards_batch)
        return orig_learn(self, rewards_batch, actions_batch)

    def learn_episode(self, obs_seq, actions_seq, rewards, gamma=1.0, gate_last_only=True):
        if not episode_enabled:
            return None
        if const is not None:
            rewards = _const_like(rewards)
        return orig_episode(self, obs_seq, actions_seq, rewards, gamma=gamma, gate_last_only=gate_last_only)

    _TPM.learn, _TPM.learn_episode = learn, learn_episode
    try:
        yield
    finally:
        _TPM.learn, _TPM.learn_episode = orig_learn, orig_episode


def _learning_trace_2(seed, num_agents=4, ticks=32, reward_scale=1.0, td_enabled=True, lr=None,
                      episode_enabled=True, reward_const=None):
    """Ce qui ATTEINT le learner d'ORIGINE sous une variante complète (count_learning_events × credit_variant) :
    les originaux `learn` / `learn_episode` sont interceptés EN PREMIER (donc au plus profond), puis
    `credit_variant`, puis `count_learning_events` par-dessus. Cohorte immortelle, clones du bassin. Mêmes clés que
    `_learning_trace` (P4.9) + `variant`."""
    from src.agents.backend_torch import TorchPopulationModel as _TPM
    if int(num_agents) <= 0 or int(ticks) <= 0:
        raise ValueError("_learning_trace_2 : num_agents/ticks <= 0 -- rien à tracer")
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
        with credit_variant(episode_enabled=episode_enabled, reward_const=reward_const), _pinned_substrate(), \
                count_learning_events(reward_scale=reward_scale, td_enabled=td_enabled, lr=lr) as ev:
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
            "variant": {"reward_scale": float(reward_scale), "td_enabled": bool(td_enabled), "lr": lr,
                        "episode_enabled": bool(episode_enabled), "reward_const": reward_const}}


def preflight_credit_seams_2(seed, num_agents=4, ticks=32):
    """Pré-vol à RÉPONSE CONNUE des seams de cette passe (question 2 du pré-vol). Lève `PreflightError` si un seam
    ment ; renvoie la mesure publiée dans le JSON. Contrôle no-op EXACT : la variante par défaut rend la trace de
    P4.9 (`_learning_trace`, sans credit_variant) au bit près."""
    from tools.experiment_preflight import PreflightError
    ref = _learning_trace(seed, num_agents=num_agents, ticks=ticks)
    full = _learning_trace_2(seed, num_agents=num_agents, ticks=ticks)
    tdonly = _learning_trace_2(seed, num_agents=num_agents, ticks=ticks, episode_enabled=False)
    const = _learning_trace_2(seed, num_agents=num_agents, ticks=ticks, reward_const=1.0)
    eplr = _learning_trace_2(seed, num_agents=num_agents, ticks=ticks, td_enabled=False, lr=LR_LOW)
    checks = {
        "noop_exact_vs_P49": (full["first_td_rewards"] == ref["first_td_rewards"]
                              and full["summary"]["dW_abs_sum"] == ref["summary"]["dW_abs_sum"]
                              and full["summary"]["td_updates"] == ref["summary"]["td_updates"] >= 1),
        "tdonly_episode_never_called": tdonly["episode_rewards"] == [] and tdonly["summary"]["episode_updates"] == 0,
        "tdonly_td_alive": tdonly["summary"]["td_updates"] >= 1 and tdonly["summary"]["dW_abs_sum"] > 0.0,
        "const_all_rewards_one": (len(const["td_rewards"]) >= 1 and all(r == 1.0 for r in const["td_rewards"])
                                  and len(const["episode_rewards"]) >= 1 and all(r == 1.0 for r in const["episode_rewards"])),
        "const_both_paths_update": const["summary"]["td_updates"] >= 1 and const["summary"]["episode_updates"] >= 1,
        "eplr_td_never_called": eplr["td_rewards"] == [] and eplr["summary"]["td_updates"] == 0,
        "eplr_episodes_alive": eplr["summary"]["episode_updates"] >= 1 and eplr["summary"]["dW_abs_sum"] > 0.0,
        "eplr_lr_published": eplr["lr_effective"] is not None and abs(eplr["lr_effective"] - LR_LOW) < 1e-12,
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise PreflightError(f"preflight_credit_seams_2 : seam(s) en défaut {failed} -- l'ablation ne coupe pas ce "
                             "qu'elle déclare ; aucune cellule ne doit être lancée")
    return {"seed": int(seed), "num_agents": int(num_agents), "ticks": int(ticks), **checks,
            "eplr_lr_effective": eplr["lr_effective"], "full_lr_effective": full["lr_effective"],
            "dW_abs_sum": {k: t["summary"]["dW_abs_sum"] for k, t in (("full", full), ("tdonly", tdonly), ("const", const), ("eplr", eplr))},
            "td_updates": {k: t["summary"]["td_updates"] for k, t in (("full", full), ("tdonly", tdonly), ("const", const), ("eplr", eplr))},
            "episode_updates": {k: t["summary"]["episode_updates"] for k, t in (("full", full), ("tdonly", tdonly), ("const", const), ("eplr", eplr))},
            "first_td_rewards_full": full["first_td_rewards"]}


def run_arm(seed, arm, num_agents=12, ticks_learn=2000, ticks_test=200):
    """Un bras pour un seed : bassin cloné ×num_agents, phase 1 (sauf bras gelé) sous la variante de crédit du bras
    (credit_variant SOUS count_learning_events), phase 2 mortelle à poids gelés. Publie la variante déclarée."""
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
        with credit_variant(episode_enabled=credit["episode_enabled"], reward_const=credit["reward_const"]):
            out["learning"] = phase1_learn_immortal(agents, seed, ticks_learn, lr=credit["lr"],
                                                    reward_scale=credit["reward_scale"], td_enabled=credit["td_enabled"])
    else:
        out["learning"] = None
    out["survival"] = phase2_survive_mortal(agents, seed, ticks_test)
    out["elapsed_s"] = time.time() - t0
    return out


def _horodatage(t=None):
    """Heure civile locale ISO (secondes). `t` : un `time.time()` ; None = maintenant."""
    return (_dt.datetime.fromtimestamp(t) if t is not None else _dt.datetime.now()).isoformat(timespec="seconds")


def cost_cells(arms, long_cell_s=5000.0):
    """Les DÉNOMINATEURS du coût, recomputés depuis les cellules elles-mêmes (P2.78 ; revue adversariale du
    2026-09-24). Une cellule IMPORTÉE porte l'`elapsed_s` du run d'origine : ce temps n'a pas été dépensé ici,
    et sommer les 60 cellules donne PLUS que le temps mur du run. Une cellule hors échelle (machine suspendue
    pendant une nuit) est exclue du DÉBIT et publiée à part, avec son propre dénominateur — jamais soustraite
    du numérateur en gardant le dénominateur complet. Un ensemble vide rend `None`, jamais 0.0 (porte 14 : un
    débit de 0 s/cellule serait une affirmation de gratuité)."""
    cells = [(a, s, float(r["elapsed_s"]), bool(r.get("imported_from")))
             for a, per in arms.items() for s, r in per.items()]
    mesurees = [(a, s, e) for a, s, e, imp in cells if not imp]
    longues = [(a, s, e) for a, s, e in mesurees if e > long_cell_s]
    courtes = [(a, s, e) for a, s, e in mesurees if e <= long_cell_s]
    som_m = sum(e for _, _, e in mesurees)
    som_c = sum(e for _, _, e in courtes)
    return {"cells_declared": len(cells), "cells_measured": len(mesurees), "cells_imported": len(cells) - len(mesurees),
            "cells_long": len(longues), "cells_short": len(courtes),
            "elapsed_measured_s": som_m, "elapsed_short_s": som_c,
            "s_per_measured_cell": (som_m / len(mesurees)) if mesurees else None,
            "s_per_short_cell": (som_c / len(courtes)) if courtes else None,
            "long_cell_s": float(long_cell_s),
            "cells_over_long_s": {f"{a}/{s}": round(e) for a, s, e in sorted(longues, key=lambda x: -x[2])}}


def _row_doses(arm, learning):
    """Doses publiées par bras : TD par agent et/ou mises à jour ÉPISODIQUES selon la voie ouverte."""
    if arm == "b_const":
        return {"dose_const_td": int(learning["td_updates"]), "dose_const_ep": int(learning["episode_updates"])}
    if arm == "b_eplr":
        return {"dose_eplr": int(learning["episode_updates"])}
    return {f"dose_{ARM_KEY[arm]}": int(learning["td_updates"])}


def credit_ablation_2_verdict(rows, harness_min=HARNESS_MIN, dose_min=DOSE_MIN, dose_episodic_min=DOSE_EPISODIC_MIN,
                              sign_min=SIGN_MIN, delta_min=DELTA_MIN, n_min=N_MIN):
    """Lecture de la règle scellée S2-CREDIT-ABLATION-2, branches dans l'ORDRE IMPOSÉ :
    1 INCOMPLET -> 2 INDETERMINE_HARNAIS -> 3 INDETERMINE_DOSE (TD < 1000 pour full/tdonly/const_td ; épisodique
    < 100 pour const_ep/eplr) -> 4 INDETERMINE_REPLICATION (b_full doit ÉRODER) -> 5 chaque bras classé
    ERODE / NEUTRE / ETENDU contre le bassin gelé (signe 10/12 ET ±5 ticks) -> 6 contenu : b_const ERODE =
    CONTENU_INDIFFERENT (l'opérateur détruit sans contenu), sinon CONTENU_COMPTE ; 7 voie : b_tdonly ERODE =
    TD_SUFFIT_AUSSI, sinon EPISODIQUE_SEUL_DESTRUCTEUR ; 8 pas épisodique : b_eplr ERODE =
    EPISODIQUE_DESTRUCTEUR_A_PETIT_PAS, sinon EPISODIQUE_ATTENUE_A_PETIT_PAS — à lire AVEC les ratios Σ|ΔW|."""
    S_KEYS = ("a", "full", "tdonly", "const", "eplr")
    D_TD = ("full", "tdonly", "const_td")
    D_EP = ("const_ep", "eplr")
    keys = [f"S_{k}" for k in S_KEYS] + [f"dose_{k}" for k in D_TD + D_EP] + [f"dW_{k}" for k in S_KEYS[1:]]
    if not rows:
        raise ValueError("credit_ablation_2_verdict : aucune ligne -- aucun verdict n'est fabriqué")
    for r in rows:
        for k in keys:
            if k not in r or not _finite(r[k]):
                raise ValueError(f"credit_ablation_2_verdict : {k} absent ou non fini pour le seed {r.get('seed')}")
        if float(r["dW_full"]) <= 0.0:
            raise ValueError(f"credit_ablation_2_verdict : dW_full <= 0 pour le seed {r.get('seed')} -- harnais cassé")
    n = len(rows)
    S = {k: [float(r[f"S_{k}"]) for r in rows] for k in S_KEYS}
    out = {"n": n, "contenu": None, "voie": None, "pas_episodique": None,
           "thresholds": {"harness_min": float(harness_min), "dose_min": int(dose_min),
                          "dose_episodic_min": int(dose_episodic_min), "sign_min": int(sign_min),
                          "delta_min": float(delta_min), "n_min": int(n_min)}}
    for k, v in S.items():
        out[f"S_{k}_median"] = float(np.median(v))
    for k in D_TD + D_EP:
        out[f"dose_{k}_median"] = float(np.median([int(r[f"dose_{k}"]) for r in rows]))
    for k in S_KEYS[1:]:
        d = [b - a for a, b in zip(S["a"], S[k])]
        cls, pos, neg, med = _classify(d, sign_min, delta_min)
        out[f"d_{k}_median"] = med
        out[f"d_{k}_positive"] = f"{pos}/{n}"
        out[f"d_{k}_negative"] = f"{neg}/{n}"
        out[f"arm_{k}"] = cls
    out["dW_ratio_median"] = {k: float(np.median([float(r[f"dW_{k}"]) / float(r["dW_full"]) for r in rows]))
                              for k in ("tdonly", "const", "eplr")}
    if n < n_min:
        out.update(verdict="INCOMPLET", why=f"{n} seeds < {n_min} : reprise, aucune lecture")
        return out
    if out["S_a_median"] < harness_min:
        out.update(verdict="INDETERMINE_HARNAIS",
                   why=f"S_a mediane {out['S_a_median']:.1f} < {harness_min} : le bassin ne transfere pas ici")
        return out
    low = [k for k in D_TD if out[f"dose_{k}_median"] < dose_min] + [k for k in D_EP if out[f"dose_{k}_median"] < dose_episodic_min]
    if low:
        out.update(verdict="INDETERMINE_DOSE",
                   why="dose insuffisante (le credit ne s'est pas applique, E2) : %s" % ", ".join(
                       f"dose_{k} mediane {out[f'dose_{k}_median']:.0f}" for k in low))
        return out
    if out["arm_full"] != "ERODE":
        out.update(verdict="INDETERMINE_REPLICATION",
                   why=(f"d_full mediane {out['d_full_median']:+.1f}, signe -{out['d_full_negative']} : le credit complet "
                        f"n'erode pas ici (P4.4/P4.8/P4.9 : -28,25, 12/12) -- rien a ablater"))
        return out
    out["contenu"] = "CONTENU_INDIFFERENT" if out["arm_const"] == "ERODE" else "CONTENU_COMPTE"
    out["voie"] = "TD_SUFFIT_AUSSI" if out["arm_tdonly"] == "ERODE" else "EPISODIQUE_SEUL_DESTRUCTEUR"
    out["pas_episodique"] = ("EPISODIQUE_DESTRUCTEUR_A_PETIT_PAS" if out["arm_eplr"] == "ERODE"
                             else "EPISODIQUE_ATTENUE_A_PETIT_PAS")
    rr = out["dW_ratio_median"]
    out.update(verdict="LU",
               why=(f"const {out['arm_const']} ({out['d_const_median']:+.1f}, dW {rr['const']:.2f}x) -> {out['contenu']} ; "
                    f"tdonly {out['arm_tdonly']} ({out['d_tdonly_median']:+.1f}, dW {rr['tdonly']:.2f}x) -> {out['voie']} ; "
                    f"eplr {out['arm_eplr']} ({out['d_eplr_median']:+.1f}, dW {rr['eplr']:.2f}x) -> {out['pas_episodique']}"))
    return out


def main():
    from src.paths import results_file
    from tools.cost_guard import project_cost
    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.jobs.run import hold
    from tools.preregister import verify

    smoke = os.environ.get("SCA2_SMOKE") == "1"
    full_all = os.environ.get("SCA2_FULL_ALL") == "1"
    n = 1 if smoke else int(os.environ.get("SCA2_SEEDS", "12"))
    ticks_learn = 200 if smoke else int(os.environ.get("SCA2_TICKS_LEARN", "2000"))
    ticks_test = 100 if smoke else int(os.environ.get("SCA2_TICKS_TEST", "200"))
    agents = int(os.environ.get("SCA2_AGENTS", "12"))
    out = os.environ.get("SCA2_OUT") or str(results_file("s2_credit_ablation_2" + ("_smoke" if smoke else "") + ".json"))
    out = out if os.path.isabs(out) else os.path.join(_ROOT, out)
    seeds = list(SEEDS_DEFAULT[:n])

    rule = verify(PREREG)
    budget_s = float(os.environ.get("SCA2_BUDGET_S") or rule["budget_s"])
    print(f"[preregistration] {PREREG} : sceau VERIFIE ({len(rule['discrimination'])} branches, budget {budget_s / 3600:.2f} h)", flush=True)
    design = declare_design(
        question=rule["question"],
        replication_unit="seed (une cohorte de %d clones du bassin par bras, un monde par seed ; 5 bras appariés)" % agents,
        n_independent=n,
        links={"seams_credit": "measured", "noop_exact_vs_P49": "measured", "dose_de_credit": "measured",
               "mouvement_dW": "measured", "resurrections": "measured", "survie_mortelle_poids_geles": "measured",
               "bassin_transfere_S_a": "measured", "replication_b_full": "measured"},
        cost_estimate=rule["plafond"], control_family=assert_control_family(cells=n, alpha_family=0.05))
    data = (json.load(open(out, encoding="utf-8")) if os.path.exists(out) else
            {"preregistration": [PREREG], "design": design, "provenance": _git_provenance(),
             "regime": dict(REGIME_P44, arms_credit=ARM_CREDIT, lr_low=LR_LOW),
             "params": {"seeds": seeds, "ticks_learn": ticks_learn, "ticks_test": ticks_test, "agents": agents,
                        "budget_s": budget_s, "smoke": smoke, "full_all": full_all},
             "arms": {arm: {} for arm in ARMS}, "cost": {}, "preflight": None, "replication": None})
    t_start = time.time()
    cpu_start = time.process_time()
    with hold("kuzu", owner="s2-credit-ablation-2" + ("-smoke" if smoke else ""), ttl_s=max(3600.0, budget_s * 2)):
        if data.get("preflight") is None:
            data["preflight"] = preflight_credit_seams_2(seeds[0], num_agents=4, ticks=32)   # lève si un seam ment
            data["regime"]["lr_published"] = data["preflight"]["full_lr_effective"]
            _save(out, data)
            p = data["preflight"]
            print(f"[preflight] seams OK : no-op exact {p['noop_exact_vs_P49']} ; dW {{{', '.join(f'{k} {v:.0f}' for k, v in p['dW_abs_sum'].items())}}} ; "
                  f"episodes {p['episode_updates']}", flush=True)
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
                                                       label="s2-credit-ablation-2 (unité = un seed, %d bras)" % (
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
            row.update(_row_doses(arm, lrn))
            row[f"dW_{k}"] = float(lrn["dW_abs_sum"])
            row[f"resurrections_{k}"] = lrn["resurrections"]
            row[f"imported_{k}"] = bool(got[arm].get("imported_from"))
        rows.append(row)
    data["rows"] = rows
    data["verdict"] = credit_ablation_2_verdict(rows) if rows else {"verdict": "INCOMPLET", "n": 0}
    data["cost"]["elapsed_total_s"] = time.time() - t_start
    data["cost"]["elapsed_cpu_s"] = time.process_time() - cpu_start     # P2.78 : le temps CPU à côté du mur
    # Heure CIVILE : aucun instrument ne la produit ailleurs, et c'est elle qui dit si un temps mur long est un
    # calcul ou une nuit (revue adversariale du 2026-09-24 : une valeur saisie à la main dans un JSON de
    # résultats est indiscernable d'une valeur mesurée).
    data["cost"]["started_at"] = _horodatage(t_start)
    data["cost"]["finished_at"] = _horodatage()
    data["cost"].update(cost_cells(data["arms"]))                        # dénominateurs recomputés, jamais à la main
    _save(out, data)
    v = data["verdict"]
    print(f"\n=== P4.16 S2-CREDIT-ABLATION-2 — n={v.get('n')} : {v.get('verdict')} | contenu {v.get('contenu')} | "
          f"voie {v.get('voie')} | pas {v.get('pas_episodique')}\n{v.get('why', '')}\n-> {out}")
    return data


if __name__ == "__main__":
    main()
