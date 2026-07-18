# EDR 113 — Recompenser le pas final ne leve PAS la navigation : le dernier levier-MONDE est elimine

> **Date** : 2026-06-29. **Verdict** : `AFFORDANCE INERTE` (pre-enregistre, atteint).
> **Outil** : `tools/lewis_survival_sweep.py` (`main_landing_nav`). **Seed** : 113. **Commit** : 0dca4f4.
> **Spec** : `docs/superpowers/specs/2026-06-29-EDR113-Landing-Affordance-design.md`.
> **Plan** : `docs/superpowers/plans/2026-06-29-EDR113-landing-affordance.md`.

## 1. Question

L'arc Lewis a elimine comme verrou du plafond de navigation (`p_reach`) : l'energie (090-101), la
cinematique (106), la selection (104/108), la **capacite reseau** (110, `CAPACITE INERTE`), et la
**demande** (111 tool-gate, le substrat s'effondre sans pivot). Convergence : seule piste survivante =
le **repertoire-MONDE** (affordances).

**Diagnostic resserre (lecture du code).** L'agent observe DEJA une direction vers la proie la plus
proche (`get_batch_observations`, `dn/ds/de/dw`), peut se deplacer directionnellement (actions 0-5), et
est recompense pour s'APPROCHER (`approach_reward`, scaffold annelé). EDR 105 montre qu'il s'approche a
`min_dist` ~1.24 case et **ne fait pas le pas final** (la capture exige d=0, meme cellule ; une fois sur
place, capture PARFAITE p_cap=1.00). Pour le petit gibier (Lapin/Cerf, `damage=0`), atterrir ne rapporte
que l'approche + le revenu de capture ; **aucun scaffold dedie au pas final** (`scaffold_bighit` ne joue
qu'au gros gibier qui riposte). Hypothese pendante d'EDR 105 : « `approach_reward` recompense la
reduction de distance, pas se tenir SUR la proie » -> attracteur de hovering a d~1.

**Question d'EDR 113.** Si l'on **recompense explicitement l'atterrissage** sur la proie (le pas final),
`p_reach` monte-t-il au-dessus de ~0.36 ? C'est le **dernier levier-MONDE** plausible sur la navigation.

## 2. Methode

Nouveau scaffold **`scaffold_land`** (config + monde, defaut 0.0 = non-regressif) verse dans le bloc
`if attacked_prey:` (atterrissage sur une cellule-proie, **tous gibiers**), annelé `* anneal(era,
30)`. Balayage `scaffold_land ∈ {0.0, 2.0, 5.0, 10.0}` (0 = controle reproduisant EDR 107 ; 10 ~ 3x le
revenu de capture). A chaque niveau : evoluer 20 gen la boucle evolve_nav d'EDR 107 (substrat prod
baseline via `_load_champions`, `N_APEX=0`, `metab=0`, `forage_payoff=3`, cliquet best-ever). Lecture
double : `gen0` (p_reach gen 1, effet brut) + `plateau` (mediane last-5, exploite par l'evolution).

**1 variable (Commandement 15)** : seul `scaffold_land` varie. Note : chaque generation tourne a
`current_era=1` (scaffold chaud, design EDR 107) -> `anneal(1,30)=0.967` ne decroit jamais : la
recompense est a ~97% de force tout du long (≈ `scaffold_land × 0.97` energie/atterrissage).

## 3. Resultats

| scaffold_land | gen0  | first | **plateau** | delta vs base |
|--------------:|------:|------:|------------:|--------------:|
| 0.0           | 0.520 | 0.391 | **0.305**   | +0.000        |
| 2.0           | 0.380 | 0.326 | **0.326**   | +0.021        |
| 5.0           | 0.242 | 0.245 | **0.288**   | -0.017        |
| 10.0          | 0.303 | 0.303 | **0.297**   | -0.008        |

- **Pente du plateau vs scaffold_land = -0.0019** (quasi nulle, legerement negative).
- **delta(max - base) = 0.297 - 0.305 = -0.008** (≪ gate +0.10, signe negatif).

Trajectoires `p_reach` par generation (20 gen) — toutes dans la **meme bande ~0.04-0.59**, sans
tendance correlee a `scaffold_land` :
```
land= 0.0 : 0.52 0.40 0.39 0.26 0.23 0.43 0.36 0.41 0.29 0.26 0.53 0.29 0.30 0.34 0.59 0.40 0.33 0.31 0.12 0.22
land= 2.0 : 0.38 0.33 0.51 0.12 0.27 0.29 0.38 0.13 0.43 0.09 0.36 0.18 0.30 0.37 0.35 0.33 0.42 0.11 0.23 0.35
land= 5.0 : 0.24 0.25 0.23 0.49 0.24 0.28 0.34 0.28 0.31 0.37 0.46 0.40 0.32 0.31 0.28 0.31 0.30 0.25 0.18 0.29
land=10.0 : 0.30 0.30 0.17 0.38 0.21 0.44 0.35 0.29 0.44 0.31 0.30 0.31 0.36 0.35 0.04 0.28 0.30 0.26 0.33 0.32
```

## 4. Verdict : `AFFORDANCE INERTE`

Le plateau **ne monte pas** avec `scaffold_land` : plat a ~0.29-0.33 (toujours ≪ 0.5), pente quasi
nulle, delta negatif. Condition pre-enregistree remplie : `abs(delta)=0.008 < 0.10` ET
`abs(slope)=0.0019 < 0.01`.

- **Baseline land=0 (plateau 0.305)** reproduit la bande ~0.36 d'EDR 107 -> harnais valide.
- **Lecture secondaire (gen0)** : la capacite brute ne monte pas non plus — elle **DECROIT** meme
  (0.520 / 0.380 / 0.242 / 0.303). Plus on recompense le pas final, moins il est franchi a la gen 1.

**Conclusion.** Recompenser grassement (jusqu'a ~9.7 energie/atterrissage, 3x le revenu de capture) le
pas exact que l'agent echoue a faire **ne le declenche pas**. Ce n'est PAS une incitation manquante :
l'agent ne sait pas executer le pas final, point. L'hypothese pendante d'EDR 105 (lacune de
reward-shaping) est **REFUTEE** -> le mur est la **capacite du substrat a executer le pas final**.

## 5. Caveat majeur — le confond energie->reproduction (revue opus), et pourquoi il NE mine PAS ce verdict

La recompense agit via l'**energie**, qui (a) retarde la mort (`age` ↑ -> `life_score` ↑ via
`age*0.1`) et (b) pousse vers le seuil de reproduction (`energy >= energy_max`). Donc `p_reach`, mesure
sur le POOL (agents + rejetons), **pourrait monter mecaniquement** par composition du pool (survivants/
rejetons selectionnes pour l'energie-d'atterrissage) **sans** amelioration de navigation.

