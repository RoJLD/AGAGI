"""P4.4 — `S2-CREDIT-RETENTION` : le crédit in-world RETIENT-il / ÉTEND-il le bassin DAgger de WARM-003,
et construit-il de la survie à FROID, quand l'apprentissage n'est plus borné par la mort ?

Règle SCELLÉE avant toute cellule : docs/preregistrations/S2-CREDIT-RETENTION.json (+ -bis, markup).
Pourquoi ce design (backlog, bloc « 🧭 2026-09-14 », rang 4 ; décision robla du 2026-09-14) :
[[EDR-CALIB-LEARNER]] a montré que l'apprenant publié APPREND à dose non bornée par la mort, et qu'un
apprenant MEURT ~100× plus qu'un non-apprenant. Un run qui mesure la survie d'un apprenant dans le monde
mortel confond donc « apprend » et « meurt en apprenant ». D'où DEUX phases par seed :

    phase 1  IMMORTELLE (énergie + hp rechargés, morts intra-tick ressuscitées, 2000 ticks) — le crédit
             s'applique, la dose est COMPTÉE (`dose_b`, `dose_c`), les résurrections publiées ;
    phase 2  MORTELLE (200 ticks), mêmes objets-agents, poids GELÉS (lr=0), forward torch identique —
             `S_a`, `S_b`, `S_c` = survie médiane des 12 agents.

Trois bras appariés par seed : (a) bassin cloné ×12 gelé (contrôle : le bassin transfère-t-il ?),
(b) bassin cloné ×12 + crédit publié, (c) cohorte fraîche + crédit publié. Unité de réplication = le
seed (n = 12). Ce que ce run NE tranche PAS est écrit dans la règle.

Usage : python tools/evo_runs/s2_credit_retention.py   (env : SCR_SEEDS=12 SCR_TICKS_LEARN=2000
        SCR_TICKS_TEST=200 SCR_AGENTS=12 SCR_BUDGET_S=7200 SCR_OUT=results/s2_credit_retention.json
        SCR_SMOKE=1 -> 1 seed, 200/100 ticks, fichier _smoke)
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
from tools.learning_events import count_learning_events  # noqa: E402
from tools.warmstart_evolution_inworld import COG_DEFAULT, METAB_DEFAULT  # noqa: E402

PREREG = "S2-CREDIT-RETENTION"
PREREG_BIS = "S2-CREDIT-RETENTION-bis"
PREREG_TER = "S2-CREDIT-RETENTION-ter"      # budget de coût RELEVÉ sur mesure (E12 sur le coût, 2026-09-14)
BASSIN_PATH = os.path.join("results", "warm003_dagger_genome.npz")
ARMS = ("a_warm_frozen", "b_warm_credit", "c_cold_credit")
SEEDS_DEFAULT = tuple(2026 + i for i in range(12))
# Seuils de la règle scellée (recopiés ICI pour l'exécutable ; le sceau fait foi, le test les confronte).
FLOOR = 9.0            # plancher no-perception, EDR-WARM-010, même régime
HARNESS_MIN = 20.0     # bassin WARM-003 publié 35,2 ; moitié perdue = harnais
DOSE_MIN = 1000        # P1.6 : 1999 TD / agent en 2000 ticks immortels
SIGN_MIN = 10          # 10/12 : binomial unilatéral P = 0,019
DELTA_MIN = 5.0        # ±5 ticks
N_MIN = 12


def load_bassin():
    """Le génome DAgger persisté de WARM-003 (`results/warm003_dagger_genome.npz`), UNE lignée
    (`n_lineage = 1`, déclaré dans le design). Refuse un chevauchement entrée/sortie (E24)."""
    from src.seed_ai.mutation import Genome
    from tools.experiment_preflight import assert_no_io_overlap
    z = np.load(os.path.join(_ROOT, BASSIN_PATH), allow_pickle=True)
    g = Genome(W=np.asarray(z["W"], dtype=np.float32), num_inputs=int(z["num_inputs"]),
               num_outputs=int(z["num_outputs"]))
    assert_no_io_overlap(g, label="bassin DAgger WARM-003")
    return g


def _world(seed, era, curiosity_scale=None, novelty_scale=None):
    """Le monde du run. `curiosity_scale` / `novelty_scale` (P4.8, S2-REWARD-ABLATION) : `None` laisse
    l'échelle du MONDE (`Biosphere3D.__init__`, attributs d'instance lus par la seule ligne de récompense
    `world_1_stoneage.py:1713`) -- chemin BIT-IDENTIQUE à P4.4 ; un flottant la remplace (0.0 = terme COUPÉ)."""
    from src.seed_ai.harness import seed_at
    from src.worlds.world_1_stoneage import Biosphere3D
    seed_at(seed, era)
    e = Biosphere3D()
    e.benchmark_mode = True
    e.night_enabled = False
    e.current_era = 10_000
    e.config.cognitive_demand = True          # monde 2-bits de S2-009 / WARM-003 (PAS cog_linear)
    e.config.cog_gain = COG_DEFAULT
    e.config.base_metabolism = METAB_DEFAULT
    e.config.forage_payoff = 0.0
    e.use_torch_inworld = True
    if curiosity_scale is not None:
        e.curiosity_scale = float(curiosity_scale)
    if novelty_scale is not None:
        e.novelty_scale = float(novelty_scale)
    if hasattr(e, "memory_retriever"):
        e.memory_retriever.stop()
        e.memory_retriever.clear()
    return e


REGIME = {"cognitive_demand": True, "cog_linear": False, "cog_gain": float(COG_DEFAULT),
          "base_metabolism": float(METAB_DEFAULT), "forage_payoff": 0.0, "benchmark_mode": True,
          "night_enabled": False, "energy_start": 80.0, "immortal_phase1": True,
          "refill_below": 30.0, "refill_to": 80.0, "hp_refill_below": 50.0, "frozen_phase2_lr": 0.0}


def immortal_refill(e, refill_below=30.0, refill_to=80.0, hp_refill_below=50.0):
    """Un tick d'IMMORTALITÉ après `e.step()` : énergie remise à `refill_to` sous `refill_below`, hp au
    plafond sous `hp_refill_below`, morts intra-tick RESSUSCITÉES (rendues à `e.agents`). Renvoie le nombre
    de résurrections de ce tick. Recette de run_learner_probe, prouvée complète 12/12 sur 2000 ticks par
    EDR-CALIB-LEARNER ; extraite de phase1_learn_immortal (P4.9) sans changer une ligne de son effet."""
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
    return len(dead)


# E34 (P2.132, 2026-09-26) : `immortal_refill` ci-dessus est le harnais PUBLIÉ de P4.4 → P4.16, laissé tel quel
# (ses lignes 107-113 sont citées par des règles scellées). Il rend la TAILLE de la cohorte mais pas son ORDRE :
# le mort revient en FIN de `e.agents` alors que la population torch n'est pas reconstruite (même B), donc après
# une mort en position p < B - 1 (depuis un ordre aligné) les B - p tranches p..B-1 pilotent chacune un autre corps ;
# une mort en DERNIÈRE position ne déplace rien, et les permutations se composent (cf. tools/slot_identity.py).
# `slot_order_fix=True` remet l'ordre de construction après chaque résurrection et VÉRIFIE l'invariant à chaque
# tick ; `identity_audit=True` le MESURE sans rien changer (lecture seule, aucun tirage RNG). Défauts = chemin
# publié au bit, aucune clé de sortie nouvelle.
# DOSE (revue E34 v1, P8.a/P10.a) : entre clones à phénotype figé, un désalignement qui PERSISTE n'est qu'un
# ré-étiquetage ; le tort se concentre aux COMMUTATIONS (une tranche change de corps : une transition TD à cheval sur
# deux corps, un transitoire de H, une fenêtre épisodique rejouée sur l'autre corps). `slot_switches` les compte dans
# TOUS les bras ; `slot_ticks_misaligned` (écart à l'ordre de construction) reste publié, il ne dose rien.
# SHAM (`sham_draws=k`, drapeau éteint) : k tirages SUPPLÉMENTAIRES du RNG global numpy (`np.random.random(k)`, jamais
# le RNG torch) au PREMIER tick où une résurrection désaligne — le tick exact où le drapeau fait diverger sa
# trajectoire. Même harnais publié, autre trajectoire du même seed : la bande de bruit du contraste allumé/éteint.
def _identity_counters():
    return {"ticks_known": 0, "ticks_unknown": 0, "slot_ticks_total": 0, "slot_ticks_misaligned": 0,
            "ticks_misaligned": 0, "first_misaligned_tick": None, "max_misaligned_slots": 0,
            "slot_switches": 0, "ticks_with_switch": 0, "first_switch_tick": None,
            "ticks_reordered": 0, "positions_reordered": 0, "first_reorder_tick": None,
            "sham_draws": 0, "sham_tick": None, "_pairing": None}


def _published_identity(identity):
    """Les compteurs publiables (l'appariement courant `_pairing` est un état de travail, pas une mesure)."""
    return {k: v for k, v in identity.items() if not k.startswith("_")}


def immortal_after_step(e, refill_below=30.0, refill_to=80.0, hp_refill_below=50.0, slot_order_fix=False,
                        identity=None, tick=None, sham_draws=0):
    """Ce qui suit `e.step()` dans une cohorte immortelle : `immortal_refill` (publié), puis, sous drapeau, la
    remise en ordre (E34), le relevé de l'invariant et des commutations dans `identity` (dict de
    `_identity_counters`, modifié en place) et, pour un bras SHAM, les `sham_draws` tirages numpy au premier tick
    désaligné. Rend le nombre de résurrections du tick. `slot_order_fix=False`, `identity=None`, `sham_draws=0` :
    exactement `immortal_refill(e, ...)`. Gardes EN TÊTE (avant la recharge) : audit sans tick, sham négatif, sham
    sans audit (son tick ne serait pas publié), sham sous drapeau (un sham ne répare pas l'identité)."""
    if identity is not None and tick is None:
        raise ValueError("immortal_after_step : `identity` sans `tick` -- first_misaligned_tick resterait None "
                         "alors qu'un désalignement a pu avoir lieu (une absence fabriquée) ; refus AVANT la recharge")
    if int(sham_draws) < 0 or (sham_draws and (identity is None or slot_order_fix)):
        raise ValueError(f"immortal_after_step : sham_draws={sham_draws!r} exige un audit (`identity`) et le drapeau "
                         "ÉTEINT -- refus AVANT la recharge")
    n = immortal_refill(e, refill_below, refill_to, hp_refill_below)
    if not slot_order_fix and identity is None:
        return n
    from tools.slot_identity import SlotIdentityError, restore_slot_order, slot_identity_violations
    if slot_order_fix:
        moved = restore_slot_order(e)
        if identity is not None and moved:
            identity["ticks_reordered"] += 1
            identity["positions_reordered"] += int(moved)
            if identity["first_reorder_tick"] is None:
                identity["first_reorder_tick"] = tick
    v = slot_identity_violations(e)
    if slot_order_fix and v != []:
        raise SlotIdentityError(f"tick {tick} : invariant slot W <-> corps NON vérifié après remise en ordre "
                                f"(violations = {v!r} ; None = appariement non défini)")
    if identity is not None:
        if v is None:
            identity["ticks_unknown"] += 1
        else:
            identity["ticks_known"] += 1
            identity["slot_ticks_total"] += len(e.agents)
            identity["slot_ticks_misaligned"] += len(v)
            identity["max_misaligned_slots"] = max(identity["max_misaligned_slots"], len(v))
            if v:
                identity["ticks_misaligned"] += 1
                if identity["first_misaligned_tick"] is None:
                    identity["first_misaligned_tick"] = tick
            pairing = [a["id"] for a in e.agents]                  # corps que chaque tranche pilote au prochain pas
            prev = identity["_pairing"]
            if prev is None:                                       # avant le 1er pas : ordre de construction
                corps = {id(a["model"]): a["id"] for a in e.agents}
                prev = [corps[id(m)] for m in e._torch_pop.agents]
            switched = sum(1 for j in range(len(pairing)) if pairing[j] != prev[j])
            if switched:
                identity["slot_switches"] += switched
                identity["ticks_with_switch"] += 1
                if identity["first_switch_tick"] is None:
                    identity["first_switch_tick"] = tick
            identity["_pairing"] = pairing
            if sham_draws and v and identity["sham_tick"] is None:
                np.random.random(int(sham_draws))                   # RNG global numpy SEUL ; torch intact
                identity["sham_tick"] = tick
                identity["sham_draws"] = int(sham_draws)
    return n


def phase1_learn_immortal(agents, seed, ticks, lr=None, refill_below=30.0, refill_to=80.0,
                          hp_refill_below=50.0, curiosity_scale=None, novelty_scale=None,
                          reward_scale=1.0, td_enabled=True, slot_order_fix=False, identity_audit=False,
                          sham_draws=0):
    """Le crédit publié s'applique à `agents` (objets persistés : genome.W accumule) dans le monde
    cognitif, cohorte IMMORTELLE (même recette que run_learner_probe, prouvée complète 12/12 sur 2000
    ticks par EDR-CALIB-LEARNER). Renvoie la dose (summary de count_learning_events) et `resurrections`.
    `curiosity_scale` / `novelty_scale` : voir `_world` (None = échelle du monde, bit-identique à P4.4).
    `reward_scale` / `td_enabled` / `lr` (P4.9, S2-CREDIT-ABLATION) : variantes de count_learning_events ;
    les défauts (1.0, True, None) sont le chemin PUBLIÉ, bit-identique à P4.4/P4.8.
    `slot_order_fix` / `identity_audit` / `sham_draws` (E34, P2.132) : voir `immortal_after_step` ; l'un des
    trois vrai publie `slot_identity` (compteurs de l'invariant et des commutations, tick du sham, le drapeau) ;
    les défauts (False, False, 0) sont le chemin PUBLIÉ, au bit, sans clé nouvelle."""
    resurrections = 0
    identity = _identity_counters() if (slot_order_fix or identity_audit or sham_draws) else None
    with _pinned_substrate(), count_learning_events(reward_scale=reward_scale, td_enabled=td_enabled, lr=lr) as ev:
        e = _world(seed, 0, curiosity_scale=curiosity_scale, novelty_scale=novelty_scale)
        for a in agents:
            e.add_agent(a, energy=80.0)
        t = 0
        while e.agents and t < int(ticks):
            e.step()
            resurrections += immortal_after_step(e, refill_below, refill_to, hp_refill_below,
                                                 slot_order_fix=slot_order_fix, identity=identity, tick=t,
                                                 sham_draws=sham_draws)
            t += 1
        if hasattr(e, "memory_retriever"):
            e.memory_retriever.stop()
    out = ev.summary()
    out["resurrections"] = int(resurrections)
    if identity is not None:
        out["slot_identity"] = dict(_published_identity(identity), slot_order_fix=bool(slot_order_fix))
    out["ticks"] = int(t)
    return out


def phase2_survive_mortal(agents, seed, ticks):
    """Survie MORTELLE à poids GELÉS (lr=0, TD coupé : aucune mise à jour, même forward torch que la
    phase 1). Mêmes objets-agents (leur genome.W porte ce qu'ils ont appris). Renvoie la survie
    médiane des agents (âge à la mort, censuré à `ticks`) et le nombre de censurés."""
    with _pinned_substrate(), count_learning_events(lr=0.0, td_enabled=False) as ev:
        e = _world(seed, 1)
        for a in agents:
            e.add_agent(a, energy=80.0)
        t = 0
        while e.agents and t < int(ticks):
            e.step()
            t += 1
        alive = list(e.agents)
        dead = list(getattr(e, "dead_agents", []))
        ages = [int(a["age"]) for a in alive + dead]
        if hasattr(e, "memory_retriever"):
            e.memory_retriever.stop()
    if not ages:
        raise ValueError("phase2_survive_mortal : aucun agent mesuré -- aucune survie n'est fabriquée")
    assert ev.summary()["dW_abs_sum"] == 0.0, "phase 2 : les poids ont bougé, le gel a échoué"
    return {"survival_median": float(np.median(ages)), "ages": ages, "censored": len(alive), "ticks": int(t)}


def run_arm(seed, arm, num_agents=12, ticks_learn=2000, ticks_test=200, lr=None):
    """Un bras pour un seed : construit la cohorte, phase 1 (sauf bras gelé), phase 2. Publie tout."""
    if int(num_agents) <= 0 or int(ticks_learn) <= 0 or int(ticks_test) <= 0 or arm not in ARMS:
        raise ValueError(
            f"run_arm : argument degenere (num_agents={num_agents}, ticks_learn={ticks_learn}, "
            f"ticks_test={ticks_test}, arm={arm!r}) -- aucune mesure possible ; ne pas confondre avec une "
            "mesure nulle OBSERVEE.")
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.harness import seed_at
    seed_at(seed, 0)
    if arm.startswith("c_"):
        agents = [MambaAgent() for _ in range(int(num_agents))]
    else:
        bassin = load_bassin()
        agents = []
        for _ in range(int(num_agents)):
            a = MambaAgent()
            a.from_genome(bassin)
            agents.append(a)
    out = {"seed": int(seed), "arm": arm, "num_agents": int(num_agents), "ticks_learn": int(ticks_learn),
           "ticks_test": int(ticks_test), "lr": lr}
    t0 = time.time()
    if arm != "a_warm_frozen":
        out["learning"] = phase1_learn_immortal(agents, seed, ticks_learn, lr=lr)
    else:
        out["learning"] = None
    out["survival"] = phase2_survive_mortal(agents, seed, ticks_test)
    out["elapsed_s"] = time.time() - t0
    return out


def _finite(x):
    try:
        return x is not None and np.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def credit_retention_verdict(rows, floor=FLOOR, harness_min=HARNESS_MIN, dose_min=DOSE_MIN,
                             sign_min=SIGN_MIN, delta_min=DELTA_MIN, n_min=N_MIN):
    """Lecture de la règle scellée, branches dans l'ORDRE IMPOSÉ. `rows` : une ligne par seed avec
    `S_a`, `S_b`, `S_c`, `dose_b`, `dose_c`. Toute entrée absente ou non finie LÈVE."""
    if not rows:
        raise ValueError("credit_retention_verdict : aucune ligne -- aucun verdict n'est fabriqué")
    for r in rows:
        for k in ("S_a", "S_b", "S_c", "dose_b", "dose_c"):
            if k not in r or not _finite(r[k]):
                raise ValueError(f"credit_retention_verdict : {k} absent ou non fini pour le seed {r.get('seed')}")
    n = len(rows)
    S_a = [float(r["S_a"]) for r in rows]; S_b = [float(r["S_b"]) for r in rows]; S_c = [float(r["S_c"]) for r in rows]
    d_ba = [b - a for a, b in zip(S_a, S_b)]
    dose_b = [int(r["dose_b"]) for r in rows]; dose_c = [int(r["dose_c"]) for r in rows]
    pos, neg = sum(1 for d in d_ba if d > 0), sum(1 for d in d_ba if d < 0)
    cold_above = sum(1 for s in S_c if s > 2.0 * floor)
    out = {"n": n, "S_a_median": float(np.median(S_a)), "S_b_median": float(np.median(S_b)),
           "S_c_median": float(np.median(S_c)), "d_ba_median": float(np.median(d_ba)),
           "d_ba_positive": f"{pos}/{n}", "d_ba_negative": f"{neg}/{n}", "cold_above_2x_floor": f"{cold_above}/{n}",
           "dose_b_median": float(np.median(dose_b)), "dose_c_median": float(np.median(dose_c)),
           "thresholds": {"floor": float(floor), "harness_min": float(harness_min), "dose_min": int(dose_min),
                          "sign_min": int(sign_min), "delta_min": float(delta_min), "n_min": int(n_min)},
           "verdict_warm": None, "verdict_cold": None}
    if n < n_min:
        out.update(verdict="INCOMPLET", why=f"{n} seeds < {n_min} : reprise, aucune lecture")
        return out
    if out["S_a_median"] < harness_min:
        out.update(verdict="INDETERMINE_HARNAIS",
                   why=f"S_a mediane {out['S_a_median']:.1f} < {harness_min} : le bassin ne transfere pas ici")
        return out
    if out["dose_b_median"] < dose_min or out["dose_c_median"] < dose_min:
        out.update(verdict="INDETERMINE_DOSE",
                   why=f"dose_b mediane {out['dose_b_median']:.0f}, dose_c mediane {out['dose_c_median']:.0f} : "
                       f"sous {dose_min}, le credit ne s'est pas applique (E2)")
        return out
    if pos >= sign_min and out["d_ba_median"] >= delta_min:
        out["verdict_warm"] = "RETENU_ETENDU"
    elif neg >= sign_min and out["d_ba_median"] <= -delta_min:
        out["verdict_warm"] = "ERODE"
    else:
        out["verdict_warm"] = "RETENU_NEUTRE"
    if cold_above >= sign_min and out["S_c_median"] >= 2.0 * floor:
        out["verdict_cold"] = "APPRIS_FROID"
    else:
        out["verdict_cold"] = "PAS_APPRIS_FROID"
    out.update(verdict="LU",
               why=(f"warm {out['verdict_warm']} (d_ba mediane {out['d_ba_median']:+.1f}, signe +{pos}/-{neg}) ; "
                    f"cold {out['verdict_cold']} (S_c mediane {out['S_c_median']:.1f} vs plancher {floor})"))
    return out


def _git_provenance():
    from tools.preregister import provenance        # P2.68 : un seul site de provenance
    return provenance()


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def main():
    from src.paths import results_file
    from tools.cost_guard import project_cost
    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.jobs.run import hold
    from tools.preregister import verify

    smoke = os.environ.get("SCR_SMOKE") == "1"
    n = 1 if smoke else int(os.environ.get("SCR_SEEDS", "12"))
    ticks_learn = 200 if smoke else int(os.environ.get("SCR_TICKS_LEARN", "2000"))
    ticks_test = 100 if smoke else int(os.environ.get("SCR_TICKS_TEST", "200"))
    agents = int(os.environ.get("SCR_AGENTS", "12"))
    out = os.environ.get("SCR_OUT") or str(results_file("s2_credit_retention" + ("_smoke" if smoke else "") + ".json"))
    out = out if os.path.isabs(out) else os.path.join(_ROOT, out)
    seeds = list(SEEDS_DEFAULT[:n])

    rule = verify(PREREG)                      # lève si le sceau a été retouché
    rule_bis = verify(PREREG_BIS)
    rule_ter = verify(PREREG_TER)              # porte le budget de coût RELEVÉ, avec la mesure qui le justifie
    budget_s = float(os.environ.get("SCR_BUDGET_S") or rule_ter["budget_s"])
    print(f"[preregistration] {PREREG} + {PREREG_BIS} + {PREREG_TER} : sceaux VERIFIES "
          f"({len(rule['discrimination'])} branches, budget {budget_s / 3600:.2f} h)")
    design = declare_design(
        question=rule["question"], replication_unit="seed (une cohorte de %d agents, un monde par seed ; 3 bras appariés)" % agents,
        n_independent=n,
        links={"dose_de_credit": "measured", "resurrections": "measured", "survie_mortelle_poids_geles": "measured",
               "bassin_transfere_S_a": "measured"},
        cost_estimate=rule["plafond"], control_family=assert_control_family(cells=n, alpha_family=0.05))
    data = (json.load(open(out, encoding="utf-8")) if os.path.exists(out) else
            {"preregistration": [PREREG, PREREG_BIS, PREREG_TER], "design": design, "provenance": _git_provenance(),
             "regime": REGIME, "params": {"seeds": seeds, "ticks_learn": ticks_learn, "ticks_test": ticks_test,
                                          "agents": agents, "budget_s": budget_s, "smoke": smoke},
             "arms": {arm: {} for arm in ARMS}, "cost": {}})
    t_start = time.time()
    with hold("kuzu", owner="s2-credit-retention" + ("-smoke" if smoke else ""), ttl_s=max(3600.0, budget_s * 2)):
        if "unit_s" not in data["cost"]:
            # Unité = UN SEED COMPLET (les trois bras), chaque bras MESURÉ : le bras (b) coûte ~100× le bras
            # gelé (les agents du bassin AGISSENT ; smoke du 2026-09-14 : 48 ms/tick contre 5 ms/tick pour
            # la cohorte froide). Projeter le bras le plus cher sur les trois (E13 dans le sens prudent)
            # refusait un run qui tient sous le plafond scellé ; projeter par type d'unité est la leçon de
            # P1.6 (« mesurer le coût par TYPE d'unité »).
            unit_s = 0.0
            for arm in ARMS:
                r = run_arm(seeds[0], arm, num_agents=agents, ticks_learn=ticks_learn, ticks_test=ticks_test)
                data["arms"][arm][str(seeds[0])] = r
                data["cost"][f"unit_{arm}_s"] = r["elapsed_s"]
                unit_s += r["elapsed_s"]
            data["cost"]["unit_s"] = unit_s
            _save(out, data)                   # AVANT la garde : un run REFUSÉ garde sa mesure (11 min perdues le 2026-09-14)
            data["cost"]["projected_s"] = project_cost(unit_s, n_units=n, budget_s=budget_s,
                                                       label="s2-credit-retention (unité = un seed, 3 bras)")
            _save(out, data)
            print(f"[cost] unité (seed complet) {unit_s:.1f}s ; projeté {data['cost']['projected_s'] / 60:.0f} min "
                  f"(budget {budget_s / 60:.0f} min)", flush=True)
        for s in seeds:
            for arm in ARMS:
                if str(s) in data["arms"][arm]:
                    continue
                r = run_arm(s, arm, num_agents=agents, ticks_learn=ticks_learn, ticks_test=ticks_test)
                data["arms"][arm][str(s)] = r
                _save(out, data)
                lrn = r["learning"] or {}
                print(f"[{arm:14s} seed {s}] S {r['survival']['survival_median']:6.1f} (censures {r['survival']['censored']}) "
                      f"| TD {lrn.get('td_updates', 0):4d} resur {lrn.get('resurrections', 0):3d} | {r['elapsed_s']:.0f}s", flush=True)
    rows = []
    for s in seeds:
        a, b, c = (data["arms"][arm].get(str(s)) for arm in ARMS)
        if not (a and b and c):
            continue
        rows.append({"seed": s, "S_a": a["survival"]["survival_median"], "S_b": b["survival"]["survival_median"],
                     "S_c": c["survival"]["survival_median"], "dose_b": b["learning"]["td_updates"],
                     "dose_c": c["learning"]["td_updates"],
                     "resurrections_b": b["learning"]["resurrections"], "resurrections_c": c["learning"]["resurrections"]})
    data["rows"] = rows
    data["verdict"] = credit_retention_verdict(rows) if rows else {"verdict": "INCOMPLET", "n": 0}
    data["cost"]["elapsed_total_s"] = time.time() - t_start
    _save(out, data)
    v = data["verdict"]
    print(f"\n=== P4.4 S2-CREDIT-RETENTION — n={v.get('n')} : {v.get('verdict')} | warm {v.get('verdict_warm')} | "
          f"cold {v.get('verdict_cold')}\n{v.get('why', '')}\n-> {out}")
    return data


if __name__ == "__main__":
    main()
