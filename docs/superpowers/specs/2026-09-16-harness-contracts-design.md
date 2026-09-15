# Spec — Harnais à deux contrats (Task / Learner) et registre de pièces

**Date** : 2026-09-16. **Statut** : conception approuvée par robla (sections 1, 2, 3 validées le 2026-09-16),
implémentation à planifier. **Décision amont** : [ADR-004](../../ADR/004_fourche_strategique_demande_generee_ou_concue.md)
(ferme P3.7). **Backlog** : P2.66, P4.10 (re-spécifié), P3.7 (close).

**Provenance de la section 2** : panel de 5 lentilles indépendantes (intégration dépôt, biologie ↔ artificiel,
rigueur de mesure, proposeur Claude Code, YAGNI/débit), 3 juges à pondérations opposées (validité, temps au
premier record, extensibilité north-star), 27 réfutations vérifiées dans le code, synthèse. Les chiffres cités
ont été confrontés au dépôt par les juges ; les numéros de ligne valent au 2026-09-16.

---

## 0. Ce qu'on construit, et pourquoi

AGAGI devient un **harnais** qui (1) génère des environnements exigeants et des architectures, (2) mesure si un
apprenant a réellement appris. Le sujet n'est plus le connectome stoneage mais **un modèle à poids que robla
possède**, dans un espace d'architectures **ouvert** (actor-critic torch + BPTT, Dreamer, transformer,
connectome évolué, architectures composées avec un LLM). Règle d'entrée : **une famille n'entre dans la recherche
qu'avec son propre contrôle positif** (sinon classe E2, bras qui ne peut pas réussir).

Première famille d'environnements : **jeux de logique vérifiables**, générés par le proposeur (Claude Code), les
tâches proxy existantes portées en premier. Deux fils en parallèle : la lignée S2/stoneage (bail `kuzu`) continue ;
le harnais est CPU pur, sans bail, sans monde.

**Critère à 3 mois (Q7)** : UN record à trois conditions — (i) une tâche GÉNÉRÉE exige X (ablation within-subject
hors bande de bruit) ; (ii) ≥ 1 architecture ACQUIERT X à dose publiée, au-dessus de la référence lr=0 appariée
ET du plafond de l'incapable, n ≥ 12 seeds ; (iii) l'ablation d'UNE pièce ANNULE l'acquisition. Sans (ii) à
3 mois, P3.7 se rouvre.

---

## 1. Forme d'ensemble

Deux **contrats**, trois **mesures**, un harnais qui **compose l'existant**.

- `Task` — un jeu de logique vérifiable : génère des épisodes, note une politique, et **déclare la capacité qu'il
  exige** avec l'ablation qui la teste (le marqueur de demande, porté par la tâche).
