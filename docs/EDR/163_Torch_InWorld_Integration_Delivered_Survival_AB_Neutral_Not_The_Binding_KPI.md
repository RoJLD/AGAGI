---
id: EDR-163
type: EDR
title: "Intégration torch IN-WORLD LIVRÉE (crans 0-1) : le crédit épisodique `learn_episode` tourne dans la boucle biosphère derrière `use_torch_inworld` (pop persistant, buffer glissant K, crédit ALIGNÉ PAR IDENTITÉ d'agent, garde benchmark_mode), non-régression legacy prouvée. Banc A/B survie apparié → VERDICT NEUTRE POWERED (12 seeds, régime very_soft EDR-085, métrique AUC de survie car le monde est létal aux frais → survie finale = plancher EDR-090) : median_diff +0.017 <bande, 7/12, sign_p 0.55 ; le signal 6-seeds (+0.033, 4/6) s'est ÉVAPORÉ sous puissance (piège SCIENCE.md). Établit deux choses : (1) NON-RÉGRESSION in-world à la puissance — torch learn+learn_episode ne dégrade PAS la survie (feu vert sûreté migration) ; (2) la survie brute N'EST PAS le KPI du binding — learn_episode porte la composition (EDR-161), pas la survie que le crédit par-tick apprend déjà. Prochain instrument = brancher une DEMANDE DE COMPOSITION in-world"
status: accepted
gate: null
verdict: TORCH_INWORLD_NEUTRAL_ON_SURVIVAL_NON_REGRESSION_CONFIRMED_SURVIVAL_NOT_THE_BINDING_KPI
---

# EDR 163 : intégration torch in-world livrée (crans 0-1) — A/B survie NEUTRE powered, la survie n'est pas le KPI du binding

## Contexte

La carte valeur torch est complète en ISOLATION (parité 140/141, mémoire BPTT 145, binding
gate+`learn_episode` 158/159, forme de gate close 160) et PAIE en proxy sous demande de composition
(EDR-161). Le reste explicite du fil G1 = **allumer `learn_episode` dans la vraie boucle biosphère**
(`world_1_stoneage.py`, `Biosphere3D.step`), pari H-unif de [[torch-inworld-integration-plan]]. Ce
EDR livre l'intégration (crans 0-1) et mesure son premier verdict de survie in-world.

## Méthode

**Livraison (subagent-driven, 6 tâches TDD + 1 fix de revue, 10 tests verts, review final PRÊT À
MERGER).** Flag opt-in `Biosphere3D.use_torch_inworld` (défaut OFF, legacy strictement non-régressif) :
- **Pop torch PERSISTANT** hissé hors de la boucle par-tick (`_get_batch_model`) — le `batch_model`
  legacy est transitoire (recréé/tick) mais l'optimiseur SGD + le gate doivent survivre entre ticks ;
  rebuild sur changement de B (mortalité).
- **Buffer glissant K** porté par le monde (`_torch_traj`, deque) ; `learn_episode` tous les K ticks.
- **Crédit ÉPISODIQUE ALIGNÉ PAR IDENTITÉ d'agent** (`_maybe_learn_episode`) : `benchmark_mode` fige la
  reproduction mais PAS la mortalité → la population décroît → chaque tick du buffer est rogné aux
  agents ENCORE vivants (population monotone décroissante → intersection = cohorte courante = `pop.B`,
  toujours définie). Sans cet alignement `learn_episode` recevrait des batchs de tailles incohérentes.
- Garde : `use_torch_inworld` EXIGE `benchmark_mode` (sinon naissance+mort le même tick → crédit sur le
  mauvais agent, corruption silencieuse). Fix d'intégration : normaliser `compute_spent` scalaire(torch)
  → array(B) (le forward torch MVP ne porte pas le TTC).

**Mesure.** Banc `tools/torch_inworld_ab.py` (A/B survie apparié par seed, `compute_ab_verdict`).
Diagnostic préalable : le monde est LÉTAL aux agents frais (extinction tick 8 défaut / 17 soft / 50
very_soft) → la survie FINALE est un plancher structurel (EDR-090) et le verdict démo était NEUTRE
artefactuel. Pivot vers la métrique **AUC de survie** (aire sous la courbe de population = durée de vie
intégrée [0,1]), qui discrimine même sous extinction totale. Régime **very_soft** (sweet spot EDR-085 :
base_metabolism 0.3, forage_payoff 3.0, food_regen_scale 1.5), 24 agents, size 20, 60 ticks. Verdict
apparié à 12 seeds (6 + power-up de 6).

