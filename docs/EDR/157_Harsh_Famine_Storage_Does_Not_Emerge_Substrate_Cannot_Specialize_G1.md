---
id: EDR-157
type: EDR
title: Durcir la famine (regime ou le stockage est load-bearing) NE fait PAS emerger le stockage — l'evolution degrade au lieu de specialiser ; le substrat n'evolue pas la competence world-specifique que le monde EXIGE
status: accepted
gate: G1
tests: [SDR-G1]
verdict: STOCKAGE_N_EMERGE_PAS_SOUS_PRESSION
---

# EDR 130 : Durcir la famine ne fait pas émerger le stockage — le substrat ne spécialise pas

## Contexte

EDR-156 (transfert zéro-shot POSITIF) a laissé un **frontier explicite** : le transfert était « parfait »
parce qu'il n'existe qu'une compétence — la survie world-générale — et **aucune compétence
world-spécifique** (craft, stockage) n'émerge pour tester une vraie généralisation. EDR-155 avait montré
le stockage **redondant** (le buffer d'énergie naturel suffit à famine courte). La question directe :
**si on rend le monde tel qu'il EXIGE le stockage, le substrat l'évolue-t-il ?** C'est le test le plus
propre du verrou « émergence d'une spécialisation » — priorité 2 tranchée après le transfert (robla).

## Méthode

**Seam de dureté** (TDD 15/15) : env-vars `FAMINE_CYCLE_ABUNDANCE`/`FAMINE_CYCLE_FAMINE`
(`world_famine.py`, non-breaking, pattern HOF_PATH/MAX_ERAS d'EDR-155).

**Calibration** (`tools/famine_harshness_probe.py`, TDD 3/3) : sur le champion EDR-155, sweep `cyc_fam`
à `cyc_ab=30`, 3 conditions — buffer seul (cache OFF), réel (cache ON, banking auto si energy>90),
oracle-storer (réserve 150 pré-injectée). **Régime cible trouvé** : `cyc_ab=30 / cyc_fam=120` → buffer
plafonne (~96), oracle survit ~223 (**2.3×**) → le stockage est **load-bearing** (corrige le « redondant »
d'EDR-155, vrai seulement à famine courte).

**Ré-évolution** : pipeline complet (`main_biosphere` famine, élitisme HoF) sous le régime dur, **3 seeds
(42/43/44) × 60 ères**, HoF dédié par seed (HoF stoneage global INTACT, contrôle sauf). **Ablation
appariée** : les 3 champions durs vs les 3 champions doux (EDR-155), tous mesurés dans le **même régime
dur** (n_eras=5, max_ticks fixe), sur buffer/réel/oracle + réserve à la 1ʳᵉ transition.

## Constat — le stockage N'ÉMERGE PAS (3/3), et durcir DÉGRADE

| groupe (médiane) | buffer (OFF) | réel (ON) | oracle | réserve@transition | storage_help (réel−buffer) |
|---|---|---|---|---|---|
| **HARSH** (évolué sous dur) | 43.5 | 45.0 | 96.5 | **7.6** | **+0.0** |
| **DOUCE** (EDR-155) | 66.0 | 66.0 | 139.0 | **7.7** | **+0.0** |

1. **Le stockage n'est pas exploité (harsh comme douce)** : `storage_help ≈ 0` (réel ≈ buffer) et
   `réserve@transition` **7.6 ≈ 7.7** — identique entre groupes. L'évolution sous pression n'a **pas**
   augmenté l'usage du stockage. (Le pic `réserve=16.8` d'un preview mono-champion s42 était un outlier ;
   la médiane 3-seeds le démasque.) Pour s43, le banking auto **nuit** même (réel < buffer).
2. **L'oracle domine partout** (96.5 vs 43.5 ; 139 vs 66) → le monde EXIGE réellement le stockage, la
   marge existe — mais **aucune politique évoluée ne la capture**.
3. **Durcir a DÉGRADÉ l'évolution** : les champions durs sont **plus faibles** que les doux dans le MÊME
   régime (buffer 43.5 < 66 ; oracle 96.5 < 139). Life_scores near-plancher + extinction totale par ère
   (~3.6 max) → piège **EDR-090** (« pas de premier barreau survivable » : régime trop létal, pas de
   prise pour l'évolution). Durcir n'a pas spécialisé, il a appauvri.

## Lecture

- **Réponse au frontier d'EDR-156** : quand on FORCE une compétence world-spécifique (stockage exigé,
  oracle 2× buffer), elle **n'émerge pas** ; le substrat **dégrade au lieu de spécialiser**. Le transfert
  « noyau-partagé-seulement » d'EDR-156 n'est donc PAS un artefact des mondes choisis — c'est la **limite
  du substrat** : il n'évolue pas de spécialisation nouvelle même quand le monde la récompense.
- **Convergence** : même verrou que EDR-111 (tool-gate → le craft n'émerge pas, apex s'effondre),
  EDR-125/128 (binding compositionnel absent), EDR-090 (durcir sans adapter le substrat = négatif).
  Le levier n'est PAS « rendre le monde plus exigeant » (world-side) mais **le substrat / le moteur
  d'apprentissage** (cf. [[nas-bottleneck-is-substrate-not-search]], [[sota-gap-substrate]],
  [[coop-competence-is-population-property]]).

## Conséquences

- **`SDR-G1`** reste `open`. Le diptyque 129/130 le cerne : (129) le transfert zéro-shot du noyau partagé
  est acquis ; (130) aucune compétence world-spécifique n'émerge pour aller au-delà. **Le north-star fort
  (généraliser une compétence composée) est bloqué en amont, à l'ÉMERGENCE, pas au transfert.**
- **Durcir-la-famine est RÉFUTÉ comme levier d'émergence.** Ne pas réinvestir côté monde. Le prochain
  levier à fort rendement est **côté substrat/moteur** : (a) forcer le conditionnement du crédit (gating
  did_x→logits, TD(λ)/éligibilité — cf. EDR-128), (b) migrer le moteur d'apprentissage (torch+plasticité
  différentiable, cf. [[sota-gap-substrate]]), plutôt qu'ajouter des exigences qu'un substrat plat ne peut
  satisfaire.

## Caveats (honnêteté)

1. **Affordance de banking auto-déclenchée** (surplus quand energy>90) : « utiliser le stockage » exige de
   sur-forager au-delà de 90, ce que l'évolution n'a pas sélectionné. Le non-usage peut donc mêler « le
   substrat ne peut pas » et « l'affordance est structurellement dure à déclencher ». Une affordance
   pilotée par une action dédiée testerait cette distinction — mais EDR-121/126/130 (trois designs de
   stockage : cache-fruits, banque, régime dur) convergent tous vers le non-usage → robustesse du négatif.
2. **Régime dur peut-être trop létal** (EDR-090) : les champions durs sont near-plancher. On ne peut donc
   pas exclure « un régime dur MAIS survivable-avec-prise » où le stockage émergerait. Mais la calibration
   montre le monde survivable (douce-champ atteint 66 en dur) → durcir n'a pas aidé, il a nui.
3. **n=3 seeds** (smoke-confirmatoire, cohérent EDR-155) ; robuste sur le pattern (3/3 réserve≈douce, 3/3
   storage_help≈0, 3/3 durs plus faibles) mais pas un verdict lourdement powered.
4. **Isolation HoF** vérifiée (md5 stoneage global inchangé) ; déterminisme résiduel `main_biosphere`
   (memory_retriever non clear entre ères, comme EDR-155).
