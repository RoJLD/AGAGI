# EDR 113 — Recompenser le pas final leve-t-il le plafond de navigation Lewis ? (affordance d'atterrissage)

> **Spec de conception** — 2026-06-29. Dernier levier-MONDE plausible sur la navigation.
> Outil : `tools/lewis_survival_sweep.py` (extension DRY, comme 105/106/107/110).
> Discipline : Commandement 15 (1 variable = `scaffold_land`).

## 1. Contexte & question

L'arc Lewis a elimine par triangulation, comme verrou du plafond de navigation (`p_reach`, fraction
d'agents atteignant une cellule-proie) : l'energie (090-101), la cinematique (106), la selection
(104/108), et la **capacite reseau** (110 : 16x de neurones cachés = `CAPACITE INERTE`). EDR 111 a
montre qu'ajouter de la **DEMANDE** (tool-gate mammouth) effondre le substrat sans pivot (Issue 2).
Convergence : seule piste survivante = le **repertoire-MONDE** (affordances).

**Decouverte (lecture du code, 2026-06-29) qui resserre le diagnostic :**
- L'agent **observe deja** une direction vers la proie la plus proche (`get_batch_observations`,
  `dn/ds/de/dw` = distance normalisee N/S/E/O, l.388-395). Le signal de navigation EXISTE.
