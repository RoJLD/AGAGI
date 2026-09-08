# B2 — Câblage du throw-gate in-world (cran 2, biosphère) — Design

**Date :** 2026-07-10
**Fil :** Axe 1 (intégration torch in-world), cran 2, Brique B2. Suite d'EDR-171 (B1).
**Statut :** design approuvé (brainstorm), en attente de relecture avant plan.

## But

Prouver que le mécanisme de gate binaire — validé EN ISOLATION par EDR-171 (B1) — tient
dans la VRAIE boucle biosphère : router l'action « ends » (throw, logit 8) sur un contexte
DISTRIBUÉ (spear-en-inventaire, porté par l'état caché `H` via la vraie dynamique, pas un
canal propre injecté verbatim comme en B1), renforcé par l'OUTCOME réel (kills-avec-outil),
avec un TÉMOIN shuffle qui sépare routage réel et artefact (leçon 169→171).

Ce que B2 ajoute au-dessus de B1 : le contexte n'est plus un scalaire propre `obs_b[:,0]` mais
la présence-spear portée par la récurrence à travers l'obs biosphère réelle ; le crédit n'est
plus un `_energy_binary` synthétique mais l'outcome balistique réel du monde.

## Contraintes globales

- **Path-scopé `world_1_stoneage.py` + banc/test neufs.** ZÉRO modification de
  `src/agents/backend_torch.py` (owned par une session parallèle ; cf.
  `parallel-sessions-shared-tree`). `git add` explicite des seuls fichiers touchés, jamais `-A`.
- **Flag-par-flag (Commandement 15).** Toute la Brique B2 est gardée par
  `use_torch_inworld AND torch_throw_gate`. `torch_throw_gate=False` (défaut) ⇒ crans 0-1
  strictement inchangés ; `use_torch_inworld=False` (défaut) ⇒ legacy strictement non-régressif.
- **Cohorte fixe.** `use_torch_inworld` exige déjà `benchmark_mode=True` (dims homogènes,
  garde I1 existante). B2 hérite cette contrainte.
- **Style :** français, concis, pas d'emojis. TDD, commits path-scopés fréquents.
- **W gelé.** Le throw-gate lit `H.detach()` — il ne rétro-propage PAS dans le tronc (mirroir B1).

## Architecture

### Où vit le gate

Une **tête apprise au niveau MONDE** (pas dans `backend_torch`), superposée au pop torch
persistant. Raison : le gate de `backend_torch` biaise les logits 0-7 (moves) ; le throw est le
logit 8, hors de son champ — et `backend_torch` est owned par une session //. Une tête
monde path-scopée est plus propre et sans risque de collision.

Attributs monde (init dans `__init__`, sous les knobs) :
- `self._throw_w` : `torch.zeros(N, requires_grad=True)` — readout PARTAGÉ population (N = dim
  cachée = `pop.N`, fixe malgré la mortalité). Zéro param par agent.
