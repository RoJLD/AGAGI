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
from src.seed_ai.s2_stats import (s2_verdict, verdict_from_survival_cmps, holm,
                                  verdict_within_subject, s2_degeneracy)
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
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06, famille run_* -- 7e elargissement du cliquet). Un
    # argument degenere est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte
    # vide / un horizon nul rend 0.0 ou nan comme une MESURE que l'aval lit comme un resultat
    # (biais negatif systematique du depot). Posee AVANT toute construction -> refus < 0.5 s.
    if int(num_agents) <= 0 or int(max_ticks) <= 0 or int(n_eras) <= 0:
        raise ValueError(
            f"run_condition : argument degenere (num_agents={num_agents}, max_ticks={max_ticks}, n_eras={n_eras}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
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
        if hasattr(env, "memory_retriever"):   # AVANT la boucle. Le `stop()` en fin d'ère (plus bas) ne
            env.memory_retriever.stop()        # protégeait RIEN : le retriever tournait pendant TOUTE la
            env.memory_retriever.clear()       # simulation -> mémoire ambiante KuzuDB -> runs non
                                               # reproductibles. Même défaut que celui mesuré dans
                                               # EDR-INFRA-001, ici dans la fonction PARTAGÉE que
                                               # traversent s2_demand_ablation, s2_openloop_probe,
                                               # cognitive_demand_inworld et warmstart (dette P2.8).
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
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06). Orchestrateur : il n'entraine pas lui-meme mais
    # AGREGE en verdict -- une cohorte/liste de seeds vide produit une agregation VIDE que l'aval
    # lit comme une mesure (biais negatif systematique). Refus instantane, avant tout appel de run.
    if int(num_agents) <= 0 or int(max_ticks) <= 0 or (K is not None and int(K) <= 0):
        raise ValueError(
            f"run_s2 : argument degenere (num_agents={num_agents} max_ticks={max_ticks} K={K}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    # ⚠️ DEUX defauts corriges le 2026-09-07 (trouves par injection a dose connue) :
    # (a) `worlds or list(WORLDS)` traitait une liste VIDE comme « pas de choix » -> demander ZERO
    #     monde lancait la grille COMPLETE (5 mondes x 6 conditions x K eres), le run le plus cher
    #     du depot. `None` = pas de choix ; `[]` = un choix vide, donc une erreur d'appel.
    # (b) `worlds` etait ITERE DEUX FOIS (la boucle de mesure, puis la famille Holm plus bas). Passe
    #     en ITERATEUR, la 2e passe etait VIDE : aucun `p_monde_holm` n'etait ecrit et `_print_table`
    #     retombait en silence sur le `p_monde` NON corrige -- la correction FWER disparaissait sans
    #     un mot, c.-a-d. exactement le p-hacking que le commentaire du code interdit.
    if worlds is None:
        worlds = list(WORLDS)
    worlds = list(worlds)                      # materialise : deux passes sont faites plus bas
    if not worlds:
        raise ValueError(
            "run_s2 : argument degenere (famille de mondes VIDE) -- aucune mesure possible ; ne pas "
            "confondre avec une mesure nulle OBSERVEE. (Passer `worlds=None` pour la grille complete.)")
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
            # ⚠️ RÉGIME ILLISIBLE — défaut corrigé le 2026-09-08 (classe E3, deux portes d'entrée).
            # `s2_verdict` pose sa garde de dégénérescence AVANT tout le reste et rend alors
            # {'verdict': 'INCONCLUSIVE_DEGENERATE', 'degenerate': True, 'why': ...} SANS clé
            # 'survival' ni 'life_p'. L'appel INCONDITIONNEL à `verdict_from_survival_cmps(v["survival"])`
            # levait donc un KeyError : l'orchestrateur DÉTRUISAIT le seul verdict d'indétermination
            # de toute la chaîne. Deux régimes réels y menaient — (a) les deux bras constants (tout le
            # monde meurt au même tick : Cliff δ vaut ±1 MÉCANIQUEMENT, cas mesuré le 2026-09-01) et
            # (b) la cohorte champion VIDE (extinction totale), que la garde d'ARGUMENTS posée en tête
            # ne couvre PAS puisqu'elle refuse `num_agents<=0` À L'APPEL, pas une extinction MESURÉE.
            # Dans les deux cas la grille S2 entière s'arrêtait sur une trace de clé.
            # On PROPAGE l'indétermination, on ne la remplace pas : ce monde reçoit
            # INCONCLUSIVE_DEGENERATE + la RAISON, la grille CONTINUE sur les mondes suivants, et rien
            # n'est fabriqué depuis une absence de mesure — pas de p_monde (donc HORS de la famille
            # Holm, il n'y a rien à corriger), pas de Cliff, pas de life_p, et pas de bloc `within`
            # (un verdict causal calculé sous un régime illisible serait fabriqué, exactement comme
            # sous un champion VOID). `verdict_from_survival_cmps` a précisément un paramètre
            # `degenerate_why` pour ça : elle ne peut pas se garder elle-même (elle ne reçoit que des
            # comparaisons déjà calculées), c'est l'appelant qui détient les distributions.
            # ⚠️ 2e DÉFAUT, trouvé en RÉFUTATION le 2026-09-08 : `s2_verdict` n'examine QU'UNE paire —
            # (champion, baseline de plus haute médiane). Or le verdict de survie est un IUT
            # CONJONCTIF : p_monde = MAX des p sur les TROIS baselines, donc N'IMPORTE LAQUELLE des
            # trois peut décider seule. Une paire illisible ailleurs que sur la plus forte traversait
            # donc la garde intacte et allait fabriquer un verdict.
            # Aggravant MESURÉ : `max(..., key=np.median)` est AVEUGLE aux bras vides — `np.median([])`
            # vaut nan, et nan ne gagne JAMAIS une comparaison `>`, donc un bras vide n'est élu « le
            # plus fort » QUE s'il est PREMIER dans le dict. Le même bras vide rendait
            # INCONCLUSIVE_DEGENERATE en 1re position et, en 2e ou 3e,
            # « VOID (survie incohérente : random_genome domine, p_monde=1.000, Cliff d=+0.00) » —
            # avec ratio_lo/ratio_hi = nan PUBLIÉS. Le verdict dépendait de l'ordre d'insertion d'un
            # dict, et une absence totale de mesure devenait l'affirmation de FOND « un baseline
            # domine le champion » (forme (a) du biais systématique du dépôt), Holm inclus — donc
            # gonflant la multiplicité m au détriment des mondes réellement mesurés.
            # On interroge donc `s2_degeneracy` sur CHAQUE membre de la famille IUT, avec les mêmes
            # distributions que celles qui entrent dans le test. Elle ne déclenche que sur les cas
            # CERTAINS (bras vide / bras identiques point par point / les deux constants) : un
            # baseline simplement PLAT face à un champion étalé reste lisible et n'est PAS refusé.
            why = v["why"] if v.get("degenerate") else None
            if why is None:
                for _k in baselines:                       # ordre déterministe -> raison déterministe
                    _why_k = s2_degeneracy(conds["champion"], baselines[_k])
                    if _why_k:
                        why = f"comparaison champion vs {_k} (membre de l'IUT) : {_why_k}"
                        break
            if why:
                sv = verdict_from_survival_cmps({}, degenerate_why=why)
                sv["strongest_baseline"] = v.get("strongest_baseline")
                sv["censored_frac_champion"] = conds["champion"]["censored_frac"]
                report["worlds"][w] = sv
                continue
            sv = verdict_from_survival_cmps(v["survival"])
            sv["survival"] = v["survival"]
            sv["life_p"] = v["life_p"]                          # corroborant NON-bloquant (rapporté)
            sv["coherence_ok_lifescore"] = v["coherence_ok"]   # ce qu'aurait tranché l'ancien gate
            sv["censored_frac_champion"] = conds["champion"]["censored_frac"]
            report["worlds"][w] = sv
            if sv["verdict"] != "VOID":                  # within = sans objet si le champion est incohérent (VOID)
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
        if v.get("degenerate"):
            # Régime illisible : il n'y a NI p-value NI Cliff à imprimer — seulement la raison du
            # refus. Le monde reste dans le tableau (la grille a bien tourné) mais hors famille Holm.
            print(f"  {w:12s} : {v['verdict']} ({v['why']}) "
                  f"| aucune p-value -> HORS de la famille Holm "
                  f"| censuré={v['censored_frac_champion']*100:.0f}%")
            continue
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
        if wi is not None and wi.get("degenerate"):
            # ⚠️ MÊME DÉFAUT, MÊME FONCTION, 12 LIGNES PLUS BAS — trouvé en RÉFUTATION du correctif
            # du 2026-09-08 (classe E3, 3e porte d'entrée). `verdict_within_subject` porte EXACTEMENT
            # la même garde de dégénérescence que `s2_verdict` et rend alors
            # {'verdict': 'INCONCLUSIVE_DEGENERATE', 'degenerate': True, 'why': ...} SANS 'causal_cmp'
            # ni 'residual_cmp' -> `cc = wi["causal_cmp"]` levait KeyError. La garde posée en tête de
            # boucle ne couvre PAS ce sous-bloc : le monde a un verdict de survie parfaitement lisible,
            # c'est le bloc CAUSAL qui ne l'est pas.
            # Régime qui y mène, et c'est le plus banal du dépôt : le champion ET sa version obs-ablée
            # censurés au MÊME tick (max_ticks atteint des deux côtés, variance nulle des deux côtés)
            # pendant que les baselines meurent -> le monde est tranché EXIGE, `within` est attaché,
            # et l'impression lève APRÈS le `h.save` : la grille est mesurée, archivée... et AUCUN des
            # mondes suivants n'est imprimé, `run_s2` ne rend jamais son rapport. C'est le comportement
            # que le correctif du jour prétendait avoir supprimé, par une troisième porte.
            # On dit la RAISON, on n'imprime NI Cliff NI p : il n'y en a pas.
            print(f"      within (ablation-perception): {wi['verdict']} ({wi['why']}) "
                  f"| aucune comparaison lisible -> ni Cliff ni p")
        elif wi is not None:
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
