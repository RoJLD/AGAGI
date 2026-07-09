---
id: EDR-163
type: EDR
title: "Le crédit épisodique + gate MULTI-CIBLE PERMET la SPÉCIALISATION (156/157) — 3e proxy H-unif, POSITIF. Monde 2-chaînes symétriques (craft_A→use_A, craft_B→use_B) : capacité ON (gate multi-cible EDR-163 + learn_episode) s'engage sur UNE chaîne (spec_depth 0.213 vs OFF 0.042 ; comp_total≈spec_depth = pas de dispersion) là où le plain reste généraliste (0 spécialiste). BONUS : hétérogénéité de population émergente (frac_A≈0.49 = division du travail ~50/50 depuis l'init). Complète le triptyque H-unif : binding(161)+spécialisation(163) POSITIFS (routage conditionnel), rétention(162) gated par la FORCE du binding. Gate multi-cible ajouté à backend_torch (additif, in-world non cassé)"
status: accepted
gate: null
verdict: CAPABILITY_ENABLES_SPECIALIZATION
---

# EDR 163 : le crédit épisodique + gate multi-cible permet la spécialisation (division du travail émergente)

## Contexte

3e et dernier proxy standalone du pari H-unif ([[torch-inworld-integration-plan]]). EDR-156/157 : le
substrat développe un NOYAU de survie PARTAGÉ, pas de compétence spécialisée. 161 avait couvert
« compétence spécialisée vs noyau générique » (composer vs FREE) ; l'angle DISTINCT ici = choisir parmi
PLUSIEURS chaînes et s'y ENGAGER (spécialisation-comme-niche), + hétérogénéité de population.

## Méthode

Monde 2 chaînes SYMÉTRIQUES : S1 CRAFT_A ou CRAFT_B ; S2 USE_A (paie SSI craft_A) ou USE_B (paie SSI
craft_B). Une chaîne CROISÉE (craft_A→use_B) ne paie pas → il faut s'ENGAGER sur une chaîne cohérente.
Cela requiert un **gate MULTI-CIBLE** (route vers use_A si did_A, use_B si did_B, appris depuis H) —
capacité ajoutée à `backend_torch.py` (`GATE_TARGETS`, ADDITIF, flag-gated ; single-target inchangé
byte-à-byte ; suite in-world `test_torch_inworld.py` re-validée 22/22). Compare ON (gate multi +
`learn_episode`) vs OFF (TD sans gate). Métriques (dernier quart, per-agent) : spec_depth =
moyenne de max(comp_A_i, comp_B_i) ; comp_total ; frac_specialists ; frac_A parmi spécialistes
(hétérogénéité de population). 2 seeds × 800 ép, chaînes symétriques r=1.

## Constat

| | spec_depth | comp_total | frac_specialists | frac_A |
|---|---|---|---|---|
| **ON** (gate multi + learn_episode) | **0.213** | 0.213 | 0.58 | 0.49 |
| OFF (TD, sans gate) | 0.042 | 0.058 | 0.01 | — |

`VERDICT = CAPABILITY_ENABLES_SPECIALIZATION` (spec_depth ON−OFF = +0.171). Reproduit à 150 ép/1 seed
(ON 0.186 vs OFF 0.035). (Bug d'affichage cp1252 sur le caractère « − » corrigé ; calcul valide.)

## Lecture

- **La capacité PERMET la spécialisation-comme-engagement** : les agents ON s'engagent sur UNE chaîne
  (spec_depth 0.213 ; `comp_total ≈ spec_depth` → la chaîne non choisie ≈0, pas de dispersion), 58 % ont
  une niche ; le plain reste généraliste (1 % de spécialistes, spec_depth au plancher).
- **Division du travail ÉMERGENTE** (bonus) : `frac_A ≈ 0.49` → la population se différencie ~50/50
  entre chaînes A et B, la symétrie brisée par l'init de chaque agent. Une hétérogénéité de population
  que le crédit épisodique + gate multi-cible rend possible et que le plain n'atteint pas.
- **Complète le triptyque H-unif** : binding/composition (161, POSITIF), rétention (162, gated par la
  force du binding), spécialisation (163, POSITIF). Les phénomènes de ROUTAGE CONDITIONNEL (binding,
  spécialisation) sont PERMIS par la capacité ; le phénomène à COÛT (rétention) reste subordonné à la
  FORCE du binding. **H-unif substantiellement VALIDÉ comme famille routage/crédit conditionnel**, avec
  la nuance 162 (mécanisme ≠ suffisant pour les phénomènes coûteux ; il faut aussi la force).

## Conséquences

- **Nouvelle capacité substrat livrée** : gate MULTI-CIBLE (`GATE_TARGETS`) = routage conditionnel vers
  PLUSIEURS ends depuis H. Additif/flag-OFF, réutilisable in-world (multi-compétences) sans casser la
  single-target ni l'intégration en cours (axe 1).
- **Informe l'axe 3 in-world** : porter `learn_episode` (+ gate multi-cible) devrait faire émerger la
  spécialisation ET une division du travail de population là où le monde offre des niches distinctes —
  au contraire de 156/157 (substrat plain). Le levier restait le moteur (crédit + routage), pas le monde.
- Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-163`.

## Caveats

1. **Chaînes SYMÉTRIQUES sans coût** (isole l'engagement/routage ; le cas coûteux = 162, où la rétention
   échoue) : la spécialisation est PERMISE, mais son PAYOFF sous coût suivrait la même limite de force
   que 162. Non testé ici.
2. spec_depth absolu bas (0.213, substrat dégénéré) ; le ROBUSTE est le ratio ON/OFF (5×) + l'émergence
   de spécialistes (58 % vs 1 %) + frac_A≈0.5, pas l'absolu.
3. 2 seeds ; reproduit à 1 seed/150 ép. frac_A une seule mesure de population — hétérogénéité indicative.
4. Gate multi-cible ADDITIF seulement (le multiplicatif EDR-160 non étendu au multi ; inutile, additif
   domine — 160). Proxy synthétique 2-pas ; test réel = in-world (axe 3).
