"""
tools/s2_demand.py — Benchmark S2 : "Le monde EXIGE-t-il l'intelligence ?" (cause-racine B).
Champion HoF + 3 baselines (RandomAction, RandomGenome, Reflex) x 4 mondes, survie INDIVIDUELLE
censurée + life_score (cohérence), appariement seedé (Harness D1), verdict IUT+Holm 3 issues.
Pré-enregistrement : docs/superpowers/specs/2026-06-14-S2-World-Demands-Intelligence-design.md.
"""
import math
import sys
import numpy as np
from src.seed_ai.harness import seed_at, Harness, _git_short_commit
from src.seed_ai.persistence import calculate_life_score, load_hall_of_fame
from src.agents.baseline_models import RandomActionBatchModel, ReflexBatchModel
from src.agents.ablation_models import ObsAblatedMambaBatchModel
from src.seed_ai.s2_stats import s2_verdict, verdict_from_survival_cmps, holm, verdict_within_subject
from src.worlds.world_1_stoneage import Biosphere3D
from src.worlds.world_0_soup import SoupWorld
from src.worlds.world_2_agricultural import AgriculturalWorld
from src.worlds.world_3_industrial import IndustrialWorld
from src.worlds.world_famine import FamineWorld


def run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20, max_ticks=400, n_eras=1, config=None):
    """K=n_eras ères seedées base+i d'UN monde sous UNE condition. batch_model_cls=None -> moteur
    normal (MambaBatchModel, pour champion/RandomGenome) ; sinon baseline injecté (RandomAction/Reflex).
    genome=None -> agents frais (RandomGenome) ; sinon clones du génome (champion). Renvoie la survie
    INDIVIDUELLE (âge de chaque agent, mort OU survivant-censuré) + life_score, agrégée sur les ères.
    config (WorldConfig) fixe le régime à la construction ; None = défaut historique."""
    from src.agents.mamba_agent import MambaAgent
    survival, life, censored = [], [], 0
    era_survival, era_life = [], []        # médiane PAR ère -> unité d'appariement par seed (spec §8)
    for i in range(max(1, int(n_eras))):
        seed_at(seed, i)
        env = world_cls(config) if config is not None else world_cls()
        env.benchmark_mode = True              # cohorte fixe (pas de reproduction/mutation/HGT)
        env.night_enabled = False              # nuit OFF (irrésoluble dans Soup)
        env.current_era = 10_000               # scaffolds OFF (anneal -> 0)
        if batch_model_cls is not None:
            env.batch_model_cls = batch_model_cls
        for _ in range(num_agents):
            a = MambaAgent()
            if genome is not None:
                a.from_genome(genome)
            env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        survivors = list(env.agents)           # encore vivants à max_ticks -> CENSURÉS
        dead = list(getattr(env, "dead_agents", []))
        era_ages, era_lifes = [], []
        for a in survivors + dead:
            age = int(a["age"]); ls = float(calculate_life_score(a))
            survival.append(age); life.append(ls)
            era_ages.append(age); era_lifes.append(ls)
        censored += len(survivors)
        era_survival.append(float(np.median(era_ages)) if era_ages else 0.0)
        era_life.append(float(np.median(era_lifes)) if era_lifes else 0.0)
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
    n = max(1, len(survival))
    return {"survival": survival, "life_score": life,
            "era_survival": era_survival, "era_life": era_life, "censored_frac": censored / n}


def load_champion_genome():
    """Génome du #1 du HoF. Lève si le HoF est vide (pas de `except: pass` silencieux, blocker panel)."""
    _version, entries = load_hall_of_fame()
    if not entries:
        raise RuntimeError("HoF vide : impossible de lancer S2 sans champion. Évoluer d'abord (main_biosphere).")
    return entries[0].genome


# Les 5 conditions par monde. (batch_model_cls, fresh_genome) :
#  - champion / random_genome -> moteur normal (None) ; genome fourni ou frais.
#  - random_action / reflex -> baseline injecté.
def _reflex_prudent(agents, world_model=None):
    return ReflexBatchModel(agents, world_model, prudent=True)


