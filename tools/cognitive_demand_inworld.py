"""S2-009 — Réalise la recette S2-006 IN-WORLD (flag cognitive_demand sur stoneage) et prouve via
l'ablation-perception que la survie devient perception-SENSIBLE (oracle) — flip du NEUTRE de S2-003.

Oracle = lecteur-de-signal câblé (décode bit_a/bit_b de l'obs → direction correcte) : preuve DÉCISIVE que
le monde EXIGE la perception (intact survit, ablé s'effondre), indépendamment du crédit. Contraste mode OFF
(doit rester NEUTRE). Réutilise run_condition (seam batch_model_cls) + derange_rows + ablation_verdict.

Usage : python tools/cognitive_demand_inworld.py  (env: CDI_SEED, CDI_K, CDI_AGENTS, CDI_TICKS, CDI_METAB, CDI_COG)
REF-DEMAND-MARKER. NE modifie PAS s2_demand.
"""
import contextlib
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.baseline_models import BaselineBatchModel
from tools.s2_demand_ablation import derange_rows
from tools.demand_marker import ablation_verdict
from tools.s2_demand import run_condition
from tools.learning_events import count_learning_events

BIT_A, BIT_B = 12, 13                                  # colonnes du signal dans l'obs (world_1 column_stack)


@contextlib.contextmanager
def _pinned_substrate():
    """P2.27 — le substrat mesuré est ÉPINGLÉ, pas hérité de l'ambiant du processus.

    `TorchPopulationModel.BILINEAR` est un attribut de CLASSE lu par `__init__` (`backend_torch.py:111`,
    crée U/V/W_bl) et par `_step` (`:128`). Non posé, une autre sonde du même interpréteur pouvait faire
    mesurer un AUTRE substrat à celle-ci, sans trace dans le résultat (défaut A du cliquet
    `tools/check_substrate_pinning.py`).

    ⚠️ Pin EN DUR à `False` = défaut de classe = BIT-IDENTIQUE aux chiffres publiés par S2-009/010/011
    (aucun `torch.randn` supplémentaire, même liste de paramètres SGD, même branche dans `_step`).

    ⚠️ Ici la population torch est construite PAR LE MONDE (`Biosphere3D._get_batch_model`, ssi
    `use_torch_inworld=True`), PAS par la sonde : construction DIFFÉRÉE (au premier `step()`) et
    RÉPÉTÉE (reconstruite à chaque changement de B, donc à chaque mort). Le pin doit donc couvrir
    TOUTE la boucle de simulation, pas seulement la ligne qui précède un `make_population`.
    Les chemins oracle (`_run_mode`, `run_linear_sanity`) construisent des `BaselineBatchModel` numpy
    via `run_condition` (use_torch_inworld=False) : ils ne sont PAS concernés et ne sont pas épinglés ;
    sur le chemin legacy (`use_credit=False`, `MambaBatchModel` numpy) le pin est un no-op."""
    from src.agents.backend_torch import TorchPopulationModel
    saved = TorchPopulationModel.BILINEAR
    TorchPopulationModel.BILINEAR = False
    # P4.11 : le crédit épinglé est TD(0) d'origine ; `count_learning_events(trace_lambda=...)` le pose
    # APRÈS ce pin (ordre du `with`) et le restaure AVANT -- même schéma que `lr`.
    saved_trace = TorchPopulationModel.CREDIT_TRACE_LAMBDA
    TorchPopulationModel.CREDIT_TRACE_LAMBDA = 0.0
    # E29 (2026-09-16) : l'activation LEGACY (`generated_ops.py`, non versionnée, rechargée à chaud à
    # chaque pas) est GELÉE au hash présent à l'entrée — un run ne peut plus changer d'activation en
    # cours de route, et un clone sans le fichier tourne en builtin DÉCLARÉ (publié par
    # `activation_provenance()` dans le bloc `regime`), jamais en tanh silencieux. `pin=None` = le
    # hash présent : BIT-IDENTIQUE aux records legacy du 2026-09-15 tant que le fichier ne change pas.
    from src.agents.mamba_agent import pinned_activation
    try:
        with pinned_activation():
            yield
    finally:
        TorchPopulationModel.BILINEAR = saved
        TorchPopulationModel.CREDIT_TRACE_LAMBDA = saved_trace


class CognitiveOracleBatchModel(BaselineBatchModel):
    """Décode le signal (bit_a/bit_b) → logits favorisant la direction correcte dir=2*(a>0)+(b>0)."""

    def _logits(self, batch_obs):
        logits = np.zeros((self.B, self.O), dtype=np.float32)
        a = batch_obs[:, BIT_A] if batch_obs.shape[1] > BIT_A else np.ones(self.B)
        b = batch_obs[:, BIT_B] if batch_obs.shape[1] > BIT_B else np.ones(self.B)
        dirs = (2 * (a > 0) + (b > 0)).astype(int)
        for i in range(self.B):
            logits[i, dirs[i]] = 1.0
        return logits


class CognitiveOracleAblated(CognitiveOracleBatchModel):
    """Oracle recevant l'obs DÉRANGÉE (within-subject) → décode le signal d'un pair → rate."""

    def forward(self, batch_obs, env_surprise_batch=None):
        return super().forward(derange_rows(batch_obs), env_surprise_batch)


