# EDR 114 — La primitive d'atteinte FERME p_reach : le mur est la POLITIQUE (et le pooling-reproduction confond la metrique)

> **Date** : 2026-06-30. **Verdict brut** : `PRIMITIVE NE FERME PAS` (0.47). **Verdict corrige (apres
> controles)** : **PRIMITIVE FERME** — le monde permet d'atteindre (oracle -> 0.984), le mur est la
> politique/substrat. **+ decouverte methodologique** : `_measure_forage` deflate p_reach 2-4x par
> pooling-reproduction.
> **Outil** : `tools/lewis_survival_sweep.py` (`main_reach_oracle`). **Seed** : 114. **Commit** : 8d8f7de.
> **Spec** : `docs/superpowers/specs/2026-06-29-EDR114-Reach-Oracle-Upper-Bound-design.md`.

## 1. Question

Tous les leviers-MONDE du plafond de navigation Lewis (`p_reach`) ont ete elimines (EDR 105-113) ->
verrou suppose = SUBSTRAT (execution de la politique). Mais `p_reach` etait toujours mesure sous la
politique APPRISE. Question borne-sup, jamais testee : si l'on remplace la politique par une
**primitive d'atteinte parfaite** (oracle obstacle-aware « va sur la proie la plus proche »), `p_reach`
monte-t-il a ~1 ? Si OUI -> le monde permet d'atteindre, mur = POLITIQUE/substrat. Si NON -> mur =
MECANIQUE du monde.

## 2. Methode

Flag monde `reach_oracle` : override l'action de chaque agent par un pas glouton vers la proie la plus
proche (Manhattan) avec evitement d'obstacle a 1 pas (utilise prey-dir + lidar, tous deux observes ;
zero apprentissage). Matrice 2x2 `{oracle off/on} x {prey_speed 1.0 mobiles, 0.0 figees}`, graines
appariees, via `_measure_forage` (replicas, SANS evolution). Verdict porte par la cellule
(oracle=True, figees). Seuils : FERME>=0.90 / NE FERME PAS<0.50 / PARTIELLE.

## 3. Resultat brut (run pre-enregistre, seed 114)

| oracle | speed | p_reach | p_cap | min_dist | n |
|-------:|------:|--------:|------:|---------:|--------:|
| False (apprise) | mobiles | 0.15 | 0.80 | 1.88 | 3481 |
| False (apprise) | figees  | 0.10 | 0.79 | 1.84 | 3030 |
| True (oracle)   | mobiles | 0.38 | 0.64 | 0.77 | 5393 |
| True (oracle)   | **figees** | **0.47** | 0.64 | 0.64 | 5857 |

cinematique (oracle) : figees 0.47 vs mobiles 0.38 (delta +0.09). **Verdict brut pre-enregistre :
`PRIMITIVE NE FERME PAS`** (0.47 < 0.50). Determinisme verifie (2 runs byte-identiques).

**MAIS** : l'oracle DOUBLE largement le baseline (0.10->0.47, min_dist 1.84->0.64) sans fermer, ET le
test comportemental (grille libre, 1 agent) montrait que l'oracle atteint sans probleme. Contradiction
-> investigation des CONTROLES avant d'interpreter (revue opus avait flague ces modes d'echec).

## 4. Controles diagnostiques — le verdict brut est un ARTEFACT

Decomposition de la cellule (oracle, figees), diagnostics deterministes (memes 8 graines ; monkeypatch
documente, reproductible) :

| condition (oracle, figees) | p_reach | min_dist | n | ce que ca isole |
|---|---:|---:|---:|---|
| **raw** (repro + obstacles) | **0.47** | 0.64 | 5857 | verdict brut |
| grille LIBRE (`_generate_geometry/_trees` no-op) | 0.513 | 0.54 | 6052 | obstacles ≈ negligeables ICI |
| **NO-REPRO** + obstacles (`_add_offspring` no-op) | **0.875** | 0.245 | 192 | **retirer la repro = +0.40** |
| NO-REPRO + grille libre | **0.984** | 0.026 | 192 | **plafond vrai ~98%** |

**Le confond dominant est le POOLING-REPRODUCTION.** Sous l'oracle, les agents atteignent -> mangent ->
survivent (metab=0) -> se reproduisent massivement (n: 192 initiaux -> ~5857). Des milliers de
**nouveau-nes tardifs** (spawn tick 140+) n'ont pas le temps d'atteindre une proie avant la fin
(150 ticks) -> ils diluent `p_reach` sur le pool entier. Retirer la reproduction (pool = cohorte
initiale de 192) fait bondir oracle-figees de **0.47 -> 0.875** ; retirer AUSSI les obstacles ->
**0.984** (un chasseur 1-pas parfait atteint ~98% des cibles immobiles).

