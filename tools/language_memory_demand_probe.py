"""AGI-Taxonomy — MESURE de l'arête « language demands memory » (delayed-code-application).

Un MÊME agent (tête d'action à 8 logits partagée, `_MOVE_LOGITS=8`) apprend DEUX capacités
distinguées par les slots actifs de l'observation : LANG = `(q+key)%K` (nécessite le `key` RETENU
via l'état récurrent H PORTÉ encode -> délai -> quête) ; CONTROL = copier `c` (feedforward,
1 tick, indépendant de la mémoire). Ablation SUBSTRAT = reset de H à l'usage (efface le portage) ;
c'est la 1ʳᵉ ablation SUBSTRAT du graphe AGI-Taxonomy (les 2 arêtes précédentes ablataient
l'ENTRÉE, `functional_aliasing='n/a'`) — ici le garde CALIB-ALIAS `functional_aliasing` DOIT être
MESURÉ ('pass'/'fail'), jamais 'n/a' : `ablation_verdict` sur LANG (X_DEMANDED si la rétention
porte la réponse) ; leakage sur CONTROL (bouge-t-il aussi sous le même reset ? si oui, l'ablation
n'est pas chirurgicale, SURGICAL/FUNCTIONAL_LEAK/VACUOUS_ABLATION/DEGENERATE_CONTROL cf.
`alias_guard_verdict` et `run_language_memory_demand_probe`).

⚠️ GARDE DE DÉGÉNÉRESCENCE DU BRAS CONTROL (armée le 2026-09-01, revue adversariale). Jusqu'ici
`functional_aliasing='pass'` ne demandait QUE `leakage <= tol` — SANS jamais vérifier que le bras
CONTROL est VIVANT. C'est exactement le motif E3 que `_degeneracy` (tools/demand_marker.py:18-66)
bloque sur le bras PRINCIPAL et que ce chemin contournait. Les deux dégénérescences sont ATTESTÉES,
pas hypothétiques, et produisent toutes deux `leakage = 0` MÉCANIQUEMENT :
  * PLANCHER — `train_control=False` n'entraîne JAMAIS CONTROL : deux mesures de hasard, écart nul
    garanti par construction (docs/EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md:120-124,
    « `functional_aliasing="pass"` y est **vide de sens** ») ;
  * PLAFOND — `train_control=True, D=0` : `control_intact = control_ablated = [1.0, 1.0, 1.0]`
    (results/lang_memory_diagnostic.json:30, « CONTROL sature et reste chirurgical (leakage=0.0) »).
Le critère commun est l'AMPLITUDE DISPONIBLE : si les deux bras tiennent dans une bande de largeur
`tol` contre une borne, `leakage <= tol` est ARITHMÉTIQUEMENT FORCÉ et le 'pass' ne mesure rien.

⚠️ Vérifié contre le code réel (`src/agents/backend_torch.py`, comme `memory_perception_demand_probe.py`) :
`TorchPopulationModel.forward(x)` renvoie `(logits, 0)` — le 2e élément est un PLACEHOLDER entier, PAS
l'état — et `forward` met déjà à jour `self.H` EN INTERNE (`self.H = H_new.detach()`). NE PAS réassigner
`agent.H` depuis le retour de `forward` (l'entier 0 écraserait la récurrence). Readout =
`np.asarray(logits)[:, :K].argmax(axis=1)`. `learn_episode(obs_seq, actions_seq, rewards,
gate_last_only=True)` REJOUE la séquence depuis un `H` LOCAL initialisé à zéro (détaché à chaque pas —
crédit 1-pas, la valeur PORTÉE traverse quand même la séquence en avant) : il NE dépend PAS de
`agent.H` externe, donc un `_reset_H(agent)` avant `learn_episode` est un no-op inoffensif — mais reste
INDISPENSABLE avant les `agent.forward(...)` utilisés pour ÉCHANTILLONNER l'action créditée (ceux-là
LISENT et ÉCRIVENT `agent.H`), sinon un trial fait fuir son état résiduel dans le suivant.

⚠️ DIVERGENCE avec le brief initial, CORRIGÉE ici : le brief créditait la RÉPONSE CIBLE (`tgt`) comme
« action prise », pondérée par l'avantage centré `(guess==tgt)-mean`. C'est un REINFORCE mal posé — les
agents qui se TROMPENT (avantage négatif) reçoivent alors un gradient qui POUSSE la probabilité de la
BONNE réponse VERS LE BAS (puisque `loss = -(R * logp).mean()` et `R<0`). Corrigé en créditant le GUESS
RÉELLEMENT ÉCHANTILLONNÉ (comme `memory_perception_demand_probe.py`, motif REINFORCE standard déjà
calibré) : avantage positif renforce le guess qui a marché, avantage négatif le décourage — jamais
l'inverse de la bonne réponse.

⚠️ POUR LA TÂCHE 2 (run-verdict) : au smoke (Task 1), `lang_intact` (mode `memory_mode="learned"`) reste
COLLÉ AU PLANCHER (~0.15-0.33, floor=1/K) sur un balayage large — `learn_episode` tronqué 1-pas (D∈{0,1,2},
lr∈{0.02,0.05,0.1}, jusqu'à 3000 épisodes), `learn_episode_bptt(truncate=False)` (BPTT réel, D∈{1,2},
1200 épisodes), ET `imitate_episode_bptt` SUPERVISÉ+BPTT+masqué sur le dernier pas (D∈{0,1}, jusqu'à
lr=0.05/5000 épisodes) — AUCUNE de ces variantes ne fait décoller LANG au-dessus de 1/K+0.15, y COMPRIS
à D=0 (query immédiatement après l'encodage, donc PAS un problème de rétention sur le délai : c'est la
COMBINAISON `(q+key)%K` de deux one-hot injectés à des ticks séparés qui semble dure à représenter/
apprendre pour ce substrat dans ces budgets, indépendamment de la méthode de crédit). `CONTROL`, lui,
APPREND bien (médianes 0.54-0.61 après le correctif d'alignement train/éval ci-dessus, >> 1/K+0.15) —
la tête d'action PARTAGÉE n'empêche donc PAS l'apprentissage en soi. La calibration (oracle/aléatoire/
leaky, ce module) est INDÉPENDANTE de ce risque (elle bypasse l'agent) et reste valide. Avant de lancer
le run n=12, la Tâche 2 devrait soit élargir encore la recherche d'hyperparamètres (episodes/lr/D/n_agents),
soit envisager une tâche de combinaison plus simple, soit documenter un NULL honnête (précédent :
`specificity_control` de MEM-PERCEPTION, EDR-MEM-PERCEPTION) — ne pas forcer.

Le nom `run_*probe` trippe le cliquet -> calibré (oracle/aléatoire/leaky) dans
`tests/sandbox/test_instrument_calibration.py`. Pur torch CPU, aucun bail.
Usage : python tools/language_memory_demand_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.demand_marker import ablation_verdict


def _slot(idx, K, offset, I, n_agents):
    """one-hot de idx dans les slots [offset:offset+K] d'un vecteur d'obs (I,)."""
    m = np.zeros((n_agents, I), dtype=np.float32)
    m[np.arange(n_agents), offset + (idx % K)] = 1.0
    return m


def _zeros(I, n_agents):
    return np.zeros((n_agents, I), dtype=np.float32)


def _reset_H(agent):
    import torch
    agent.H = torch.zeros((agent.W.shape[0], agent.N))


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sample(preds, n, rng, n_agents):
    p = _softmax(np.asarray(preds)[:, :n])
    return np.array([rng.choice(n, p=pi) for pi in p])


def _carry(agent, key, K, I, n_agents, D, rng):
    """Reset H puis encode(key) + D ticks de délai. H porte le key retenu (MAJ interne de self.H
    à chaque forward). Contexte PARTAGÉ pour l'éval LANG et CONTROL (même substrat ablaté)."""
    _reset_H(agent)
    agent.forward(_slot(key, K, 0, I, n_agents))               # encodage (slots [0:K])
    for _ in range(D):
        agent.forward(_zeros(I, n_agents))                     # délai (H porté, MAJ interne)


