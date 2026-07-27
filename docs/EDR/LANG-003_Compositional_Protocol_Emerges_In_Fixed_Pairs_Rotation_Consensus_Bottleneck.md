---
id: LANG-003
type: EDR
title: "Un protocole STRUCTURELLEMENT COMPOSITIONNEL émerge en PAIRES FIGÉES (Arc 4 langage, systématicité). Référents (a0,a1) in [0,A)^2, messages 2-symboles (rollout 2-pas indicé par position), receiver prédit les DEUX attributs. Test = généralisation ZÉRO-SHOT sur la diagonale held-out (combos jamais vus, valeurs vues) + similarité topographique. FIXED : zeroshot 0.505 ~ within 0.539 >> chance 0.333 (écart 0.03) ET topsim +0.30 (répliqué M=8 : 0.49/0.55/+0.36) -> code compositionnel qui généralise, DOUBLE-confirmé. La ROTATION (levier LANG-002) NE CONVERGE PAS sur la tâche 2-symboles (within~chance à M=8/8000ép) -> goulot de consensus prohibitif ; la compositionnalité vient de la STRUCTURE positionnelle du message, pas de la pression communautaire. Compositionnalité PARTIELLE (within ~0.54 = capacité du substrat 172-nœuds)"
status: accepted
gate: null
verdict: COMPOSITIONAL_PROTOCOL_EMERGES_IN_FIXED_PAIRS
---

# LANG-003 : un protocole structurellement compositionnel émerge en paires figées (Arc 4)

## Contexte

LANG-001 (signalisation porteuse) et LANG-002 (protocole partagé sous rotation) portaient sur des référents
ATOMIQUES (un symbole = un référent). Un vrai langage DÉCOMPOSE le sens : référent = (attribut1, attribut2),
message = plusieurs symboles, et le protocole GÉNÉRALISE à des combinaisons JAMAIS VUES (systématicité) —
le test-or de l'emergent-comm. Deux questions : (1) le substrat développe-t-il un code compositionnel
(généralisation zéro-shot + structure topographique) ? (2) la rotation de partenaires (levier LANG-002)
augmente-t-elle la compositionnalité (« effet communauté » de la littérature) ?

## Méthode

`tools/compositional_language_probe.py`. 2 populations torch distinctes, crédit épisodique, sans gate.
- SENDER voit un référent (a0,a1) ∈ [0,A)² → émet un MESSAGE de 2 symboles : rollout 2-pas indicé par
  position (obs = référent complet + drapeau de position ; H porté entre pas). Il PEUT encoder holistiquement
  (chaque symbole = f(a0,a1)) ou compositionnellement (symbole_t = f(a_t)) — non pré-câblé.
- RECEIVER lit le MESSAGE complet (2 symboles) aux deux pas → prédit les DEUX attributs (position → quel
  attribut sortir). Récompense partagée = fraction d'attributs corrects.
- **Généralisation zéro-shot** : held-out = la DIAGONALE (a,a) (A combos) tenue hors entraînement ; on
  entraîne sur les A²−A autres combos (chaque VALEUR d'attribut reste vue). Éval greedy : within (combos
  entraînés) vs zeroshot (diagonale). Code compositionnel → zeroshot ≫ chance (1/A) ; holistique → ~chance
  (le message de (a,a) est inédit → indécodable).
- **Similarité topographique** (métrique canonique, indépendante du split) : ρ de Spearman entre distance de
  SENS (Hamming attributs) et distance de MESSAGE (Hamming symboles greedy), par agent, médiane. ρ>0 =
  systématique. Levier : FIXED (paires figées) vs ROTATION (partenaire aléatoire/épisode, cf. LANG-002).
  A=3, V=6, 2 seeds.

## Constat

| Config | within | zeroshot | gen_gap | topsim |
|---|---|---|---|---|
| FIXED M=16, 5000 ép | 0.539 | 0.505 | +0.172 | **+0.304** |
| FIXED M=8, 8000 ép | 0.547 | 0.490 | +0.156 | **+0.357** |
| ROTATION M=8, 8000 ép | 0.328 | 0.312 | −0.021 | +0.241 |
| ROTATION M=16, 5000 ép | 0.333 | 0.333 | +0.000 | — |

(chance = 0.333 ; `VERDICT = COMPOSITIONAL_PROTOCOL_EMERGES_IN_FIXED_PAIRS`.)

## Lecture

