# EDR 127 — La selection QD ne sauve PAS le craft mort : le craft est ATTEINT mais NON RETENU (ni substrat ni selection -> retention)

> **Date** : 2026-07-01. **Verdict pre-enregistre** : `QD_RESCUE_CRAFT CONFIRME` si `d = frac_craft_QD - frac_craft_HOF >= 0.10` ET `frac_craft_QD >= 0.10` ; `QD_NUIT` si `d <= -0.10` ; sinon `QD_NEUTRE`.
> **Resultat** : **QD_NEUTRE** (d = **+0.011**, 0/3 seeds per-seed) — MAIS lecture affinee par le readout C1 : le craft est **atteint** (cellule tier2 occupee, borne haute sample 0.25) et **non ecarte par la selection** (QD preserve l'elite craft), donc le verrou = **RETENTION** (le champion crafteur ne re-crafte pas en cohorte fixe).
> **Outil** : `tools/qd_tier_rescue.py` (`main_qd_tier_rescue`). **Seed** : 1260, R=3 (smoke 99260). **Commit** : bdb7cb9.
> **Spec/Plan** : `docs/superpowers/{specs,plans}/2026-07-01-qd-tier-rescue-craft*`. Chantier P3 de l'audit memoire (`docs/AUDIT_MEMOIRE_INTELLIGENCE.md`) — 2e instrument PER-TYPE (apres EDR 125).

## 1. Question

EDR 125 a montre que le tier CRAFT est quasi-mort au niveau population (frac_craft 0.011) et que le poids
`spears_crafted`x300 de `life_score` est **inerte**. Le levier de l'audit : « selectionner sur des niches
diverses » (QD/MAP-Elites) plutot que sur le scalaire `life_score`. `tools/map_elites_compare.py` comparait
DEJA QD vs HoF, mais sur le scalaire `life_score` (QD~=HoF, non concluant). Question falsifiable NEUVE :
la selection QD **sauve-t-elle le tier CRAFT mort** que `life_score` droppe structurellement (top-5 par
score ecarte un genome craft-pur : spears x300 < forager+apex-coop), ou le mur du craft est-il du
**substrat/atteignabilite** (refute, coherent EDR 111) ?

**Mecanisme teste** : le HoF top-5 par `life_score` n'a pas de cellule dediee au craft ; l'archive QD garde
une elite dans la **cellule tier=2** (`descriptor` de `map_elites.py`) et reproduit depuis elle. Si le craft
est atteignable ET retenu, QD le propage -> `frac_craft_QD` monte ; sinon non.

## 2. Methode

Instrument `qd_tier_rescue`, deux bras evolutifs APPARIES par seed (R=3, graines `seed_boundary`) :
1. **Bras HoF** = `_evolve_champions` (cliquet top-5 `life_score`, EDR 125, reutilise verbatim).
2. **Bras QD** = `_evolve_qd_champions` (archive MAP-Elites, reproduit depuis `archive.sample(5)`) -> renvoie
   `(champions=archive.sample(5), archive)`.
3. **Mesure per-tier** de CHAQUE bras sur **cohorte FIXE** (`benchmark_mode` : pas de reproduction, lecon
   114b ; memory_retriever neutralise, lecon P0) via `_measure_profile` + `_tier_fractions` (fractions
   binaires par agent, `_frac_reaching`).

**Champions QD mesures = `archive.sample(5)`** (l'operateur de selection PROPRE au bras QD), PAS le top-5
`life_score` (qui collapserait QD sur HoF -> test tautologique). Symetrie : les deux bras evoluent memory-ON
(empiriquement deterministe) et se mesurent memory-OFF + `benchmark_mode` (deterministe strict).

**Readouts anti-confond (revue finale opus)** : (I1) `n_confirme_seeds` = nb de seeds portant le CONFIRME
per-seed (le verdict gele reste sur la MOYENNE ; ce readout evite un faux CONFIRME pilote par 1 graine au
plancher, n=3) ; (C1) `craft_cell_share = cells_tier2 / coverage` = **borne haute de `frac_craft_QD` qu'un
`sample(5)` UNIFORME peut delivrer** -> desambiguise « craft inatteignable » (tier2 vide) de « craft present
mais dilue/non-retenu » (tier2 occupe).

## 3. Resultat (run pre-enregistre, seed 1260, R=3, 2 passes byte-identiques)

```
  seed | HOF  forg  craf  apex | QD   forg  craf  apex | QDcells t2/t3
  1260 |      0.400 0.000 0.133 |      0.567 0.000 0.200 |    1/ 1
  1261 |      0.600 0.000 0.267 |      0.733 0.000 0.400 |    1/ 1
  1262 |      0.600 0.000 0.267 |      0.433 0.033 0.133 |    1/ 1
  MOYEN|      0.533 0.000 0.222 |      0.578 0.011 0.244
  d(craft) = +0.011
  seeds CONFIRME per-seed = 0/3
  QD craft-cell share (borne haute sample) = 0.250 (cells_tier2 1.00 / coverage 4.00)
  VERDICT : QD_NEUTRE
```

`d = frac_craft_QD 0.011 - frac_craft_HOF 0.000 = +0.011 < 0.10` (0/3 seeds per-seed) -> **QD_NEUTRE**.
Determinisme verifie (pass 1 == pass 2, bloc resultat byte-identique).

## 4. Lecture

- **QD ne sauve PAS le craft** : la selection par niches diverses ne fait pas mieux que `life_score` sur le
  tier craft (d +0.011, sous le seuil ; 0/3 seeds). Le levier « selectionner sur des niches » est REFUTE
  pour le craft.
- **MAIS le readout C1 tranche POURQUOI — ce n'est ni le substrat ni la selection, c'est la RETENTION.**
  L'archive QD a **peuple une cellule tier2** (cells_tier2 = 1.00 en moyenne, sur 3/3 seeds) : le craft EST
  atteint pendant l'evolution. La borne haute `craft_cell_share = 0.25` signifie qu'un `sample(5)` uniforme
  tire ~1.25 champion crafteur en esperance -> **les champions mesures CONTIENNENT l'elite craft**. Pourtant
  `frac_craft_QD = 0.011 << 0.25` : le champion crafteur, replique en cohorte fixe et rejoue sur un episode
  neuf, **ne re-crafte pas**. Donc le craft n'est ni inatteignable (tier2 occupe), ni ecarte par la
  selection (QD l'a garde, l'echantillon le contient) -> le verrou est la **NON-RETENTION** : le craft est un
  **evenement stochastique non reproductible**, pas un comportement appris/stable.
- **Convergence.** Confirme l'arc substrat (EDR 111 repertoire-monde, 119 taille, 120 memoire, 125 mur du
  craft) au niveau selection : meme un operateur de selection qui PRESERVE explicitement le craft ne le rend
  pas retenu. Resonne directement avec **EDR 126** (le plafond joint compositionnel etait la RETENTION de X,
  pas le binding) : ici aussi, le verrou terminal est la retention, pas l'acquisition ponctuelle.

## 5. Caveats (perimetre du verdict)

- **Le readout C1 est ce qui rend le NEUTRE informatif.** Sans lui, un NEUTRE serait ambigu (substrat vs
  selection vs retention). `craft_cell_share = 0.25` avec `frac_craft_QD = 0.011` isole la retention. Sans
  controle du biais d'echantillonnage uniforme, on aurait pu (a tort) lire « QD ne trouve pas le craft ».
- **Verdict sur la MOYENNE de n=3** (comme EDR 125). Ici c'est un NEUTRE robuste (0/3 seeds per-seed, aucune
  graine ne s'approche du seuil), donc pas de risque de masquage-de-variance (le risque I1 vaut pour un
  faux CONFIRME, absent ici).