def _lang_move(agent, q, K, I, n_agents):
    """Forward LANG (quête aux slots [K:2K]) -> guess = argmax(logits[:, :K])."""
    logits, _ = agent.forward(_slot(q, K, K, I, n_agents))
    return np.asarray(logits)[:, :K].argmax(axis=1)


def _control_move(agent, c, K, I, n_agents):
    """Forward CONTROL (cible aux slots [2K:3K]) -> guess = argmax(logits[:, :K])."""
    logits, _ = agent.forward(_slot(c, K, 2 * K, I, n_agents))
    return np.asarray(logits)[:, :K].argmax(axis=1)


def alias_guard_verdict(control_intact, control_ablated, x_response, floor, ceiling=1.0,
                        tol=0.05, alive_margin=None, intervention_verified=True):
    """Garde CALIB-ALIAS sur le bras CONTROL : l'ablation est-elle CHIRURGICALE — et la question
    a-t-elle seulement un sens sur ce bras ? Fonction de décision PURE (aucun entraînement, aucun
    torch) : elle ne prend que les accuracies par seed, ce qui la rend calibrable numériquement.

    Décision (ordre significatif, il encode « la dégénérescence n'invalide que le NUL », cf. note de
    conception de `ablation_verdict`) :
      1. `x_response <= tol`  -> VACUOUS_ABLATION : l'ablation ne mord même pas le bras PRINCIPAL,
         parler de chirurgie n'a pas de sens (comportement historique, inchangé) ;
      2. `leakage > tol`      -> FUNCTIONAL_LEAK : le CONTROL bouge sous le même reset -> 'fail'
         (comportement historique, inchangé — un POSITIF de fuite n'a pas besoin d'un bras vivant :
         un bras qui BOUGE est vivant par définition) ;
      3. bras CONTROL DÉGÉNÉRÉ -> DEGENERATE_CONTROL : `leakage <= tol` est arithmétiquement forcé,
         le 'pass' serait vide de sens -> 'fail' (NOUVEAU, 2026-09-01) ;
      4. sinon                -> SURGICAL -> `functional_aliasing='pass'`.

    ⚠️ POURQUOI L'ÉTAPE 3 (motif E3, cf. docstring du module). `leakage = |med(ci) - med(ca)|` était
    lu comme « pas d'effet » alors qu'un bras COLLÉ À UNE BORNE le rend nul MÉCANIQUEMENT. Trois
    façons de le dire, une seule règle : le bras CONTROL doit disposer d'une AMPLITUDE d'au moins
    `alive_margin` pour qu'une fuite de taille `tol` soit seulement OBSERVABLE.
      - PLANCHER : `med(ci) <= floor + marge` -> CONTROL jamais appris (config `train_control=False`,
        EDR-LANG-MEMORY:120-124) : deux mesures de hasard, rien à faire fuir.
      - PLAFOND : `med(ci)` ET `med(ca)` `>= ceiling - marge` -> les deux bras tiennent dans une bande
        de largeur `marge`, donc `leakage <= marge` est FORCÉ (cas attesté `[1.0]*3` vs `[1.0]*3`,
        results/lang_memory_diagnostic.json:30).
      - GÉNÉRAL : le `why` de `_degeneracy` via `ablation_verdict(ci, ca, floor=…, ceiling=…)`, avec
        les MÊMES bornes que le bras principal — toute règle future de `_degeneracy` s'applique donc
        ici sans nouvelle modification.
    `intervention_verified=True` par défaut : c'est la MÊME intervention (H-reset) que celle attestée
    sur le bras principal, et le bras CONTROL est ATTENDU X_DECOY — bloquer des bras identiques ici
    reviendrait à refuser la réponse même qu'on cherche (cas (b) de `_degeneracy`).

    ⚠️ APPARIEMENT PAR SEED (`leak_seeds`). `leakage` est une différence de MÉDIANES AGRÉGÉES, alors
    que `demand_marker` est explicitement l'instrument WITHIN-SUBJECT et que la SÉPARATION PAR SEED
    (« 12/12 seeds à recouvrement ZÉRO ») porte les verdicts gravés du graphe. Une médiane agrégée à
    0.03 est INDISCERNABLE entre une chirurgie propre (12 seeds à ~0.03) et 4 seeds qui fuient à 0.20
    noyés par 8 seeds à 0.00 : la médiane écrase l'appariement, la fuite survit dans les seeds.
    `leak_seeds` = nombre de seeds où `ci - ca > tol` (fuite DIRECTIONNELLE : le CONTROL se dégrade
    quand on efface l'état) ; `leak_seeds_two_sided` compte `|ci - ca| > tol`.
    ⚠️ CETTE MESURE N'ENTRE PAS DANS LA DÉCISION, délibérément : aucun seuil par seed n'est étalonné
    ici (combien de seeds fuyants rendent une ablation non chirurgicale ? la réponse dépend du n et
    du bruit d'échantillon, et l'inventer produirait un instrument non calibré de plus). Elle est
    EXPOSÉE pour que le lecteur du verdict voie l'appariement ; un `alias_verdict='SURGICAL'` avec
    `leak_seeds > 0` doit être regardé, pas gravé tel quel.
    """
    ci = [float(x) for x in control_intact]
    ca = [float(x) for x in control_ablated]
    if not ci or not ca:
        raise ValueError("alias_guard_verdict : bras CONTROL vide (rien à garder)")
    m = tol if alive_margin is None else float(alive_margin)
    med_i, med_a = float(np.median(ci)), float(np.median(ca))
    leakage = abs(med_i - med_a)
    per_seed = [a - b for a, b in zip(ci, ca)]
    leak_seeds = int(sum(1 for d in per_seed if d > tol))
    leak_seeds_two_sided = int(sum(1 for d in per_seed if abs(d) > tol))

    ctrl = ablation_verdict(ci, ca, intervention_verified=intervention_verified,
                            floor=floor, ceiling=ceiling)
    reasons = []
    if ctrl["why"]:
        reasons.append(f"_degeneracy(bras CONTROL) : {ctrl['why']}")
    if floor is not None and med_i <= floor + m:
        reasons.append(f"CONTROL jamais appris : médiane intacte {med_i:g} <= plancher {floor:g} "
                       f"+ marge {m:g} — deux mesures de hasard, leakage {leakage:g} sans contenu")
    if ceiling is not None and med_i >= ceiling - m and med_a >= ceiling - m:
        reasons.append(f"CONTROL SATURÉ : médianes {med_i:g}/{med_a:g} >= plafond {ceiling:g} "
                       f"- marge {m:g} — leakage <= {m:g} est arithmétiquement FORCÉ")
    why = " ; ".join(reasons) or None

    if x_response <= tol:
        alias = "VACUOUS_ABLATION"
    elif leakage > tol:
        alias = "FUNCTIONAL_LEAK"
    elif why:
        alias = "DEGENERATE_CONTROL"
    else:
        alias = "SURGICAL"
    return {"functional_aliasing": "pass" if alias == "SURGICAL" else "fail",
            "alias_verdict": alias, "leakage": leakage, "x_response": float(x_response),
            "leak_seeds": leak_seeds, "leak_seeds_two_sided": leak_seeds_two_sided,
            "leak_per_seed": per_seed, "control_intact_median": med_i,
            "control_ablated_median": med_a, "control_degenerate": bool(why),
            "control_why": why, "control_demand": ctrl,
            "alias_tol": float(tol), "alive_margin": float(m)}


