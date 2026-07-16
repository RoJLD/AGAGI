# EDR 125 — Le mur du craft : l'echelle de l'outil S'INVERSE (apex par coop, pas par la lance) -> le poids spears de life_score est inerte

> **Date** : 2026-06-30. **Verdict pre-enregistre** : `CRAFT_WALL CONFIRME` si `frac_craft < frac_forage` ET `frac_apex >= frac_craft` (echelle inversee) ET `frac_craft <= 0.10` ; sinon `ECHELLE MONOTONE` ; `INDETERMINE` si `frac_forage < 0.10`.
> **Resultat** : **CRAFT_WALL CONFIRME** (forage 0.600, craft **0.011**, apex **0.156** -> apex ~14x craft, echelle inversee).
> **Outil** : `tools/competence_profile.py` (`main_competence_profile`). **Seed** : 1240 (smoke 99240). **Commit** : eb81cff.
> **Spec/Plan** : `docs/superpowers/{specs,plans}/2026-06-30-competence-profile-craft-wall*`. Chantier P3a de l'audit memoire (`docs/AUDIT_MEMOIRE_INTELLIGENCE.md`) — 1er instrument PER-TYPE.

## 1. Question

`life_score` (seul signal de selection) ECRASE la competence en un scalaire : `mammoth_kills*400 +
spears_crafted*300 + preys_eaten*50 + ...`. On ne mesure JAMAIS la competence ventilee par TYPE. Les
fractions par tier existent dans `stoneage_competence` (`frac_hunt/frac_apex/frac_tool` via
`_frac_reaching`) mais sont immediatement collapsees. Question falsifiable : dans l'echelle moyens->ends
{survie < forage < CRAFT < apex}, le tier CRAFT (fabriquer la lance) est-il un goulot ANORMAL que
l'apex CONTOURNE ? Prediction non-triviale (issue de `world-floor-survivability-gate` : apex par
COOPERATION, lance 1.6%, altars = code mort) = **INVERSION DE L'ECHELLE** : `frac_apex >= frac_craft`
(les agents chassent le mammouth PLUS qu'ils ne craftent), alors que craft est cense etre un barreau
INFERIEUR a apex.

## 2. Methode

Instrument `competence_profile`, deux phases par seed (R=3, graines appariees `seed_boundary`) :
1. **Evolution** (repro ON) : faire evoluer une lignee stoneage `eras=12` (cliquet top-5, sweet metab
   0.25 / payoff 3.0) -> champions competents (best_ever top-5).
2. **Mesure profil** (cohorte FIXE) : repliquer les champions en cohorte de `num_agents=30`, mesurer sur
   un episode a `benchmark_mode=True` (**leçon EDR 114b** : pas de reproduction -> pool = cohorte
   initiale, pas de dilution par nouveau-nes tardifs ; **leçon P0** : memory_retriever neutralise AVANT
   la boucle). Fractions « a deja atteint » binaires par agent (`_frac_reaching`, seuil >=1).

Verdict porte par les fractions moyennes sur R seeds. **Revue opus** : `benchmark_mode` ne gate QUE les
3 chemins de reproduction (energie/MATE/HGT) — RIEN dans le pipeline forage/craft/apex -> la cohorte
fixe defait le confond 114b sans biaiser les tiers ; pas de cohorte degeneree (placement x/y stochastique).

## 3. Resultat (run pre-enregistre, seed 1240, R=3, 2 passes byte-identiques)

```
  seed | forage  craft   apex  |   n
  1240 |  0.600  0.000  0.200 |   30
  1241 |  0.500  0.000  0.100 |   30
  1242 |  0.700  0.033  0.167 |   30
  MOYEN|  0.600  0.011  0.156
  VERDICT : CRAFT_WALL CONFIRME
```

`frac_craft 0.011 < frac_forage 0.600` (craft plus rare que forage) ET `frac_apex 0.156 >= frac_craft
0.011` (echelle INVERSEE : apex ~14x craft) ET `frac_craft <= 0.10` (quasi-mort) -> **CRAFT_WALL
CONFIRME**. Determinisme verifie (pass 1 == pass 2). Cohere avec les ordres de grandeur de world-floor
(apex 21.7% / lance 1.6% ; ici apex 15.6% / lance 1.1%).

## 4. Lecture

- **L'echelle de l'outil est INVERSEE.** Les agents atteignent l'apex (mammouth) ~14x plus souvent
  qu'ils ne fabriquent la lance. Le pathway OUTIL (rub -> lance -> chasse armee) est une **branche
  quasi-morte** ; l'apex est atteint AUTREMENT — par COOPERATION (meute), pas par l'outil (confirme
  `coop-competence-is-population-property` + `world-floor-survivability-gate` au niveau POPULATION,
  proprement mesure sur cohorte fixe).
- **La metrique est inculpee.** `life_score` pondere `spears_crafted` a 300 (2e poids le plus fort)
  mais **1.1% seulement** des agents craftent un jour -> ce terme est **largement INERTE** : il
  contribue a la selection pour une fraction infime de la population. Le signal qui pilote reellement
  la selection = forage (0.60) + apex-coop (0.16) + survie. Levier « reparer la metrique » (re-ponderer
  sur le signal vivant, retirer/abaisser le poids craft mort, comme l'autel deja retire d'EDR 096).
- **Premier instrument PER-TYPE.** Contre le constat de l'audit (« on ecrase les intelligences sur
  l'age de survie »), ce banc SURFACE enfin la competence ventilee {forage/craft/apex} et la rend
  falsifiable. Les composants existaient (`_frac_reaching`, descripteur MAP-Elites 4-tiers) ; ils
  n'etaient jamais rapportes separement.

## 5. Caveats (perimetre du verdict)

- Verdict au regime stoneage sweet-spot (`metab=0.25/payoff=3.0`, `eras=12`, `num_agents=30`, R=3). Le
  craft pourrait emerger sous d'autres pressions (gate-outil, EDR 111 a montre que forcer le monde a
  EXIGER l'outil effondre l'apex sans faire emerger le craft -> coherent : le craft ne vient pas).