def _run_mode(cognitive_demand, seed, K, num_agents, max_ticks, base_metabolism, cog_gain):
    """Configure le régime (via un world_cls partiel) puis oracle intact vs ablé → verdict."""
    from src.worlds.world_1_stoneage import Biosphere3D

    def make_world():
        env = Biosphere3D()
        env.config.cognitive_demand = cognitive_demand
        env.config.cog_gain = cog_gain
        env.config.base_metabolism = base_metabolism
        env.config.forage_payoff = 0.0                # neutralise la chasse (corps insuffisant en ON)
        return env

    intact = run_condition(make_world, CognitiveOracleBatchModel, None, seed,
                           num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
    ablated = run_condition(make_world, CognitiveOracleAblated, None, seed,
                            num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
    # `ceiling=max_ticks` : borne CONNUE (les survivants à max_ticks sont censurés). On ne déclare PAS
    # de `floor` ici — le plancher 9.0 mesuré par WARM-010 vaut pour le régime ON, pas pour le bras OFF,
    # et importer un plancher d'un autre régime est précisément l'erreur E8. La garde auto (bras
    # identiques / variance nulle) s'applique quand même.
    v = ablation_verdict(intact["era_survival"], ablated["era_survival"], ceiling=float(max_ticks))
    verdict = {"X_DEMANDED": "PERCEPTION_DEMANDED",
               "X_DECOY": "NEUTRAL",
               "INCONCLUSIVE": "INCONCLUSIVE"}.get(v["verdict"], v["verdict"])
    return {"ratio": v["ratio"], "verdict": verdict, "n": v["n"],
            "censored": v.get("censored"), "why": v.get("why")}


def run_cog_demand_map(seed=2026, K=12, num_agents=12, max_ticks=200, base_metabolism=4.0, cog_gain=6.0):
    """Oracle intact vs ablé, mode ON vs OFF. ON attendu SENSIBLE (PERCEPTION_DEMANDED), OFF NEUTRE."""
    return {
        "on": _run_mode(True, seed, K, num_agents, max_ticks, base_metabolism, cog_gain),
        "off": _run_mode(False, seed, K, num_agents, max_ticks, base_metabolism, cog_gain),
    }


def run_credit_probe(seed=2026, eras=6, num_agents=12, max_ticks=200, base_metabolism=0.75, cog_gain=12.0,
                     learning_out=None):
    """Sonde crédit intra-vie (Task 4) : une cohorte FRAÎCHE use_torch_inworld (REINFORCE) apprend-elle la
    nourriture cognitive ? Le monde EXIGE la perception (oracle : survie 200 vs plancher ~7). Si le crédit
    apprend, la survie médiane MONTE sur les ères ; sinon elle reste au plancher (= verrou = crédit, pas le
    monde). Renvoie la liste des survies médianes par ère. Prérequis : corps insuffisant structurel (ver/
    trésor/alignment gatés en cognitive_demand). Borné (à froid, sans warm-start/curriculum)."""
    # ⚠️ GARDE D'ARGUMENTS, EN TETE (2026-09-01). Sans elle, une cohorte vide ou un horizon nul
    # produisait une MESURE : 0.0 rendu comme survie observee, puis lu par un verdict comme
    # « reste au plancher ». Un argument degenere n'est pas un resultat scientifique, c'est une
    # erreur d'appel -> on LEVE, on ne rend pas de sentinelle qui entrerait dans une moyenne.
    # Posee AVANT la construction du monde : le refus ne coute aucune simulation.
    if int(eras) <= 0 or int(num_agents) <= 0 or int(max_ticks) <= 0:
        raise ValueError(
            f"run_credit_probe : argument degenere (eras={eras}, num_agents={num_agents}, max_ticks={max_ticks}) -- "
            "aucune mesure possible ; ne pas confondre avec une survie nulle MESUREE.")
    import numpy as np
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.seed_ai.harness import seed_at
    from src.agents.mamba_agent import MambaAgent

    trend = []
    # P2.27 : substrat EPINGLE sur TOUTE la boucle -- le monde construit (et RECONSTRUIT a chaque mort)
    # la population torch dans `e.step()`, pas ici. Cf. `_pinned_substrate`.
    # P1.6 : la DOSE de credit est COMPTEE (tools/learning_events) et publiee dans learning_out --
    # le type de retour publie (liste des survies medianes) est INCHANGE, le chemin est bit-identique.
    with _pinned_substrate(), count_learning_events() as ev:
        for era in range(eras):
            seed_at(seed, era)
            e = Biosphere3D()
            e.benchmark_mode = True
            e.night_enabled = False
            e.current_era = 10_000
            e.config.cognitive_demand = True
            e.config.cog_gain = cog_gain
            e.config.base_metabolism = base_metabolism
            e.config.forage_payoff = 0.0
            e.use_torch_inworld = True
            for _ in range(num_agents):
                e.add_agent(MambaAgent(), energy=80.0)
            t = 0
            while e.agents and t < max_ticks:
                e.step()
                t += 1
            ages = [int(a["age"]) for a in list(e.agents) + list(getattr(e, "dead_agents", []))]
            trend.append(float(np.median(ages)) if ages else 0.0)
            if hasattr(e, "memory_retriever"):
                e.memory_retriever.stop()
    if learning_out is not None:
        learning_out.update(ev.summary())
    return trend


CURRICULUM_COG = [(0.75, 40.0), (0.75, 28.0), (0.75, 20.0), (0.75, 16.0), (0.75, 12.0), (0.75, 12.0)]
CURRICULUM_METAB = [(0.25, 12.0), (0.35, 12.0), (0.5, 12.0), (0.65, 12.0), (0.75, 12.0), (0.75, 12.0)]


def run_warmstart_credit_probe(seed=2026, num_agents=12, max_ticks=200, schedule=None, floor=7.0):
    """Suite naturelle (warm-start/curriculum du credit-probe). Le probe FROID (run_credit_probe) montre que
    le crédit in-world n'apprend pas la nourriture cognitive à froid (survie plate ~7). Catch-22 du
    bootstrap : régime dur = meurt avant d'apprendre ; régime facile = pas de pression. Curriculum : UNE
    cohorte PERSISTÉE (mêmes MambaAgent → genome.W accumule l'apprentissage, world_1 sync) traverse un
    `schedule` de (base_metabolism, cog_gain) allant du FACILE au DUR. Si à l'étape finale (dure) la survie
    TIENT (≫ floor) → le curriculum a franchi le bootstrap (loi warm-start). CURRICULUM_COG = cog annelé
    haut→normal (metab dur fixe) ; CURRICULUM_METAB = metab facile→dur (cog fixe). Renvoie survie médiane
    par étape + flag learned."""
    # ⚠️ GARDE D'ARGUMENTS, EN TETE (2026-09-01). Meme raison que pour les autres mesures : sans
    # elle, une cohorte vide ou un horizon nul produit une MESURE (0.0 rendu comme observation),
    # que l'aval lit comme un resultat. On LEVE : un argument degenere est une erreur d'appel, pas
    # un fait sur le monde. Posee avant la construction du monde -> le refus ne coute rien.
    if int(num_agents) <= 0 or int(max_ticks) <= 0:
        raise ValueError(
            f"run_warmstart_credit_probe : argument degenere (num_agents={num_agents}, max_ticks={max_ticks}) -- "
            "aucune mesure possible ; ne pas confondre avec une mesure nulle OBSERVEE.")
    import numpy as np
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.seed_ai.harness import seed_at
    from src.agents.mamba_agent import MambaAgent

    schedule = schedule if schedule is not None else CURRICULUM_COG
    agents = [MambaAgent() for _ in range(num_agents)]     # cohorte PERSISTÉE (genome.W accumule)
    trend = []
    # P2.27 : substrat EPINGLE sur TOUTE la boucle -- le monde construit (et RECONSTRUIT a chaque mort)
    # la population torch dans `e.step()`, pas ici. Cf. `_pinned_substrate`.
    with _pinned_substrate(), count_learning_events() as ev:      # P1.6 : dose comptee
        for stage, (metab, cog) in enumerate(schedule):
            seed_at(seed, stage)
            e = Biosphere3D()
            e.benchmark_mode = True
            e.night_enabled = False
            e.current_era = 10_000
            e.config.cognitive_demand = True
            e.config.cog_gain = cog
            e.config.base_metabolism = metab
            e.config.forage_payoff = 0.0
            e.use_torch_inworld = True
            if hasattr(e, "memory_retriever"):     # AVANT la boucle : un retriever actif pendant la sim rend
                e.memory_retriever.stop()          # les runs NON REPRODUCTIBLES (KuzuDB ambiant). Même défaut
                e.memory_retriever.clear()         # que celui mesuré dans EDR-INFRA-001. Règle projet.
            for a in agents:
                e.add_agent(a, energy=80.0)                    # réutilise les objets → genome.W persiste
            t = 0
            while e.agents and t < max_ticks:
                e.step()
                t += 1
            ages = [int(a["age"]) for a in list(e.agents) + list(getattr(e, "dead_agents", []))]
            trend.append((metab, cog, float(np.median(ages)) if ages else 0.0))
            if hasattr(e, "memory_retriever"):
                e.memory_retriever.stop()
    final = trend[-1][2]
    return {"trend": trend, "final": final, "learned": final >= 4 * floor,
            "learning": ev.summary()}   # 4× plancher = franchi


class LinearCognitiveOracle(BaselineBatchModel):
    """Oracle du signal LINÉAIRE 1-bit (S2-011) : dir = int(bit_a>0) ∈ {0,1} (col 12 de l'obs)."""

    def _logits(self, batch_obs):
        logits = np.zeros((self.B, self.O), dtype=np.float32)
        a = batch_obs[:, BIT_A] if batch_obs.shape[1] > BIT_A else np.ones(self.B)
        dirs = (a > 0).astype(int)                         # {0,1}
        for i in range(self.B):
            logits[i, dirs[i]] = 1.0
        return logits


class LinearOracleAblated(LinearCognitiveOracle):
    """Oracle linéaire recevant l'obs DÉRANGÉE (within-subject) → lit le bit d'un pair.
    ⚠️ Avec `dir ∈ {0,1}`, il tombe juste **une fois sur deux** par accident : le plancher de cette
    variante est structurellement PLUS HAUT que celui du régime 4-directions. D'où l'obligation de le
    mesurer ici et non de l'importer (S2-011 importait « ~7-8 » du régime 2-bits — classe E8)."""

    def forward(self, batch_obs, env_surprise_batch=None):
        return super().forward(derange_rows(batch_obs), env_surprise_batch)


def _acquire_kuzu(owner):
    """Bail sur la ressource exclusive « kuzu » (cf. tools/jobs/lease.py) : deux sondes monde
    concurrentes se disputent le lock KuzuDB -> mesure silencieusement contaminée."""
    try:
        from tools.jobs import lease as _lz
        return _lz.acquire("kuzu", owner=owner)
    except ImportError:
        return None


def _release_kuzu(lz):
    if lz is not None:
        try:
            from tools.jobs import lease as _l
            _l.release(lz)
        except Exception:
            pass


def _bc_clone_linear(agents, steps=800, seed=0):
    """Warm-start des POIDS par behavioral cloning de l'oracle LINÉAIRE (obs col 12 → dir 0/1) dans la
    politique torch, puis sync → genome.W. Renvoie l'accuracy finale (gate : >0.9 = bassin formé).
    ⚠️ CAVEAT (EDR-S2-011) : le BC entraîne `_step(obs, H_in=0)` (SINGLE-step). Le bassin obtenu (acc 1.0)
    NE TRANSFÈRE PAS au forward RÉCURRENT du monde (H accumulé sur les ticks + gate) : la cohorte
    warm-startée survit au plancher (~8) même SANS crédit. Pour un vrai warm-start in-world, cloner sur des
    ROLLOUTS réels (séquences obs/H/action de l'oracle in-world), pas `_step` à H=0."""
    import torch
    from src.agents.backend import make_population
    # P2.27 : substrat EPINGLE AVANT make_population (U/V/W_bl ne sont crees qu'a la construction) et
    # pendant les `_step` d'entrainement. Cf. `_pinned_substrate`.
    with _pinned_substrate():
        pop = make_population(agents, backend="torch")
        I, O, N, B = pop.I, pop.O, pop.N, pop.B
        rng = np.random.RandomState(seed)

        def batch():
            a = rng.choice([-1.0, 1.0], B)
            o = np.zeros((B, I), dtype=np.float32)
            o[:, BIT_A] = a
            return torch.tensor(o), torch.tensor((a > 0).astype(np.int64))

        for _ in range(steps):
            o, tg = batch()
            out = pop._step(o, torch.zeros((B, N)))[:, N - O:N][:, :8]
            loss = torch.nn.functional.cross_entropy(out, tg)
            pop.opt.zero_grad(); loss.backward(); pop.opt.step()
        o, tg = batch()
        out = pop._step(o, torch.zeros((B, N)))[:, N - O:N][:, :8]
        acc = float((out.argmax(1) == tg).float().mean())
        pop._write_back()                                      # sync poids appris → genome.W des agents
    return acc


def make_linear_world(base_metabolism=0.75, cog_gain=12.0):
    """Callable zero-arg construisant la variante `cog_linear` (signal 1-bit) au régime dur S2-011."""
    from src.worlds.world_1_stoneage import Biosphere3D

    def _make():
        e = Biosphere3D()
        e.config.cognitive_demand = True
        e.config.cog_linear = True
        e.config.cog_gain = cog_gain
        e.config.base_metabolism = base_metabolism
        e.config.forage_payoff = 0.0
        return e
    return _make


def run_linear_sanity(seed=2026, K=12, num_agents=12, max_ticks=200,
                      base_metabolism=0.75, cog_gain=12.0):
    """CONTRÔLE POSITIF + PLANCHER de la variante `cog_linear` — les deux chiffres que S2-011 publiait
    SANS chemin d'exécution committé (dette P2.8, ouverte par EDR-AUDIT-001).

    POURQUOI ÇA COMPTAIT : le finding « VALIDE » de S2-011 (« le crédit à froid n'apprend pas ») repose
    sur la prémisse « un suiveur-de-signal survit trivialement (oracle 200) ». Cette ligne n'avait aucun
    appelant : `LinearCognitiveOracle` était du CODE MORT. Un contrôle positif jamais exécuté ne prouve
    rien — c'est le générateur A du pré-vol.

    ⚠️ Le PLANCHER de cette variante ne peut PAS être importé du régime 4-directions : avec
    `dir ∈ {0,1}`, un agent privé de signal tombe juste **une fois sur deux** au lieu d'une sur quatre.
    S2-011 y importait « ~7-8 », mesuré ailleurs — classe E8. On le mesure ici, dans son propre régime."""
    world = make_linear_world(base_metabolism, cog_gain)
    lz = _acquire_kuzu("linear-sanity")
    try:
        intact = run_condition(world, LinearCognitiveOracle, None, seed,
                               num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
        ablated = run_condition(world, LinearOracleAblated, None, seed,
                                num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
    finally:
        _release_kuzu(lz)
    v = ablation_verdict(intact["era_survival"], ablated["era_survival"], ceiling=float(max_ticks))
    return {"oracle": intact["era_survival"], "floor": ablated["era_survival"],
            "oracle_median": float(np.median(intact["era_survival"])),
            "floor_median": float(np.median(ablated["era_survival"])),
            "ratio": v["ratio"], "verdict": v["verdict"], "censored": v["censored"], "n": v["n"]}


def run_credit_linear(seed=2026, warmstart=False, eras=6, num_agents=12, max_ticks=200,
                      base_metabolism=0.75, cog_gain=12.0, bc_steps=800, use_credit=True):
    """Test PROPRE du verrou crédit (tâche LINÉAIREMENT décodable, isole le crédit de la représentation).
    warmstart=False : cohorte fraîche → le crédit in-world APPREND-il la tâche linéaire à froid ?
    warmstart=True  : cohorte BC-clonée (bassin de poids pré-formé) → le crédit RETIENT-il le bassin sous
    le régime dur ? Renvoie {bc_acc, trend (survie médiane/ère), final}.

    `use_credit=False` : cohorte warm-startée SANS apprentissage in-world — c'est le bras DIAGNOSTIC que
    S2-011 publiait (« WARM SANS crédit → 8 ») alors que `use_torch_inworld` était codé EN DUR à True :
    la ligne n'avait aucun chemin d'exécution (dette P2.8)."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06, famille run_* -- 7e elargissement du cliquet). Un
    # argument degenere est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte
    # vide / un horizon nul rend 0.0 ou nan comme une MESURE que l'aval lit comme un resultat
    # (biais negatif systematique du depot). Posee AVANT toute construction -> refus < 0.5 s.
    if int(eras) <= 0 or int(num_agents) <= 0 or int(max_ticks) <= 0 or (warmstart and int(bc_steps) <= 0):
        raise ValueError(
            f"run_credit_linear : argument degenere (eras={eras}, num_agents={num_agents}, max_ticks={max_ticks}, warmstart={warmstart}, bc_steps={bc_steps}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.seed_ai.harness import seed_at
    from src.agents.mamba_agent import MambaAgent

    agents = [MambaAgent() for _ in range(num_agents)]
    bc_acc = _bc_clone_linear(agents, steps=bc_steps, seed=seed) if warmstart else None
    trend = []
    # P2.27 : substrat EPINGLE sur TOUTE la boucle -- `use_credit=True` fait construire (et RECONSTRUIRE
    # a chaque mort) la population torch par le monde dans `e.step()` ; `use_credit=False` = chemin
    # legacy numpy, ou le pin est un no-op. Cf. `_pinned_substrate`.
    with _pinned_substrate(), count_learning_events() as ev:      # P1.6 : dose comptee
        for era in range(eras):
            seed_at(seed, era)
            e = Biosphere3D()
            e.benchmark_mode = True
            e.night_enabled = False
            e.current_era = 10_000
            e.config.cognitive_demand = True
            e.config.cog_linear = True
            e.config.cog_gain = cog_gain
            e.config.base_metabolism = base_metabolism
            e.config.forage_payoff = 0.0
            e.use_torch_inworld = bool(use_credit)   # False = bras DIAGNOSTIC (bassin BC, aucun apprentissage)
            if hasattr(e, "memory_retriever"):       # AVANT la boucle (cf. EDR-INFRA-001, règle projet)
                e.memory_retriever.stop()
                e.memory_retriever.clear()
            for a in agents:
                e.add_agent(a, energy=80.0)
            t = 0
            while e.agents and t < max_ticks:
                e.step()
                t += 1
            ages = [int(a["age"]) for a in list(e.agents) + list(getattr(e, "dead_agents", []))]
            import numpy as _np
            trend.append(float(_np.median(ages)) if ages else 0.0)
            if hasattr(e, "memory_retriever"):
                e.memory_retriever.stop()
    return {"bc_acc": bc_acc, "trend": trend, "final": trend[-1] if trend else 0.0,
            "learning": ev.summary()}


_LEARNER_POLICIES = ("torch", "oracle", "legacy")


def _cause_de_mort(agent):
    """P2.72 (b), 2026-09-15 — la CAUSE de mort d'un agent que la cohorte immortelle ressuscite. Le monde tue
    ssi `energy <= 0` OU `hp <= 0` (`world_1_stoneage.py`, phase de survie) ; l'énergie tombe par drain, par
    projectile d'un pair (`energy_spent × poids`) ; les hp par la riposte du gibier et par l'attrition
    (−1/tick sous 20 d'énergie ou de confort). Trois classes, exhaustives sur un agent mort ; un agent qui
    n'est ni l'un ni l'autre n'est pas mort -> `AUCUNE` (crie au lieu d'inventer)."""
    e, hp = float(agent.get("energy", 1.0)), float(agent.get("hp", 1.0))
    if e <= 0.0 and hp <= 0.0:
        return "les_deux"
    if e <= 0.0:
        return "energie_epuisee"
    if hp <= 0.0:
        return "hp_epuise"
    return "AUCUNE"


class _NoThrowMamba(object):
    """Fabrique (P2.72 c, 2026-09-15) : sous-classe de MambaBatchModel dont `forward` force le logit de
    LANCER (index 8, lu par le monde comme `float(logits[8]) > 0`) sous le seuil, sur la COPIE `preds` que
    `forward` renvoie (tableau frais, jamais une vue de H) ; le crédit lit `H_prev_batch`, pas `preds`, donc
    seule l'ACTION disparaît. Ablation chirurgicale du projectile -- même geste que `_GrabOffTorchPop`."""

    @staticmethod
    def make():
        from src.agents.mamba_agent import MambaBatchModel

        class NoThrowMamba(MambaBatchModel):
            def forward(self, batch_obs, env_surprise_batch=None):
                preds, spent = MambaBatchModel.forward(self, batch_obs, env_surprise_batch)
                if getattr(preds, "ndim", 0) == 2 and preds.shape[1] > 8:
                    preds[:, 8] = -1.0
                return preds, spent
        return NoThrowMamba


def run_learner_probe(seed=2026, num_agents=12, ticks=2000, block=400, policy="torch",
                      reward_scale=1.0, td_enabled=True, lr=None,
                      base_metabolism=0.75, cog_gain=12.0, immortal=True,
                      refill_below=30.0, refill_to=80.0, hp_refill_below=50.0, no_throw=False):
    """P1.6 — CONTRÔLE POSITIF de l'APPRENANT in-world, à DOSE PUBLIÉE (backlog, bloc « 🧭 2026-09-14 »).

    Ce que ce dépôt appelait « le crédit n'apprend pas à froid » (S2-009 §crédit, S2-010, S2-011) était
    un nul mesuré sur des agents morts à 7-9 ticks — une dose de quelques dizaines de mises à jour, jamais
    comptée. Ici la cohorte est IMMORTELLE : après chaque tick, l'énergie est remise à `refill_to` sous
    `refill_below` (la récompense `cog_gain` n'est jamais écrêtée par la faim), les `hp` sont remis à
    leur plafond sous `hp_refill_below`, et un agent MORT DANS LE TICK est RESSUSCITÉ (même objet, même
    génome, énergie et hp rechargés) — le monde tue à l'intérieur d'un tick : un projectile lancé par un
    pair retire `energy_spent × poids` d'un coup (`world_1_stoneage.py`, phase de lancer), donc aucune
    recharge entre deux ticks ne suffit. `resurrections` est PUBLIÉ : c'est la létalité du monde, un
    chiffre, pas un biais. ⚠️ La version v1 (2026-09-14) ne rechargeait que l'énergie :
    le monde tue aussi par `hp` — la RIPOSTE du gibier frappe l'agent qui se place sur sa case
    (`world_1_stoneage.py`, phase prédateurs) — et les bras APPRENANTS, qui se déplacent vers la
    récompense, y perdaient jusqu'à la moitié de leur cohorte dès le premier bloc (seed 2027 : 12 → 9
    à 400 ticks, 3 à 800) contre 11/12 pour lr=0 et l'oracle : un biais de SURVIVANTS corrélé au bras.
    `deaths` et `n_agents` par bloc sont publiés pour que ce biais ne puisse plus passer inaperçu ;
    la DV est le TAUX DE COUPS
    sur la tâche linéaire 1-bit de S2-011 (`move == int(bit_a > 0)`), par blocs de `block` ticks, avec la
    dose comptée par `tools.learning_events.count_learning_events` — donc publiée à côté du résultat.

    `policy="oracle"` : `LinearCognitiveOracle` câblé, réponse connue 1.0 EXACTEMENT (contrôle positif de
    la DV). `policy="torch"` : l'apprenant tel que le monde le construit (`use_torch_inworld`), avec ses
    variantes déclarées : `reward_scale`, `td_enabled`, `lr` (`lr=0.0` = le bras qui ne peut RIEN
    apprendre — le plafond de l'incapable, mesuré dans CE dispositif, jamais importé).
    `policy="legacy"` (P3.4, 2026-09-15) : l'apprenant LEGACY, `MambaBatchModel.compute_policy_gradient`
    (Actor-Critic TD(0) numpy, `use_torch_inworld=False`, modèle recréé à chaque tick) — le chemin actif
    pendant tout l'arc EVO ; mêmes variantes, même compteur (`legacy_calls` / `legacy_updates`).
    `no_throw=True` (P2.72 c, legacy seulement) : le logit de LANCER est forcé sous le seuil sur la copie de
    sortie -> aucun projectile, rien d'autre ne change. Sert à départager « tué par un pair » de « tué par le
    drain » : la cause de mort est l'énergie à 100 % (LEGACY-CAUSE-DE-MORT-R1).

    Renvoie un dict publiable : `blocks` (tick, n_agents, hit_rate, n_decisions), `hit_first`, `hit_last`,
    `chance` (1/8 : 8 logits de déplacement), `learning` (dose et variante), `regime` (les valeurs de
    configuration RÉELLEMENT posées — jamais recopiées d'un record, E8 occ. 4)."""
    # GARDE D'ARGUMENTS, EN TÊTE, AVANT toute construction (refus < 0.5 s).
    if (int(num_agents) <= 0 or int(ticks) <= 0 or int(block) <= 0
            or policy not in _LEARNER_POLICIES or (no_throw and policy != "legacy")):
        raise ValueError(
            f"run_learner_probe : argument degenere (num_agents={num_agents}, ticks={ticks}, block={block}, "
            f"policy={policy!r}) -- aucune mesure possible ; ne pas confondre avec une mesure nulle OBSERVEE.")
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.seed_ai.harness import seed_at
    from src.agents.mamba_agent import MambaAgent
    from tools.learning_events import count_learning_events

    regime = {"cognitive_demand": True, "cog_linear": True, "cog_gain": float(cog_gain), "no_throw": bool(no_throw),
              "base_metabolism": float(base_metabolism), "forage_payoff": 0.0,
              "benchmark_mode": True, "night_enabled": False, "immortal": bool(immortal),
              "refill_below": float(refill_below), "refill_to": float(refill_to),
              "hp_refill_below": float(hp_refill_below), "energy_start": 80.0}
    # E29 : l'activation legacy EN VIGUEUR est une prémisse mesurée, pas un décor (E8) — publiée pour
    # TOUTE politique (le chemin torch ne la lit pas, mais le lecteur saura sous quelle activation le
    # bras legacy comparé a tourné). Posée ici, AVANT le pin de `_pinned_substrate`, donc = l'ambiant.
    from src.agents.mamba_agent import activation_provenance
    regime["legacy_activation"] = activation_provenance()
    lz = _acquire_kuzu("learner-probe")
    # E12/E13 (2026-09-16) : l'async_logger poussait UN AGENT_THOUGHT par agent et par tick dans KuzuDB (210 243
    # emissions sur un run de 60 cellules) ; une cellule a tourne > 3 h a 1,7 Go la ou ses soeurs prenaient
    # 2-3 min. Le logger ne nourrit PAS le monde (memory_retriever arrete -> in_mem = 0) : il est neutralise
    # AVANT la creation du monde, comme le fait `tools.evo_memory_inworld._disable_kuzu` (regle CLAUDE.md).
    # `count_learning_events` enveloppe `emit` APRES ce point et continue de compter TORCH_EPISODE_SKIP.
    from src.graph_rag.async_logger import logger as _al
    _al._running = False
    _al.start = lambda *a, **k: None
    _al.emit = lambda *a, **k: None
    _al.emit_sync = lambda *a, **k: False
    try:
        with _pinned_substrate(), count_learning_events(reward_scale=reward_scale,
                                                        td_enabled=td_enabled, lr=lr) as ev:
            seed_at(seed, 0)
            e = Biosphere3D()
            e.benchmark_mode = True
            e.night_enabled = False
            e.current_era = 10_000
            e.config.cognitive_demand = True
            e.config.cog_linear = True
            e.config.cog_gain = cog_gain
            e.config.base_metabolism = base_metabolism
            e.config.forage_payoff = 0.0
            e.config.trace_energy_sinks = True        # P4.14 : le prix du calcul (brain) est lu sur le monde, EDR-099
            if policy == "oracle":
                e.batch_model_cls = LinearCognitiveOracle
                e.use_torch_inworld = False
            elif policy == "legacy":
                e.use_torch_inworld = False           # MambaBatchModel, recree a chaque tick
                if no_throw:
                    e.batch_model_cls = _NoThrowMamba.make()
            else:
                e.use_torch_inworld = True
            if hasattr(e, "memory_retriever"):       # AVANT la boucle (EDR-INFRA-001)
                e.memory_retriever.stop()
                e.memory_retriever.clear()
            for _ in range(int(num_agents)):
                e.add_agent(MambaAgent(), energy=80.0)
            regime["torch_episode_k"] = int(getattr(e, "torch_episode_k", -1))
            hits, n, blocks, t, resurrections = 0, 0, [], 0, 0
            from src.agents.world_model import WorldModel as _WM
            _wm_resets0 = int(getattr(_WM, "nonfinite_resets", 0))     # E28 : remises a zero du World Model
            cause_de_mort = {"energie_epuisee": 0, "hp_epuise": 0, "les_deux": 0, "AUCUNE": 0}
            morts_w_non_fini = 0                          # E28 : morts d'agents dont W n'est plus fini
            pertes_a_la_mort = []                      # P2.72 c : energie au debut du tick - energie a la mort
            while e.agents and t < int(ticks):
                _avant = {id(a): float(a["energy"]) for a in e.agents}
                e.step()
                for a in e.agents:
                    sig = a.get("_cog_sig")
                    mv = (a.get("_pg") or {}).get("move")
                    if sig is not None and mv is not None and int(mv) >= 0:
                        hits += int(int(mv) == int(sig[0] > 0))
                        n += 1
                    if immortal:
                        if a["energy"] < refill_below:
                            a["energy"] = refill_to
                        if a["hp"] < hp_refill_below:      # riposte du gibier : jusqu'a 50 hp en un tick
                            a["hp"] = 100.0 + float(getattr(a["model"], "phenotype_hp_bonus", 0.0))
                if immortal:
                    dead = list(getattr(e, "dead_agents", []))
                    for a in dead:                     # mort DANS le tick : ressuscite, meme objet
                        cause_de_mort[_cause_de_mort(a)] += 1     # P2.72 (b) : compte AVANT la recharge
                        if not np.all(np.isfinite(np.asarray(a["model"].genome.W, dtype=np.float64))):
                            morts_w_non_fini += 1
                        if id(a) in _avant:
                            pertes_a_la_mort.append(round(_avant[id(a)] - float(a["energy"]), 2))
                        a["energy"] = refill_to
                        a["hp"] = 100.0 + float(getattr(a["model"], "phenotype_hp_bonus", 0.0))
                        e.agents.append(a)
                        resurrections += 1
                    if dead:
                        e.dead_agents.clear()          # ressuscites : jamais comptes deux fois
                t += 1
                if t % int(block) == 0 or t == int(ticks):
                    if n == 0:
                        raise ValueError(
                            f"run_learner_probe : bloc se terminant au tick {t} SANS aucune decision -- "
                            "la DV n'est pas mesurable (cohorte eteinte ?), aucun taux n'est fabrique.")
                    blocks.append({"tick": t, "n_agents": len(e.agents),
                                   "hit_rate": hits / n, "n_decisions": int(n)})
                    hits, n = 0, 0
            deaths = int(num_agents) - len(e.agents)
            _tous = list(e.agents) + list(getattr(e, "dead_agents", []))
            _ph = [a.get("_e_phases") or {} for a in _tous]
            brain_cost_total = float(sum(p.get("brain", 0.0) for p in _ph))
            drain_total = float(sum(sum(p.values()) for p in _ph))
            nan_skips = int(sum(int(getattr(a["model"], "_td_nan_skips", 0)) for a in list(e.agents) + list(getattr(e, "dead_agents", []))))
            if hasattr(e, "memory_retriever"):
                e.memory_retriever.stop()
    finally:
        _release_kuzu(lz)
    if not blocks:
        raise ValueError("run_learner_probe : aucun bloc mesure (cohorte eteinte avant le premier bloc).")
    return {"policy": policy, "immortal": bool(immortal), "seed": int(seed), "ticks": int(ticks),
            "block": int(block), "num_agents": int(num_agents), "chance": 1.0 / 8.0, "deaths": deaths,
            "resurrections": int(resurrections), "cause_de_mort": cause_de_mort,
            # P4.14 « glia » : le PRIX du calcul a cote de la dose -- compute_spent (branches de reve, via le
            # compteur) et brain_cost (puits `brain` d'EDR-099, cumule sur la cohorte, resurrections comprises).
            "glia": {"compute_spent_total": float(ev.summary()["compute_spent_total"]),
                     "brain_cost_total": brain_cost_total, "energie_perdue_total": drain_total,
                     "brain_share": (brain_cost_total / drain_total) if drain_total > 0 else None},
            "morts_w_non_fini": int(morts_w_non_fini), "nan_skips": nan_skips,      # E28
            "wm_resets": int(getattr(_WM, "nonfinite_resets", 0)) - _wm_resets0,
            "nan_brain_cost": int(getattr(e, "nan_brain_cost", 0)),                   # E28, garde du monde
            "pertes_a_la_mort": {"n": len(pertes_a_la_mort),
                                 "mediane": (float(np.median(pertes_a_la_mort)) if pertes_a_la_mort else None),
                                 "min": (min(pertes_a_la_mort) if pertes_a_la_mort else None),
                                 "max": (max(pertes_a_la_mort) if pertes_a_la_mort else None)},
            "blocks": blocks, "hit_first": blocks[0]["hit_rate"], "hit_last": blocks[-1]["hit_rate"],
            "learning": ev.summary(), "regime": regime}


def learner_verdict(learner_first, learner_last, reference_last, oracle_last,
                    min_sep=0.05, min_gain=0.05, oracle_min=0.9, reference_max=0.5):
    """Lit les taux de coups de `run_learner_probe` et REFUSE de conclure hors bornes.

    `reference_last` est le bras `lr=0` du MÊME dispositif (le plafond de ce qu'un agent qui ne peut rien
    apprendre atteint) ; la barre est `reference_last + min_sep` — jamais « chance + marge » (P2.15).
    `oracle_last` est le contrôle positif de la DV (câblé, attendu 1.0).

      INDETERMINE_HARNAIS     l'oracle rate (< `oracle_min`) ou la référence touche trop haut
                              (> `reference_max`) : la DV ne lit pas ce qu'on croit, on ne lit rien.
      LEARNER_INERT           l'apprenant finit à moins de `min_sep` au-dessus de la référence.
      LEARNER_LEARNS          au-dessus de la barre. `onset` date l'apprentissage : "during_run" si le
                              gain intra-run >= `min_gain`, "early" sinon (appris dans le premier bloc).

    ⚠️ Le gain intra-run ne DÉCIDE pas : une cohorte FRAÎCHE appariée par seed à sa référence lr=0
    (mêmes génomes initiaux) ne peut être au-dessus de la barre que parce qu'elle a appris. Règle
    corrigée le 2026-09-14 après le seed 1/12 du run P1.6 (lr=0,004 à 0,32 dès le premier bloc contre
    0,15 pour lr=0) ; la version d'origine rendait « INDETERMINATE » dans ce cas — dit ici, pas caché.

    Toute entrée absente ou non finie LÈVE : une donnée manquante ne devient jamais un verdict."""
    vals = {"learner_first": learner_first, "learner_last": learner_last,
            "reference_last": reference_last, "oracle_last": oracle_last}
    for k, v in vals.items():
        if v is None or not np.isfinite(float(v)):
            raise ValueError(
                f"learner_verdict : {k}={v!r} -- entree absente ou non finie, aucun verdict possible ; "
                "ne pas confondre avec une mesure nulle OBSERVEE.")
    lf, ll = float(learner_first), float(learner_last)
    rl, ol = float(reference_last), float(oracle_last)
    sep, gain, bar = ll - rl, ll - lf, rl + float(min_sep)
    out = {"learner_first": lf, "learner_last": ll, "reference_last": rl, "oracle_last": ol,
           "sep": sep, "gain": gain, "bar": bar, "min_sep": float(min_sep), "min_gain": float(min_gain)}
    if ol < float(oracle_min):
        out.update(verdict="INDETERMINE_HARNAIS",
                   why=f"oracle {ol:.3f} < {oracle_min} : le controle positif de la DV echoue")
    elif rl > float(reference_max):
        out.update(verdict="INDETERMINE_HARNAIS",
                   why=f"reference lr=0 {rl:.3f} > {reference_max} : le bras qui ne peut rien apprendre "
                       "touche trop haut, la DV ne lit pas l'apprentissage")
    elif sep <= float(min_sep):
        out.update(verdict="LEARNER_INERT", why=f"sep {sep:.3f} <= {min_sep} au-dessus de la reference")
    elif gain >= float(min_gain):
        out.update(verdict="LEARNER_LEARNS", onset="during_run",
                   why=f"sep {sep:.3f} au-dessus de la reference, gain {gain:.3f} pendant le run")
    else:
        out.update(verdict="LEARNER_LEARNS", onset="early",
                   why=f"sep {sep:.3f} au-dessus de la reference, gain {gain:.3f} < {min_gain} : "
                       "appris dans le premier bloc")
    return out


def main():
    seed = int(os.environ.get("CDI_SEED", "2026"))
    K = int(os.environ.get("CDI_K", "12"))
    num_agents = int(os.environ.get("CDI_AGENTS", "12"))
    max_ticks = int(os.environ.get("CDI_TICKS", "200"))
    metab = float(os.environ.get("CDI_METAB", "4.0"))
    cog = float(os.environ.get("CDI_COG", "6.0"))
    m = run_cog_demand_map(seed, K, num_agents, max_ticks, metab, cog)
    print(f"\n=== S2-009 — recette cognitive IN-WORLD (oracle, seed={seed}, K={K}, metab={metab}, cog={cog}) ===")
    print(f"{'mode':6s} {'ratio':>7s}  verdict")
    for mode in ("on", "off"):
        r = m[mode]
        print(f"{mode:6s} {r['ratio']:7.2f}  {r['verdict']} (n={r['n']})")
    print("\nAttendu : ON=PERCEPTION_DEMANDED (ratio>>1, le monde exige la perception) / OFF=NEUTRAL "
          "(ratio~1) -> la recette S2-006 flip la survie IN-WORLD. -> Rédiger EDR-S2-009.")
    return m


if __name__ == "__main__":
    main()