## Constat

| n seeds | favorables torch | median_diff (AUC) | sign_p | verdict |
|---|---|---|---|---|
| 6 | 4/6 | +0.033 | 0.69 | GRADIENT_GAGNE (fragile) |
| **12** | **7/12** | **+0.017** (<bande 0.02) | **0.55** | **NEUTRE** |

Le verdict robuste est **NEUTRE** : torch in-world ≈ legacy sur la durée de vie. Le signal apparent à
6 seeds (+0.033) a fondu à +0.017 en doublant la puissance ; le test de signe (juge fiable) n'a jamais
confirmé (7/12).

## Lecture

- **NON-RÉGRESSION IN-WORLD À LA PUISSANCE.** Allumer torch (`learn` TD par-tick + `learn_episode`
  épisodique) dans la boucle ne dégrade PAS la survie sur 12 seeds appariés. C'est le feu vert de sûreté
  pour la migration — cohérent avec la parité forward hors-boucle (140/141, p=0.46).
- **LA SURVIE BRUTE N'EST PAS LE KPI DU BINDING.** `learn_episode` porte le crédit conditionnel
  means→ends (composition, EDR-158/159/161), PAS la survie de base — que le crédit par-tick (`learn`)
  apprend déjà. Un A/B survie SANS demande de composition ne peut donc pas détecter l'apport de
  `learn_episode` : les deux bras survivent pareil. Le NEUTRE est ATTENDU, pas décevant.
- **Le signal 6-seeds = bruit** : 6ᵉ fois qu'un signal à peu de seeds s'évapore sous puissance
  (discipline SCIENCE.md « powerer avant de conclure »). Le verdict de bande sur médiane est fragile ;
  le test de signe tranche.

## Conséquences

- **Prochain instrument = DEMANDE DE COMPOSITION in-world** (pont axe 1 cran 2 + axe 3) : porter le
  monde craft→consomme d'EDR-161 dans la biosphère, là où `learn_episode` peut montrer un effet
  mesurable. La survie brute est le bon instrument de NON-RÉGRESSION, pas de détection du binding.
- ⚠️ **Bloqueur cran 2** (gate in-world) : le rebuild du pop sur mortalité RÉINITIALISE `w_gate`/`b_gate`
  → éroderait l'accumulation du gate. À résoudre (persister le gate à travers rebuild) AVANT d'allumer
  le gate in-world.
- **Leçon méthodo réutilisable** : pour tout banc de survie in-world sur substrat dégénéré, la survie
  FINALE est un plancher (EDR-090) → mesurer l'**AUC de survie** (durée de vie intégrée).
- Converge le pari H-unif AFFINÉ par EDR-162 (le crédit épisodique active le binding mais pas assez FORT
  pour racheter la rétention craft coûteuse) : le levier de l'axe 3 est la FORCE du binding, pas le
  crédit. Cf. [[torch-inworld-integration-plan]].

## Caveats

1. **Régime very_soft + AUC** : le verdict NEUTRE vaut pour ce barème de survie (sweet spot). Un autre
   régime (agents pré-entraînés/champions, budget plus long) pourrait exposer un signal — mais mélangerait
   compétence acquise et apport du crédit (1 variable violée). L'AUC sur agents frais appariés est le
   contraste le plus propre (seul le backend varie).
2. **12 seeds** : suffisant pour réfuter le signal de bande (median tombe sous seuil), pas pour prouver
   une équivalence stricte. Le ROBUSTE = disparition du signal sous doublement de puissance.
3. **Scripts de mesure THROWAWAY** (scratchpad `torch_inworld_ab_long.py` avec AUC+knobs,
   `survival_regime_probe.py`) : l'AUC et les knobs de survie ne sont PAS encore dans
   `tools/torch_inworld_ab.py` (banc du repo mesure la survie finale). À formaliser si l'AUC devient le
   KPI standard des bancs in-world.
4. Le forward torch reste MVP (pas de TTC/NTM/attention) : la garde `compute_spent` traite cette limite
   côté monde, pas une capacité portée. Bornage attendu (substrat minimal volontaire, 158).