- `frac_craft` est mesure sur des CHAMPIONS evolues (les meilleurs) en cohorte fixe ; il reste ~0.01
  (2 seeds sur 3 a exactement 0) -> robuste. Mesurer la population entiere (pas que les champions)
  donnerait probablement encore moins de craft.
- L'evolution (phase 1) utilise `run_era_pool` (memory_retriever non neutralise), mais le run est
  EMPIRIQUEMENT deterministe (2 passes byte-identiques) ; seule la phase de MESURE exige le determinisme
  strict (assure par benchmark_mode + P0). 

## 6. Suite & provenance

- **Suite** : le levier d'action est la **metrique** (re-ponderer life_score sur les tiers vivants), pas
  un nouveau levier d'exploration du craft (EDR 014/111 ont montre que le craft n'emerge pas). Cela
  s'inscrit dans le diagnostic substrat ([[sota-gap-substrate]]) : la chaine compositionnelle outil
  (means->ends) est precisement ce que la session // attaque en torch (EDR 122).
- **Provenance** : `Harness(name="competence_profile")` -> `results/competence_profile_1240.json`
  (gitignore) ; seed 1240, smoke 99240 distinct ; 2 passes byte-identiques ; AUCUN test relance apres
  le run (EDR 107). Tooling-only : `git diff src/` VIDE (zero collision session //).
- **Revue** : subagent-driven (Task 1 + Task 2 SPEC ok + quality Approved) ; revue finale **opus**
  READY TO MERGE — cohorte fixe valide (benchmark_mode ne gate que la repro), verdict falsifiable.
- **Numerotation** : EDR 125 (123/124 pris sur origin/main). ⚠️ collision cross-session sur 123
  (`Credit_Horizon` vs `Compositional_Fade`) a arbitrer au merge de feat/d1.