- **Cohorte QD mesuree = fresh `sample(5)` post-evolution**, pas la population de la derniere ere
  (intentionnel : c'est l'operateur de selection du bras QD ; cf. revue finale M2/C1).
- Regime stoneage sweet-spot (`metab=0.25/payoff=3.0`, `eras=12`, `num_agents=30`, R=3). `cells_tier2 = 1`
  (une seule cellule craft, souvent 1 elite ayant crafte une fois) est coherent avec l'apparition RARE du
  craft (EDR 125 : 1.1%).
- L'evolution (bras QD/HoF) utilise `run_era_pool` (memory non neutralisee) ; run EMPIRIQUEMENT deterministe
  (2 passes byte-identiques) ; seule la MESURE exige le determinisme strict (assure par benchmark_mode + P0).

## 6. Suite & provenance

- **Suite** : le levier « selection QD » etant refute pour le craft, et le verrou identifie = **retention**,
  la suite n'est ni un nouvel operateur de selection ni un nouveau levier d'exploration (EDR 014/111 :
  le craft n'emerge pas ; ici il est atteint mais non retenu). C'est un probleme de **substrat** : rendre le
  craft RETENU = plasticite/apprentissage stable de la chaine outil (means->ends), precisement ce que la
  session // attaque en torch (EDR 122/126). Cote metrique (audit) : re-ponderer `life_score` sur les tiers
  VIVANTS et RETENUS (forage/apex-coop) reste le levier cheap ; le poids `spears` demeure inerte.
- **Provenance** : `Harness(name="qd_tier_rescue")` -> `results/qd_tier_rescue_1260.json` (gitignore) ;
  seed 1260, smoke 99260 distinct ; 2 passes byte-identiques ; AUCUN test relance apres le run (EDR 107).
  Tooling-only : `git diff src/` VIDE (zero collision session //).
- **Revue** : subagent-driven (Task 1 + Task 2 : SPEC conforme + qualite Approved) ; revue finale **opus**
  PRET A INTEGRER — anti-tautologie validee (QD mesure par son propre operateur), symetrie de mesure reelle,
  verdict falsifiable des deux cotes ; 2 findings integres AVANT le run (I1 readout per-seed, C1 borne haute
  craft_cell_share) sans toucher le verdict gele.
- **Numerotation** : EDR 127 (123 Credit_Horizon + 125 Craft_Wall = chantiers audit ; 124 S2 + 126
  Compositional_Fade = session //, tous mergees sur main via #102 sync/d1-catchup).
