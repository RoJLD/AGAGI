---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-080
type: EDR
title: "Le HoF robuste en PRODUCTION + validation avec PUISSANCE"
status: legacy
gate: foundational
---

# EDR 080 : Le HoF robuste en PRODUCTION + validation avec PUISSANCE

> ⚠️ **Correction (trouvaille D1, post-081)** : la revendication « EN PRODUCTION » a été INVALIDÉE puis
> corrigée — `main_biosphere` réinstanciait un 2ᵉ `WorldConfig()` qui écrasait `robust_hof_K=4`, donc la
> prod tournait en sélection **bruitée K=0** (pas robuste) jusqu'au fix D1. Les mesures ISOLÉES de cet
> EDR (validation avec puissance) ne sont pas affectées ; c'est le déploiement prod qui n'a pris effet
> qu'après le fix. Détail : `docs/roadmap/SCIENCE.md` §D1.

## Contexte

EDR 078 (banc) + 079 (vivant, +27 % en 1 run) : de-bruiter la fitness de sélection lève le plateau de
compétence. Deux livrables ici : (1) **mettre le remède en production** (gated), (2) **valider avec
puissance statistique** (le run unique de 079 était bruité — K=4 avait chuté à 14.4).

## (1) Production — HoF robuste, gated

| Composant | Rôle |
|---|---|
| `config.robust_hof_K` (défaut **0**) | active l'éval robuste ; 0/1 = comportement historique |
| `src/seed_ai/robust_hof.py` | `robust_evaluate(cfg, genome, K, ...)` (K ères clones → moyenne life_score) ; `robust_rank` |
| `persistence.save_to_hall_of_fame(agent, score=None)` | accepte un score robuste fourni |
| `main_biosphere` (bloc HoF, gated) | si `robust_hof_K>1` : ré-évalue les top candidats sur K ères et committe le score ROBUSTE |

- **Non-régression** : défaut `robust_hof_K=0` → la biosphère se comporte exactement comme avant.
  **146 tests verts** (5 ajoutés : gating, signature `score`, API, tri de `robust_rank`, pool vide → 0.0).
- **Smoke production** : `robust_evaluate(K=2) → 150.95` (chemin réel Biosphere3D OK).
- Imports paresseux (Biosphere3D/MambaAgent dans la fonction) → pas de circularité.

## (2) Validation avec PUISSANCE (R=4 runs/K)

| K | compétence vraie (moyenne ± écart, 4 runs) |
|---|---|
| **1** (biosphère actuelle) | 31.0 ± 13.5 |
| 4 | 44.2 ± 14.2 |
| **8** | **46.5 ± 8.5** |

> **Sous puissance, le signal est PROPRE et MONOTONE : 31 → 44 → 46 ticks, +50 % à K=8.** Le K=4 qui
> avait chuté à 14.4 en run unique (079) remonte à 44.2 sur 4 runs — c'était du bruit. La discipline
> (exiger des répétitions, refuser de conclure du run unique non-monotone) a tranché.

> **Détail révélateur : l'écart-type DIMINUE avec K (13.5 → 8.5).** De-bruiter la sélection forge non
> seulement PLUS de compétence mais un résultat PLUS FIABLE. Le bruit de fitness fabriquait *à la fois*
> la médiocrité ET la variabilité du plateau (076).

## L'arc de la compétence — clos, validé, en production

| EDR | acquis |
|---|---|
| 075 | la compétence est le goulot |
| 076 | elle plafonne sous mutation+extinction |
| 077 | le BPTT n'est PAS le remède (il nuit en RL — auto-réfutation) |
| 078 | le plateau est du BRUIT DE FITNESS (banc, ×3) |
| 079 | remède validé dans le vivant (+27 %, 1 run) |
| **080** | **remède EN PRODUCTION (gated, testé) + validé avec PUISSANCE (+50 %, écart réduit)** |

## Recommandation

- Le remède est *prouvé, puissant, en production*. **Recommandation : activer `robust_hof_K=4`** pour les
  runs sérieux (bon compromis : 44.2 ≈ 46.5 à K=8, pour la moitié du coût). Coût = K× la ré-évaluation
  des *candidats* (pas de la population) par génération. Laissé à **0 par défaut** (le choix d'activer +
  le réglage de K reste à l'utilisateur, fondé sur le compromis coût/compétence).

## Honnêteté

- Validation à R=4, 12 ères, num_agents=30 ; les écarts restent larges (la fitness de groupe est
  bruitée) mais la séparation 31→46 dépasse le bruit combiné. Un R plus grand resserrerait.
- Le gain en production réel (sur de longues runs avec curriculum/tuner) reste à observer ; l'infra
  gated permet de l'A/B-tester proprement.

## Statut

- Production : `robust_hof.py` + config + `save_to_hall_of_fame(score=)` + `main_biosphere` gated, 146
  tests. Validation : `robust_amplify.py` (sweep), `robust_power.py` (puissance). **+50 % de compétence
  forgée, en production derrière un flag.**

## Variables d'expérience

K (4 vs 8) vs coût, activation par défaut, R (puissance), nombre d'ères, A/B en production longue
(curriculum/tuner), num_agents.