- `self._throw_b` : `torch.zeros(1, requires_grad=True)` — biais scalaire.
- `self._throw_opt` : `torch.optim.Adam([_throw_w, _throw_b], lr=torch_throw_gate_lr)`.
- Ces attributs sont créés paresseusement au 1er tick torch (quand `pop.N` est connu), pas
  dans `__init__` (où le pop n'existe pas encore).

### Knobs de config (défauts = comportement historique)

| Knob | Défaut | Rôle |
|---|---|---|
| `torch_throw_gate` | `False` | Active la tête throw-gate B2. |
| `torch_throw_gate_lr` | `0.05` | LR Adam de la tête (valeur B1). |
| `torch_throw_antisat` | `6.0` | Coefficient anti-saturation homéostatique (valeur B1). |
| `torch_throw_shuffle` | `False` | Bras TÉMOIN : entraîne la tête sur une récompense permutée. |

Le semis des spears est **au niveau du banc** (pas du monde) — voir §Découplage.

### Flux de données (par tick, sous `use_torch_inworld AND torch_throw_gate`)

1. **Forward (inchangé)** : `batch_logits, _ = batch_model.forward(...)` (ligne 1063). Comme
   `batch_model is self._torch_pop`, `self._torch_pop.H` est peuplé (shape `(B, N)`, B = vivants).
   Cache : `H = self._torch_pop.H.detach()`.
2. **Injection du biais (loop par-agent, avant le seuil throw ligne 1142)** :
   `z_i = float(H[idx] @ self._throw_w) + float(self._throw_b)` ajouté au logit throw :
   `p_throw_i = sigmoid(clamp(logits[8] + z_i, -10, 10))`.
3. **Décision STOCHASTIQUE sous le gate** : `do_throw = (rng.random() < p_throw_i)`.
   (Sous le gate SEULEMENT ; `torch_throw_gate=False` garde le seuil dur `logits[8] > 0`.)
   Le reste de la balistique throw (lignes 1223-1299) est inchangé.
4. **Enregistrement du crédit** : ajouter `"throw"` au dict `_pg` (ligne 1330) :
   `_pg = {"move":…, "grab":…, "rub":…, "throw": 1 if do_throw else 0}`. Enregistrer aussi sur
   l'agent le contexte et l'outcome pour la tête et le KPI :
   `agent["_throw_ctx"] = bool(has_spear(agent["inventory"]))` (AVANT le pop de l'inventaire),
   `agent["_throw_did"] = bool(do_throw)`, et l'outcome renseigné par la balistique
   (`throw_feedback` existant, + flag kill-avec-outil).
5. **Récompense de la tête** (`r_throw`, vecteur par agent vivant) :
   - a throw + hit une prey en tenant un spear → `+1.0` (kill-avec-outil : la cible).
   - a throw + miss (ou hit non-prey) → `−throw_gate_cost` (gâchis).
   - a throw SANS spear → `−throw_gate_cost` (throw faible/gâché).
   - pas de throw → `0.0` (baseline).
   (Le `throw_gate_cost` = `0.5` en dur, aligné sur l'esprit de `_energy_binary` de B1.)
6. **REINFORCE immédiat de la tête** (1-pas — l'outcome du throw est immédiat, contraste avec le
   crédit épisodique means→ends) sur les agents VIVANTS ce tick :
   ```
   r = r_throw ; if torch_throw_shuffle: r = r[self._throw_perm_restreint_aux_vivants]
   ret = r − r.mean()                     # baseline = moyenne population
   logp = did*log(p+1e-6) + (1-did)*log(1-p+1e-6)
   loss = -(ret * logp).mean() + torch_throw_antisat * p.mean()**2
   opt.zero_grad(); loss.backward(); opt.step()
   ```
   `p` et `did` sont ré-assemblés (torch) pour les agents vivants ; `p` est différentiable via
   `self._throw_w/_throw_b` (H détaché). Le shuffle permute le vecteur `r` PARMI les agents
   VIVANTS du tick, via une permutation seed-déterministe (`self._throw_shuf_rng`, `RandomState`
   fixe stocké à l'init) : reproductible mais décorrèle la récompense du contexte porté par H. Ré-
   tirée par tick sur le set vivant courant (évite le piège d'une permutation globale figée qui,
   filtrée aux vivants, ne serait plus une bijection).
7. **Compteurs KPI** : `self._throw_kills_tool += …`, et les records `agent["_throw_ctx"] /
   _throw_did` sont laissés lisibles par le banc pour agréger le binding_gap.

`learn` / `learn_episode` (crédit move/grab/rub) restent INCHANGÉS et coexistent : la tête
throw est un canal de crédit SÉPARÉ, immédiat, path-scopé.

## Découplage du mur du craft (décision de design, approuvée)

Le KPI kills-avec-outil exige une lance ; or le craft est un MUR non-retenu en cohorte fixe
(EDR-125/127). Si B2 exigeait l'émergence du craft, il hériterait ce mur ⇒ NEUTRE garanti,
indépendamment du gate. On **sème les spears exogènement AU NIVEAU DU BANC** :

- À la construction du monde, le banc ajoute un `{"type":"Spear","weight":2.0}` à l'inventaire
  de chaque agent.
- Entre deux `step()`, le banc RE-SÈME : tout agent vivant sans spear en récupère un avec
  probabilité `respawn_p` (défaut `0.5`). Cela produit un MÉLANGE dynamique spear / ¬spear à
  travers agents et temps (indispensable pour que `P(throw|spear)` ET `P(throw|¬spear)` soient
  toutes deux échantillonnées), et le contexte VARIE via la vraie dynamique (spear présent
  jusqu'à ce qu'il soit lancé) — c'est précisément le « contexte distribué » que B2 teste, vs le
  canal propre statique de B1.

Le semis reste hors de `world_1_stoneage.py` (path-scopé au banc) : le monde n'a besoin que de
LIRE `has_spear(inventory)` au moment de la décision (déjà disponible, helper ligne 709).

## Témoin (le joyau méthodo 169→171)

Deux bras, nombres aléatoires communs (CRN, même seed) :
- **ON** (`torch_throw_shuffle=False`) : la tête est entraînée sur la vraie récompense (outcome
  corrélé à la présence-spear via H).
- **SHUFFLE** (`torch_throw_shuffle=True`) : la tête est entraînée sur la récompense PERMUTÉE
  (permutation fixe entre agents) — décorrélée de la présence-spear portée par H ⇒ aucune règle
  généralisante à apprendre ⇒ gap attendu ~0.

Le binding_gap est TOUJOURS mesuré sur la VRAIE présence-spear et les VRAIES décisions throw,
dans les deux bras. C'est le contraste ON−SHUFFLE (pas la magnitude ON seule) qui tranche.

## KPI et verdict

Agrégés par le banc sur une fenêtre de mesure (derniers ticks, après warm-up de la tête) :
- **Primaire** : `binding_gap_inworld = P(throw | has_spear) − P(throw | ¬has_spear)`, agrégé sur
  tous les couples (agent, tick) de la fenêtre, sur la vraie présence.
- **Secondaire** : `kills_with_tool` (throws touchant une prey en tenant un spear),
  `throw_hit_rate` (hits / throws).
- **Verdict** : `compute_ab_verdict(rows, band=0.02)` sur `diff = gap_ON − gap_SHUFFLE` par seed.
  `GRADIENT_GAGNE` ⇒ `BINDING_INWORLD_REEL` ; `NEUTRE` ⇒ `PAS_DE_BINDING_INWORLD` ;
  `HEBBIEN_GAGNE` ⇒ `SHUFFLE_BINDE_PLUS` (drapeau rouge d'artefact).

## Composants (unités et interfaces)

1. **`world_1_stoneage.py` — tête throw-gate** (modif path-scopée) :
   - `_ensure_throw_gate()` : init paresseuse de `_throw_w/_throw_b/_throw_opt/_throw_perm` au 1er
     tick torch (quand `pop.N` connu). No-op si déjà init ou gate OFF.
   - Injection du biais + décision stochastique dans le loop d'action (entre 1102 et 1142).
   - `"throw"` ajouté à `_pg` ; records `_throw_ctx/_throw_did` sur l'agent.
   - `_learn_throw_gate(...)` : le REINFORCE immédiat (§Flux 5-6), appelé après le loop d'action,
     avant/à côté du bloc torch existant (1517-1531). Skip propre (log, pas de crash) si gate OFF,
     pop absent, ou B=0.
   - Compteur `self._throw_kills_tool`.
2. **`tools/torch_throw_gate_inworld_ab.py`** (neuf) :
   - `build_world(seed) -> Biosphere3D` : monde benchmark_mode + use_torch_inworld +
     torch_throw_gate, memory_retriever stoppé, cohorte fixe, spears semés.
   - `reseed_spears(world, rng, respawn_p)` : re-semis entre steps.
   - `run_arm(shuffle, seeds, ticks, warmup, ...) -> dict{binding_gap_inworld, kills_with_tool,
     throw_hit_rate, throw_rate}` : boucle step + reseed + agrégation fenêtre.
   - `compare(seeds, ...) -> dict{rows, verdict}` : diff = gap_ON − gap_SHUFFLE ; verdict.
   - `__main__` : env `TTG_SEEDS/TTG_TICKS/TTG_WARMUP`, imprime rows + verdict + interprétation.
3. **`tests/sandbox/test_torch_throw_gate_inworld_ab.py`** (neuf) :
   - smoke non-régression : `torch_throw_gate=False` ⇒ un `step()` legacy ne crashe pas, throw
     reste le seuil dur (comportement inchangé).
   - smoke gate : `run_arm` court (peu de ticks/agents) renvoie les clés attendues, gap ∈ [−1,1].
   - test verdict pur : `compute_ab_verdict` sur des `diff` positifs synthétiques ⇒ `GRADIENT_GAGNE`.

## Sûreté, non-régression, erreurs

- **Non-régression** : `torch_throw_gate=False` (défaut) ⇒ aucun des chemins B2 n'est atteint ;
  test de smoke legacy le prouve. `use_torch_inworld=False` ⇒ idem crans 0-1.
- **Pop désync / mortalité** : la tête est population-partagée (N fixe) ; le REINFORCE ne
  s'applique qu'aux vivants du tick (alignement identité pour la permutation shuffle). Skip propre
  si B=0 ou pop absent (log `TORCH_THROW_SKIP`, pas de crash).
- **KuzuDB ambiant** : le banc stoppe `env.memory_retriever` AVANT la boucle (repro, cf.
  `biosphere-ambient-memory-nonrepro`).
- **Effet plancher survie** : B2 ne mesure PAS la survie (KPI = binding_gap, pas AUC) ⇒ immunisé
  contre l'extinction précoce (leçon EDR-090/163).

## Hors périmètre (YAGNI)

- Émergence du craft (spears semés, pas craftés) — c'est délibéré (découplage du mur).
- Représentation distribuée « riche » au-delà de spear-en-inventaire (un seul contexte binaire).
- Toute modif de `backend_torch.py` ou du gate move-logits existant.
- Bras ON-vs-OFF (gate vs pas de gate) : lecture secondaire optionnelle, pas le témoin primaire.
- Portée sur les autres mondes / autres actions « ends ».

## Risques et parades

| Risque | Parade |
|---|---|
| `pop.N` / `pop.H` d'attribut/forme différents in-world | Pré-flight smoke AVANT dispatch : 1 `step()` torch, asserter `pop.H.shape == (B, pop.N)`. |
| Spears tous lancés tick 1 ⇒ plus de contexte spear | Re-semis probabiliste (`respawn_p`) ⇒ mélange dynamique soutenu. |
| Décision throw stochastique change trop la dynamique | Gardée sous le gate seulement ; CRN ON/SHUFFLE partagent le même monde de départ ⇒ le contraste isole l'effet gate. |
| n=seeds petit (p-value plafonnée) | L'effet-taille (diff vs bande) est le juge, comme EDR-171 ; viser 4+ seeds. |
| binding_gap gonflé par un canal trivial (comme B1) | Le contexte passe par la récurrence + obs réelle (pas injecté verbatim) ; le shuffle reste le juge d'artefact. |

## Livrable et suite

~5-6 tâches TDD subagent-driven : (1) `_ensure_throw_gate` + init paresseuse ; (2) injection
biais + décision stochastique + `_pg["throw"]` + records ; (3) `_learn_throw_gate` REINFORCE +
shuffle + compteurs ; (4) banc `run_arm` + reseed + agrégation ; (5) `compare` + verdict + main ;
(6) tests + pré-flight smoke. Puis run powered (contrôleur), EDR, PR (ajout au #143).