**Asymetrie qui sauve l'experience :** ce confond ne pourrait que **GONFLER** un `AFFORDANCE LEVE`. Or
le resultat est `INERTE` -> le confond joue CONTRE le verdict obtenu, donc le renforce : **meme en
donnant l'avantage energetique (qui aurait du biaiser p_reach vers le haut), le plateau reste plat.**
De plus le signal **resistant au confond** (`gen0`, gen 1, avant que 20 gen de reproduction ne composent
le biais) ne monte pas non plus (il decroit). Les deux lectures concordent : pas de benefice.

(Pre-enregistrement honnete : un verdict LEVE aurait ete provisoire, a lire d'abord sur `gen0` et a
confirmer par un signal d'atterrissage NON-energetique. Le verdict INERTE, lui, est propre.)

## 6. Convergence (surdetermination finale)

`AFFORDANCE INERTE` **clot le cote MONDE** du mur de navigation. Triangulation complete :

| Levier | EDR | Verdict |
|---|---|---|
| Energie / depense | 090-101 | sature, NON SUFFISANT |
| Cinematique (fuite des proies) | 106 | REFUTE (POLITIQUE) |
| Selection (diversite/tournoi) | 104/108 | n'eleve pas |
| Capacite reseau (neurones caches) | 110 | INERTE (16x = rien) |
| Demande (tool-gate) | 111 | substrat s'effondre (Issue 2) |
| **Affordance du pas final (reward)** | **113** | **INERTE** |

**Ni le monde (knobs, affordance de reward), ni la selection, ni la taille du reseau** ne levent la
navigation. Le verrou est l'**ARCHITECTURE/capacite du substrat a executer une politique de navigation
fine** (le pas final), converge avec [[lewis-energy-economy-wall]] (107 SUBSTRAT BLOQUE),
[[nas-bottleneck-is-substrate-not-search]], [[from-genome-flattens-architecture]] (connectome 97% I/O,
hidden=5/172). Le repertoire-MONDE n'est pas le levier de la NAVIGATION (il pourrait l'etre pour
d'autres axes, p.ex. l'apex/coop, hors de ce test).

## 7. Caveats & limites

- **R=1** (un seed, confirmatoire). Determinisme **verifie** : deux runs (seed 113) byte-identiques.
  Trajectoires bruitees a R=1 (bande 0.04-0.59) ; le verdict tient sur l'absence de tendance a travers
  4 niveaux, pas sur un point.
- **Confond energie->reproduction** (section 5) : neutralise par l'asymetrie (INERTE propre) + lecture
  gen0 concordante.
- **gen0 = generation 1** (apres un `_reproduce`), pas litteralement pre-evolution ; ~ capacite brute.
- **In-world reproduction non figee** (energie/MATE/HGT), comme EDR 107 -> identique au baseline, pas un
  confond differentiel entre bras.
- **Distinction EDR 111** : 111 ajoutait de la DEMANDE (gate dur) -> effondrement ; 113 ajoute une AIDE
  (payer une action deja possible) -> inerte. Deux faces, meme verrou substrat.

## 8. Suite

- **Dernier levier-MONDE sur la navigation ELIMINE.** Cote monde, le mur de navigation est clos
  (cf. table section 6). Toute suite navigation doit attaquer le **SUBSTRAT** (architecture : vraie
  couche cachee profonde, plasticite locale, primitive de locomotion/atteinte) — retour au programme NAS
  mais sur l'EXECUTION du pas final, pas la capacite brute (110 l'a clos).
- **Piste substrat ciblee** : pourquoi un connectome 97% I/O ne peut-il pas apprendre « si dn>0 et
  dn<seuil, emettre move-N » ? Tester une primitive d'atteinte (action « step-to-nearest-prey » cablee)
  comme borne superieure : si meme une primitive parfaite ne ferme pas p_reach->1, le verrou est
  ailleurs ; sinon, c'est la POLITIQUE apprise qui manque la primitive -> piste apprentissage/plasticite.
- **Repertoire-MONDE reste plausible pour l'APEX/coop** (axe distinct de la navigation ; EDR 111 l'a
  teste par la demande, pas par une nouvelle affordance) — orthogonal a ce verdict.