CONDITIONS = {
    "champion":        {"batch_model_cls": None,                    "fresh_genome": False},
    "random_genome":   {"batch_model_cls": None,                    "fresh_genome": True},
    "random_action":   {"batch_model_cls": RandomActionBatchModel,  "fresh_genome": True},
    "reflex_naive":    {"batch_model_cls": ReflexBatchModel,        "fresh_genome": True},
    "reflex_prudent":  {"batch_model_cls": _reflex_prudent,         "fresh_genome": True},
    "champion_obs_ablated": {"batch_model_cls": ObsAblatedMambaBatchModel, "fresh_genome": False},
}


K_FLOOR = 12                 # plancher pré-enregistré (réf EDR 087), spec §9
Z_ALPHA = 1.96               # alpha=0.05 bilatéral
Z_POWER = 0.84               # puissance 0.80


def required_k(mean_diff, std_diff, floor=K_FLOOR):
    """K requis pour détecter un effet apparié (t apparié) à puissance 0.80, alpha 0.05.
    K = ((z_alpha + z_power) / d)^2, d = |mean_diff|/std_diff. Planché à K_FLOOR."""
    if mean_diff == 0.0 or std_diff <= 0.0:
        return floor
    d = abs(mean_diff) / std_diff
    k = math.ceil(((Z_ALPHA + Z_POWER) / d) ** 2)
    return max(floor, int(k))


def pilot_required_k(world_cls, champion_genome, seed, k_pilot=5):
    """Pilote : survie champion vs réflexe naïf sur k_pilot ères, -> K requis (par monde)."""
    champ = run_condition(world_cls, None, champion_genome, seed, n_eras=k_pilot)["survival"]
    refl = run_condition(world_cls, ReflexBatchModel, None, seed, n_eras=k_pilot)["survival"]
    m = min(len(champ), len(refl))
    diff = np.array(champ[:m], dtype=float) - np.array(refl[:m], dtype=float)
    return required_k(float(np.mean(diff)), float(np.std(diff) + 1e-9))


WORLDS = {"soup": SoupWorld, "stoneage": Biosphere3D,
          "agricultural": AgriculturalWorld, "industrial": IndustrialWorld,
          "famine": FamineWorld}
BASELINE_KEYS = ("random_action", "random_genome", "reflex_naive", "reflex_prudent")


def _within_block(conds):
    """Verdict CAUSAL within-subject d'UN monde depuis ses conditions : ablation-perception du champion.
    champion vs champion_obs_ablated (l'ablation effondre-t-elle la survie ?), corroboré par
    champion_obs_ablated vs random_action (l'ablé retombe-t-il au niveau aléatoire ?)."""
    return verdict_within_subject(conds["champion"], conds["champion_obs_ablated"], conds["random_action"])


