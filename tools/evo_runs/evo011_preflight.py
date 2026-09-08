#!/usr/bin/env python
"""EVO-011 PRE-VOL DECISIF -- runner des TROIS bras (TEMOIN / LECTEUR / BROUILLE).

Regle SCELLEE : `docs/preregistrations/EVO-011-PREVOL.json`. Ce runner appelle `verify()` AVANT toute
lecture de resultat, et re-verifie que les seuils codes ici sont bien ceux du sceau
(`_assert_rule_matches_code`) -- une regle scellee qu'on n'applique pas est une regle absente (E11).

QUESTION : un LECTEUR CABLE A LA MAIN du canal de type `obs[4]` survit-il MIEUX in-world qu'un TEMOIN
identique sans l'arete ? Chaine REELLE scellee (la chaine kill est COUPEE PAR CONSTRUCTION, E2 occ.3) :

    obs[4] -> logits[8] > 0 -> lancer -> la proie passe `stunned` -> `_move_preys` fait `continue`
    (ni deplacement NI RIPOSTE) -> l'agent marche dessus -> melee SANS riposte.

⚠️ CE QUE LA REVUE ADVERSARIALE A MESURE SUR CETTE CHAINE (v2, cf. `notes`) : le dernier maillon
(« melee SANS riposte ») est QUANTITATIVEMENT NEGLIGEABLE dans ce banc -- la diagonale reflexe +10
que le sceau impose aux TROIS bras porte `phenotype_hp_bonus` a 1220, donc hp = 1320, contre une
riposte de 50 (3.8 %). Les agents ne meurent PAS de riposte, ils meurent de FAIM (drain 18.2/tick).
Le maillon qui porte reellement l'effet est le PRECEDENT : `stunned > 0` -> la proie ne se DEPLACE
plus -> elle est rattrapable. Le runner MESURE les deux (riposte encaissee, cause de mort, type des
proies etourdies) au lieu de les inferer : « une chaine causale transporte son signe, pas son
amplitude » (CLAUDE.md). Cela ne change AUCUN seuil du sceau ; cela change ce que le record pourra
affirmer si le lecteur paie.

--------------------------------------------------------------------------------------------------
CE QUE LE HARNAIS AJOUTE AU MONDE, ET POURQUOI (tout est IDENTIQUE dans les trois bras)
--------------------------------------------------------------------------------------------------
1. `_equip` : le gate `len(inventory) > 0` (world_1_stoneage.py:1404) est une LOI PHYSIQUE -- on ne la
   leve pas, on RE-EQUIPE. Une lance {'type':'Spear','weight':0.5} est remise en TETE d'inventaire
   (a) au debut du tick (pour le lancer) et (b) juste avant `_resolve_biology` (pour la melee, qui est
   resolue APRES le lancer dans le meme tick : sans (b), lancer DESARME l'agent pour sa propre melee --
   50 degats -> 10 -- et le bras LECTEUR paierait un cout que la regle n'a pas scelle).
   `weight=0.5` -> damage = 10*0.5 = 5 -> `stunned = int(damage*2) = 10` ticks.
   ⚠️ Ce meme `_equip` est ce qui neutralise le confond nomme par la revue (« le lanceur porte moins
   de poids ») : `_resolve_biology` facture `carry_weight * 0.5` JUSTE APRES le re-equipement, donc le
   lanceur et le temoin paient le meme port. Ce n'est plus une inference : controle (vii), le port
   est MESURE dans les trois bras, au point exact ou le monde le facture, ET A AGE APPARIE (le port
   cumule est downstream de la duree de vie -- comparer les moyennes de vie entiere reviendrait a
   tester la DV avec elle-meme). Mesure : 0.583 / 0.542 / 0.533 (n=120/bras), ecart 0.050 de poids =
   0.025 energie/tick = 0.14 % du drain metabolique 18.2. Le confond EXISTE et va CONTRE le lecteur
   (il porte moins, donc il est legerement avantage) mais il est ~50x trop petit pour porter l'effet.
2. BALLAST (defaut ON, `--no-ballast` pour la lecture litterale) : `phenotype_hp_bonus` et
   `phenotype_energy_drain` sont calcules a partir de `sum|W[0:5]|` (mamba_agent.py:47-50). L'arete
   du LECTEUR est en LIGNE 4 -> sans compensation, cabler l'arete donne AUSSI +80 hp et +0.8 de drain
   metabolique au LECTEUR : le contraste ne mesurerait plus SEULEMENT la lecture. Le TEMOIN recoit
   donc une arete de MEME norme vers un noeud CACHE sans arete sortante (inerte : sa colonne n'est lue
   par personne). `logits[8]` reste 0 EXACTEMENT dans le TEMOIN.
   Le phenotype est desormais releve SUR L'AGENT VIVANT (`model.phenotype_*`), pas recalcule a cote :
   un instrument se mesure la ou il agit.
3. Diagonale reflexe +10 dans LES TROIS bras (scelle) : le confond E6 (derive d'etat) est neutralise
   par construction, pas mesure.
4. GEL DE LA PLASTICITE INTRA-VIE. `Biosphere3D.step` appelle `batch_model.compute_policy_gradient(...)`
   A CHAQUE TICK (world_1_stoneage.py:1734), qui fait `genome.W = clip(W + dW, -5, +5)`
   (mamba_agent.py:913-915). MESURE : l'arete du LECTEUR passait de 8.0 a 5.0 (et la diagonale reflexe
   de 10 a 5). Sans ce gel le controle (ii) ECHOUE toujours et aucun verdict n'est atteignable.
   `--no-freeze` reproduit le defaut.

Unite de replication : le SEED (les 24 agents d'un bras-seed sont des clones partageant le monde).

CONTROLES HORS SCEAU AJOUTES PAR LA REVUE (declares comme tels dans la sortie et dans le record ;
ils ne peuvent que rendre le verdict PLUS conservateur, jamais plus permissif) :
  (i+)   IDENTITE DE DECISION : la somme des decisions LUES au seam batch egale EXACTEMENT le nombre
         de `throw_decided` incrementes par le monde. Sans elle, « in situ » n'est qu'une intention.
  (i-bis) BROUILLAGE EFFICACE : chez BROUILLE, P(throw | valeur VUE) doit rester ~1/0. Sinon un bras
         « brouille » pourrait n'etre qu'un lecteur casse -- meme chiffre, autre monde.
  (vii)  CONFOND MECANIQUE : port (`carry_weight`) egal entre bras A AGE APPARIE, evalue en ENERGIE
         (fraction du drain metabolique) -- un ecart de poids n'est un confond que s'il pese sur le
         bilan qui tue reellement les agents. Le phenotype est verifie IN SITU (ii-bis).
  (viii) MONDE INITIAL IDENTIQUE : empreinte du monde + etat du RNG global BIT-IDENTIQUES a t=0.

Usage :  python evo011_preflight.py --smoke          # 1 seed, 3 bras, sous bail, chronometre
         python evo011_preflight.py --seeds 12       # plan complet (NE PAS lancer sans decision)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import math
import statistics
import sys
import time

import numpy as np

PREREG = "EVO-011-PREVOL-bis"

# --------------------------------------------------------------------------------------------------
# CONSTANTES DE CABLAGE -- toutes verifiees contre le monde (src/worlds/world_1_stoneage.py)
# --------------------------------------------------------------------------------------------------
N_NODES, N_IN, N_OUT = 172, 59, 108
OUT0 = N_NODES - N_OUT                 # 64 : premiere colonne du bloc de SORTIE
TYPE_COL = 4                           # obs[4] = on_apex_type : +1 Mammouth, 0.5 Ours, -1 Leurre (dist <= 1)
DIST_COLS = (0, 1, 2, 3)               # obs[0..3] = dn, ds, de, dw (distance /size, >= 0)
THROW_IDX = 8                          # `do_throw = float(logits[8]) > 0`            (:1321)
AIM_X_IDX, AIM_Y_IDX = 11, 12          # `aim_vec = [logits[11], logits[12]]`         (:1322)
ACT_N, ACT_S, ACT_E, ACT_W = 0, 1, 2, 3  # 0: ny-1 (Nord), 1: ny+1 (Sud), 2: nx+1 (Est), 3: nx-1 (Ouest)
REFLEX_DIAG = 10.0                     # delta = sigmoid(10) ~ 1 -> H = f(excitation), pas de report
READER_W = 8.0                         # l'arete EXACTE de la regle : W[4, OUT0+8] = +8
K_APPROACH = 8.0                       # > le malus anti-repetition `logits[last_action] -= 0.1` (:1281)
K_AIM = 8.0
BALLAST_NODE = N_IN + 1                # 60 : noeud CACHE (59..63), aucune arete sortante -> INERTE
SPEAR = {"type": "Spear", "weight": 0.5}
APEX_TYPES = ("Mammouth", "Ours", "Leurre")

ARMS = ("TEMOIN", "LECTEUR", "BROUILLE")

# --- parametres scelles ---------------------------------------------------------------------------
N_AGENTS = 24
TICKS = 200
ENERGY0 = 80.0
MAX_AGENT_TICKS = 4800                 # 24 x 200
SEALED_SEEDS = 12                      # « 3 bras x 12 seeds » -- l'unique n de la regle scellee
SEED_BUDGET_S = 150.0                  # plafond scelle PAR SEED (les 3 bras)
TOTAL_BUDGET_S = SEALED_SEEDS * SEED_BUDGET_S
SAL_AGENTS, SAL_TICKS = 8, 40          # saillance : instrument calibre, dose reduite (cout borne)
SEED_BASE = 11_000
SCRAMBLE_BASE = 90_211                 # RNG DEDIE du brouillage (E5 : le RNG global n'est pas consomme)
E6_PROBE_TICKS = 10                    # ticks ou l'on compare batch vs recurrent_forward (cout borne)

# --- seuils de la regle de lecture -----------------------------------------------------------------
BAR_LOW = 1.10
BAR_HIGH = 1.25
ALPHA = 0.05
SAL_READER_MIN = 0.5
SAL_WITNESS_MAX = 0.05
P_THROW_POS_MIN = 0.9                  # P(throw | obs4 = +1) pour LECTEUR
P_THROW_NEG_MAX = 0.05                 # P(throw | obs4 = -1) pour LECTEUR
# --- controle (i) BROUILLE, CORRIGE par la regle -bis (2026-09-07) ---------------------------------
# La bande FIXE (0.25, 0.75) etait appliquee a une proportion par seed, sur une FAMILLE de 24 cellules
# (2 types x 12 seeds scelles), sans aucun controle du taux de fausse alarme. Calcul EXACT aux n
# observes : P(au moins une cellule hors bande | brouillage PARFAIT) = 0.216 -- un harnais correct
# echouait une fois sur cinq, et c'est ce qui est arrive au premier run (seed 9, verdict
# INDETERMINE-HARNAIS, results/evo011_preflight.json). Meme classe que la correction de Holm perdue
# dans `run_s2`, en sens inverse : la fausse alarme au lieu du p-hacking.
# La taille de la famille est connue D'AVANCE (le n est scelle), donc Bonferroni se calcule cellule
# par cellule, sans regarder les autres seeds.
P_THROW_SCRAMBLED = (0.25, 0.75)       # CONSERVEE : rapportee, plus jamais decisive (tracabilite)
ALPHA_FAMILY = 0.05
FAMILY_CELLS = 2 * SEALED_SEEDS        # 24 : les deux types x les 12 seeds de la regle
ALPHA_CELL = ALPHA_FAMILY / FAMILY_CELLS   # 0.002083
CENSURE_MAX = 0.50                     # (v) censure > 50 % dans un bras -> INDETERMINE-PLAFOND
CARRY_AGE_WINDOW = (1, 5)              # (vii) fenetre d'AGE APPARIE ou le port est compare (cf. §vii)
CARRY_MIN_OBS = 24                     # (vii) obs minimales par bras dans la fenetre, sinon non evaluable
CARRY_FRAC_MAX = 0.05                  # (vii) ecart tolere, EN ENERGIE, rapporte au drain metabolique


# ==================================================================================================
# 1. VERDICT -- PUR (aucun monde, aucun import lourd) : c'est l'instrument, il se calibre
# ==================================================================================================
def _sign_p(k: int, n: int) -> float:
    """p-value binomiale exacte bilaterale (test des signes, H0 p=0.5). Copie de tools/substrate_ab.py."""
    if n <= 0:
        return 1.0
    k_hi = max(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k_hi, n + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def _ratio_stats(pairs):
    """(ratios, r median, sign_p) sur des couples (num, den) APPARIES par seed. Entree douteuse -> None."""
    ratios = []
    for num, den in pairs:
        try:
            num_f, den_f = float(num), float(den)          # None / str -> TypeError -> refus
        except (TypeError, ValueError):
            return None, float("nan"), float("nan")
        if not (np.isfinite(num_f) and np.isfinite(den_f)) or den_f == 0.0:
            return None, float("nan"), float("nan")
        ratios.append(num_f / den_f)
    eff = [r for r in ratios if r != 1.0]                  # test des signes : ex aequo ecartes
    return ratios, statistics.median(ratios), _sign_p(sum(1 for r in eff if r > 1.0), len(eff))


def verdict_evo011_prevol(rows, n_required=SEALED_SEEDS):
    """INSTRUMENT DE VERDICT d'EVO-011-PREVOL. PUR : lignes appariees -> verdict scelle.

    `rows` : une ligne PAR SEED (l'unite de replication), avec au moins
        {'seed', 'age_LECTEUR', 'age_TEMOIN', 'age_BROUILLE', 'control_failures': [str]}.

    Quatre branches de lecture, EXACTEMENT celles du sceau :
      * un controle echoue sur >= 1 seed                   -> INDETERMINE-HARNAIS
        (sous-cas nomme par la regle : censure > 50 %      -> INDETERMINE-PLAFOND)
      * r <= 1.10                                          -> NE PAIE PAS
      * r >= 1.25 ET sign_p < 0.05                         -> LE LECTEUR PAIE (+ sous-lecture
        DISCRIMINATION : LECTEUR vs BROUILLE aux MEMES seuils)
      * sinon (1.10 < r < 1.25, ou r >= 1.25 avec sign_p >= 0.05) -> INDETERMINE

    ⚠️ TROIS FACONS DE FABRIQUER UN NEGATIF, toutes fermees ici (direction d'erreur CONSTANTE du
    depot : donnee absente -> affirmation NEGATIVE de fond) :
      1. entree vide / `nan` / denominateur nul            -> INDETERMINE-HARNAIS ;
      2. cle `control_failures` ABSENTE : « controles non passes » n'est PAS « controles passes »
         -- un dict silencieux ne vaut pas un dict propre  -> INDETERMINE-HARNAIS ;
      3. SOUS-PUISSANCE : le sceau dit « 12 seeds ». A n=1 (un smoke !) la branche basse rendait
         « NE PAIE PAS » -- un non-paiement fabrique par la taille d'echantillon, avec un `sign_p`
         structurellement egal a 1. Defaut REEL trouve en revue -> `n_required` (12 par le sceau ;
         l'unique extension scellee est 24).
    Les DV secondaires se rapportent dans TOUS les cas -- ce verdict ne les filtre pas."""
    out = {"verdict": None, "r": float("nan"), "sign_p": float("nan"), "n_seeds": 0,
           "ratios": None, "discrimination": None, "r_disc": float("nan"),
           "sign_p_disc": float("nan"), "raisons": []}
    if not rows:
        out["verdict"] = "INDETERMINE-HARNAIS"
        out["raisons"].append("aucune ligne : rien n'a ete mesure (ce n'est PAS un non-paiement)")
        return out
    out["n_seeds"] = len(rows)

    # --- (a) controles : ils PRECEDENT toute lecture de la DV -------------------------------------
    fails, plafond = [], False
    for r in rows:
        if not isinstance(r, dict) or "control_failures" not in r:
            fails.append(f"seed {r.get('seed') if isinstance(r, dict) else '?'} : cle "
                         f"`control_failures` ABSENTE -> les controles n'ont pas ete PASSES, ils "
                         f"n'ont pas ete FAITS")
            continue
        cf = r["control_failures"]
        if cf is None or not isinstance(cf, (list, tuple)):
            fails.append(f"seed {r.get('seed')} : `control_failures` de type {type(cf).__name__} "
                         f"(attendu list) -> illisible")
            continue
        for f in cf:
            fails.append(f"seed {r.get('seed')}: {f}")
            if "censure" in str(f).lower():
                plafond = True
    if fails:
        out["verdict"] = "INDETERMINE-PLAFOND" if plafond else "INDETERMINE-HARNAIS"
        out["raisons"] = fails
        return out

    # --- (a-bis) PUISSANCE : le n du sceau, avant toute lecture de fond ----------------------------
    if len(rows) < int(n_required):
        out["verdict"] = "INDETERMINE-HARNAIS"
        out["raisons"].append(
            f"SOUS-PUISSANCE : {len(rows)} seed(s) < {int(n_required)} scelles. Aucune branche de fond "
            f"n'est lisible (a n=1 le test des signes vaut 1.0 PAR CONSTRUCTION) -- lire « NE PAIE "
            f"PAS » ici serait un negatif fabrique par la taille d'echantillon.")
        return out

    # --- (b) DV primaire : r = mediane des ratios apparies -----------------------------------------
    pairs = [(r.get("age_LECTEUR"), r.get("age_TEMOIN")) for r in rows]
    ratios, r_med, p = _ratio_stats(pairs)
    if ratios is None:
        out["verdict"] = "INDETERMINE-HARNAIS"
        out["raisons"].append("mediane d'age absente/nan/denominateur nul -> ratio indefini "
                              "(defaut d'INSTRUMENT, pas resultat sur le monde)")
        return out
    out.update({"r": r_med, "sign_p": p, "ratios": ratios})

    if r_med <= BAR_LOW:
        out["verdict"] = "NE PAIE PAS"
        return out
    if r_med >= BAR_HIGH and p < ALPHA:
        out["verdict"] = "LE LECTEUR PAIE"
        d_pairs = [(r.get("age_LECTEUR"), r.get("age_BROUILLE")) for r in rows]
        d_ratios, r_d, p_d = _ratio_stats(d_pairs)
        if d_ratios is None:
            out["discrimination"] = "INDETERMINE-HARNAIS"
            out["raisons"].append("bras BROUILLE non lisible -> sous-lecture impossible")
            return out
        out.update({"r_disc": r_d, "sign_p_disc": p_d})
        if r_d >= BAR_HIGH and p_d < ALPHA:
            out["discrimination"] = "DISCRIMINATION DE TYPE"
        elif r_d <= BAR_LOW:
            out["discrimination"] = "LE LANCER SEUL (type indifferent)"
        else:
            out["discrimination"] = "INDETERMINE-DISCRIMINATION"
        return out
    out["verdict"] = "INDETERMINE"
    return out


# ==================================================================================================
# 2. CABLAGE -- pur numpy (aucun monde) : c'est le contre-exemple a reponse connue
# ==================================================================================================
def build_genome(arm: str, ballast: bool = True):
    """Genome CABLE A LA MAIN d'un bras. LECTEUR et BROUILLE sont BIT-IDENTIQUES (le brouillage est
    dans le MONDE, pas dans le genome) ; TEMOIN n'a pas l'arete de lecture."""
    from src.seed_ai.mutation import Genome
    if arm not in ARMS:
        raise ValueError(f"bras inconnu : {arm!r} (attendu {ARMS})")
    W = np.zeros((N_NODES, N_NODES), dtype=np.float32)
    np.fill_diagonal(W, REFLEX_DIAG)                       # reflexe : LES TROIS bras
    # approche gloutonne vers la proie la plus proche (identique partout)
    W[DIST_COLS[0], OUT0 + ACT_N] = K_APPROACH             # dn -> Nord
    W[DIST_COLS[1], OUT0 + ACT_S] = K_APPROACH             # ds -> Sud
    W[DIST_COLS[2], OUT0 + ACT_E] = K_APPROACH             # de -> Est
    W[DIST_COLS[3], OUT0 + ACT_W] = K_APPROACH             # dw -> Ouest
    # visee balistique vers la proie la plus proche (identique partout)
    W[DIST_COLS[2], OUT0 + AIM_X_IDX] = +K_AIM             # de -> +x
    W[DIST_COLS[3], OUT0 + AIM_X_IDX] = -K_AIM             # dw -> -x
    W[DIST_COLS[1], OUT0 + AIM_Y_IDX] = +K_AIM             # ds -> +y (Sud)
    W[DIST_COLS[0], OUT0 + AIM_Y_IDX] = -K_AIM             # dn -> -y (Nord)
    if arm in ("LECTEUR", "BROUILLE"):
        W[TYPE_COL, OUT0 + THROW_IDX] = READER_W           # L'ARETE
    elif ballast:
        W[TYPE_COL, BALLAST_NODE] = READER_W               # meme norme en ligne 4, INERTE
    return Genome(W, N_IN, N_OUT)


def phenotype_of(genome):
    """Les trois grandeurs que le monde derive de `W[0:5]`/`W[5:10]` (mamba_agent.py:47-50). PUR.
    ⚠️ REFERENCE seulement : le controle (ii-bis) lit le phenotype SUR L'AGENT VIVANT."""
    hp = float(np.sum(np.abs(np.nan_to_num(genome.W[0:5]))) * 10.0)
    inv = max(3, int(np.sum(np.abs(np.nan_to_num(genome.W[5:10])))))
    organ = getattr(genome, "organ_genes", None)
    mcts = 0.5 if (organ is not None and organ[0]) else 0.0
    return {"hp_bonus": hp, "inv_capacity": inv, "energy_drain": 1.0 + hp / 100.0 + inv * 0.1 + mcts}


def decision_flip_rate_pure(genome, obs_rows, out_idx=THROW_IDX, channel=TYPE_COL):
    """Saillance de DECISION en version PURE (meme operateur que `measure_decision_saliency` : la
    bascule de `sign(logits[out_idx])` quand `obs[channel]` passe de +1 a -1), mais sur des obs
    FOURNIES -- aucun monde, aucun RNG, aucun bail. Sert de contre-exemple a reponse connue."""
    from src.seed_ai.rl_evolution import recurrent_forward
    H = np.zeros((1, genome.num_nodes), dtype=np.float32)
    hist = np.zeros((1, 5, genome.num_nodes), dtype=np.float32)
    pot = np.zeros((1, genome.num_nodes), dtype=np.float32)
    flips = []
    for row in np.asarray(obs_rows, dtype=np.float32):
        op = row.reshape(1, -1).copy(); op[0, channel] = +1.0
        om = row.reshape(1, -1).copy(); om[0, channel] = -1.0
        pp = recurrent_forward(genome, op, H, hist, pot)[0]
        pm = recurrent_forward(genome, om, H, hist, pot)[0]
        flips.append(float((float(pp[0, out_idx]) > 0.0) != (float(pm[0, out_idx]) > 0.0)))
    return float(np.mean(flips)) if flips else 0.0


# ==================================================================================================
# 3. MONDE -- sous bail `kuzu` uniquement
# ==================================================================================================
def _type_key(v: float) -> str:
    if v > 0.75:
        return "+1"          # Mammouth
    if v > 0.25:
        return "+0.5"        # Ours
    if v < -0.75:
        return "-1"          # Leurre
    return "0"               # aucun apex adjacent


def world_fingerprint(env):
    """Empreinte du MONDE (pas du genome) + de l'etat du RNG GLOBAL. Sert au controle (viii) : les
    trois bras doivent partir d'un monde BIT-IDENTIQUE, sinon le contraste porte aussi le monde.
    Inclut hp/energie des agents -> re-verifie EN SITU que le ballast egalise le phenotype."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(env.geometry).tobytes())
    h.update(np.ascontiguousarray(env.terrain_type).tobytes())
    for p in env.preys:
        h.update(f"P|{p['type']}|{p['x']}|{p['y']}|{p.get('z', 0)}|{p.get('hp')}|"
                 f"{p.get('stunned', 0)}".encode())
    for a in env.agents:
        h.update(f"A|{a['x']}|{a['y']}|{a.get('z', 0)}|{a['energy']:.6f}|{a['hp']:.6f}|"
                 f"{a['inv_capacity']}|{len(a['inventory'])}".encode())
    for it in env.items:
        h.update(f"I|{it.get('type')}|{it.get('x')}|{it.get('y')}".encode())
    h.update(f"T|{env.treasure_x}|{env.treasure_y}|{env.treasure_z}".encode())
    st = np.random.get_state()                               # E5 : le flux global lui-meme
    h.update(np.asarray(st[1], dtype=np.uint32).tobytes())
    h.update(f"|{st[2]}|{st[3]}|{st[4]}".encode())
    return h.hexdigest()[:16]


def _world_class():
    """Sous-classe MINIMALE : (a) equipement, (b) capture in situ obs[4] -> decision, (c) brouillage,
    (d) gel de la plasticite, (e) comptabilite mecanique (port, riposte, etourdissements, morts)."""
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.environments.stone_economy import has_spear

    class Evo011Biosphere(Biosphere3D):
        scramble = False
        freeze = True                                 # gel de la plasticite intra-vie (cf. en-tete §4)
        rng = None                                    # RNG DEDIE (E5)
        insitu_h0 = False                             # CONTRE-EXEMPLE de (i+) : cf. `--break-insitu`

        # -- le genome CABLE doit rester le genome cable -------------------------------------------
        def _get_batch_model(self, models):
            bm = super()._get_batch_model(models)
            if self.freeze:
                bm.compute_policy_gradient = lambda *a, **k: None   # sinon : W <- clip(W+dW, -5, 5)
            return bm

        # -- (a) la LOI PHYSIQUE n'est pas levee : on re-equipe ------------------------------------
        def _equip(self, agent):
            inv = agent["inventory"]
            if not inv or not has_spear([inv[0]]):
                inv.insert(0, dict(SPEAR))
                agent["_e11_equips"] = agent.get("_e11_equips", 0) + 1

        def _resolve_biology(self, agent, action, logits):
            self._equip(agent)                        # AVANT la melee (elle suit le lancer, meme tick)
            # (vii) PORT mesure AU POINT EXACT ou le monde le facture (`carry_weight * 0.5`), et
            # VENTILE PAR AGE : le port cumule est DOWNSTREAM de la duree de vie (grabs epsilon-greedy),
            # donc le comparer brut entre bras teste la DV avec elle-meme (causalite inversee).
            cw = sum(i.get("weight", 1.0) if isinstance(i, dict) else 1.0
                     for i in agent["inventory"])
            self.carry_sum += cw
            self.carry_n += 1
            age = int(agent["age"])
            s, n = self.carry_by_age.setdefault(age, [0.0, 0])
            self.carry_by_age[age] = [s + cw, n + 1]
            alive = {id(p): str(p["type"]) for p in self.preys}
            out = super()._resolve_biology(agent, action, logits)
            still = {id(p) for p in self.preys}
            for pid, ptype in alive.items():          # proies RETIREES par cette melee = tuees ici
                if pid not in still:
                    self.kills_by_type[ptype] = self.kills_by_type.get(ptype, 0) + 1
            return out

        def _move_preys(self):
            hp0 = [(a, float(a["hp"])) for a in self.agents]
            super()._move_preys()
            self.riposte_hp += sum(max(0.0, h - float(a["hp"])) for a, h in hp0)

        def step(self):
            for a in self.agents:
                self._equip(a)                        # AVANT le lancer
            stun0 = {id(p): int(p.get("stunned", 0)) for p in self.preys}
            typ0 = {id(p): p["type"] for p in self.preys}
            dec0 = self._sum_decided()
            self._pred_decided = 0
            super().step()
            # (i+) IDENTITE DE DECISION : ce qu'on a LU au seam == ce que le monde a DECIDE
            got = self._sum_decided() - dec0
            if got != self._pred_decided:
                self.decision_mismatch.append((self.ticks, self._pred_decided, got))
            for p in self.preys:                      # etourdissements NOUVEAUX, par type de proie
                if int(p.get("stunned", 0)) > stun0.get(id(p), 0):
                    t = str(typ0.get(id(p), p["type"]))    # str() : `np.random.choice` rend np.str_
                    self.stunned_by_type[t] = self.stunned_by_type.get(t, 0) + 1

        def _sum_decided(self):
            return sum(int(a.get("throw_decided", 0)) for a in self.agents) + \
                   sum(int(a.get("throw_decided", 0)) for a in self.dead_agents)

        # -- (b) + (c) ----------------------------------------------------------------------------
        def get_batch_observations(self):
            obs = super().get_batch_observations()
            if getattr(obs, "size", 0) == 0:
                return obs
            # E6 : etat AVANT le forward batch (le forward le mute) -> sonde batch vs recurrent
            if self.ticks <= E6_PROBE_TICKS:
                self._h_snap = [(a["model"].H_prev.copy(), a["model"].H_history.copy(),
                                 a["model"].H_potentials.copy()) for a in self.agents]
                self._obs_snap = obs.copy()
            else:
                self._h_snap = self._obs_snap = None
            self._obs_now = obs                       # (i+) : l'obs REELLEMENT donnee au reseau
            for i, ag in enumerate(self.agents):
                if i >= obs.shape[0]:
                    break
                ag["_e11_true4"] = float(obs[i, TYPE_COL])       # la VRAIE valeur, avant toute ecriture
                if self.scramble:
                    v = 1.0 if float(self.rng.random()) < 0.5 else -1.0
                    obs[i, TYPE_COL] = v
                    ag["_e11_seen4"] = v
                    self.n_scrambled += 1
                else:
                    ag["_e11_seen4"] = ag["_e11_true4"]
            if self._obs_snap is not None:
                self._obs_snap = obs.copy()           # obs REELLEMENT donnee au reseau (post-brouillage)
            return obs

        def _apply_social_consensus(self, batch_logits):
            out = super()._apply_social_consensus(batch_logits)
            for i, ag in enumerate(self.agents):
                if i >= len(out):
                    break
                t = ag.pop("_e11_true4", None)        # consomme : jamais compte deux fois
                s = ag.pop("_e11_seen4", None)
                if t is None:
                    continue
                if self.insitu_h0:
                    # CONTRE-EXEMPLE ARME de (i+) : lire la decision hors regime, sur un etat FRAIS
                    # (H=0) au lieu du seam batch -- exactement l'erreur E6 que le sceau nomme
                    # (« un lecteur parfait a H=0 tombe a la chance in-world », EVO-005).
                    from src.seed_ai.rl_evolution import recurrent_forward
                    Z1 = np.zeros((1, ag["model"].genome.num_nodes), dtype=np.float32)
                    Z3 = np.zeros((1, 5, ag["model"].genome.num_nodes), dtype=np.float32)
                    row = np.asarray(self._obs_now[i:i + 1], dtype=np.float32)
                    decided = float(recurrent_forward(ag["model"].genome, row, Z1, Z3, Z1)[0][0, THROW_IDX]) > 0.0
                else:
                    decided = float(np.asarray(out[i], dtype=np.float32)[THROW_IDX]) > 0.0
                self._pred_decided += 1 if decided else 0
                for nkey, hkey, val in (("_e11_n", "_e11_thr", t),
                                        ("_e11_sn", "_e11_sthr", s if s is not None else t)):
                    k = _type_key(float(val))
                    n, h = ag.setdefault(nkey, {}), ag.setdefault(hkey, {})
                    n[k] = n.get(k, 0) + 1
                    h[k] = h.get(k, 0) + (1 if decided else 0)
                # E6 : le regime batch differe-t-il de `recurrent_forward` (l'instrument calibre) ?
                if self._h_snap is not None and self._obs_snap is not None and i < len(self._h_snap):
                    from src.seed_ai.rl_evolution import recurrent_forward
                    H, hist, pot = self._h_snap[i]
                    row = self._obs_snap[i:i + 1].astype(np.float32)
                    pr = recurrent_forward(ag["model"].genome, row, H, hist, pot)[0]
                    lb = float(np.asarray(out[i], dtype=np.float32)[THROW_IDX])
                    lr = float(pr[0, THROW_IDX])
                    self.e6_gap = max(self.e6_gap, abs(lb - lr))
                    self.e6_n += 1
                    self.e6_sign_agree += 1 if ((lb > 0.0) == (lr > 0.0)) else 0
            return out

    return Evo011Biosphere


def _carry_matched(carry_by_age, window=CARRY_AGE_WINDOW):
    """Port moyen SUR UNE FENETRE D'AGE APPARIEE. PUR (dict age -> [somme, n]).

    ⚠️ Pourquoi : le port CUMULE d'un bras est downstream de sa duree de vie -- un agent qui vit plus
    longtemps ramasse plus (epsilon-greedy `force_grab`), donc porte plus. Comparer les moyennes de vie
    entiere entre bras, c'est tester la DV avec elle-meme (causalite INVERSEE). Mesure : sur le smoke,
    le brut donnait TEMOIN 0.832 / LECTEUR 0.846 / BROUILLE 0.661 -- l'ecart 0.185 est un ARTEFACT de
    la mortalite de BROUILLE, et il faisait ECHOUER mon propre controle. A age apparie, la question
    posee (« le lanceur porte-t-il moins ? ») redevient decidable. Renvoie (moyenne, n)."""
    lo, hi = window
    s = sum(v[0] for a, v in carry_by_age.items() if lo <= a <= hi)
    n = sum(v[1] for a, v in carry_by_age.items() if lo <= a <= hi)
    return ((s / n) if n else float("nan"), n)


def run_arm(arm: str, seed: int, ballast=True, ticks=TICKS, n_agents=N_AGENTS, guard=None, freeze=True,
            insitu_h0=False):
    """Un bras-seed. Renvoie un dict de mesures. AUCUNE lecture de verdict ici."""
    from tools.evo_memory_inworld import _cfg, N_APEX     # importe `_disable_kuzu()` a l'import
    from tools.lewis_world import _setup_lewis
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.persistence import calculate_life_score, REF_FITNESS_WEIGHT

    cls = _world_class()
    np.random.seed(SEED_BASE + seed)                  # RNG GLOBAL : identique entre bras a t=0 (E5)
    cfg = _cfg()
    # BILAN ENERGETIQUE (EDR-099/100) : `trace_energy_sinks` est du BOOKKEEPING PUR -- il n'ecrit que
    # des cles `_e_*` et ne consomme aucun RNG. Verifie : sous ce flag le smoke rend des med_age et
    # une empreinte (viii) BIT-IDENTIQUES. Sans lui, le cout du lancer serait INFERE (10 energie x
    # `throws`) au lieu d'etre mesure -- or le sceau ne scelle pas ce cout, et c'est lui qui decide
    # si « le lecteur paie » peut vouloir dire autre chose que « il lit ».
    cfg.trace_energy_sinks = True
    env = cls(cfg)
    env.freeze = bool(freeze)
    env.insitu_h0 = bool(insitu_h0)
    env.scramble = (arm == "BROUILLE")
    env.rng = np.random.default_rng(SCRAMBLE_BASE + seed)
    env.n_scrambled = 0
    env.carry_sum, env.carry_n = 0.0, 0
    env.carry_by_age = {}
    env.riposte_hp = 0.0
    env.kills_by_type, env.stunned_by_type = {}, {}
    env.decision_mismatch = []
    env._pred_decided = 0
    env._h_snap = env._obs_snap = env._obs_now = None
    env.e6_gap, env.e6_n, env.e6_sign_agree = 0.0, 0, 0
    _setup_lewis(env, n_each=N_APEX)
    env.benchmark_mode = True                         # cohorte FIXE -> n EXACT par bras
    env.night_enabled = False
    env.current_era = 10_000                          # scaffolds annules
    g = build_genome(arm, ballast=ballast)
    for _ in range(n_agents):
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=ENERGY0)
    fingerprint = world_fingerprint(env)              # (viii) monde + RNG global, AVANT le 1er tick
    apex0 = sum(1 for p in env.preys if p["type"] in APEX_TYPES)

    t, agent_ticks = 0, 0
    while env.agents and t < ticks:
        agent_ticks += len(env.agents)
        env.step()
        t += 1
        if guard is not None:
            guard.tick()

    pool = list(env.agents) + list(env.dead_agents)
    ages = [float(a["age"]) for a in pool]

    def _prof(nkey, hkey):
        n_by, thr_by = {}, {}
        for a in pool:
            for k, v in (a.get(nkey) or {}).items():
                n_by[k] = n_by.get(k, 0) + v
            for k, v in (a.get(hkey) or {}).items():
                thr_by[k] = thr_by.get(k, 0) + v
        return ({k: (thr_by.get(k, 0) / n_by[k] if n_by.get(k) else float("nan"))
                 for k in ("+1", "+0.5", "-1", "0")}, n_by)

    profile, n_by = _prof("_e11_n", "_e11_thr")            # conditionne sur la VRAIE valeur d'obs[4]
    profile_seen, n_by_seen = _prof("_e11_sn", "_e11_sthr")  # conditionne sur la valeur VUE (brouillee)

    # (vi) IDENTITE life_score : recomposition depuis les composantes, MEME ordre d'operations
    d_max = 0.0
    for a in pool:
        recomposed = ((a["age"] * 0.1) + (a["preys_eaten"] * 50.0)
                      + (a["altars_solved"] * 20.0) + (a.get("spears_crafted", 0) * 300.0)
                      + (a.get("mammoth_kills", 0) * 400.0)
                      + (a.get("_ref_distinction", 0.0) * REF_FITNESS_WEIGHT))
        d_max = max(d_max, abs(calculate_life_score(a) - recomposed))

    # (ii) ARETE en fin de run, sur le genome VIVANT de chaque agent (from_genome deep-copie)
    edges = {float(a["model"].genome.W[TYPE_COL, OUT0 + THROW_IDX]) for a in pool}
    w_intact = all(np.array_equal(a["model"].genome.W, g.W) for a in pool)
    w_drift = max((float(np.abs(a["model"].genome.W - g.W).max()) for a in pool), default=0.0)
    # (ii-bis) phenotype releve SUR L'AGENT VIVANT (pas recalcule a cote)
    pheno_insitu = {(float(a["model"].phenotype_hp_bonus), int(a["model"].phenotype_inv_capacity),
                     float(a["model"].phenotype_energy_drain)) for a in pool}

    phases = {"brain": 0.0, "action": 0.0, "biologie": 0.0, "mouvement": 0.0}
    for a in pool:
        for k, v in (a.get("_e_phases") or {}).items():
            phases[k] = phases.get(k, 0.0) + float(v)
    hits = sum(int(a.get("throw_hits", 0)) for a in pool)
    prey_hits = sum(int(a.get("throw_prey_hits", 0)) for a in pool)
    return {
        "arm": arm, "seed": seed, "n": len(pool), "ticks_run": t, "agent_ticks": agent_ticks,
        "med_age": statistics.median(ages) if ages else float("nan"), "ages": sorted(ages),
        "alive_end": len(env.agents), "censure": (len(env.agents) / len(pool)) if pool else float("nan"),
        "age_at_cap": sum(1 for x in ages if x >= ticks),
        "throw_decided": sum(int(a.get("throw_decided", 0)) for a in pool),
        "throws": sum(int(a.get("throws", 0)) for a in pool),
        "throw_hits": hits, "throw_prey_hits": prey_hits,
        "throw_agent_hits": hits - prey_hits,          # TIR FRATRICIDE : -damage sur un CO-EQUIPIER
        "preys_eaten": sum(int(a.get("preys_eaten", 0)) for a in pool),
        "mammoth_kills": sum(int(a.get("mammoth_kills", 0)) for a in pool),
        "big_kills": int(getattr(env, "big_kills", 0)),
        "leurre_hits": int(getattr(env, "leurre_hits", 0)),
        "apex0": apex0, "apex_end": sum(1 for p in env.preys if p["type"] in APEX_TYPES),
        "kills_by_type": dict(env.kills_by_type), "stunned_by_type": dict(env.stunned_by_type),
        "riposte_hp": float(env.riposte_hp),
        "hp_start": float(pool[0]["model"].phenotype_hp_bonus + 100.0) if pool else float("nan"),
        "died_energy": sum(1 for a in pool if a["energy"] <= 0.0),
        "died_hp": sum(1 for a in pool if a["hp"] <= 0.0),
        "equips": sum(int(a.get("_e11_equips", 0)) for a in pool),
        "n_scrambled": int(env.n_scrambled),
        "carry_mean": (env.carry_sum / env.carry_n) if env.carry_n else float("nan"),
        "carry_matched": _carry_matched(env.carry_by_age),
        "energy_phases": {k: round(v, 1) for k, v in phases.items()},
        "energy_action_per_throw": (phases["action"] / t2) if (t2 := sum(int(a.get("throws", 0)) for a in pool)) else float("nan"),
        "drain": float(pool[0]["model"].phenotype_energy_drain) if pool else float("nan"),
        "decision_mismatch": list(env.decision_mismatch),
        "e6_gap": float(env.e6_gap), "e6_n": int(env.e6_n),
        "e6_sign_agree": (env.e6_sign_agree / env.e6_n) if env.e6_n else float("nan"),
        "profile": profile, "n_by_type": n_by,
        "profile_seen": profile_seen, "n_by_type_seen": n_by_seen,
        "edges": edges, "w_intact": w_intact, "w_drift": w_drift, "life_score_max_dev": d_max,
        "phenotype": phenotype_of(g), "phenotype_insitu": pheno_insitu,
        "fingerprint": fingerprint,
    }


# ==================================================================================================
# 4. LES CONTROLES -- (i)-(vi) SCELLES, puis (i+)/(i-bis)/(vii)/(viii) AJOUTES PAR LA REVUE
# ==================================================================================================
def check_controls(seed, res, sal, ballast=True):
    """Renvoie (failures, detail). Un controle qui ne PEUT pas etre evalue (bucket vide, nan) est un
    ECHEC de harnais -- jamais un silence."""
    from tools.experiment_preflight import (assert_ablation_changes_something, assert_n_per_arm,
                                            assert_not_degenerate, PreflightError)
    F, D = [], {}
    L, T, B = res["LECTEUR"], res["TEMOIN"], res["BROUILLE"]

    # (i) MANIPULATION, deux fois : instrument calibre PUIS in situ (regime reel, forward batch)
    D["sal"] = sal
    if not (sal["LECTEUR"] > SAL_READER_MIN):
        F.append(f"(i) saillance LECTEUR {sal['LECTEUR']:.3f} <= {SAL_READER_MIN}")
    if not (sal["TEMOIN"] < SAL_WITNESS_MAX):
        F.append(f"(i) saillance TEMOIN {sal['TEMOIN']:.3f} >= {SAL_WITNESS_MAX}")
    if sal["BROUILLE"] != sal["LECTEUR"]:             # meme genome, meme seed -> identite EXACTE
        F.append(f"(i) saillance BROUILLE {sal['BROUILLE']:.6f} != LECTEUR {sal['LECTEUR']:.6f} alors "
                 f"que les genomes sont bit-identiques -> l'instrument n'est pas deterministe")
    for arm in ("LECTEUR", "BROUILLE"):
        for k in ("+1", "-1"):
            if not res[arm]["n_by_type"].get(k):
                F.append(f"(i) in situ {arm} : bucket obs4={k} VIDE (n=0) -> P(throw|{k}) indefinie, "
                         f"controle non evaluable (harnais)")
    if res["LECTEUR"]["n_by_type"].get("+1"):
        p = L["profile"]["+1"]
        if not (p > P_THROW_POS_MIN):
            F.append(f"(i) in situ LECTEUR P(throw|+1)={p:.3f} <= {P_THROW_POS_MIN}")
    if res["LECTEUR"]["n_by_type"].get("-1"):
        p = L["profile"]["-1"]
        if not (p < P_THROW_NEG_MAX):
            F.append(f"(i) in situ LECTEUR P(throw|-1)={p:.3f} >= {P_THROW_NEG_MAX}")
    for k in ("+1", "-1"):
        nk = res["BROUILLE"]["n_by_type"].get(k)
        if nk:
            p = B["profile"][k]
            # Regle -bis : test binomial bilateral EXACT contre p=0.5, seuil de Bonferroni sur la
            # famille SCELLEE. `_sign_p` EST ce test (meme fonction que la DV), donc le controle et
            # la DV partagent leur statistique -- une seule chose a calibrer.
            pv = _sign_p(int(round(p * nk)), nk)
            D.setdefault("scrambler_binom", {})[k] = {"p_obs": p, "n": nk, "p_value": pv,
                                                      "alpha_cell": ALPHA_CELL,
                                                      "hors_bande_ancienne": not (
                                                          P_THROW_SCRAMBLED[0] <= p <= P_THROW_SCRAMBLED[1])}
            if pv < ALPHA_CELL:
                F.append(f"(i) in situ BROUILLE P(throw|{k})={p:.3f} (n={nk}) s'ecarte de 0.5 : "
                         f"binomial p={pv:.2g} < alpha'={ALPHA_CELL:.6f} (Bonferroni sur "
                         f"{FAMILY_CELLS} cellules)")
    if T["throws"] != 0 or T["throw_decided"] != 0:
        F.append(f"(i) in situ TEMOIN throws={T['throws']} decided={T['throw_decided']} != 0")

    # (i+) HORS SCEAU -- IDENTITE DE DECISION : la grandeur LUE est celle qui AGIT (E6 / no-aliasing).
    D["decision_mismatch"] = {a: res[a]["decision_mismatch"][:3] for a in ARMS}
    for arm in ARMS:
        if res[arm]["decision_mismatch"]:
            F.append(f"(i+) {arm} : {len(res[arm]['decision_mismatch'])} tick(s) ou la decision LUE au "
                     f"seam batch differe du `throw_decided` incremente par le monde "
                     f"{res[arm]['decision_mismatch'][:3]} -> « in situ » n'est pas in situ")
    D["e6"] = {a: {"gap": res[a]["e6_gap"], "n": res[a]["e6_n"],
                   "sign_agree": res[a]["e6_sign_agree"]} for a in ARMS}
    for arm in ARMS:
        if res[arm]["e6_n"] <= 0:
            F.append(f"(i+) {arm} : sonde batch-vs-recurrent JAMAIS evaluee (n=0) -> l'ecart de "
                     f"regime E6 est inconnu, pas nul")

    # (i-bis) HORS SCEAU -- LE BROUILLAGE ATTEINT-IL LA DECISION ? Conditionne sur la valeur VUE :
    # si le bras BROUILLE etait un lecteur CASSE, P(throw | vu=+1) tomberait, et les ~0.5 du controle
    # (i) seraient les MEMES chiffres pour une TOUTE AUTRE raison.
    D["profile_seen"] = {a: res[a]["profile_seen"] for a in ARMS}
    for k, lo, hi in (("+1", P_THROW_POS_MIN, 1.01), ("-1", -0.01, P_THROW_NEG_MAX)):
        if not res["BROUILLE"]["n_by_type_seen"].get(k):
            F.append(f"(i-bis) BROUILLE : bucket VU={k} vide -> brouillage non verifiable")
            continue
        p = B["profile_seen"][k]
        if not (lo < p < hi):
            F.append(f"(i-bis) BROUILLE P(throw | VU={k})={p:.3f} hors ]{lo}, {hi}[ -> le bras n'est "
                     f"pas « un lecteur qui lit du bruit », c'est un lecteur CASSE")

    # (ii) ARETE PRESENTE en fin de run
    D["edges"] = {a: sorted(res[a]["edges"]) for a in ARMS}
    for arm in ("LECTEUR", "BROUILLE"):
        if res[arm]["edges"] != {READER_W}:
            F.append(f"(ii) {arm} : W[4,{OUT0 + THROW_IDX}] = {sorted(res[arm]['edges'])} != {READER_W}")
    if T["edges"] != {0.0}:
        F.append(f"(ii) TEMOIN : W[4,{OUT0 + THROW_IDX}] = {sorted(T['edges'])} != 0.0")
    D["w_drift"] = {a: res[a]["w_drift"] for a in ARMS}
    for arm in ARMS:                                   # (ii+) version FORTE : W ENTIER intact
        if not res[arm]["w_intact"]:
            F.append(f"(ii+) {arm} : le genome a BOUGE pendant le run (ecart max "
                     f"{res[arm]['w_drift']:.3g}) -> plasticite intra-vie non gelee")

    # (ii-bis) CONFOND DE PHENOTYPE : hp/drain derivent de W[0:5], ou vit l'arete. RELEVE IN SITU.
    D["phenotype_insitu"] = {a: sorted(res[a]["phenotype_insitu"]) for a in ARMS}
    insitu = {a: res[a]["phenotype_insitu"] for a in ARMS}
    for arm in ARMS:
        if len(insitu[arm]) != 1:
            F.append(f"(ii-bis) {arm} : les 24 agents n'ont PAS le meme phenotype {sorted(insitu[arm])}")
    if len({tuple(sorted(insitu[a])) for a in ARMS}) != 1:
        F.append(f"(ii-bis) phenotypes IN SITU non identiques entre bras : {D['phenotype_insitu']}"
                 + ("" if ballast else " -- attendu sous --no-ballast : c'est le CONTRE-EXEMPLE"))

    # (iii) BUDGET
    for arm in ARMS:
        if res[arm]["n"] != N_AGENTS:
            F.append(f"(iii) {arm} : n={res[arm]['n']} != {N_AGENTS} (cohorte non figee ?)")
        if res[arm]["agent_ticks"] > MAX_AGENT_TICKS:
            F.append(f"(iii) {arm} : {res[arm]['agent_ticks']} agent-ticks > {MAX_AGENT_TICKS}")
    try:
        assert_n_per_arm(L["ages"], T["ages"], label="(iii) LECTEUR/TEMOIN")
        assert_n_per_arm(L["ages"], B["ages"], label="(iii) LECTEUR/BROUILLE")
    except PreflightError as e:
        F.append(f"(iii) {e}")

    # (iv) E1/E2 : la chaine se FERME, et l'ablation du canal MORD
    D["throw_prey_hits"] = {a: res[a]["throw_prey_hits"] for a in ARMS}
    if L["throw_prey_hits"] < 1:
        F.append("(iv) LECTEUR : throw_prey_hits = 0 -> la chaine throw->stun ne se ferme JAMAIS "
                 "(le bras ne peut pas produire l'issue cherchee)")
    pl = [L["profile"][k] for k in ("+1", "-1")]
    pb = [B["profile"][k] for k in ("+1", "-1")]
    if not all(np.isfinite(x) for x in pl + pb):
        # ⚠️ `assert_ablation_changes_something` compare par `==` : [nan,nan] != [nan,nan] -> elle
        # PASSERAIT sur deux bras entierement indefinis. Refus explicite AVANT de l'appeler.
        F.append(f"(iv) profils non finis (LECTEUR {pl}, BROUILLE {pb}) -> le controle d'ablation "
                 f"passerait VACUEMENT (nan != nan)")
    else:
        try:
            assert_ablation_changes_something(pl, pb, label="(iv) profil P(throw|type) LECTEUR vs BROUILLE")
        except PreflightError as e:
            F.append(f"(iv) {e}")

    # (v) E14 : ni plancher ni plafond ; censure > 50 % -> INDETERMINE-PLAFOND
    D["censure"] = {a: res[a]["censure"] for a in ARMS}
    D["age_at_cap"] = {a: res[a]["age_at_cap"] for a in ARMS}
    for arm in ARMS:
        try:
            assert_not_degenerate(res[arm]["ages"], label=f"(v) ages {arm}")
        except PreflightError as e:
            F.append(f"(v) {e}")
        if res[arm]["censure"] > CENSURE_MAX:
            F.append(f"(v) censure {arm} = {res[arm]['censure']:.0%} > {CENSURE_MAX:.0%} "
                     f"-> plafond (baisser ticks/energie, JAMAIS le seuil)")

    # (vi) IDENTITE life_score
    D["life_score_max_dev"] = {a: res[a]["life_score_max_dev"] for a in ARMS}
    for arm in ARMS:
        if res[arm]["life_score_max_dev"] != 0.0:
            F.append(f"(vi) {arm} : life_score != recomposition (ecart max "
                     f"{res[arm]['life_score_max_dev']:.3g})")

    # (vii) HORS SCEAU -- CONFOND MECANIQUE. Le lanceur consomme des lances : porte-t-il moins ?
    # Compare A AGE APPARIE (le port cumule est downstream de la duree de vie), et en ENERGIE (le
    # monde facture `carry_weight * 0.5` contre un drain metabolique de `phenotype_energy_drain`) :
    # un ecart de POIDS n'est un confond que s'il pese sur le bilan qui tue reellement les agents.
    D["carry_lifetime"] = {a: round(res[a]["carry_mean"], 4) for a in ARMS}   # DIAGNOSTIC (biaise)
    D["carry_matched"] = {a: res[a]["carry_matched"] for a in ARMS}
    cm = [res[a]["carry_matched"][0] for a in ARMS]
    nobs = [res[a]["carry_matched"][1] for a in ARMS]
    drain = res["TEMOIN"]["drain"]
    if not all(np.isfinite(x) for x in cm) or min(nobs) < CARRY_MIN_OBS:
        F.append(f"(vii) port a age apparie NON EVALUABLE (fenetre {CARRY_AGE_WINDOW}, "
                 f"valeurs {D['carry_matched']}, min n={min(nobs)} < {CARRY_MIN_OBS}) -- non evaluable "
                 f"n'est pas « pas de confond »")
    else:
        gap_w = max(cm) - min(cm)
        frac = (gap_w * 0.5) / drain if (np.isfinite(drain) and drain > 0) else float("inf")
        D["carry_gap_energy_frac"] = round(frac, 5)
        if frac > CARRY_FRAC_MAX:
            F.append(f"(vii) PORT INEGAL a age apparie : {D['carry_matched']} -> ecart {gap_w:.3f} de "
                     f"poids = {gap_w * 0.5:.3f} energie/tick, soit {frac:.1%} du drain metabolique "
                     f"{drain:.2f} (> {CARRY_FRAC_MAX:.0%}) : le contraste porte aussi le PORT")

    # (viii) HORS SCEAU -- MONDE INITIAL IDENTIQUE (le sceau le DIT : « le RNG global reste identique
    # entre bras, classe E5 ») : empreinte monde + etat du RNG global a t=0.
    D["fingerprint"] = {a: res[a]["fingerprint"] for a in ARMS}
    if len({res[a]["fingerprint"] for a in ARMS}) != 1:
        F.append(f"(viii) les bras NE partent PAS du meme monde : {D['fingerprint']}"
                 + ("" if ballast else " -- attendu sous --no-ballast (hp de depart different)"))
    return F, D


def saturation_flags(res):
    """DRAPEAUX DE SATURATION sur les DV SECONDAIRES (E14). PAS un gate : la DV primaire est l'age.
    Mais un plafond doit etre DIT, sinon « aucune difference » se lit comme un resultat."""
    flags = []
    a0 = res["TEMOIN"]["apex0"]
    if a0 > 0 and all(res[a]["apex_end"] <= 0.2 * a0 for a in ARMS):
        flags.append(f"PLAFOND : la population d'apex est EPUISEE dans les TROIS bras "
                     f"({a0} -> {[res[a]['apex_end'] for a in ARMS]}) -> `big_kills` et `leurre_hits` "
                     f"sont SATURES ; leur egalite entre bras "
                     f"({[res[a]['big_kills'] for a in ARMS]} / {[res[a]['leurre_hits'] for a in ARMS]}) "
                     f"n'est PAS une absence d'effet, c'est un epuisement de la ressource. Ces DV "
                     f"secondaires ne discriminent RIEN dans ce regime : ne pas les lire comme un nul.")
    hp0 = res["TEMOIN"]["hp_start"]
    worst = max(res[a]["riposte_hp"] / max(1, res[a]["n"]) for a in ARMS)
    if np.isfinite(hp0) and hp0 > 0 and worst < 0.10 * hp0:
        flags.append(f"MAILLON FAIBLE : riposte encaissee = {worst:.0f} hp/agent au pire des bras, pour "
                     f"hp de depart {hp0:.0f} ({worst / hp0:.1%}) -> le maillon scelle « melee SANS "
                     f"riposte » ne peut pas porter l'effet ; morts par energie/hp = "
                     f"{[(res[a]['died_energy'], res[a]['died_hp']) for a in ARMS]}.")
    return flags


# ==================================================================================================
# 5. ORCHESTRATION
# ==================================================================================================
def _assert_rule_matches_code(rule):
    """La regle scellee doit CONTENIR les seuils codes ici -- sinon la pre-inscription est decorative."""
    disc = " | ".join(rule.get("discrimination", {}))
    txt = " ".join(str(v) for v in rule.values()) + " " + disc
    need = [("1.10", disc), ("1.25", disc), ("sign_p < 0.05", disc), ("4800", txt), ("150 s/seed", txt),
            ("24 agents", txt), ("200 ticks", txt), ("W[4, o+8] == 8.0", txt),
            ("P(throw | obs4=+1) > 0.9", txt), ("P(throw | -1) < 0.05", txt),
            ("12 seeds", txt), ("censure > 50 %", txt),
            # regle -bis : le correctif d'instrument doit etre DANS le sceau, sinon il est decoratif
            ("0.05 / 24 = 0.002083", txt), ("0.216", txt)]
    missing = [s for s, where in need if s not in where]
    if missing:
        raise AssertionError(f"la regle scellee ne porte pas {missing} : le code n'applique pas le sceau")
    return True


def run_seed(seed, ballast=True, ticks=TICKS, n_agents=N_AGENTS, verbose=True, freeze=True,
             insitu_h0=False):
    from tools.cost_guard import CostGuard, CostExceeded
    import tools.evo_cognitive_objective as M
    guard = CostGuard(budget_s=SEED_BUDGET_S, label=f"seed {seed}")
    res, sal = {}, {}
    t0 = time.time()
    try:
        for arm in ARMS:
            ta = time.time()
            res[arm] = run_arm(arm, seed, ballast=ballast, ticks=ticks, n_agents=n_agents,
                               guard=guard, freeze=freeze, insitu_h0=insitu_h0)
            if verbose:
                r = res[arm]
                print(f"    {arm:9s} med_age={r['med_age']:6.1f} n={r['n']:2d} "
                      f"ticks={r['ticks_run']:3d} agent_ticks={r['agent_ticks']:4d} "
                      f"decided={r['throw_decided']:5d} throws={r['throws']:5d} "
                      f"prey_hits={r['throw_prey_hits']:4d} agent_hits={r['throw_agent_hits']:4d} "
                      f"preys={r['preys_eaten']:4d} big={r['big_kills']:3d} mk={r['mammoth_kills']:3d} "
                      f"leurre={r['leurre_hits']:3d} port@age={r['carry_matched'][0]:.3f} "
                      f"censure={r['censure']:.0%} [{time.time() - ta:.1f}s]")
        for arm in ARMS:                                   # (i) instrument CALIBRE, 3 mesures
            sal[arm] = M.measure_decision_saliency(build_genome(arm, ballast=ballast), seed=SEED_BASE + seed,
                                                   channel=TYPE_COL, out_idx=THROW_IDX,
                                                   num_agents=SAL_AGENTS, ticks=SAL_TICKS)
    except CostExceeded as e:
        return {"seed": seed, "control_failures": [f"(iii) budget PENDANT depasse : {e}"],
                "age_LECTEUR": float("nan"), "age_TEMOIN": float("nan"), "age_BROUILLE": float("nan"),
                "elapsed_s": time.time() - t0}
    fails, detail = check_controls(seed, res, sal, ballast=ballast)
    row = {"seed": seed, "control_failures": fails, "detail": detail, "res": res, "sal": sal,
           "saturation": saturation_flags(res), "elapsed_s": time.time() - t0}
    for arm in ARMS:
        row[f"age_{arm}"] = res[arm]["med_age"]
    return row


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="1 seed, 3 bras, chronometre")
    ap.add_argument("--seeds", type=int, default=SEALED_SEEDS)
    ap.add_argument("--ticks", type=int, default=TICKS)
    ap.add_argument("--agents", type=int, default=N_AGENTS)
    ap.add_argument("--no-ballast", dest="ballast", action="store_false",
                    help="lecture LITTERALE du sceau (« TEMOIN : rien de plus ») -> confond de phenotype")
    ap.add_argument("--no-freeze", dest="freeze", action="store_false",
                    help="laisse la plasticite intra-vie ecraser le genome cable -> (ii) ECHOUE")
    ap.add_argument("--out", default=None,
                    help="fichier JSON ou persister lignes + verdict (defaut : results/evo011_preflight"
                         "[_smoke].json ; `--out -` desactive)")
    ap.add_argument("--break-insitu", dest="insitu_h0", action="store_true",
                    help="CONTRE-EXEMPLE de (i+) : lit la decision hors regime (H=0, recurrent_forward) "
                         "au lieu du seam batch -> (i+) ECHOUE")
    args = ap.parse_args(argv)

    # --- LA REGLE EST LUE ET VERIFIEE AVANT TOUTE MESURE ------------------------------------------
    from tools.preregister import verify
    rule = verify(PREREG)
    _assert_rule_matches_code(rule)
    print(f"[preregistration] {PREREG} : sceau VERIFIE, seuils du code confrontes au sceau -> OK")

    from tools.experiment_preflight import declare_design, assert_control_family
    # GARDE E23 : la famille de controles est celle que la regle -bis SCELLE -- 2 types x 12 seeds.
    # Le seuil par cellule qui en sort DOIT etre celui que le code applique (ALPHA_CELL), sinon la
    # declaration serait decorative : on le VERIFIE ici, pas ailleurs.
    famille = assert_control_family(cells=FAMILY_CELLS, alpha_family=ALPHA_FAMILY,
                                    alpha_cell=ALPHA_CELL, method="bonferroni")
    assert abs(famille["alpha_cell"] - ALPHA_CELL) < 1e-15, (
        "le seuil declare et le seuil applique ont divergé -- la declaration serait decorative")
    design = declare_design(
        control_family=famille,
        question=rule["question"],
        replication_unit="seed (les 24 agents d'un bras-seed sont des CLONES partageant le monde)",
        n_independent=(1 if args.smoke else args.seeds),
        links={"obs[4] -> logits[8]": "measured",           # (i) in situ + (i+) identite de decision
               "logits[8] -> lancer execute": "measured",   # `throws` vs `throw_decided`
               "lancer -> proie stunned": "measured",       # `throw_prey_hits`, `stunned_by_type`
               "stun -> proie immobilisee": "measured",     # `stunned_by_type` + kills par type
               "stun -> melee sans riposte": "measured",    # `riposte_hp` (encaisse) + morts par hp
               "melee -> survie": "measured"},              # DV primaire
        cost_estimate=f"<= {MAX_AGENT_TICKS} agent-ticks par bras-seed, plafond {SEED_BUDGET_S:.0f} s/seed")
    print(f"[design] unite = {design['replication_unit']}")

    n = 1 if args.smoke else args.seeds
    rows, t0 = [], time.time()
    from tools.jobs.run import hold
    with hold("kuzu", owner="evo011-prevol-smoke" if args.smoke else "evo011-prevol", ttl_s=1800):
        for s in range(n):
            print(f"  seed {s} :")
            rows.append(run_seed(s, ballast=args.ballast, ticks=args.ticks,
                                 n_agents=args.agents, verbose=True, freeze=args.freeze,
                                 insitu_h0=args.insitu_h0))
    elapsed = time.time() - t0

    print("\n  --- CONTROLES ((i)-(vi) SCELLES ; (i+)/(i-bis)/(vii)/(viii) AJOUTES PAR LA REVUE) ---")
    for r in rows:
        d = r.get("detail", {})
        if d:
            print(f"    seed {r['seed']} saillance : " +
                  " ".join(f"{a}={d['sal'][a]:.3f}" for a in ARMS))
            print(f"    seed {r['seed']} P(throw|type VRAI) : " +
                  " | ".join(f"{a}: " + " ".join(f"{k}={r['res'][a]['profile'][k]:.3f}"
                                                 f"(n={r['res'][a]['n_by_type'].get(k, 0)})"
                                                 for k in ("+1", "-1", "0"))
                             for a in ARMS))
            print(f"    seed {r['seed']} P(throw|type VU)   : " +
                  " | ".join(f"{a}: " + " ".join(f"{k}={r['res'][a]['profile_seen'][k]:.3f}"
                                                 f"(n={r['res'][a]['n_by_type_seen'].get(k, 0)})"
                                                 for k in ("+1", "-1", "0"))
                             for a in ARMS))
            print(f"    seed {r['seed']} (i+) decisions lues == decidees : "
                  f"{ {a: (not r['res'][a]['decision_mismatch']) for a in ARMS} } | ecart batch-vs-"
                  f"recurrent (E6) : { {a: (round(r['res'][a]['e6_gap'], 4), r['res'][a]['e6_n'], r['res'][a]['e6_sign_agree']) for a in ARMS} }")
            print(f"    seed {r['seed']} (vii) port a age apparie {CARRY_AGE_WINDOW} : {d['carry_matched']} "
                  f"-> {d.get('carry_gap_energy_frac')} du drain | port vie entiere (BIAISE par la "
                  f"duree de vie) : {d['carry_lifetime']}")
            print(f"    seed {r['seed']} (viii) empreinte monde+RNG a t=0 : {d['fingerprint']}")
            print(f"    seed {r['seed']} censure : {d['censure']} | ages au plafond : {d['age_at_cap']} "
                  f"| life_score dev : {d['life_score_max_dev']} | aretes : {d['edges']}")
            print(f"    seed {r['seed']} phenotype IN SITU : {d['phenotype_insitu']}")
            print(f"    seed {r['seed']} derive du genome (max|W-W0|) : {d['w_drift']}")
        print(f"    seed {r['seed']} -> {'TOUS PASSES' if not r['control_failures'] else 'ECHECS :'}")
        for f in r["control_failures"]:
            print(f"        - {f}")
        for f in r.get("saturation", []):
            print(f"        [SATURATION, non bloquant] {f}")

    v = verdict_evo011_prevol(rows)
    print(f"\n  VERDICT : {v['verdict']}  (r={v['r']:.3f} sign_p={v['sign_p']:.3g} n={v['n_seeds']})")
    for why in v["raisons"][:4]:
        print(f"      raison : {why}")
    if v["discrimination"]:
        print(f"  sous-lecture DISCRIMINATION : {v['discrimination']} "
              f"(r={v['r_disc']:.3f} sign_p={v['sign_p_disc']:.3g})")
    print("  DV secondaires (rapportees dans TOUS les cas) :")
    for r in rows:
        for a in ARMS:
            x = r["res"][a] if "res" in r else None
            if x:
                print(f"    seed {r['seed']} {a:9s} decided={x['throw_decided']} throws={x['throws']} "
                      f"hits={x['throw_hits']} prey_hits={x['throw_prey_hits']} "
                      f"agent_hits={x['throw_agent_hits']} big_kills={x['big_kills']} "
                      f"sum(mammoth_kills)={x['mammoth_kills']} leurre_hits={x['leurre_hits']} "
                      f"apex {x['apex0']}->{x['apex_end']} equips={x['equips']} scrambled={x['n_scrambled']}")
                print(f"        {'':9s} bilan energie (somme cohorte) {x['energy_phases']} "
                      f"-> cout ACTION par lancer = {x['energy_action_per_throw']:.2f} energie")
                print(f"        {'':9s} preys_eaten={x['preys_eaten']} kills_by_type={x['kills_by_type']} "
                      f"stunned_by_type={x['stunned_by_type']} riposte_hp={x['riposte_hp']:.0f} "
                      f"(hp_depart={x['hp_start']:.0f}) morts energie/hp={x['died_energy']}/{x['died_hp']} "
                      f"ages={x['ages'][:6]}...{x['ages'][-3:]}")

    # --- (iii) project_cost APRES le smoke --------------------------------------------------------
    unit = elapsed / max(1, n)
    print(f"\n  COUT : {elapsed:.1f}s pour {n} seed(s) -> {unit:.1f} s/seed")
    from tools.cost_guard import project_cost, CostTooHighToStart
    try:
        p = project_cost(unit_s=unit, n_units=SEALED_SEEDS, budget_s=TOTAL_BUDGET_S,
                         label=f"EVO-011-PREVOL {SEALED_SEEDS} seeds")
        print(f"  project_cost({SEALED_SEEDS} seeds, marge x3) = {p / 60:.1f} min <= budget "
              f"{TOTAL_BUDGET_S / 60:.0f} min -> TENABLE")
    except CostTooHighToStart as e:
        print(f"  project_cost REFUSE : {e}")

    # --- PERSISTANCE ------------------------------------------------------------------------------
    # Un verdict qu'on ne peut pas RECALCULER n'est pas verifiable : on ecrit les lignes PAR SEED
    # (l'unite de replication), le verdict, le sceau et le regime. `verdict_evo011_prevol` etant PUR,
    # ce fichier suffit a rejouer la lecture sans relancer une seule simulation.
    out = args.out
    if out != "-":
        if out is None:
            out = os.path.join("results", "evo011_preflight%s.json" % ("_smoke" if args.smoke else ""))
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({
                "preregistration": PREREG,
                "rule_hash": rule.get("_hash") or rule.get("hash"),
                "design": design,
                "regime": {"seeds": n, "n_agents": args.agents, "ticks": args.ticks,
                           "energy0": ENERGY0, "ballast": args.ballast, "freeze": args.freeze,
                           "insitu_h0": args.insitu_h0, "smoke": bool(args.smoke)},
                "elapsed_s": elapsed,
                "verdict": v,
                "rows": rows,
            }, fh, indent=1, default=str)
        print(f"  persiste -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
