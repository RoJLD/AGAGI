---
id: EDR-121
type: EDR
title: Evolvabilite du stockage en famine INCONCLUSIVE — l'evolution erode la competence (meltdown GA) avant que le stockage puisse etre teste
status: accepted
gate: G1
tests: [SDR-G1]
verdict: INCONCLUSIF
---

# EDR 121 : L'évolvabilité du stockage en famine est INCONCLUSIVE (l'évolution érode avant de bâtir)

## Contexte

Suite directe d'EDR-118 : `FamineWorld` EXIGE l'intelligence, mais via le **transfert de compétence
générale** (champion stoneage), PAS via le **stockage** (mécanique réelle mais inerte dans le banc S2).
Question north-star (`SDR-G1`) : si on **évolue** une population *dans* FamineWorld, le substrat
**apprend-il** la gratification différée (stocker en abondance pour survivre la famine) ? Méthode validée
(brainstorm) : **ablation causale** (survie cache ON vs OFF) sur le champion évolué vs le champion
stoneage (contrôle), + corroboration comportementale.

## Méthode

Instrument livré (`tools/famine_storage_probe.py`, 4 tâches subagent-driven revues) : seam d'ablation
`cache_enabled` ; `measure_genome` (survie médiane d'une cohorte + réserve à la transition) ;
`evolve_in_famine` (GA autonome, génome en mémoire) ; `compute_emergence_verdict` (delta d'ablation
apparié famine−stoneage, test de signe) ; `run_storage_probe` (orchestration). **Sélection par survie
(`calculate_life_score`), JAMAIS récompense du stockage** (test d'émergence, pas d'enseignement).

**Découverte au run (7 smokes de calibration, variables d'expérience spec §4/§6)** :
1. Le **cache-fruits d'EDR-118 est INERTE en jeu** : le moteur stoneage auto-mange le 1ᵉʳ fruit de
   l'inventaire à `energy<80` (world_1_stoneage:672) → un fruit ramassé est mangé immédiatement, ne
   s'accumule jamais. La distinctness d'EDR-118 ne tenait QUE parce que le test *plaçait les fruits à la
   main*. → Ajout d'une **banque d'énergie** exploitable (abondance : surplus au-dessus de
   `BANK_THRESHOLD` → réserve ; famine : retrait si l'agent starve ; gate `cache_enabled`).
2. Calibrations pour une affordance **équitable** : sweet-spot métab 0.25 (sinon mort en abondance avant
   la famine, EDR-085) ; `BANK_EFFICIENCY=1.0` (coût = verrou d'opportunité, pas taxe) ; `BANK_THRESHOLD=90`
   (ne capter que le vrai surplus proche du plafond, sinon écrème l'énergie vitale) ; `benchmark=False`
   pendant l'évolution (reproduction in-world = vraie évolution) ; **warm-start depuis le champion
   stoneage** (isole l'évolvabilité du stockage du bootstrap de la survie famine).

Run powered : **n=8 seeds appariés**, 30 ères, 20 agents, cycle abondance 30 / famine 40, `deterministic`.

## Constat — INCONCLUSIF (l'expérience ne peut pas trancher), mais l'évolution ÉRODE (robuste 8/8)

| seed | famine-évolué (warm-start) survie | stoneage nu survie | delta_famine (ON−OFF) |
|---|---|---|---|
| 0-7 | **7–12 ticks (les 8)** | 53–200 ticks | **0.0 (les 8)** |

- **`delta_famine = 0.0` pour les 8 seeds** : le champion famine-évolué meurt à **7–12 ticks**, AVANT la
  famine (tick 30) → il n'atteint jamais la phase de famine, le cache n'est jamais sollicité → l'ablation
  ne mesure rien. **L'expérience ne teste jamais le stockage.**
- **Érosion systématique (8/8)** : warm-starté depuis le champion stoneage (survie 53–200 selon seed),
  après 30 ères de famine le champion **s'effondre à 7–12 ticks** (×10 de dégradation). La pression de
  famine, via ce GA, **érode** la compétence au lieu de bâtir le stockage.
- Banque **équitable mais inutilisée** : `delta_stoneage` médian −9.5 (banque légèrement nuisible au
  contrôle au seuil 90) ; `fruits_at_transition=0` partout (cache-fruits mort en jeu confirmé).
- Verdict brut de l'outil = `N_EMERGE_PAS` (sign_p=0.125, médiane appariée 9.5, 6/8 fav) — **mais
  confondu** : on juge sur la science, pas le label (cf. motif EDR-116).

## Pourquoi INCONCLUSIF (les deux confusions)

1. **Mort pré-famine** : les champions meurent avant la famine → `delta_famine` structurellement 0, le
   stockage n'est jamais exercé. On ne peut pas conclure « le stockage n'émerge pas » d'agents qui
   n'atteignent pas la famine.
2. **Meltdown du GA léger** : `evolve_in_famine` (mono-champion reseed, mutation forte
   `weight_init_std=2.0`, pas d'élitisme HoF ni de fitness moyennée) dérive catastrophiquement sous une
   fitness famine bruitée/létale — il **détruit** même un warm-start compétent. C'est largement un
   artefact de la **qualité du GA**, non isolable de la capacité du substrat sans le pipeline complet.

## Conséquences

- **`SDR-G1` reste `open`** : l'évolvabilité de la gratification différée **n'est pas tranchée**.
- **Convergence (prudente) avec le verrou substrat** (EDR 095/113/117) : sous demande temporelle, le
  substrat ne bâtit pas — ici l'évolution *érode* (×10, 8/8). Magnitude trop forte pour un pur artefact,
  mais le confond GA empêche une attribution propre au substrat.
- **Correctif d'EDR-118** : la mécanique de stockage par cache-fruits est **inerte en jeu réel** (le
  moteur auto-mange les fruits) ; la distinctness d'EDR-118 était une preuve *de laboratoire* (fruits
  placés à la main), pas une affordance exploitable. La **banque d'énergie** livrée ici est la première
  affordance de stockage atteignable par la politique — équitable et ablatable, prête pour un futur test.
- **Test propre = sous-chantier dédié (backlog)** : évoluer un champion famine **compétent** (qui atteint
  la famine) exige le pipeline biosphère complet — élitisme HoF, fitness accumulée, grandes populations,
  centaines d'ères — + isolation du HoF global (`data/hall_of_fame.pkl`) pour ne pas écraser le champion
  stoneage (le contrôle). Ce n'est plus de la calibration, c'est un run de l'ordre de celui qui a produit
  le champion stoneage. Rejoint aussi l'axe gradient/torch (ADR-003) : un substrat différentiable à
  horizon explicite pourrait apprendre le report là où le GA érode.

## Honnêteté (garde-fous)

Évolution pour la survie seule (jamais récompense du stockage) ; ablation = inférence causale ; contrôle
stoneage nu ; `deterministic`. Le résultat NÉGATIF (érosion / non-émergence) est consigné avec la même
rigueur qu'un positif — et explicitement borné comme **INCONCLUSIF** plutôt que sur-vendu en
« le substrat ne sait pas stocker ». Régime nuit OFF (cohérent EDR-118), KuzuDB ambiant = corruption
logging seule (intégrité sim, précédent EDR 113/095).