def _train_and_eval(seed, episodes, n_agents, K, D, lr, memory_mode, control_mode, eval_batches=40,
                     train_control=True, weight_decay=0.0, bilinear=True):
    """Entraîne l'agent (learned) sur LANG+CONTROL interleavés (même tête d'action, même W), puis
    évalue LANG et CONTROL intact vs H-reset. Renvoie (lang_i, lang_a, ctrl_i, ctrl_a) = accuracies.

    Crédit REINFORCE standard : le GUESS échantillonné (pas la cible) est l'« action prise »,
    pondérée par l'avantage centré (guess correct -> avantage>0 -> renforce ce guess). Les ticks
    intermédiaires (encode/délai) portent une action neutre `{"move": 0}` mais reçoivent le MÊME
    retour épisodique (`gate_last_only=True` ne pilote que le gate, désactivé ici ; le crédit
    d'action, lui, s'applique à CHAQUE pas via `total_logp`, cf. `learn_episode`).

    `train_control=False` (Tâche 2, levier 1 : isoler l'interférence de tête partagée) SAUTE le
    bloc d'entraînement CONTROL -> seul LANG entraîne W. Défaut True = comportement Tâche 1 inchangé
    (calibration non affectée : oracle/random/leaky utilisent episodes=0, ce bloc n'exécute jamais).
    `weight_decay` (Tâche 2, levier 2 : grokking) est threadé dans le constructeur Adam ; défaut 0.0
    = comportement Tâche 1 inchangé (Adam sans decay)."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)
    # ⚠️ P2.14 (2026-09-02) : BILINEAR rejoint le try/finally. La sonde d'origine ne sauvait que
    # (CONDITION_GATE, GATE_TARGET) -> BILINEAR n'etait JAMAIS active et la sonde mesurait le substrat
    # PLAIN, prouvablement incapable de (q+key)%K (plafond structurel 0.3889, P2.15). Son negatif etait
    # correct POUR SON SUBSTRAT — caduc depuis EDR-BILINEAR + EDR-RETAIN-COMPOSE-LR (0.923, 12/12).
    # Le flag doit etre pose AVANT make_population : les params U/V/W_bl ne sont crees qu'a la
    # construction (backend_torch.py:111).
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
             TorchPopulationModel.BILINEAR)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    TorchPopulationModel.BILINEAR = bool(bilinear)
    try:
        agent = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I = agent.I
        rng = np.random.RandomState(seed + 1)
        learned = memory_mode == "learned"
        if learned:
            # P2.14 : l'optimiseur couvre le substrat COMPLET. `[agent.W]` seul laissait U/V/W_bl
            # geles a leur init meme avec BILINEAR actif -> le terme qui debloque la composition
            # n'aurait jamais appris.
            params = [agent.W] + [p for p in (agent.U, agent.V, agent.W_bl) if p is not None]
            agent.opt = torch.optim.Adam(params, lr=lr, weight_decay=weight_decay)
            for _ in range(episodes):
                # --- trial LANG : encode(key) + délai + usage(query) -> (q+key)%K ---
                key = rng.randint(0, K, size=n_agents)
                q = rng.randint(0, K, size=n_agents)
                _reset_H(agent)
                enc = _slot(key, K, 0, I, n_agents)
                seq = [enc] + [_zeros(I, n_agents) for _ in range(D)] + [_slot(q, K, K, I, n_agents)]
                logits = None
                for x in seq:
                    logits, _ = agent.forward(x)                # forward() porte agent.H en interne
                guess = _sample(logits, K, rng, n_agents)
                tgt = (q + key) % K
                adv = (guess == tgt).astype(np.float32); adv = adv - adv.mean()
                acts = [[{"move": 0} for _ in range(n_agents)] for _ in range(len(seq) - 1)]
                acts.append([{"move": int(g)} for g in guess])  # crédit du GUESS échantillonné
                agent.learn_episode(seq, acts, adv, gate_last_only=True)

                if not train_control:
                    continue  # levier Tâche 2 #1 : isoler l'interférence de tête partagée -> W ne voit que LANG

                # --- trial CONTROL : encode(nuisance) + délai + usage(control) -> c (feedforward) ---
                # ⚠️ CORRIGÉ : entraîner CONTROL sur H=0 pur (reset direct avant le tick unique) désaligne
                # l'entraînement de l'ÉVAL, qui porte `c` sur le MÊME contexte que LANG (`_carry`, H non nul
                # à l'intact). Sans ça, l'agent apprend « CONTROL sous H=0 », et à l'éval intact (H≠0,
                # hors-distribution) performe PIRE que sous ablation (H=0, distribution d'entraînement) —
                # un artefact qui inverserait le sens de la mesure de fuite. Ici la clé de nuisance est
                # DÉCOUPLÉE de `c` (comme le leurre PRESENT de MEM-PERCEPTION) : le gradient n'a aucune
                # raison d'utiliser H, donc CONTROL apprend à ÊTRE feedforward et voit la MÊME distribution
                # qu'à l'éval (carried H).
                nuisance = rng.randint(0, K, size=n_agents)
                c = rng.randint(0, K, size=n_agents)
                _reset_H(agent)
                cenc = _slot(nuisance, K, 0, I, n_agents)
                cseq = [cenc] + [_zeros(I, n_agents) for _ in range(D)] + [_slot(c, K, 2 * K, I, n_agents)]
                clog = None
                for x in cseq:
                    clog, _ = agent.forward(x)
                cguess = _sample(clog, K, rng, n_agents)
                cadv = (cguess == c).astype(np.float32); cadv = cadv - cadv.mean()
                cacts = [[{"move": 0} for _ in range(n_agents)] for _ in range(len(cseq) - 1)]
                cacts.append([{"move": int(g)} for g in cguess])
                agent.learn_episode(cseq, cacts, cadv, gate_last_only=True)

        def _eval_lang(ablate):
            hits = []
            for _ in range(eval_batches):
                key = rng.randint(0, K, size=n_agents); q = rng.randint(0, K, size=n_agents)
                _carry(agent, key, K, I, n_agents, D, rng)
                if ablate:
                    _reset_H(agent)                              # ABLATION MÉMOIRE : efface le key retenu
                if memory_mode == "oracle":
                    g = ((q + key) % K) if not ablate else rng.randint(0, K, size=n_agents)  # key parfait vs perdu
                elif memory_mode == "random":
                    g = rng.randint(0, K, size=n_agents)
                else:
                    g = _lang_move(agent, q, K, I, n_agents)
                hits.append((g == ((q + key) % K)).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        def _eval_control(ablate):
            hits = []
            for _ in range(eval_batches):
                key = rng.randint(0, K, size=n_agents); c = rng.randint(0, K, size=n_agents)
                _carry(agent, key, K, I, n_agents, D, rng)       # même contexte porté que LANG
                if ablate:
                    _reset_H(agent)
                if control_mode == "leaky":
                    # CONTROL forcé de dépendre du key retenu -> ablater fait FUIR (vérité-terrain du garde)
                    g = c if not ablate else rng.randint(0, K, size=n_agents)
                elif memory_mode in ("oracle", "random"):
                    g = c                                        # contrôle feedforward parfait (bypass)
                else:
                    g = _control_move(agent, c, K, I, n_agents)
                hits.append((g == c).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        return _eval_lang(False), _eval_lang(True), _eval_control(False), _eval_control(True)
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
         TorchPopulationModel.BILINEAR) = saved


def run_language_memory_demand_probe(seeds, episodes=1200, n_agents=16, K=6, D=2, lr=0.02,
                                     memory_mode="learned", control_mode="feedforward",
                                     train_control=True, weight_decay=0.0, bilinear=True):
    """Mesure « language demands memory ». Par seed : LANG et CONTROL, chacun éval intact/ablé (H-reset).
    LANG -> ablation_verdict (X_DEMANDED) ; CONTROL -> `alias_guard_verdict` (leakage≈0 sur un bras
    VIVANT -> pass ; bras collé à une borne -> DEGENERATE_CONTROL, pas un 'pass' silencieux),
    1er usage réel du jalon CALIB-ALIAS sur une ablation SUBSTRAT — les 2 arêtes précédentes du graphe
    AGI-Taxonomy ablataient l'ENTRÉE, `functional_aliasing='n/a'`.
    Le dict renvoyé fusionne celui de `alias_guard_verdict` : outre `functional_aliasing`/`alias_verdict`/
    `leakage`, il porte `leak_seeds` (appariement PAR SEED, hors décision), `control_degenerate` et
    `control_why`.

    `train_control` / `weight_decay` : knobs diagnostiques Tâche 2 (défauts = comportement Tâche 1
    inchangé), cf. docstring de `_train_and_eval`."""
    li, la, ci, ca = [], [], [], []
    for s in seeds:
        l_i, l_a, c_i, c_a = _train_and_eval(s, episodes, n_agents, K, D, lr, memory_mode, control_mode,
                                             train_control=train_control, weight_decay=weight_decay, bilinear=bilinear)
        li.append(l_i); la.append(l_a); ci.append(c_i); ca.append(c_a)

    floor = 1.0 / K
    lang = ablation_verdict(li, la, intervention_verified=True, floor=floor, ceiling=1.0)
    x_response = abs(float(np.median(li)) - float(np.median(la)))
    tol = 0.05                                                  # tolérance de fuite (bruit d'échantillon)
    guard = alias_guard_verdict(ci, ca, x_response, floor=floor, ceiling=1.0, tol=tol)
    out = {"lang_demand": lang, "n": len(seeds),
           "lang_intact": li, "lang_ablated": la, "control_intact": ci, "control_ablated": ca}
    out.update(guard)                                           # fa, alias_verdict, leakage, leak_seeds…
    return out


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("LM_SEEDS", "12"))))
    r = run_language_memory_demand_probe(seeds, episodes=int(os.environ.get("LM_EPISODES", "1200")),
                                         n_agents=int(os.environ.get("LM_AGENTS", "16")))
    print(json.dumps({k: v for k, v in r.items()
                      if k in ("lang_demand", "functional_aliasing", "alias_verdict", "leakage",
                               "x_response", "n", "leak_seeds", "control_degenerate", "control_why",
                               "control_intact_median", "control_ablated_median")},
                     ensure_ascii=False, indent=2))