Controle apprise (no-repro, figees) : **p_reach = 0.432** (vs 0.10 brut) -> meme deflation.

## 5. Verdict corrige : `PRIMITIVE FERME` — le mur est la POLITIQUE

Une fois l'artefact de pooling retire :
- **Le monde PERMET d'atteindre** : l'oracle atteint **0.984** (grille libre) / **0.875** (avec
  obstacles), cohorte equitable. Il n'y a PAS de mur de mecanique-monde. La primitive FERME p_reach.
- **A condition egale (no-repro, obstacles)** : politique apprise **0.432** vs oracle **0.875** -> le
  substrat n'attrape que **~la moitie** de ce qu'une primitive triviale (argmax direction + sidestep
  1-pas) realise sur le MEME terrain. **Le mur EST la politique apprise / le substrat**, pas le monde.
- Le residu de l'oracle (0.875 vs 0.984 avec obstacles) = limite du sidestep 1-pas dans les clusters
  d'arbres 3x3 (besoin de vrai pathfinding) ; mineur (~0.11) vs le mur de politique.

**Conclusion** : EDR 114 **confirme par exclusion** le verdict de l'arc (le mur de navigation est le
SUBSTRAT/la politique, pas le monde) — cette fois via la borne-sup positive : *un agent qui execute la
primitive atteint ; l'agent appris ne l'execute pas*. Converge le mandat [[sota-gap-substrate]]
(migrer le moteur vers un substrat differentiable : ~5 noeuds caches n'apprennent pas cette politique).

## 6. Decouverte methodologique — `_measure_forage` deflate p_reach

`p_reach` mesure sur le POOL (`agents + dead_agents`) est **confondu par la reproduction intra-monde** :
quand le forage reussit, la population explose et les nouveau-nes tardifs (jamais le temps d'atteindre)
deflate la fraction de **2-4x**. Implications :
- Les chiffres p_reach REPLICA d'EDR 105 (0.18) / 106 (0.21) **SOUS-ESTIMENT** la vraie capacite : la
  politique apprise atteint en realite **~0.43** (figees, cohorte equitable), pas ~0.10-0.21. Les
  conclusions QUALITATIVES (mur = substrat) tiennent ; les MAGNITUDES etaient deflatees.
- Meme famille que le confond reproduction d'EDR 110 (in-world repro pollue le pool).
- **Correctif propre (suite)** : un knob `disable_repro` dans le harnais OU un `p_reach` restreint a la
  cohorte (age >= diametre de grille), pour de-confondre les futures mesures de forage.

## 7. Caveats & limites

- **Verdict brut vs corrige** : le run pre-enregistre committe donne `NE FERME PAS` (0.47) — verdict
  mecaniquement correct sur la metrique brute, mais REVISE par les controles en `FERME`. Les controles
  sont des diagnostics post-hoc (monkeypatch `_add_offspring`/`_generate_*` no-op), deterministes et
  reproductibles, mais PAS dans le harnais committe -> le knob `disable_repro` est la suite propre pour
  un verdict committe non-confondu.
- **Oracle 1-pas, pas BFS** : la borne-sup obstacles (0.875) sous-estime « reaching POSSIBLE » ; la vraie
  borne (grille libre) = 0.984. Un oracle BFS fermerait aussi avec obstacles.
- **R=1** ; determinisme verifie (run brut x2 byte-identique ; diagnostics deterministes par graine).
- **Cellule oracle-MOBILES** : ne pas sur-interpreter — le mapping de mouvement des proies
  (`world_1_stoneage:642-645`) est pre-existant et possiblement inverse (note revue opus, hors perimetre).
- **p_cap oracle 0.64 < apprise 0.79** : sous forte densite (pool ~5857), les proies atteintes sont
  souvent capturees par un AUTRE agent co-localise le meme tick -> credit de capture dilue ; artefact de
  population, sans rapport avec le verdict p_reach.

## 8. Suite

- **Le mur de navigation est le SUBSTRAT/la politique — confirme par borne-sup positive.** Cote monde,
  clos definitivement (le monde est navigable : oracle -> 0.984). Direction = **migration moteur**
  (substrat differentiable + plasticite) per [[sota-gap-substrate]] : un connectome ~5 caches n'apprend
  pas une politique que 12 lignes de code executent.
- **Dette harnais** : de-confondre `p_reach` (knob `disable_repro` ou cohorte par age) -> re-baser
  EDR 105/106 si une magnitude propre est requise.
- Etend [[lewis-energy-economy-wall]] + [[nas-bottleneck-is-substrate-not-search]] + [[sota-gap-substrate]].