def _run_all_conditions(world_cls, champion_genome, seed, K, num_agents, max_ticks):
    """Toutes les conditions d'UN monde -> {cond: {survival, life_score, censored_frac}}."""
    out = {}
    for name, spec in CONDITIONS.items():
        genome = None if spec["fresh_genome"] else champion_genome
        out[name] = run_condition(world_cls, spec["batch_model_cls"], genome,
                                  seed, num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
    return out


def run_s2(worlds=None, seed=2026, K=None, num_agents=20, max_ticks=400, with_db=False):
    """Grille S2 complète. K=None -> pilote par monde (power analysis). Renvoie le rapport + le sauve."""
    worlds = worlds or list(WORLDS)
    champion = load_champion_genome()
    report = {"seed": seed, "commit": _git_short_commit(), "K": {}, "worlds": {}}

    with Harness(seed=seed, name="s2_demand", with_db=with_db) as h:
        for w in worlds:
            wcls = WORLDS[w]
            k_w = K if K is not None else pilot_required_k(wcls, champion, seed)
            report["K"][w] = k_w
            conds = _run_all_conditions(wcls, champion, seed, k_w, num_agents, max_ticks)

            # survie : réflexe = la variante à plus haute survie médiane (borne haute du réflexe, spec §5)
            refl = max((conds["reflex_naive"], conds["reflex_prudent"]),
                       key=lambda c: np.median(c["survival"]) if c["survival"] else 0.0)
            # s2_verdict reçoit les dicts de condition (pooled pour l'effet + par-ère pour l'appariement)
            baselines = {"random_action": conds["random_action"],
                         "random_genome": conds["random_genome"], "reflex": refl}
            # Verdict basé SURVIE (addendum daté 2026-06-30, cf. EDR 124) : le gate de cohérence
            # life_score donnait un faux VOID quand le champion domine la survie 3-5x mais que son
            # edge life_score est noyé par des événements rares/chanceux. s2_verdict calcule déjà les
            # cmps de survie (dans les 2 branches) + life_p -> on re-rend le verdict SANS re-simuler.
            v = s2_verdict(conds["champion"], baselines)
            sv = verdict_from_survival_cmps(v["survival"])
            sv["survival"] = v["survival"]
            sv["life_p"] = v["life_p"]                          # corroborant NON-bloquant (rapporté)
            sv["coherence_ok_lifescore"] = v["coherence_ok"]   # ce qu'aurait tranché l'ancien gate
            sv["censored_frac_champion"] = conds["champion"]["censored_frac"]
            report["worlds"][w] = sv
            report["worlds"][w]["within"] = _within_block(conds)

        # FWER global : Holm sur les p_monde de la famille des mondes testés (tous ont un p_monde
        # sous la base survie ; ne plus sélectionner la famille a posteriori sur le non-VOID)
        decided = [w for w in worlds if report["worlds"][w].get("p_monde") is not None]
        if decided:
            adj = holm([report["worlds"][w]["p_monde"] for w in decided])
            for w, pa in zip(decided, adj):
                report["worlds"][w]["p_monde_holm"] = float(pa)

        h.save(report)

    _print_table(report)
    return report


def _print_table(report):
    print(f"\n=== S2 — Le monde exige-t-il l'intelligence ? (seed={report['seed']}, commit={report['commit']}) ===")
    print("    cohérence basée SURVIE (addendum 2026-06-30, EDR 124) ; life_p = corroborant non-bloquant")
    for w, v in report["worlds"].items():
        s = v["survival"][v["strongest_baseline"]]
        if v["verdict"] == "VOID":
            # base survie : VOID = un baseline domine le champion en survie (vraie incohérence)
            print(f"  {w:12s} : VOID (survie incohérente : {v['strongest_baseline']} domine, "
                  f"p_monde={v['p_monde']:.3f}, Cliff d={s['cliff']:+.2f})")
            continue
        gate = "ok" if v.get("coherence_ok_lifescore") else "faux-VOID"
        print(f"  {w:12s} : {v['verdict']:12s} | p_monde={v.get('p_monde_holm', v['p_monde']):.3f} "
              f"| vs {v['strongest_baseline']}: Cliff d={s['cliff']:+.2f}, ratio[{s['ratio_lo']:.2f},{s['ratio_hi']:.2f}] "
              f"| censuré={v['censored_frac_champion']*100:.0f}% | life_p={v['life_p']:.3f} (ancien gate: {gate})")
        wi = v.get("within")
        if wi is not None:
            cc = wi["causal_cmp"]; rc = wi["residual_cmp"]
            print(f"      within (ablation-perception): {wi['verdict']:14s} "
                  f"| champion vs ablaté: Cliff d={cc['cliff']:+.2f} p={cc['p']:.4f} "
                  f"| ablaté vs random: Cliff d={rc['cliff']:+.2f}")
    print("  -> Verdict porté par EDR 124. Si censuré>5% quelque part : augmenter max_ticks.")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import os
    run_s2(seed=int(os.getenv("EXPERIMENT_SEED", "2026")), with_db=False)
