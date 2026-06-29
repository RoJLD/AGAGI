# Audit SOTA, migration du moteur & procédure anti-réinvention — Design

> Date : 2026-06-29. Continue `docs/FIL_CONDUCTEUR.md` / `docs/roadmap/FIL_DIRECTEUR_AGI.md`.
> Mémoire de session associée : `sota-gap-substrate`. Plan d'exécution :
> `../plans/2026-06-29-SOTA-Migration.md`.

## 1. Verdict d'audit

AGAGI **n'a aucune découverte révolutionnaire publiable** : les EDR redécouvrent, avec
rigueur, des résultats établis. Fait technique décisif — `requirements.txt` n'a **ni
torch/tf/jax** : tout le moteur « neuronal » (Actor-Critic TD, REINFORCE, World Model,
gradient) est dérivé **à la main en numpy**, sur un connectome ≈172 nœuds dont **~5 cachés**
(I≈59, O≈108 → quasi-réflexe). Le « Mamba » est en réalité un **Liquid Time-Constant network**
(δⱼ=sigmoid(W[j,j]), ODE discrétisée) réimplémenté main, privé de l'entraînement gradient qui
le rend SOTA.

Le verrou que les EDR 104-111 identifient empiriquement (**SUBSTRAT / capacité d'apprentissage**)
est précisément la raison historique du pivot neuroévolution-pure → deep-learning+gradient.

**La vraie valeur = l'INSTRUMENT** (mondes exigeants, métriques G0-G4, discipline
anti-théâtre/powered/négatifs-livrables). On le **garde** ; on **migre le moteur**.

### Mapping découverte → état de l'art (nœuds REF du graphe)

| EDR | Redécouvre | REF |
|---|---|---|
| 060 / 064 | spéciation protège la nouveauté ; add_node = bloat | REF-NEAT-2002 |
| 068 | apprentissage guide l'évolution | REF-Baldwin-1987 |
| 077 | variance du gradient de politique (BPTT nuit en RL) | REF-REINFORCE-1992 |
| 011 / 098 | curiosité = erreur de prédiction (réseau fixe) | REF-RND-2018 |
| 078 | fitness bruitée → ré-échantillonnage | REF-NoisyFitness-2000 |
| 047 | langage référentiel émerge sous demande (Lewis) | REF-EmComm-2017 (EGG) |
| (A2) | quality-diversity | REF-MAPElites-2015 (pyribs) |

## 2. Plan A — Migration du moteur (par levier décroissant)

Principe : chaque migration = **expérience gated, non-régressive, valide-ou-revert**
(Commandement 15), A/B contre le baseline numpy via le `Harness` existant. **1 variable.**
Décision actée : **PyTorch en extra optionnel** (`requirements-torch.txt`, backend
sélectionnable, legacy numpy conservé).

| Ordre | Axe | Verrou EDR | SOTA cible | REF | Intégration | Validation (harness) |
|---|---|---|---|---|---|---|
| 1 | Substrat + apprentissage | 104-111, 067-077 | LTC officiel + plasticité diff. / meta-RL | REF-LTC-2021 | `agents/mamba_agent.py` derrière `AgentModel`, backend `legacy`/`torch` | A/B `transfer_ratio` torch vs numpy, apparié multi-seed |
| 2 | NAS utile | 064/110 | NAS différentiable / profondeur+backprop | REF-NEAT-2002 | `seed_ai/mutation.py` → hyperparams de profondeur | sweep `hidden_layers` sous gradient : la capacité paie-t-elle ? |
| 3 | Anticipation (G4) | 092-095 | DreamerV3 | REF-DreamerV3-2023 | `agents/world_model.py` + `rl_evolution.py` | `anticipation_bench.py` Dreamer ON/OFF |
| 4 | Langage (Arc 4) | 047-087 | EGG | REF-EmComm-2017 | `seed_ai/referential_head.py` → wrapper EGG | `wire_ref_head.py` MI + bénéfice fonctionnel |
| 5 | Curriculum / open-end (G0-G1) | 090, S2 | POET / OMNI-EPIC | REF-POET-2019 | `curriculum/runner.py` (dormant) | `curriculum_transfer.py` POET vs manuel |
| 6 | RSI #8 | 065-066 | ELM / FunSearch / ADAS | REF-ELM-2022 | `metaprog/rsi_loop.py` + `llm_proposer_fn.py` | amélioration réelle une fois substrat torch ? |

## 3. Plan B — Procédure anti-réinvention (« SOTA-gate »)

Règle d'or : *aucun nouvel « organe » cognitif ne démarre sans un SDR qui cite ≥1 nœud REF
et tranche build-vs-adopt.*

1. **SOTA-scan** (timeboxé) : ce mécanisme existe-t-il déjà, entraîné par gradient, en lib ?
2. **Créer ≥1 nœud `REF`** (`docs/REF/`, voir §4).
3. **Build-vs-adopt** :

   | Critère | → Adopter | → Construire |
   |---|---|---|
   | Lib maintenue + gradient | ✅ | — |
   | Brique cœur de la thèse (mondes exigeants) | — | ✅ (notre actif) |
   | Brique générique (optimiseur, world model, RNN) | ✅ | — |

4. **Wrapper non-régressif** : la lib passe derrière une interface, baseline maison conservé.

**Enforcement** : extension future de `consolidate_records.py` — un SDR marqué « nouvel organe »
sans `grounds`/REF lié devient un problème dur (comme un lien cassé).

## 4. Décision — nœuds REF DANS le graphe records (pas de graphe séparé)

Retenu : nœuds `REF` typés dans le graphe existant (`tools/consolidate_records.py` →
`results/records_graph.json`), arêtes-pont **émanant des REF** (`rediscovered_by`,
`supersedes`, `adopt_for`, `grounds` → `REDECOUVERT_PAR`/`DEPASSE`/`A_ADOPTER_POUR`/`FONDE`).
Avantage : « réinvente-t-on la roue ? » devient une requête de graphe ; réutilise le gate
anti-théâtre (échec sur pont cassé) ; aucune édition des EDR/SDR/ADR existants. Rejeté : graphe
séparé (2 systèmes à synchroniser, perte du gate, dérive).

**Livré (2026-06-29)** : type `REF` + dossier `docs/REF/` + 11 nœuds + 14 arêtes-pont, 0
problème ; 15 tests verts (TDD). Convention : `docs/REF/README.md`.