- **La compositionnalité ÉMERGE en paires figées, DOUBLE-confirmée.** Deux métriques indépendantes
  convergent : (1) **généralisation zéro-shot** — zeroshot 0.505 ≈ within 0.539 (écart 0.03), tous deux
  ≫ chance 0.333 : le code décode des combinaisons JAMAIS VUES presque aussi bien que les vues ; (2)
  **topsim +0.30 à +0.36** : distances de sens et de message corrélées → structure systématique. Répliqué à
  M=8 (0.49/0.55/+0.36) ET M=16 → robuste (4 runs concordants). Un code holistique aurait échoué au
  zéro-shot (message de la diagonale inédit → hasard) ; il ne le fait pas. La structure positionnelle du
  message 2-symboles suffit à faire émerger un code ~compositionnel.
- **Le levier rotation est RÉFUTÉ dans ce budget.** La rotation, qui produisait un protocole PARTAGÉ sur la
  tâche 1-symbole (LANG-002), **ne converge pas** ici (within = chance à M=8 comme M=16, jusqu'à 8000 ép).
  La coordination 2-symboles sous partenaire changeant est un problème de consensus bien plus dur (le goulot
  de conventionnalisation de LANG-002 explose avec la complexité du message). Donc la compositionnalité
  observée vient de la STRUCTURE du message, PAS de la pression communautaire. (topsim rotation +0.24 malgré
  within~chance = structure résiduelle du sender non décodée par le receiver — coordination échouée, pas
  compositionnalité fonctionnelle : zeroshot = chance.)
- **Compositionnalité PARTIELLE.** within ~0.54 (pas ~1.0) et topsim ~0.3 (pas ~0.9) : le code est
  systématique mais imparfait (confusions d'attributs résiduelles). Le plafond est la capacité du substrat
  (LTC 172 nœuds, crédit tronqué), pas l'absence de structure — cohérent avec le verrou substrat récurrent.

## Conséquences

- **Systématicité livrée (partielle) hors biosphère** : le substrat torch développe un protocole
  compositionnel qui généralise à des combinaisons inédites — le troisième palier du langage (après
  signalisation 001 et partage 002). L'axe langage a désormais capacité + partage + systématicité *en proxy*.
- **Recette compositionnelle torch** : messages MULTI-SYMBOLES indicés par position + prédiction par attribut
  + crédit épisodique suffisent ; la compositionnalité émerge en PAIRES FIGÉES (pas besoin de rotation, qui
  est même contre-productive ici faute de converger). In-world, cela prédit qu'un langage compositionnel peut
  émerger même en interactions dyadiques stables, POURVU que les référents soient structurés (attributs
  composables) et les messages multi-tokens.
- **Nuance à LANG-002** : la rotation aide le PARTAGE (1-symbole) mais son coût de consensus scale mal avec la
  complexité du message → à grande complexité, la structure du message (positionnelle) est le levier de
  compositionnalité, pas la communauté. Leviers ouverts pour pousser la compositionnalité PARFAITE : plus
  d'épisodes / capacité de substrat ; pression de longueur/vocabulaire ; curriculum de rotation (converger
  d'abord en dyade, rotationner ensuite).
- Relié : `REF-LTC -A_ADOPTER_POUR-> LANG-003`. Prolonge [[lang-referential-capability]] (001/002). Recoupe
  la SOTA `langage→EGG` (compositionnalité émergente, topographic similarity, zero-shot generalization) de
  [[sota-gap-substrate]].

## Caveats

1. Compositionnalité PARTIELLE (within ~0.54, topsim ~0.3) : le code est systématique mais n'atteint pas la
   maîtrise parfaite des combos entraînés — convergence incomplète / capacité de substrat bornée. Le ROBUSTE
   est le CONTRASTE (zeroshot ≈ within ≫ chance + topsim>0, répliqué M=8/M=16), pas les décimales.
2. Held-out = la DIAGONALE (a,a) fixe (non varié par seed) ; A=3 (2 attributs × 3 valeurs, 9 combos, 3
   held-out). 2 seeds/config, mais la réplication cross-config (M=8 ET M=16 positifs) renforce. A=4 / autres
   splits non sweepés.
3. Le design ALLOUE une prédiction par attribut (2 sorties positionnelles) : c'est ce qui rend le zéro-shot
   possible (un décodage joint A²-way ne pourrait pas produire un combo held-out). Le test porte donc sur la
   compositionnalité du CODE (message factorise-t-il ?) mesurée par topsim + généralisation, PAS sur la
   capacité du receiver à inventer une classe jointe inédite. C'est le cadrage standard emergent-comm.
4. ROTATION non poussée à convergence (échoue à M=8/16 jusqu'à 8000 ép) : le levier communautaire est
   inconclusif/négatif DANS CE BUDGET, pas prouvé impossible (curriculum dyade→rotation non testé).
5. Proxy synthétique hors biosphère (même bornage que 001/002) : le vrai bénéfice = in-world (087).
