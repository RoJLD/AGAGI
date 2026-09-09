"""P4.1-MECANISME -- par quel CANAL le grab coute-t-il 39 % de survie ?

`EDR-GRAB-COST` a etabli QUE retirer le grab ameliore la survie mediane de +39 % (28+/2-,
sign p = 8.7e-07, 30 eres appariees), sur un instrument dont le plancher de bruit est mesure
EXACTEMENT NUL. Il declare le MECANISME ouvert, et nomme les deux mesures manquantes : le taux de
grab in situ et `trace_energy_sinks`. Ce module les fait, toutes les deux.

Ce que le CODE dit avant toute simulation -- et qui rend l'hypothese falsifiable :

  * DEPENSES du grab, toutes lisibles a l'oeil : `-1.0` par ramassage reussi ; `-2.0` par debordement
    LIFO quand l'inventaire est plein (plus `last_env_surprise = 0.5`, qui remonte `surprise_scale`
    donc le `brain_cost`) ; et surtout la taxe de PORTAGE `carry_weight * 0.5` payee A CHAQUE TICK,
    pour toujours (`world_1_stoneage.py:_resolve_biology`).
  * REVENU du grab, un seul chemin, et il est ETROIT : le moteur rend `+20` a `inventory[0]` si son
    type est `Fruit` et si `energy < 80`. Or `FamineWorld.step()` REBAPTISE tout Fruit d'inventaire en
    `_FruitReserve` AVANT `super().step()`. Un fruit detenu depuis un tick anterieur est donc masque :
    le `+20` ne peut concerner qu'un fruit ramasse DANS LE TICK COURANT et pose en position 0 --
    c'est-a-dire seulement si l'inventaire etait VIDE au moment du ramassage.
  * REVENU de la CHASSE : `+prey_reward` directement sur `energy`, sans jamais passer par l'inventaire
    (`world_1_stoneage.py:800-824`). La chasse est donc INDIFFERENTE au grab.

D'ou trois predictions distinctes, chacune refutable par une observable de ce module :

  H1 PORTAGE    -- le poste `carry` du bilan energetique est nettement plus lourd a l'intact.
  H2 ETRANGLEMENT -- la fraction de ticks a inventaire VIDE (seul etat ou un grab peut nourrir) est
                   faible a l'intact : le revenu du grab est structurellement inaccessible.
  H3 DEBORDEMENT -- l'inventaire est SATURE la plupart du temps a l'intact -> `-2.0` par tick.

⚠️ CE QUE CE MODULE NE PEUT PAS FAIRE, et qui est declare et non contourne. Les deux bras DIVERGENT
dynamiquement des le premier tick : le decompte par poste decrit OU l'energie est passee dans chaque
bras, ce n'est PAS une partition causale du differentiel. On peut donc nommer le canal DOMINANT ; on
ne peut pas attribuer les 39 % a un poste au pourcentage pres. Le dire est le seul moyen de ne pas
transformer une description en attribution.

⚠️ ANCRAGE (E19 occ. 6). Ce module refait la boucle de `run_condition` pour pouvoir observer le monde
que celle-ci jette. Une boucle refaite est un INSTRUMENT NEUF : `anchor_against_run_condition` exige
qu'elle rende la survie EXACTEMENT egale a celle de l'originale avant qu'on lise le moindre bilan.
Sans cet ancrage, un decompte parfaitement coherent pourrait decrire un autre monde que le record.

Usage : python tools/grab_mechanism_probe.py    (env GRABM_SEEDS, GRABM_ERAS, GRABM_AGENTS,
GRABM_TICKS ; defauts = smoke. Le run publie du record est GRABM_ERAS=10.)
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.mamba_agent import MambaAgent, MambaBatchModel
from src.environments.config import WorldConfig
from src.seed_ai.harness import seed_at
from src.seed_ai.persistence import calculate_life_score
from src.worlds.world_famine import FamineWorld
from tools.experiment_preflight import assert_no_aliasing, assert_not_degenerate
from tools.s2_demand_ablation import _GRAB_LOGIT, GrabOffMamba, NullGrabOffMamba

_PHASES = ("brain", "action", "biologie", "mouvement")
_SINKS = ("metab", "terrain", "carry", "autres")


class GrabCensusMamba(MambaBatchModel):
    """OBSERVATEUR PUR de la colonne du grab -- il compte, il ne change rien.

    Meme forme que `NullGrabOffMamba` (copie, garde d'aliasing, reecriture de la valeur lue), donc
    BIT-IDENTIQUE au bras intact et sans consommation de tirage RNG. C'est ce qui autorise a lire son
    taux de grab comme celui du champion INTACT et non comme celui d'un bras perturbe.

    Le compteur est un attribut de CLASSE parce que le moteur reconstruit le modele a chaque tick
    (`world_1_stoneage.py:1050`) : un attribut d'instance mourrait avec le tick. Un compteur global
    est un etat partage, donc un risque d'artefact (classe E5) -- il est remis a zero explicitement
    par `reset_census()` et confronte a une reponse connue par `calibrate_census()`.
    """

    _n_ticks_agents = 0        # agent-ticks observes
    _n_attempts = 0            # agent-ticks ou do_grab > 0 (le seuil que le monde applique)

    @classmethod
    def reset_census(cls):
        cls._n_ticks_agents = 0
        cls._n_attempts = 0

    @classmethod
    def attempt_rate(cls):
        """Taux de TENTATIVE de grab. None si rien n'a ete observe -- surtout PAS 0.0 : une absence
        de donnee n'est pas un taux nul, et ce depot a paye une trentaine de fois ce glissement."""
        if cls._n_ticks_agents == 0:
            return None
        return cls._n_attempts / cls._n_ticks_agents

    def forward(self, batch_obs, env_surprise_batch=None):
        preds, spent = super().forward(batch_obs, env_surprise_batch)
        arr = np.asarray(preds)
        if arr.size and arr.ndim == 2 and arr.shape[1] > _GRAB_LOGIT:
            arr = arr.copy()
            assert_no_aliasing(arr, preds, label="sortie de GrabCensusMamba")
            col = arr[:, _GRAB_LOGIT]
            type(self)._n_ticks_agents += int(col.shape[0])
            type(self)._n_attempts += int(np.count_nonzero(col > 0))
            arr[:, _GRAB_LOGIT] = col              # meme ecriture, valeur INCHANGEE -> bit-identique
            return arr, spent
        return preds, spent


class GrabCensusWorld(FamineWorld):
    """FamineWorld + recensement de l'INVENTAIRE, sans toucher a une seule mecanique.

    Le recensement est pris au DEBUT du tick, avant que `FamineWorld.step()` ne rebaptise les Fruits
    en `_FruitReserve` -- c'est-a-dire dans l'etat que le moteur va voir. `inv_vide` est l'observable
    qui decide H2 : c'est le SEUL etat d'inventaire dans lequel un fruit ramasse peut atterrir en
    position 0 et donc nourrir.
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.census = {"agent_ticks": 0, "inv_vide": 0, "inv_plein": 0,
                       "inv_taille": 0.0, "tete_fruit": 0,
                       # recensement AU POINT DE FACTURATION (voir `_resolve_biology` ci-dessous)
                       "bio_ticks": 0, "carry_poids": 0.0, "repas_fruit": 0, "inv_taille_bio": 0.0,
                       "cache_consomme": 0,
                       # ⚠️ LE COMPTE QUI TRANCHE entre un fait sur la POLITIQUE et un fait sur le
                       # MONDE. WARM-008 avait deja borne sa propre portee ainsi : son banc
                       # « n'engendre AUCUN item de type Fruit », donc « grab nuit » y etait
                       # quasi-tautologique. Sans ces deux compteurs, « le champion ne porte aucun
                       # aliment » serait indiscernable de « il n'y a aucun aliment a porter ».
                       "fruits_monde": 0, "fruits_sous_le_pied": 0}
        # Histogramme des types PORTES, releve au point de facturation. Sans lui, « le grab n'a aucun
        # revenu » reposerait sur `tete_fruit`, qui ne regarde que l'indice 0 : une absence de donnee
        # promue en affirmation NEGATIVE, le biais systematique que ce depot traque chez ses sondes.
        self.types_portes = {}

    def _auto_consume_cache(self, agent):
        """SECOND chemin de revenu, propre a FamineWorld -- et celui que la premiere version de cette
        sonde ne regardait pas. Sous `starve_threshold`, un Fruit d'inventaire rend
        `max(5, 25 - 0.1 x age)`. Le compter est indispensable : le moteur stoneage et FamineWorld
        n'ont pas le meme revenu, et n'en retenir qu'un fabriquerait un zero d'INSTRUMENT."""
        pris = super()._auto_consume_cache(agent)
        if pris:
            self.census["cache_consomme"] += 1
        return pris

    def _resolve_biology(self, agent, action, logits):
        """Recensement AU MOMENT OU LE MOTEUR FACTURE, et non au debut du tick.

        ⚠️ Defaut mesure sur la premiere version de cette sonde, et conserve ici comme raison d'etre :
        recense en tete de `step()`, l'inventaire moyen valait 0,35 tandis que le poste `carry`
        impliquait un poids porte de 1,28 -- un facteur 3,7 inexplique. La cause est un decalage de
        MOMENT : le grab a lieu APRES le debut du tick et AVANT la biologie, donc le moteur taxe un
        inventaire que le recensement de tete ne voit pas. Un bilan qui ne boucle pas ne se publie pas.

        `repas_fruit` reproduit la condition EXACTE du moteur (`inventory[0]` de type `Fruit` et
        `energy < 80`) juste avant de la lui laisser appliquer -- c'est le seul revenu que le grab
        puisse produire, et le compter est la seule facon de ne pas l'inferer d'un residu."""
        inv = agent["inventory"]
        c = self.census
        c["bio_ticks"] += 1
        c["inv_taille_bio"] += len(inv)
        c["carry_poids"] += sum(i.get("weight", 1.0) if isinstance(i, dict) else 1.0 for i in inv)
        for it in inv:
            t = it.get("type", "?") if isinstance(it, dict) else str(it)
            self.types_portes[t] = self.types_portes.get(t, 0) + 1
        nourrit = (bool(inv) and isinstance(inv[0], dict)
                   and inv[0].get("type") == "Fruit" and agent["energy"] < 80)
        super()._resolve_biology(agent, action, logits)
        if nourrit:
            c["repas_fruit"] += 1

    def step(self):
        c = self.census
        # Fruits PRESENTS dans le monde, et fruits ACCESSIBLES (sur la case meme d'un agent) : le
        # second est le nombre d'occasions de ramassage nourrissant que la politique a EUES.
        fruits = [i for i in self.items if isinstance(i, dict) and i.get("type") == "Fruit"]
        c["fruits_monde"] += len(fruits)
        cases = {(i["x"], i["y"], i.get("z", 0)) for i in fruits}
        for a in self.agents:
            if (a["x"], a["y"], a.get("z", 0)) in cases:
                c["fruits_sous_le_pied"] += 1
        for a in self.agents:
            inv = a["inventory"]
            c["agent_ticks"] += 1
            c["inv_taille"] += len(inv)
            if not inv:
                c["inv_vide"] += 1
            if len(inv) >= a["inv_capacity"]:
                c["inv_plein"] += 1
            # ⚠️ PAS un `elif` : la premiere version rangeait `tete_fruit` derriere `inv_plein`, donc
            # un inventaire plein a tete-fruit n'etait jamais compte -- une troncature SILENCIEUSE,
            # la forme (c) des trois que la dette de calibration a revelees.
            if inv and isinstance(inv[0], dict) and inv[0].get("type") == "Fruit":
                c["tete_fruit"] += 1
        super().step()


def _trace_config():
    """WorldConfig par DEFAUT + `trace_energy_sinks` seul modifie.

    ⚠️ Le record annonce `forage_payoff = 3.0` ; la valeur reellement en vigueur dans le run P4.1 est
    le DEFAUT 1.0, parce que `run_condition` construit le monde avec `config=None`. On reproduit donc
    le regime MESURE, pas le regime annonce -- et c'est cette fonction qui le rend verifiable."""
    cfg = WorldConfig()
    cfg.trace_energy_sinks = True
    return cfg


def _harvest(env):
    """Somme les postes energetiques sur TOUS les agents de l'ere -- morts ET survivants censures.

    Ne garder que les vivants biaiserait vers les agents qui ont peu depense ; ne garder que les morts
    biaiserait dans l'autre sens. Le bilan d'une ere est celui de sa cohorte entiere."""
    phases = dict.fromkeys(_PHASES, 0.0)
    sinks = dict.fromkeys(_SINKS, 0.0)
    n = 0
    for a in list(env.agents) + list(getattr(env, "dead_agents", [])):
        n += 1
        for k, v in a.get("_e_phases", {}).items():
            if k in phases:
                phases[k] += float(v)
        for k, v in a.get("_e_bio", {}).items():
            if k in sinks:
                sinks[k] += float(v)
    return phases, sinks, n


def run_census_arm(batch_model_cls, genome, seed, num_agents=20, max_ticks=400, n_eras=1,
                   current_era=10_000):
    """Une ere-serie sous UNE condition, avec recensement. Miroir EXACT de `run_condition` pour tout
    ce qui touche la simulation (meme ordre de seed, memes reglages de banc, meme arret du
    retriever) -- l'ancrage le verifie plutot que de le supposer.

    GARDE D'ARGUMENTS EN TETE, avant toute construction de monde : un argument degenere est une erreur
    d'APPEL, et sans elle l'aval lirait un 0.0 comme une mesure."""
    if int(num_agents) <= 0 or int(max_ticks) <= 0 or int(n_eras) <= 0:
        raise ValueError(
            f"run_census_arm : argument degenere (num_agents={num_agents}, max_ticks={max_ticks}, "
            f"n_eras={n_eras}) -- aucune mesure possible ; ne pas confondre avec une mesure nulle OBSERVEE.")

    survival, era_survival = [], []
    phases = dict.fromkeys(_PHASES, 0.0)
    sinks = dict.fromkeys(_SINKS, 0.0)
    census = {"agent_ticks": 0, "inv_vide": 0, "inv_plein": 0, "inv_taille": 0.0, "tete_fruit": 0,
              "bio_ticks": 0, "carry_poids": 0.0, "repas_fruit": 0, "inv_taille_bio": 0.0,
              "cache_consomme": 0, "fruits_monde": 0, "fruits_sous_le_pied": 0}
    types_portes = {}
    n_agents_total = 0

    for i in range(int(n_eras)):
        seed_at(seed, i)
        env = GrabCensusWorld(_trace_config())
        env.benchmark_mode = True
        env.night_enabled = False
        # `current_era` pilote l'ANNELAGE des scaffolds. Le banc (`run_condition`) pose 10_000 ->
        # `anneal` vaut 0.0, donc la prime de ramassage `scaffold_grab` vaut EXACTEMENT ZERO -- alors
        # qu'elle valait ~0.967 pendant les premieres eres ou le champion a evolue. Le laisser
        # REGLABLE est ce qui permet de tester si le verdict est un fait sur le MONDE ou sur la
        # convention du BANC ; le defaut reproduit le banc, donc le record.
        env.current_era = int(current_era)
        if batch_model_cls is not None:
            env.batch_model_cls = batch_model_cls
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()
        for _ in range(num_agents):
            a = MambaAgent()
            if genome is not None:
                a.from_genome(genome)
            env.add_agent(a, energy=80.0)
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        era_ages = [int(a["age"]) for a in list(env.agents) + list(getattr(env, "dead_agents", []))]
        survival.extend(era_ages)
        era_survival.append(float(np.median(era_ages)) if era_ages else 0.0)
        ph, sk, n = _harvest(env)
        for k in _PHASES:
            phases[k] += ph[k]
        for k in _SINKS:
            sinks[k] += sk[k]
        n_agents_total += n
        for k in census:
            census[k] += env.census[k]
        for t, v in env.types_portes.items():
            types_portes[t] = types_portes.get(t, 0) + v
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()

    at = max(1, census["agent_ticks"])
    bt = max(1, census["bio_ticks"])
    # IDENTITE COMPTABLE -- la calibration de ce recensement contre le MOTEUR lui-meme. Le moteur
    # facture exactement `carry_weight * 0.5` entre `_s3_bio` et `_s4_bio` ; si le poids que l'on
    # recense au meme instant ne reproduit pas ce poste, on ne recense pas ce que le moteur taxe, et
    # aucune attribution de canal n'est lisible. On PUBLIE l'ecart plutot que de le supposer nul.
    carry_attendu = census["carry_poids"] * 0.5
    ecart = abs(sinks["carry"] - carry_attendu) / max(1e-12, abs(carry_attendu)) if carry_attendu else (
        0.0 if abs(sinks["carry"]) < 1e-9 else 1.0)
    return {
        "survival": survival,
        "era_survival": era_survival,
        "bouclage_carry": ecart,          # 0.0 attendu : le poste `carry` EST 0.5 x le poids recense
        "bio_ticks": census["bio_ticks"],
        "carry_poids_moy": census["carry_poids"] / bt,
        "inv_taille_bio": census["inv_taille_bio"] / bt,
        "repas_fruit": census["repas_fruit"],
        "repas_fruit_frac": census["repas_fruit"] / bt,
        "cache_consomme": census["cache_consomme"],
        "fruits_monde_moy": census["fruits_monde"] / max(1, census["agent_ticks"]),
        "fruits_sous_le_pied": census["fruits_sous_le_pied"],
        "occasions_par_tick": census["fruits_sous_le_pied"] / at,
        # `types_portes` recense les DEUX chemins de revenu possibles a la fois : un `Fruit` porte est
        # une reserve exploitable, tout le reste est du poids mort. C'est ce qui permet de dire « le
        # grab n'a pas de revenu » sans le DEDUIRE d'une absence.
        "types_portes": dict(sorted(types_portes.items(), key=lambda kv: -kv[1])),
        # postes NORMALISES par agent-tick : comparer des totaux entre bras de durees differentes
        # ferait passer « le bras qui vit deux fois plus longtemps » pour « le bras qui depense deux
        # fois plus ». C'est le meme piege que la pseudo-replication, applique a l'energie.
        "phases_par_tick": {k: phases[k] / at for k in _PHASES},
        "sinks_par_tick": {k: sinks[k] / at for k in _SINKS},
        "phases_total": phases,
        "sinks_total": sinks,
        "agent_ticks": census["agent_ticks"],
        "n_agents": n_agents_total,
        "inv_vide_frac": census["inv_vide"] / at,
        "inv_plein_frac": census["inv_plein"] / at,
        "inv_taille_moy": census["inv_taille"] / at,
        "tete_fruit_frac": census["tete_fruit"] / at,
    }


def anchor_against_run_condition(genome, seed, num_agents=8, max_ticks=120, n_eras=1):
    """ANCRAGE OBLIGATOIRE : la boucle refaite doit rendre la survie EXACTEMENT egale a celle de
    `run_condition`, l'instrument deja audite qui a produit le record.

    Un ecart, meme d'un tick, signifie que le monde recense n'est pas le monde mesure -- et alors
    aucun bilan energetique n'est lisible, si coherent soit-il. Renvoie (identique, mien, reference).

    ⚠️ La comparaison se fait sur `run_condition(FamineWorld, ...)` -- le monde du record -- contre
    `GrabCensusWorld`, qui n'ajoute qu'un comptage. Le `trace_energy_sinks` du bras recense ecrit des
    cles supplementaires sur les agents mais ne touche AUCUN bilan : si c'etait faux, l'ancrage
    echouerait, ce qui est precisement sa fonction."""
    from tools.s2_demand import run_condition
    ref = run_condition(FamineWorld, None, genome, seed,
                        num_agents=num_agents, max_ticks=max_ticks, n_eras=n_eras)
    mine = run_census_arm(None, genome, seed,
                          num_agents=num_agents, max_ticks=max_ticks, n_eras=n_eras)
    return mine["survival"] == ref["survival"], mine["survival"], ref["survival"]


def calibrate_census(n_agents=6, n_ticks=5, taux_impose=0.5):
    """CALIBRATION A DOSE CONNUE du compteur de tentatives, sans simuler un seul monde.

    On impose une colonne 24 dont la fraction de positifs est CONNUE, et on exige que le compteur la
    retrouve. C'est la technique d'injection pour orchestrateurs : elle teste la couche qui transforme
    des observations en taux (accumulation, remise a zero, unite de comptage) a cout nul. Renvoie
    (mesure, attendu)."""
    GrabCensusMamba.reset_census()
    k = int(round(taux_impose * n_agents))
    for _ in range(n_ticks):
        col = np.array([1.0] * k + [-1.0] * (n_agents - k))
        GrabCensusMamba._n_ticks_agents += n_agents
        GrabCensusMamba._n_attempts += int(np.count_nonzero(col > 0))
    mesure = GrabCensusMamba.attempt_rate()
    GrabCensusMamba.reset_census()
    return mesure, k / n_agents


def _fmt(d):
    return "  ".join(f"{k}={v:+.4f}" for k, v in d.items())


def main():
    import json
    import pickle

    from tools.jobs.run import hold

    seeds = [int(s) for s in os.environ.get("GRABM_SEEDS", "42,43,44").split(",")]
    n_eras = int(os.environ.get("GRABM_ERAS", "2"))
    num_agents = int(os.environ.get("GRABM_AGENTS", "20"))
    max_ticks = int(os.environ.get("GRABM_TICKS", "400"))
    current_era = int(os.environ.get("GRABM_ERA", "10000"))

    # --- PRE-VOL, avant toute simulation -------------------------------------------------------
    mesure, attendu = calibrate_census()
    print(f"[pre-vol] compteur a dose connue : mesure={mesure} attendu={attendu}")
    assert mesure == attendu, "le compteur de tentatives ne retrouve pas une dose CONNUE"

    # `pickle` : Hall-of-Fame produits LOCALEMENT par les runs d'evolution de ce depot (juillet 2026),
    # charges de la meme facon par `tools/s2_demand.py`. Aucune donnee non fiable n'est deserialisee.
    genomes = {}
    for s in seeds:
        p = f"data/hof_famine_harsh_s{s}.pkl"
        with open(p, "rb") as fh:
            genomes[s] = pickle.load(fh)["entries"][0].genome

    out = {"regime": {"forage_payoff": _trace_config().forage_payoff,
                      "base_metabolism": _trace_config().base_metabolism,
                      "n_eras": n_eras, "num_agents": num_agents, "max_ticks": max_ticks,
                      "current_era": current_era, "scaffold_grab_effectif": None},
           "ancrage": {}, "bras": {}}

    from src.worlds.world_1_stoneage import anneal
    _w = FamineWorld()
    out["regime"]["scaffold_grab_effectif"] = float(
        _w.scaffold_grab * anneal(current_era, _w.scaffold_eras))
    print(f"[regime] current_era={current_era} -> prime de ramassage EFFECTIVE = "
          f"{out['regime']['scaffold_grab_effectif']:.4f}")

    with hold("kuzu", owner="grab-mechanism"):
        ok, mien, ref = anchor_against_run_condition(genomes[seeds[0]], seeds[0])
        out["ancrage"] = {"identique": bool(ok), "n": len(ref)}
        print(f"[ancrage] boucle recensee == run_condition : {ok}  (n={len(ref)})")
        if not ok:
            print("  ARRET : le monde recense n'est pas le monde mesure -- aucun bilan n'est lisible.")
            print(f"  mien={mien[:8]}\n  ref ={ref[:8]}")
            return

        for nom, cls in (("intact", GrabCensusMamba), ("grab_off", GrabOffMamba)):
            GrabCensusMamba.reset_census()
            agg = None
            for s in seeds:
                r = run_census_arm(cls, genomes[s], s, num_agents=num_agents,
                                   max_ticks=max_ticks, n_eras=n_eras, current_era=current_era)
                if agg is None:
                    agg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in r.items()}
                    agg["_n"] = 1
                else:
                    for k, v in r.items():
                        if isinstance(v, dict):
                            # `.get(kk, 0)` et non `agg[k][kk] += ...` : un seed peut faire porter un
                            # type absent du premier seed. La forme naive leverait KeyError -- ou pire,
                            # sur un `defaultdict`, avalerait le type en silence.
                            for kk in v:
                                agg[k][kk] = agg[k].get(kk, 0) + v[kk]
                        elif isinstance(v, list):
                            agg[k] = agg[k] + v
                        else:
                            agg[k] += v
                    agg["_n"] += 1
            n = agg.pop("_n")
            for k in ("phases_par_tick", "sinks_par_tick"):
                agg[k] = {kk: vv / n for kk, vv in agg[k].items()}
            agg["types_portes"] = dict(sorted(agg["types_portes"].items(), key=lambda kv: -kv[1]))
            for k in ("inv_vide_frac", "inv_plein_frac", "inv_taille_moy", "tete_fruit_frac",
                      "bouclage_carry", "carry_poids_moy", "inv_taille_bio", "repas_fruit_frac",
                      "fruits_monde_moy", "occasions_par_tick"):
                agg[k] /= n
            agg["taux_grab"] = GrabCensusMamba.attempt_rate() if cls is GrabCensusMamba else None
            assert_not_degenerate(agg["survival"], label=f"survie {nom}")
            assert agg["bouclage_carry"] < 1e-9, (
                f"le recensement ne reproduit PAS le poste `carry` du moteur (ecart relatif "
                f"{agg['bouclage_carry']:.3e}) -- aucune attribution de canal n'est lisible")
            out["bras"][nom] = agg
            print(f"\n=== {nom} ===  survie mediane={np.median(agg['survival']):.2f}  "
                  f"agent-ticks={agg['agent_ticks']}  bio-ticks={agg['bio_ticks']}")
            print(f"  taux de grab in situ : {agg['taux_grab']}")
            print(f"  postes/tick   {_fmt(agg['phases_par_tick'])}")
            print(f"  biologie/tick {_fmt(agg['sinks_par_tick'])}")
            print(f"  bouclage carry (ecart relatif au moteur) : {agg['bouclage_carry']:.2e}")
            print(f"  inventaire    vide={agg['inv_vide_frac']:.3f}  plein={agg['inv_plein_frac']:.3f}  "
                  f"taille(tete)={agg['inv_taille_moy']:.2f}  taille(facture)={agg['inv_taille_bio']:.2f}  "
                  f"poids(facture)={agg['carry_poids_moy']:.3f}  tete_fruit={agg['tete_fruit_frac']:.4f}")
            print(f"  REVENU du grab : {agg['repas_fruit']} repas-fruit (moteur, +20) + "
                  f"{agg['cache_consomme']} consommations de cache (famine, +5 a +25)")
            print(f"  types portes  : {agg['types_portes'] or 'AUCUN'}")
            print(f"  OFFRE du monde : {agg['fruits_monde_moy']:.2f} fruits presents / tick  |  "
                  f"{agg['fruits_sous_le_pied']} occasions SOUS LE PIED "
                  f"({agg['occasions_par_tick']:.4f} / agent-tick)")

    os.makedirs("results", exist_ok=True)
    suffixe = "" if current_era == 10000 else f"_era{current_era}"
    with open(f"results/p41_grab_mechanism{suffixe}.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    # ⚠️ Cette ligne annoncait `p41_grab_mechanism.json` en dur pendant que le `open()` ci-dessus
    # ecrivait `_era1.json` : une reecriture programmatique dont la 7e substitution etait la seule
    # sans assertion, et elle a echoue EN SILENCE. Le fichier etait bon, le rapport faux -- exactement
    # la forme d'E22, appliquee a un chemin de sortie. Une substitution sans assert est un no-op muet.
    print(f"\n-> results/p41_grab_mechanism{suffixe}.json")


if __name__ == "__main__":
    main()