- `Learner` — une architecture : apprend sur une `Task` à dose comptée, et **déclare ses pièces** avec, pour
  chacune, la variante « sans cette pièce » (le marqueur de nécessité, porté par l'architecture).
- Le harnais compose : `tools/experiment_preflight.py` (gardes, `declare_design`), `src/seed_ai/eval_harness.py`
  (n ≥ 12, `welch`), `src/seed_ai/harness.py` (`SeedManager`), `tools/preregister.py` (règle scellée),
  `tools/cost_guard.py`, `tools/demand_marker.py::ablation_verdict`, `tools/check_bar_separation.py` (plafond de
  l'incapable), REF-DEMAND-MARKER (ratio within-subject, plancher de bruit publié).

Approches écartées : (a) gymnasium + PPO de bibliothèque — apprenant capable en un jour mais **opaque** (on ne
peut pas ôter une pièce d'un PPO de bibliothèque ; dose et référence lr=0 demandent des hooks) ; utile plus tard
comme *famille*, pas comme socle. (b) Étendre `rsi_loop` (5 paramètres → paramètres de tâche) — le proposeur ne
peut toujours pas *écrire* une tâche ; on ne teste pas la demande générée.

---

## 2. Les deux contrats et le registre de pièces

Faits vérifiés dans le dépôt qui gouvernent le design : `_SCOPES` / `_SCAN_DIRS = ("tools", "src/seed_ai")`
dans `tools/check_bar_separation.py:40`, `tools/check_control_family.py:42`, `tools/check_substrate_pinning.py:43`,
scannés par `os.walk` (récursif) — un package `src/harness/` serait **invisible à trois portes sur quatre**,
`tools/harness/` est couvert ; `PLAIN_COMPOSITION_CEILING = 34/36` (`tools/plain_substrate_ceiling.py:155`) ;
`_MOVE_LOGITS = 8` lu par `imitate_episode_bptt` (`src/agents/backend_torch.py:304`) ; `learner_verdict` prend
des scalaires (`tools/cognitive_demand_inworld.py:527`) ; `seed_at` ne pose que `np.random.seed`
(`src/seed_ai/harness.py:17-22`) ; `count_learning_events` ne patche pas `imitate_episode_bptt`
(`tools/learning_events.py:96-98, 135-136`) ; `secure_sandbox.ALLOWED_MODULES = {"numpy", "math"}`
(`src/metaprog/secure_sandbox.py:23`).

### 2.1 Les deux contrats

**Emplacement** : contrats + lecture de verdict pure dans `src/seed_ai/` ; runner, tâches et learners dans
`tools/harness/`. Noms choisis pour être captés par `check_instrument_calibration.py` (`assert_*`, `run*`,
`*verdict*`, `measure*`) — un instrument nommé hors motif est invisible au cliquet.

#### Task — `src/seed_ai/harness_task.py`

```python
from dataclasses import dataclass
from typing import Protocol, Callable, Literal, Optional
import numpy as np

Split = Literal["train", "eval", "control", "shift"]   # "shift" réservé (hypothèse neuromodulée) ; None accepté en v1

@dataclass(frozen=True)
class Episode:
    obs_seq: list            # T tableaux (n, obs_dim) float32 — forme de bilinear_composition_probe._make_seq
    target: np.ndarray       # (n,) int dans [0, K)
    mask_seq: Optional[list] # T tableaux (n,), 1.0 au pas noté ; None si T == 1
    meta: dict               # opérandes bruts (key, q, ...) : lus par ablate/oracle/plafond Bayes, JAMAIS par le Learner

@dataclass(frozen=True)
class Ablation:
    name: str                                   # "permute_key" | "permute_query" | "state_reset" | ...
    site: Literal["input", "state"]             # input -> Ablation.apply ; state -> LearnerInstance.ablate_state(name)
    must_bite: bool                             # True : la capacité EXIGE ce canal ; False : contrôle de SPÉCIFICITÉ
    apply: Optional[Callable[[Episode, np.random.RandomState], Episode]] = None
    # apply : distribution conservée, information détruite (barreau `permuted`, jamais `zero`) ; rend un NOUVEL Episode
    # (np.shares_memory False). Un site="state" exige un split "control" (bras CONTROL de alias_guard_verdict).

@dataclass(frozen=True)
class DemandDeclaration:
    capacity: str                               # "composition" | "retention_D1" | ... | texte libre pour une tâche générée
    ablations: tuple                            # >= 1 must_bite=True ET >= 1 must_bite=False (les DEUX issues)
    incapable_ceiling: Optional[tuple]          # (float, provenance >= 20 car., proven: bool) : plafond de REPRÉSENTATION,
                                                # publié avec statut MINORANT/PROUVÉ ; None -> CEILING_UNVALIDATED. JAMAIS 1/K.
    key_entropy_bits: Optional[float] = None    # réservé aux familles LLM (clé retirée par seed) ; None en v1

class Task(Protocol):
    name: str
    version: str
    K: int                                      # chance = 1/K ; vérifié <= Learner.max_K en tête
    obs_dim: int
    T: int                                      # horizon fixe (v1 : boucle OUVERTE ; v2 réserve Task.step, cf. 2.7)
    demand: DemandDeclaration
    def episodes(self, rng: np.random.RandomState, n: int, split: Split = "train") -> Episode: ...
        # seul générateur autorisé : rng (np.random.* interdit par l'AST) ; même (seed, n, split) -> bit-identique
    def score(self, actions: np.ndarray, ep: Episode) -> np.ndarray: ...
        # (n,) hits {0,1} ; VÉRIFIEUR indépendant de oracle (force brute sur les K réponses) ; lève si n == 0 (porte 14)
    def oracle(self, ep: Episode) -> np.ndarray: ...
        # (n,) politique câblée lisant meta : contrôle positif de la DV, attendu 1.0
    def enumerate_states(self) -> Optional[int]: ...
        # cardinal FINI de l'espace des opérandes, ou None -> plafond Bayes du flux ablaté MESURÉ, non certifié
    def regime(self) -> dict: ...               # publié tel quel dans le bloc `regime` du JSON (E8 occ. 4)

def assert_task_contract(task, seed=0, n=64) -> dict:
    """Garde EN TÊTE, zéro entraînement, refus < 50 ms :
    (a) >= 1 must_bite True et >= 1 False ; site="state" -> split "control" existe ;
    (b) score(oracle) == 1.0 ; mutation oracle décalé ((x+1) % K) -> 0.0 (le vérifieur n'est pas l'oracle, E1) ;
    (c) pour chaque must_bite=True : score(oracle, apply(ep)) dans [1/K ± 2 se] ; must_bite=False : > 0.9 ;
    (d) deux appels episodes(rng même état) bit-identiques ; np.shares_memory(apply(ep).obs, ep.obs) False ;
    (e) incapable_ceiling : provenance >= 20 caractères, et != 1/K (docstring assert_bar_separates_the_incapable) ;
    (f) regime() non vide. Rend {"bayes_floor_ablated": ..., "certified": enumerate_states() is not None}."""
```

Ce que la Task DÉCLARE : la capacité, les ablations qui la testent (mordantes et non mordantes), le site de chaque
ablation, un oracle et un vérifieur indépendant, son plafond de représentation avec provenance et statut, son
régime. Elle ne connaît ni learner, ni torch, ni monde.

Portage sans copie — `tools/harness/tasks/composition.py` importe `_make_seq` et `_slot` de
`tools/bilinear_composition_probe.py` (inchangé : il reste la réponse connue) ; `CompositionTask(K=6, same_tick,
kind="composition"|"recall")` consomme `rng.randint` dans le MÊME ordre (key puis q, `:124-125`) pour la
bit-identité. Ablations : `permute_key`, `permute_query` (must_bite), `permute_distractor_slot` (must_bite=False) ;
en 2-pas, `state_reset` (site="state", must_bite) avec split "control" = même épisode, key re-présentée au pas de
réponse.

Modules GÉNÉRÉS : fichiers autonomes (numpy + math + dataclasses + typing — élargissement d'UNE ligne de
`ALLOWED_MODULES` par kind, avec son cas positif et négatif ; jamais torch, jamais `src.*`), vérifiés
STRUCTURELLEMENT par `assert_task_contract` (duck typing) — le Protocol n'est pas importé par le module généré.

#### Learner — `src/seed_ai/harness_learner.py`

```python
@dataclass(frozen=True)
class Piece:
    name: str
    artificial_form: str            # fichier:ligne
    biological_analogue: str
    analogue_solidity: Literal["solide", "moyenne", "faible", "aucune"]
    bio_lesion_prediction: Optional[str]   # lésion connue de l'analogue et capacité abolie ; maillon `inferred`, jamais `measured`
    capacity_served: str            # doit nommer une DemandDeclaration.capacity de la famille
    without: dict                   # kwargs de build() pour la variante « sans » ; DOIT changer un logit (VACUOUS_PIECE sinon)
    dose_matched: bool              # la variante reçoit le même nombre de mises à jour
    matched_sham: Optional[dict]    # variante à MÊME nombre de paramètres, pièce inerte ; None -> PARAMS_NON_APPARIES
    in_repo_today: str              # chiffre + record, ou "absent"
    evo_discoverable: Literal["measured", "unknown"] = "unknown"   # pont EVO-009

@dataclass
class Dose:
    calls: int = 0
    updates: int = 0                # mises à jour qui ont RÉELLEMENT changé un paramètre (comptées dans learn, pas déduites)
    dparam_abs_sum: Optional[float] = None   # None si la famille n'a pas de θ dense
    episodes_seen: int = 0
    unit: str = "gradient_updates"  # | "generations" | "llm_calls" — jamais comparée entre familles

class LearnerInstance(Protocol):
    def init_state(self): ...
    def act(self, obs_t: np.ndarray, state) -> tuple:   # (n, obs_dim) -> ((n, K) logits COPIÉS, nouvel état) ; aucune vue de H
    def learn(self, ep: Episode, actions: np.ndarray, hits: np.ndarray) -> Dose: ...   # UNE mise à jour ; rend la dose cumulée
    def ablate_state(self, state, name: str): ...        # requis ssi une Ablation site="state" est déclarée
    def state_dict(self) -> dict: ...                    # persistance des poids (règle coût CLAUDE.md)
    def dose(self) -> Dose: ...

class Learner(Protocol):
    name: str
    family: str                     # "connectome_torch" | "gru_bptt" | "tabular" | "llm_composed" | ...
    pieces: tuple                   # tuple[Piece, ...]
    entry_task: str                 # billet d'entrée de la FAMILLE (règle Q2 / E2), mesuré une fois, gravé
    max_K: int                      # 8 pour le connectome (_MOVE_LOGITS)
    supported_state_ablations: frozenset
    def sweep(self) -> list: ...    # >= 2 réglages de l'axe d'optimisation ({"lr": ...}, taux de mutation, température...)
    def build(self, seed: int, n: int, obs_dim: int, K: int, hyper: dict, *,
              without: dict = {}, reference: bool = False) -> LearnerInstance: ...
        # reference=True : MÊME init, MÊMES tirages, MÊME boucle, apprentissage COUPÉ (pas d'opt.step) — la barre de (ii)
        # torch.manual_seed(seed) posé ICI (seed_at ne seed que numpy)

def assert_learner_contract(learner, task, seed=0) -> None:
    """Garde EN TÊTE, une population, 5 épisodes :
    (L0) task.K <= learner.max_K ; toute Ablation site="state" ∈ supported_state_ablations ;
    (L1) deux build(seed) -> logits bit-identiques ; build(without={}) bit-identique (no-op exact) ;
    (L2) REFERENCE_LEARNS : build(reference=True).learn ×5 -> dparam_abs_sum == 0 et updates == 0, calls == 5 ;
    (L3) DEAD_LEARNER : build(...).learn ×5 -> dparam_abs_sum > 0 (le cas « curiosité morte », P4.8) ;
    (L4) VACUOUS_PIECE : pour chaque Piece, build(without=p.without) diffère de l'intact sur >= 1 logit ;
    (L5) assert_no_aliasing(logits, state) ; (L6) entry_task présent dans le ledger de la famille, sinon refus E2 ;
    (L7) len(sweep()) >= 2 (assert_verdict_invariant_to_optimizer refuse un seul point)."""
```

Premier entrant — `tools/harness/learners/connectome.py::ConnectomeLearner` : SEUL adaptateur vers
`make_population(..., backend="torch")` (frontière ADR-003), pose/restaure les drapeaux de classe `BILINEAR`,
`CONDITION_GATE` dans un `try/finally` comme `_train_eval_one` (`bilinear_composition_probe.py:98-118`), verrou
de process (drapeaux = état global E5 : une cellule connectome par process, parallélisme par seed en
sous-processus). `learn` enveloppe `imitate_episode_bptt` (crédit supervisé) ou `learn_episode` (REINFORCE, pièce
optionnelle) et compte la dose EN LIGNE (Σ|Δθ| après chaque `opt.step`) — pas de patch de classe.
`pieces = (bilinear, recurrent_state, bptt_credit)` ; `max_K = 8` ; `sweep() = [{"lr": lr0}, {"lr": lr1}]`
scellés par cellule. Son **billet d'entrée** (`entry_task`) est déjà payé : `results/bilinear_composition.json`
(acquisition 0,932 sur `composition_same_tick`, n=12) — le ledger de la famille `connectome_torch` le cite ; la
cellule A du §2.4 le REJOUE en bit-identité, elle ne le crée pas. La famille `gru_bptt` (semaines 6-8) paiera le
sien sur la même Task avant toute cellule de nécessité.

Learner de vérité-terrain — `tools/harness/learners/tabular.py` : table de comptage (pièce `table`, nécessaire
par construction ; pièce `decoy`, jamais lue → doit être REFUSÉE par L4, pas jugée « dispensable ») ; variante
`oracle_init` → PRIOR_SOLVES. Calibre le runner et la lecture en secondes, sans torch.

### 2.2 Le registre de pièces — `src/seed_ai/harness_pieces.py` (données) + `docs/REF/REF-HARNESS-PIECES.md`

Statut : **R1** = premier record (2 pièces), **R2** = semaines 6-8, **attend** = n'entre qu'avec son contrôle
positif (E2).

| pièce | forme artificielle | analogue biologique (solidité) | variante « sans » | capacité servie | déjà mesuré dans le dépôt | statut |
|---|---|---|---|---|---|---|
| `bilinear` | `((H·U)⊙(H·V))·W_bl` rang 16 dans `_step` (`backend_torch.py:111-131`), flag `BILINEAR` | intégration dendritique multiplicative / coïncidence NMDA (**moyenne** ; le rang et U/V n'ont pas de correspondant). Lésion prédite : blocage des spikes NMDA abolit les conjonctions, pas la détection de traits | `without={"bilinear": False}` (chemin plain bit-identique) ; sham linéaire de même rang : **absent** → PARAMS_NON_APPARIES | composition (q+key)%K | plain 0,271 vs bilinéaire 0,932, 0/144, n=12, 300 ép. (`results/bilinear_composition.json`) ; **mais** forme close plain 34/36 = 0,944 > 0,932 (`plain_substrate_ceiling.py:155`) : nécessité d'ACQUISITION à dose, pas de représentation | **R1** |
| `recurrent_state` | H porté : `H' = (1−δ)H + δ·tanh(H·W_off)`, δ = σ(diag W) (`:119-132`) | activité persistante préfrontale, mémoire de travail (**solide** fonctionnellement, aucune au mécanisme). Lésion : dlPFC abolit le rappel différé, pas l'immédiat | `without={"feedforward": True}` (H=0 à chaque pas = `control_mode="feedforward"`) ; ablation d'éval `state_reset` (`_reset_H`, `language_memory_demand_probe.py:88`) | rétention D ≥ 1 | LOCK-002 : 0,814/0,168 = 4,85×, n=12, SURGICAL fuite 0,028 (REINFORCE D=2, 14 400 ép.) ; 2-pas supervisé : 0,923 à lr 0,002/600 ép. (`retain_compose_lr_replication.json`) | **R1** |
| `bptt_credit` | graphe retenu à travers les pas (`imitate_episode_bptt :263`, `learn_episode_bptt truncate=False :230`) | traces d'éligibilité / synaptic tagging (**moyenne** ; BPTT lui-même : aucune) | `without={"truncate": True}` (H détaché à chaque pas, `:357`) | écriture apprise dans la mémoire (verrou LOCK-001) | RETAIN-COMPOSE-LR : 0,173 → 0,923 au seul lr (E19) ; nécessité NON établie | **R2** |
| `td_critic` | value head nœud 28, δ = r + γV(s') − V(s) (`:174-229`) | erreur de prédiction de récompense dopaminergique (**solide**, Schultz). Lésion : VTA/SNc abolit l'apprentissage instrumental, pas l'exécution | `td_enabled=False` (`learning_events.py:89`) | crédit temporel dense | CALIB-LEARNER : td_off −0,046 (2/12) ; P4.9 en cours | attend (Task à récompense scalaire) |
| `condition_gate` | readout de H biaisant le logit cible (`:48-53, 134-149`) | gating go/no-go ganglions de la base (**moyenne**) | `CONDITION_GATE=False` (bit-identique) | binding means→ends | EDR-129/136/148 : suffisant en proxy ; nécessité à dose appariée jamais mesurée | attend |
| `warm_start_prior` | init depuis bassin DAgger / HoF vs `0.1·randn` (`:113-115`) | pré-câblage génomique, périodes critiques (**solide** conceptuellement, Zador 2019) | `init="random"` même seed ; « warm gelé » = référence | bootstrap ; rétention du bassin | loi warm-start (6 fils) ; S2-CREDIT-RETENTION : le crédit érode 36 → 8, 12/12 | attend |
| `neuromod_plasticity` (hypothèse de robla) | règle à 3 facteurs ΔW = η·m(t)·pre⊗post, m(t) readout appris de H (Miconi 2018) — **à écrire** | plasticité hebbienne gatée par DA/ACh (**solide** comme phénomène, **moyenne** comme règle). Lésion : nucleus basalis → déficit sous NOUVEAUTÉ, ancien préservé | DEUX variantes ordonnées : `modulator="constant"` (m≡1, teste la MODULATION) puis `plasticity=0` (teste la PLASTICITÉ) ; contrôle : m(t) permuté dans le temps | rétention sous changement de distribution (split `"shift"`) | **absent** (hebbien legacy numpy = no-op sous torch, ADR-003) ; entre avec son billet : une Task à shift que Hebb pur échoue et que 3-facteurs réussit | attend |
| `frozen_llm_backbone` | LLM gelé + adaptateur apprenant (tête / LoRA) | cortex mature + plasticité locale, CLS (**faible**) | `adapter=False` (zéro-shot) ET `backbone="random_features"` ; référence = « LLM sans module » | a priori symbolique | **rien** ; seul `llm_fn(str)->str` existe | attend (clé par seed, PRIOR_SOLVES obligatoires ; non CPU-pur) |
| `state_noise_regulator` (dreaming) | bruit sur l'état récurrent porté | homéostasie du sommeil (**faible** ; DREAM-007 : pas du rejeu) | organe off | régulation de bruit d'état (+77 % survie) | arc DREAM-001→007, in-world seulement | hors v1 |
| `curiosity_intrinsic` | surprise du modèle du monde → bonus | dopamine de nouveauté (**moyenne**) | `intrinsic_scale=0` | exploration | **MORTE sous torch** (surprise jamais écrite, P4.8) — cas gelé de L3 DEAD_LEARNER | hors registre actif |
| `targeted_variation` | `add_connection` biaisé entrée→sortie | biais développementaux de connectivité (**faible**) | opérateur uniforme (EVO-010 : 254 117 réveils → 0) | découverte d'arête | EVO-009 : 1/12 → 12/12, p = 9,6e-6 ; dose en `generations` | attend (famille évoluée : `reference()` = variation coupée) |

Test du registre : toute pièce citée par un Learner accepté existe ; toute `without` d'une pièce in-repo est
constructible ; une pièce marquée « absent » n'est référencée par aucun Learner de la famille.

### 2.3 Déroulé d'une cellule

Une CELLULE = (Task acceptée, Learner accepté, 12 seeds, règle scellée). Tout ce qui refuse refuse AVANT le
premier entraînement :

0. **Proposition** (`tools/harness/propose.py --kind task`, semaine 5+) : `claude_code_llm_fn` (P2.66 : prompt
   par stdin, `claude -p --output-format text --allowedTools ""`, timeout 600 s, binaire = `AGAGI_CLAUDE_BIN` —
   factice en CI). Prompt = contrat en prose (REF-HARNESS-CONTRACTS) + gabarit `template_task.py` (passe
   `assert_task_contract` tel quel) + demands déjà couvertes + les N derniers refus du ledger.
   → `validate_code(code, kind="task")` (AST : `np.random.*`, `global`, `try/except`, `import src`, `torch`
   refusés) → `run_sandboxed(code, smoke)` (subprocess `-I`, 60 s : oracle 1,0 ; must_bite → 1/K ;
   must_bite=False > 0,9 ; oracle décalé → 0,0) → dépôt dans `proposals/task/<slug>/` (chemin via
   `src/paths.proposals_root`) + ledger `{prompt_sha, response_sha, modèle, statut, raison}`. REVIEW_PENDING ≤ 5.
   Learners générés : hors v1 (torch hors allow-list ; revue humaine seule digue).
1. **Revue humaine** (`tools/harness/accept.py <slug> --reviewer robla --reason`) : seul écrivain de
   `tools/harness/tasks/` ; en-tête `# ACCEPTED sha256 reviewer date` ; entrée dans `REGISTRY.json`.
   `run_harness_cell` refuse en tête une Task absente du registre.
2. **Scellement** : `preregister("HARNESS-<task>-<learner>-Rn", rule)` avec branches EXHAUSTIVES (2.3-b), `sweep`
   déclaré (E19), `n_floor=12`, `dv_primaire = [hits, ratio_within, sep_ref, dose.updates]`. Le runner appelle
   `verify()` puis `declare_design(question, replication_unit="seed", n_independent=12,
   links={"ablation->chute": "measured", "dose->acquisition": "measured", "sans_piece->chute": "measured",
   "analogue_bio": "inferred"}, control_family=assert_control_family(cells=n_ablations·n_pieces·len(sweep)))`.
3. **Pré-vol de cellule** (secondes) : `assert_task_contract`, `assert_learner_contract`,
   `assert_selection_nonempty(12)`, `measure_ablated_bayes_ceiling(task)` (énumération si `enumerate_states()`,
   sinon mesuré sur `oracle_without` et étiqueté non certifié) ; `project_cost(unit_s=<smoke 1 seed × 1 bras
   MESURÉ ici>, n_units=12·n_bras, budget_s, safety=3)`.
4. **Bras par seed** (`SeedManager.seed_boundary(s)` + `torch.manual_seed(s)` dans `build` ; `CostGuard` par seed,
   abandon COMPTÉ et publié ; `Harness(with_db=False)`, aucun bail) — tous consomment les MÊMES tirages :
   A `build(hyper=sweep[0])` ; A0 `build(reference=True)` ; A' `build(hyper=sweep[1])` ; pour la pièce ciblée :
   D `build(without)`, D' à `sweep[1]` (lancé seulement sur la branche nulle de (iii)) ; sham si déclaré. Courbe
   par blocs avec point à D/2.
5. **Évaluation du MÊME sujet**, 40 lots × 16 sur rng d'éval séparé : `intact` ; `noop` = même politique, SECOND
   rng d'éval → `noise_floor = [min, max]` des ratios intact/noop sur seeds (bande réelle, ≈ ±2 % attendus à
   n_eval = 640, à MESURER — un no-op à l'argmax sur le même batch rend 1,000 par construction et ne mesure rien) ;
   `ablated_k` pour chaque Ablation (input : `apply` ; state : `ablate_state`) ; `ctrl_intact/ctrl_ablated` sur
   split "control" si site="state" ; `first`, `mid` (D/2), `last`.
6. **Verdicts** — `harness_verdict_lecture(db, rule)` PURE (`src/seed_ai/harness_verdict.py`), sur médianes par
   seed, composant les instruments calibrés :
   - (i) DEMANDE : `ablation_verdict(intact, ablated_k, floor=bayes_floor_ablated, ceiling=1.0, n_floor=12,
     intervention_verified=True)` par ablation ; X_DEMANDED exige must_bite → ratio ≥ 1,5 ET hors `noise_floor` ;
     must_bite=False → DECOY (sinon INCONCLUSIVE_SPECIFICITY) ; site="state" → `alias_guard_verdict(ctrl_i,
     ctrl_a, ...)` SURGICAL. Ratio dans la bande → `DEMAND_WITHIN_NOISE`, jamais DECOY.
   - (ii) ACQUISITION : `learner_verdict(first, last, reference_last, oracle_last)` sur médianes — barre =
     référence + 0,05 ; PRIOR_SOLVES si référence > barre (contamination ou tâche triviale, jamais « acquis ») ;
     12/12 seeds au-dessus de leur référence appariée ; `assert_bar_separates_the_incapable(bar,
     incapable_ceiling=med(D), provenance="bras sans pièce, ce run, MINORANT")` appelé inconditionnellement ; le
     plafond de REPRÉSENTATION déclaré (forme close) est confronté SÉPARÉMENT et publié
     `representational_ceiling_above_bar: bool` — jamais barre. Nul → dose publiée + `saturation:
     TENDANCE|PLATEAU` (score(D) − score(D/2)).
   - (iii) NÉCESSITÉ : `ablation_verdict(last_A, last_D, floor, 1.0)` ; **NECESSARY** ssi chute ≥ 1,5 hors bande
     ET med(D) ≤ référence + 0,05 (la variante retombe à la référence) ; **PARTIAL** si chute ≥ 1,5 mais D franchit
     la barre ; **NOT_NECESSARY** sinon. Tout nul ou PARTIAL passe `assert_verdict_invariant_to_optimizer(
     measure=lambda h: (med_D(h), med_A(h)), lrs=sweep, reference_floor=bar)` → `PreflightError` = LR_ARTIFACT,
     `ReferenceCollapsedError` = INDETERMINE_HARNAIS ; alias de pièce : `alias_guard_verdict(ctrl_A, ctrl_D)` (la
     tâche de contrôle doit survivre au retrait, sinon la « pièce » est tout le learner) ; `PARAMS_NON_APPARIES` si
     `matched_sham is None`.
   - Ordre des branches (2.3-b) : `INCOMPLET` → `INCONCLUSIVE_N` → `INDETERMINE_HARNAIS` (oracle < 0,9, référence
     effondrée, PRIOR_SOLVES) → `LR_ARTIFACT` → `NOT_DEMANDED` / `DEMAND_WITHIN_NOISE` → `NOT_ACQUIRED` →
     `PIECE_NOT_NECESSARY` / `PIECE_PARTIAL` → `DEMANDED_ACQUIRED_NECESSARY` → `autre`. Aucune branche ne rend une
     constante sur collection vide : `None` ou `raise`.
7. **Record** via `Harness.save()` (`src/paths.results_file`, `_rerun`), frontmatter `tests:[SDR-G2]`,
   `adopts: REF-DEMAND-MARKER`. Le verdict de (iii) s'énonce « nécessaire à l'ACQUISITION à dose D, sweep {…},
   sous crédit C », jamais « nécessaire » nu.

**Forme JSON publiée** :

```json
{"regime": {"task": "Task.regime()", "learner": {"hyper", "n_params_by_variant", "credit", "n_agents", "seeds_torch_numpy"},
            "incapable_ceiling": {"value": 0.944, "provenance": "...", "status": "MINORANT|PROUVE|UNVALIDATED"},
            "bayes_floor_ablated": {"value": 0.1667, "certified": true}, "sweep": [{"lr": 0.02}, {"lr": 0.002}]},
 "design": "declare_design(...)", "control_family": {"cells", "alpha_cell"}, "preregistration": {"name", "seal"},
 "dose": {"per_arm": {"A": {"calls", "updates", "dparam_abs_sum", "episodes_seen", "unit"}, "A0": {"updates": 0}, "D": "..."},
          "abandoned_seeds": {"A": [], "D": []}},
 "noise_floor": {"band": [0.98, 1.02], "eval_se": 0.015, "n_eval": 640},
 "demand": {"<ablation>": {"verdict", "ratio", "per_seed": {"intact", "ablated", "noop"}, "in_noise_band": false}, "alias": "SURGICAL"},
 "acquisition": {"verdict", "bar": "ref+0.05", "reference_last", "per_seed_above_ref": "12/12", "saturation",
                 "representational_ceiling_above_bar": true},
 "necessity": {"<piece>": {"verdict", "ratio", "per_seed_diff", "e19": {"gaps_by_lr", "closure"}, "sham": "PARAMS_NON_APPARIES", "alias"}},
 "cost": {"unit_s_smoke", "projected_s", "actual_s", "machine_load_note"}}
```

### 2.4 Premier contrôle positif exact

Famille scellée `HARNESS-R1` (une règle, trois cellules, pour que (iii) rende LES DEUX issues) :

| cellule | Task | Learner | attendu (réponse connue) | coût |
|---|---|---|---|---|
| **A** bit-identité | `CompositionTask(K=6, same_tick=True)`, ablations permute_key/permute_query (bite), permute_distractor (no-bite) ; `incapable_ceiling=(0.944, "forme close plain 34/36, plain_substrate_ceiling.py — MINORANT", False)` | `ConnectomeLearner(bilinear=True, credit="supervised")`, sweep {0,02 ; 0,002}, 300 ép., 16 agents, seeds 0-11 ; pièce `bilinear` | per_seed EXACTEMENT égaux à `results/bilinear_composition.json` (seed 0 : 0,9328125 / 0,2703125 ; médianes 0,932 / 0,271) ; (i) X_DEMANDED sur les deux bite, DECOY sur distractor ; (ii) ACQUIRED, référence lr=0 ≈ 0,167 (à mesurer), `representational_ceiling_above_bar: true` (0,944 > 0,932 : le harnais sait dire non) ; (iii) **PIECE_PARTIAL** (chute 3,4× hors bande, mais 0,271 > 0,217) — pas NECESSARY, et c'est le résultat honnête | 12 × 3 bras × 12,2 s ≈ **7 min** (mesuré : 292,4 s / 24 cellules) |
| **A'** témoin négatif | `CompositionTask(K=6, same_tick=True, kind="recall")` | idem, 150 ép. | plain 0,975-1,0 (`test_bilinear_noop_on_recall`) → (iii) **NOT_NECESSARY** obligatoire | ≈ 3 min (mesuré) |
| **B** nécessité par construction | `CompositionTask(K=6, same_tick=False)` (key t0, q t1), ablation `state_reset` site="state" + split control | idem, lr 0,002, 600 ép. ; pièce `recurrent_state` | intact ≈ 0,923 (`retain_compose_lr_replication.json`, lr_0.02 = 0,173 est l'artefact E19) ; H-reset → information absente → 1/K ; (iii) **NECESSARY** ; second lr du sweep = sortie d'un smoke de 3 seeds publié dans la règle (0,0005 n'a AUCUNE mesure dans ce régime — les 0,78-0,84 de LOCK-002 sont REINFORCE 14 400 ép.) ; (0,02 ; 0,002) INTERDIT (référence effondrée à 0,02 → ReferenceCollapsedError) | 12 × 3 × 9,4 s ≈ **6 min** (mesuré : 337,2 s / 36) ; + D' sur branche nulle seulement |

Total < 20 min mesurés ; `project_cost` à marge ×3 : budget scellé 60 min. Ces cellules CALIBRENT le harnais sur
des tâches PORTÉES ; le record Q7 exige une tâche GÉNÉRÉE (semaine 5+) — la branche « aucune des N premières
propositions ne passe (i) hors bande et (ii) » est scellée, pas découverte. Avant A : `run_harness_cell` avec le
learner tabulaire (secondes, zéro torch) doit rendre NECESSARY sur `table` et refuser `decoy` par L4.

### 2.5 Fichiers

**Nouveaux** (chaque instrument avec son test à réponse connue dans `tests/sandbox/test_harness_contracts.py` +
entrée `CALIBRATED`) :

| fichier | rôle | test à réponse connue |
|---|---|---|
| `src/seed_ai/harness_task.py` | Episode, Ablation, DemandDeclaration, Protocol Task, `assert_task_contract` | CompositionTask passe ; ablation sans must_bite=False → lève ; oracle décalé → 0,0 exigé ; `apply` aliasé → lève ; provenance = 1/K → lève ; refus chronométré < 50 ms, `TorchPopulationModel.__init__` jamais appelé |
| `src/seed_ai/harness_learner.py` | Piece, Dose, Protocols, `assert_learner_contract` | ConnectomeLearner passe ; L0 K=9 → lève ; L2 référence Adam qui bouge → REFERENCE_LEARNS ; L3 learn inerte → DEAD_LEARNER ; L4 without bit-identique → VACUOUS_PIECE ; L5 vue de H (`np.shares_memory`) → lève |
| `src/seed_ai/harness_pieces.py` | PIECES + test de cohérence registre/learners | pièce « absent » référencée → lève |
| `src/seed_ai/harness_verdict.py` | `harness_verdict_lecture` PURE ; `measure_noise_floor` ; `measure_ablated_bayes_ceiling` | injection de db factices : (a) → DEMANDED_ACQUIRED_NECESSARY ; ablated = intact → NOT_DEMANDED ; ratio 1,05 bande [0,92 ; 1,06] → DEMAND_WITHIN_NOISE ; A = ref → NOT_ACQUIRED avec `dose` et `saturation` ; ref > barre → PRIOR_SOLVES ; D = 0,27 vs ref 0,17 → PARTIAL ; D rejoint A au 2ᵉ lr → LR_ARTIFACT ; référence effondrée → INDETERMINE_HARNAIS ; cellule manquante → INCOMPLET ; n=11 → INCONCLUSIVE_N ; nan → lève ; listes vides → lève ; mutation `>=`→`>` de (iii) rougit (porte 15) ; Bayes : 36 états → 1/6 exact, `enumerate_states()=None` → non certifié |
| `tools/harness/cell.py` | `run_harness_cell` (verify, declare_design, project_cost, CostGuard, bras appariés, Harness.save) | injection `learner_factory` factice : unité = seed (12 valeurs, pas 192) ; hash des Episodes identique entre A et A0 ; abandon seed 3 → compté, INCONCLUSIVE_N ; règle retouchée → PreregistrationTampered avant toute construction ; `assert_bar_separates_the_incapable` appelé inconditionnellement ; @slow : bit-identité seed 0 (0,9328125 / 0,2703125) ; rng après `build(reference=True)` == rng après intact |
| `tools/harness/tasks/composition.py`, `tools/harness/tasks/template_task.py`, `tools/harness/tasks/REGISTRY.json` | port (import de `_make_seq`) ; gabarit ; registre des acceptées | oracle sous chaque ablation ; gabarit passe le contrat |
| `tools/harness/learners/connectome.py`, `tools/harness/learners/tabular.py` | adaptateur unique ; vérité-terrain | contrats L0-L7 ; tabular : table NECESSARY, oracle_init PRIOR_SOLVES |
| `tools/harness/propose.py`, `tools/harness/accept.py` (semaine 5) | boucle `claude -p` + ledger ; seul écrivain | faux binaire : 1 bloc OK, 0/2 blocs refusés, timeout, exit ≠ 0 ; refus réinjecté dans le prompt suivant |
| `docs/preregistrations/HARNESS-R1.json`, `docs/REF/REF-HARNESS-CONTRACTS.md`, `docs/REF/REF-HARNESS-PIECES.md` | règle scellée ; contrat en prose (cité par le prompt et les records) ; registre publié | — |

**Modifiés** : `src/metaprog/secure_sandbox.py` (allow-list par kind : `task` += dataclasses/typing, règles AST
`np.random.*`/`global`/`try`/`import src` — un cas accepté et un refusé par règle) ; `src/metaprog/llm_proposer_fn.py`
(`claude_code_llm_fn`, ferme P2.66) ; `src/paths.py` (`proposals_root`) ; `tests/sandbox/test_instrument_calibration.py`
(CALIBRATED) ; `docs/roadmap/PRIORITES_ET_DETTES.md` (dettes : sham bilinéaire, Task à shift, sandbox torch pour
learners générés, `learner_verdict` dans un module qui importe le monde → import paresseux). Arbre partagé :
`snapshot/verify` de `check_staged_authorship` avant chaque fichier partagé.

**Réutilisés sans modification** : `tools/bilinear_composition_probe.py` (réponse connue),
`tools/demand_marker.py::ablation_verdict`, `tools/language_memory_demand_probe.py::alias_guard_verdict`,
`tools/cognitive_demand_inworld.py::learner_verdict` (import paresseux), `tools/experiment_preflight.py`
(assert_*, declare_design, assert_control_family, assert_verdict_invariant_to_optimizer,
assert_bar_separates_the_incapable), `tools/preregister.py`, `tools/cost_guard.py`, `src/seed_ai/harness.py`
(SeedManager, Harness.save), `src/seed_ai/eval_harness.py` (welch, std None à n<2),
`tools/plain_substrate_ceiling.py` (34/36 + provenance), `src/agents/backend_torch.py`,
`src/agents/backend.py::make_population`.

### 2.6 « L'artificiel forme-t-il l'organique, ou l'inverse ? »

Le harnais tourne nativement dans le sens **organique → artificiel** : une hypothèse venue de la biologie entre
comme une `Piece` au niveau de sa FONCTION (ce qu'elle calcule), avec sa variante « sans », son sham et son billet
d'entrée, et le verdict (iii) dit si cette forme est nécessaire à l'acquisition de X dans CETTE architecture à
CETTE dose — jamais « c'est ce que fait le cerveau ». L'exemple de robla devient : Task à `split="shift"` (mapping
key→cible remappé par bloc) × Learner 3-facteurs, variantes m≡1 puis η=0, prédiction scellée : « la variante non
modulée retombe à la référence aux deux pas du sweep pendant que la modulée reste au-dessus » ; les deux issues
sont nommées et la seconde (l'analogie ne transporte pas, ou le crédit érode par un autre canal — P4.8) est un
résultat.

Le sens **artificiel → organique** n'est pas mesurable ici (aucun sujet organique) ; il s'écrit comme PRÉDICTION :
chaque pièce NECESSARY porte `bio_lesion_prediction` (maillon `inferred`), et une table de concordance 2×2 (pièce
nécessaire ici × lésion abolit là-bas), scellée avant les runs, exige une DOUBLE dissociation (la pièce doit être
NON nécessaire sur une capacité témoin, comme la lésion épargne) et reste corrélationnelle. Deux garde-fous : une
nécessité INFORMATIONNELLE (`recurrent_state`, plafond Bayes 1/K) vaut pour tout substrat et ne dit rien de
l'architecture ; une nécessité de RÉGIME (`bilinear`, PARTIAL attendu) ne s'exporte pas. Une pièce ne devient
candidate « du puzzle » que si elle est nécessaire dans **≥ 2 familles** (connectome puis GRU+BPTT) — sinon c'est un
artefact d'architecture. Le dépôt mesure déjà que le gradient CRÉE les pièces et que la sélection les RETIENT sans
les créer (EVO-008/009/010) : la direction fertile est « la pièce nécessaire sous gradient devient CIBLE de
l'opérateur de variation » (`evo_discoverable`).

### 2.7 Risques

1. **(iii) confondue avec le réglage (E19)** : chaque variante « sans » change le nombre de paramètres et le pas
   optimal (batch effectif 1). Le sweep est obligatoire sur tout nul ou PARTIAL, le couple de lr scellé APRÈS
   smoke (jamais importé d'un autre régime), et la référence doit rester au-dessus de `reference_floor` aux deux
   pas. Sans sham apparié, `bilinear` reste PARAMS_NON_APPARIES.
2. **Q7(i) exige une tâche GÉNÉRÉE** : R1 calibre sur tâches portées ; le chemin critique du record Q7 est la
   boucle `claude -p` (semaine 5+), avec fuite de réponse possible (le proposeur reformule les tâches portées) —
   règle scellée : demand ∉ {composition, retention_D1} ou ablations ≠ {permute_key, permute_query}.
3. **Barre (ii) vs plafond de représentation** : 0,944 > 0,932 — un lecteur pressé lira « bilinéaire nécessaire » ;
   le record porte le mot MINORANT et la clause « à dose D » ou il ne se grave pas.
4. **Boucle OUVERTE** : v1 tire l'observation avant l'action ; WSL, corps, stoneage-comme-Task sont interactifs.
   `LearnerInstance.act(obs_t, state)` est déjà compatible ; REF-HARNESS-CONTRACTS réserve
   `Task.step(actions, state) -> (obs, reward, done)` en v2 sans le construire (marqueur de demande en boucle
   fermée = ablation de l'obs à chaque pas, bande no-op appariée obligatoire).
5. **Sûreté du proposeur** : la porte AST n'est pas une frontière pour torch ; Learners générés hors v1, revue
   humaine seule digue, conteneur EDR 044 différé — inscrit comme dette, pas glissé.

---

## 3. Plan à 12 semaines et décisions

| sem. | livrable | garde-fou |
|---|---|---|
| 1 | Contrats + gardes en tête, learner **tabulaire** de vérité-terrain, `harness_verdict_lecture` pur calibré sur db factices | `run_harness_cell` rend NECESSARY sur `table` et refuse `decoy` ; chaque instrument `CALIBRATED` avant tout torch |
| 2 | `ConnectomeLearner` (adaptateur unique) + `CompositionTask` portée ; **smoke 3 seeds × 3 lr sur la cellule B** → fixe le second lr ; scellement `HARNESS-R1` | bit-identité seed 0 avec `results/bilinear_composition.json` (0,9328125 / 0,2703125) |
| 3 | Run R1 (A, A', B — < 20 min CPU, sans bail) ; record `EDR-HARNESS-R1` | **revue adversariale à sondes propres** |
| 4 | Corrections de revue ; démarrage du **preprint méthodo** (plan + figures depuis les records existants, zéro run) | 7/7 revues WARM ont trouvé une erreur réelle : la correction est budgétée |
| 5 | `claude_code_llm_fn` (ferme P2.66) + `propose.py` / `accept.py` + ledger ; premier lot de Tasks proposées | cap **5 en attente**, accepteur = robla |
| 6-8 | Règle scellée `HARNESS-GEN-1` (20 propositions, les deux issues nommées) ; cellules sur les Tasks acceptées ; **2ᵉ famille `gru_bptt`** entre avec son billet sur `CompositionTask` | fuite de réponse : une Task générée ne compte que si ses ablations ≠ {permute_key, permute_query} |
| 9-10 | Record Q7 candidat : première Task générée qui passe (i) hors bande + (ii) sur ≥ 1 famille + (iii) sur une pièce ; revue | si aucune → branche nulle **gravée**, pas découverte |
| 11-12 | Réplication de la pièce sur la 2ᵉ famille (règle « ≥ 2 familles ») ; **preprint soumis** ; bilan P3.7 | sans (ii) → P3.7 rouverte, ADR amendé |

Le fil S2 (P4.9 en cours, bail `kuzu`) continue en parallèle ; il n'est sur aucune ligne de ce tableau.

**Décisions prises le 2026-09-16** :
- **(a)** Le second lr de la cellule B sort du smoke de la semaine 2, publié dans la règle AVANT scellement —
  jamais importé d'un autre régime.
- **(b)** R2 = la **famille** `gru_bptt` avant la pièce `bptt_credit` : une pièce n'est « du puzzle » que nécessaire
  dans ≥ 2 familles ; la 2ᵉ famille est le chemin critique, pas une 3ᵉ pièce dans la même.
- **(c)** La boucle de proposition démarre à la semaine 5, après la revue adversariale de R1 (aucune génération sur
  un instrument non revu).
- **(d)** Cap 5 propositions en attente ; robla accepte ; le `ablation_site` de toute Task qui compte pour Q7 est
  relu par la revue adversariale de son record, pas seulement à l'acceptation.
- **(e)** Réglé par lecture : les trois cliquets scannent `tools/` par `os.walk` (récursif) et le hook filtre
  `^(tools|src/seed_ai)/.*\.py` — `tools/harness/` est couvert, rien à élargir.

---

## 4. Hors périmètre (coupes YAGNI, jusqu'au premier record)

Dreamer / modèle du monde (aucun contrôle positif : entrerait sans pouvoir réussir) ; architectures composées
avec un LLM (sandbox torch + budget d'inférence + contrôle positif : rien n'existe — papier 2) ; Learners GÉNÉRÉS
(la sandbox ne laisse passer que numpy) ; conteneur EDR 044 (n'achète rien avant que du torch généré tourne) ;
frontend ; KuzuDB / `async_logger` (harnais CPU pur) ; machinerie d'analogie biologique au-delà des champs de
`Piece` ; REINFORCE comme crédit par défaut (pièce optionnelle, 50× plus cher) ; stoneage comme Task (autre fil) ;
connectome ÉVOLUÉ comme Learner (le crédit in-world érode, l'évolution n'a pas de contrôle positif proxy) ; plus de
2 lr, plus d'une pièce ablatée, plus de 3 ablations d'entrée au premier record ; hiérarchie de classes (Protocol +
dataclass + fonctions) ; mesure de dose par patch de classe (compter DANS `learn`).

---

## 5. Dettes inscrites en passant

À porter au backlog lors de l'implémentation, avec preuve : sham bilinéaire apparié en paramètres (sinon
`PARAMS_NON_APPARIES` permanent) ; Task à `shift` pour l'hypothèse neuromodulée ; sandbox torch pour Learners
générés (décision de sûreté EDR 044, à part) ; `learner_verdict` vit dans un module qui importe le monde
(`tools/cognitive_demand_inworld.py`) → import paresseux ou extraction ; `count_learning_events` aveugle à
`imitate_episode_bptt` (dose = 0 sur un apprenant supervisé qui apprend) ; les instruments `noise_floor` /
`preflight_task` hors motifs du cliquet de calibration → nommer `measure_noise_floor` / `assert_task_contract`.