- L'agent **peut** se deplacer directionnellement (actions 0-5 = N/S/E/O + haut/bas).
- L'agent **est recompense** pour s'approcher (`approach_reward`, scaffold d'approche annelé, l.651-656).
- La capture exige d'atteindre **d=0** (meme cellule que la proie ; `attacked_prey` l.691) ; une fois
  sur place, capture PARFAITE (EDR 105 : `p_cap=1.00`, 10 dmg mains nues one-shot le petit gibier).
- **MAIS** : EDR 105 montre que l'agent s'approche a `min_dist` ~1.24 case et **ne fait pas le pas
  final**. Pour le petit gibier (Lapin/Cerf, `damage=0`), atterrir ne rapporte QUE l'approche + le
  revenu de capture ; **aucun scaffold dédié au pas final** (le `scaffold_bighit=2.0` ne s'applique
  qu'au gros gibier qui riposte, `cfg.damage>0`, l.707-710).

**Hypothese pendante d'EDR 105 (citee dans la memoire) :** « `approach_reward` recompense la
REDUCTION de distance, pas se tenir SUR la proie ». L'agent s'installe dans un **attracteur de
hovering** a d~1 (s'approcher est paye ; le pas final ne l'est pas distinctement).

**Question d'EDR 113.** Si l'on **recompense explicitement l'atterrissage sur la proie** (le pas
final), le plafond `p_reach` monte-t-il au-dessus de ~0.36 ? C'est le test DIRECT de l'hypothese
d'EDR 105 et le **dernier levier-MONDE** plausible : si meme payer le pas final ne le declenche pas,
le verrou-monde est elimine et tout pointe vers le substrat (architecture).

## 2. Pourquoi ce n'est ni EDR 111 ni un signal manquant

- **Pas EDR 111** : 111 ajoutait de la DEMANDE (gate plus dur) -> substrat s'effondre. EDR 113 ajoute
  une AIDE (recompenser une action que l'agent peut deja faire). Caveat #3 d'EDR 111 le dit : « le
  knob hp ne modifie pas les affordances ». EDR 113 modifie l'affordance (le payoff du pas final).
- **Pas un signal manquant** : la direction-proie existe deja (refute l'hypothese « le monde ne
  fournit pas de signal »). EDR 113 ne cible pas la DIRECTION (qui marche : l'agent s'approche) mais
  le PAS FINAL (qui echoue).

## 3. Architecture

Etendre `tools/lewis_survival_sweep.py`. Ajouter un scaffold **`scaffold_land`** (defaut 0.0 =
non-regressif) verse quand l'agent **atterrit sur une cellule-proie** (bloc `if attacked_prey:`,
l.692), annelé comme les autres scaffolds (`anneal(era, scaffold_eras=30)`). Balayer son intensite
`land_levels=(0.0, 2.0, 5.0, 10.0)` et mesurer le plateau `p_reach` via la boucle evolve_nav d'EDR 107
(substrat prod baseline, `N_APEX=0`, `metab=0`, `forage_payoff=3`, cliquet best-ever, 20 gen). Le bras
`scaffold_land=0` reproduit EXACTEMENT EDR 107 (~0.36) = controle de validite du harnais. **Seule
variable entre bras = `scaffold_land`.**

Lecture double (gratuite, comme EDR 110) : `gen0` (p_reach gen 1, effet brut de l'affordance avant
evolution) + `plateau` (mediane last-5, affordance exploitee par l'evolution).

## 4. Composants & interfaces

### 4.1 `src/environments/config.py`
- Ajouter le champ `scaffold_land: float = 0.0` a `WorldConfig` (comme `trace_forage` l.59, EDR 105).
  Defaut 0.0 -> non-regressif (aucun monde existant ne change).

### 4.2 `src/worlds/world_1_stoneage.py`
- En `__init__` (pres des scaffolds l.118-122) : `self.scaffold_land = getattr(config, "scaffold_land",
  0.0)`. (Lecture defensive : robuste aux configs sans le champ.)
- Dans le bloc `if attacked_prey:` (juste apres l.692, AVANT le calcul de degats pour ne dependre
  d'aucun resultat de combat) : `agent["energy"] += self.scaffold_land * anneal(getattr(self,
  "current_era", 1), self.scaffold_eras)`. **Tous gibiers** (pas gaté sur `cfg.damage>0`, contrairement
  a `scaffold_bighit`) : le pas final vers N'IMPORTE quelle proie est l'objet du test. A `scaffold_land
  =0.0` -> +0.0 -> byte-identique au comportement actuel (non-regression).

### 4.3 `tools/lewis_survival_sweep.py`
- `_cfg(...)` gagne un parametre `scaffold_land=0.0` qui pose `cfg.scaffold_land = float(scaffold_land)`
  (comme `trace_forage`/`prey_speed_scale`). Defaut 0.0 -> les appels existants inchanges.
- `_landing_arm(cfg, generations, num_agents, max_ticks, base_seed)` : calque `main_evolve_nav`
  d'EDR 107 (best_ever seedé par `_load_champions`, `_reproduce` avec `mc=MutationConfig(
  weight_init_std=2.0)`, `_evolve_nav_gen`, cliquet best-ever top-5). Renvoie un dict
  `{scaffold_land, traj, gen0, first, plateau, stats}`. Le `scaffold_land` est porte par le `cfg`.
- `_verdict_landing(arms)` : trie par `scaffold_land` croissant ; `delta = plateau(max) - plateau(0)` ;
  `slope = polyfit(land_levels, plateaus, 1)[0]` (echelle lineaire, pas log : les niveaux incluent 0).
  - **AFFORDANCE LEVE** si `delta >= 0.10` ET `slope > 0`.
  - **AFFORDANCE INERTE** si `abs(delta) < 0.10` ET `abs(slope) < 0.01` (pente quasi nulle sur l'echelle
    0-10).
  - **AFFORDANCE AMBIGUE** sinon (signal partiel/non-monotone).
- `_report_landing(h, arms, ...)` : table ASCII (1 ligne/bras : `scaffold_land`, `gen0`, `first`,
  `plateau`, `delta_vs_base`) + pente + delta + verdict + provenance. Tout ASCII (cp1252).
- `main_landing_nav(land_levels=(0.0, 2.0, 5.0, 10.0), generations=20, num_agents=24, max_ticks=80,
  seed=113, _return=False)` : pour chaque niveau, `cfg = _cfg(3, base_metabolism=0.0, trace_forage=
  True, scaffold_land=level)`, `seed_at(base + int(level*10), 0)` (graine deterministe par bras),
  `_landing_arm(...)`. Puis `_report_landing`.

## 5. Verdict pre-enregistre (fige AVANT les donnees, falsifiable des deux cotes)

| Branche | Condition | Lecture scientifique |
|---|---|---|
| **AFFORDANCE LEVE** | plateau monte avec `scaffold_land` (`delta >= +0.10`, pente > 0) | Le mur etait une **lacune d'affordance-MONDE** (reward-shaping) : recompenser le pas final leve la navigation. **L'hypothese repertoire-MONDE est vindiquee** pour la navigation -> premier levier POSITIF de tout l'arc Lewis. Ouvre la voie a façonner le monde plutot que le substrat. |
| **AFFORDANCE INERTE** | plateau plat (`abs(delta) < 0.10`, pente ~0) | Meme fortement recompense, l'agent ne fait pas le pas final -> le verrou est la **capacite du substrat a executer le pas final**, pas le payoff du monde. **Elimine le dernier levier-MONDE** sur la navigation -> convergence surdeterminee finale avec l'architecture (107/110/111). |
| **AFFORDANCE AMBIGUE** | non-monotone / signal partiel (p.ex. gen0 monte mais plateau non) | Sous-determine. Documenter le sens du signal partiel ; suivi (R>1, niveaux plus fins). |

**Seuil delta = +0.10** : coherent avec EDR 110 (meme metrique `p_reach`, meme gate). Un effet
d'affordance reel devrait deplacer le plafond d'au moins ~0.10 ; en deca = bruit de la meme famille
que la saturation 107.

**Lecture secondaire (gen0).** Si `gen0` monte avec `scaffold_land` mais le plateau non -> l'affordance
aide la navigation BRUTE mais l'evolution ne consolide pas (rare ; a noter). Si ni gen0 ni plateau ne
montent -> affordance franchement inerte.

## 6. Tests (TDD, banc `tests/sandbox/test_edr113_landing.py`)

1. **Config additive** : `WorldConfig().scaffold_land == 0.0` ; `_cfg(3, scaffold_land=5.0).scaffold_land
   == 5.0` ; `_cfg(3).scaffold_land == 0.0` (defaut).
2. **Cablage monde non-regressif a 0** : construire `Biosphere3D(_cfg(3, scaffold_land=0.0))`, verifier
   `env.scaffold_land == 0.0`. Construire avec `scaffold_land=5.0` -> `env.scaffold_land == 5.0`.
3. **Recompense d'atterrissage versee (cible le pas final)** : monde minimal, placer un agent SUR une
   cellule-proie (petit gibier `damage=0`), `current_era=1`, comparer le gain d'energie du pas de
   resolution entre `scaffold_land=0.0` et `scaffold_land=10.0` -> le second est superieur d'environ
   `10.0 * anneal(1, 30)` (le scaffold d'atterrissage). (Test cible : isole le terme `scaffold_land`
   en figeant le reste ; tolerance sur l'annealing.)
4. **Non-regression byte-identique a 0** : deux env `scaffold_land=0.0`, memes graines, N pas ->
   trajectoires d'energie identiques (le champ defaut ne change rien).
5. **`_verdict_landing` branches** : bras synthetiques montant -> `AFFORDANCE LEVE` ; plats ->
   `AFFORDANCE INERTE` ; non-monotone/descendant -> `AFFORDANCE AMBIGUE`.
6. **Determinisme** : `main_landing_nav(land_levels=(0.0,), generations=2, seed=88113, _return=True)`
   appele deux fois -> trajectoires identiques. **Seed distinct de 113** (le run reel) pour ne pas
   ecraser sa provenance JSON.
7. **Smoke** : `main_landing_nav(land_levels=(0.0, 5.0), generations=2, num_agents=6, max_ticks=40,
   seed=99113, _return=True)` tourne, verdict valide, JSON ecrit. **Seed distinct de 113** (provenance).

## 7. Cout & repli puissance

4 bras x 20 gen x 24 agents x 80 ticks a metab=0 (~ comme EDR 110). Confirmatoire **R=1, seed 113**.
Repli : 15 gen, ou 3 bras `(0, 5, 10)`. Run reel APRES la revue de code ; AUCUN test relancé apres le
run reel (ecraserait le JSON de provenance — lecon EDR 107).

## 8. Provenance, determinisme, non-regression

- `results/` gitignore ; provenance citee par seed (113) + commit dans le doc EDR.
- Determinisme verifie (test 6) ; run reel reproduit une fois.
- **Non-regression** : `scaffold_land=0.0` par defaut -> tous les mondes/EDR existants byte-identiques
  (test 4). Le cablage monde est additif et gaté par la valeur (0 -> +0.0).
- ASCII-only dans tout `print` execute (Windows cp1252) : `->` ASCII OK, pas de fleche unicode/accents.
- **Caveat in-world reproduction (lecon EDR 110)** : l'ere comporte de la reproduction intra-monde
  (energie/MATE/HGT) qui peut faire grossir les reseaux ; comme EDR 113 ne fige PAS la capacite (ce
  n'est pas la variable) et n'a pas d'assert de capacite, ceci est ACCEPTABLE et identique a EDR 107
  (le bras baseline reproduit 107). La seule variable reste `scaffold_land`, identique a travers les
  generations d'un bras.

## 9. Commandement 15 — 1 variable

La **seule** variable manipulee entre bras est `scaffold_land` (le payoff du pas final). Tout le reste
est identique : monde (Lewis vide d'apex, metab=0, forage_payoff=3, approach scaffold inchangé),
substrat (prod baseline via `_load_champions`), selection (`calculate_life_score`, cliquet best-ever),
graines (deterministes par bras), config de mutation, ticks, population.
