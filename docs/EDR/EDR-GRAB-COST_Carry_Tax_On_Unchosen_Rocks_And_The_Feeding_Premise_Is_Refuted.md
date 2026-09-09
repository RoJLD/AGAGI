---
id: EDR-GRAB-COST
type: EDR
title: "Le GRAB coûte la survie (+39 %, 28+/2−, p = 8.7e-07) et le CANAL est la TAXE DE PORTAGE sur des rochers que l'agent ne choisit pas : 34 % du métabolisme, 102 % du différentiel par tick. ⚠️ La prémisse « grabber NOURRIT » est RÉFUTÉE — le monde n'offre AUCUN fruit atteignable (0 sur 20 776 agent-ticks), ce qui replace ce record DANS la borne de portée déjà déclarée par EDR-WARM-008"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
extends: [EDR-WARM-008]
---

## Question

P4.1 : **le grab nuit-il, et par quel canal ?** Le verdict de survie a été mesuré le 2026-09-08 ; le
MÉCANISME était déclaré ouvert, avec deux mesures nommées et non faites — le taux de grab in situ et
`trace_energy_sinks`. Les deux sont faites ici, et elles ont retourné la question de départ.

## ⚠️ RECTIFICATION de la version du 2026-09-08 — la prémisse était fausse trois fois

La première version s'ouvrait sur : *« le régime de famine dure porte `forage_payoff = 3.0` — ramasser
un fruit RAPPORTE »*, et son titre était « …**Even When Grabbing Feeds** ». Mesuré :

1. **La VALEUR est fausse.** `run_condition` construit le monde avec `config=None`, donc le DÉFAUT :
   `forage_payoff = 1.0`. Le 3.0 n'a jamais eu cours dans ce run.
2. **Le RÉFÉRENT est faux, et c'est structurel.** `forage_payoff` ne multiplie que `prey_reward` sur une
   **mise à mort de proie** (`world_1_stoneage.py:800`). Il ne touche **jamais** `do_grab`. Même à 3.0 il
   n'aurait rien dit sur l'action ablatée.
3. **Le fait lui-même est faux.** Sur **20 776 agent-ticks**, le grab nourrit **exactement 0 fois** — 0 par
   le revenu du moteur (`+20` sur `inventory[0]` de type `Fruit`), 0 par le cache de famine
   (`_auto_consume_cache`). Le champion ne porte **aucun aliment** : 4 549 `rock`, 1 166 `Spark`,
   663 `stick`, 513 `Spear`, 358 `Wood`, 314 `stick_long`, 131 `stick_short`, 5 `Fire` — **zéro `Fruit`**.

Enregistré comme **classe E8 occurrence 4** (`docs/REF/REGISTRE_ERREURS.md`) : *ce n'est pas une mesure
qui a raté, c'est une phrase qui n'a jamais été mesurée.* **Les chiffres de survie, eux, tiennent
intégralement** — c'est le cadre qui tombe, pas la mesure.

## Le canal : la TAXE DE PORTAGE, et elle explique tout le différentiel

Décomposition par `trace_energy_sinks`, **normalisée par agent-tick** (comparer des totaux entre bras de
durées différentes ferait passer « le bras qui vit deux fois plus longtemps » pour « celui qui dépense
deux fois plus »). Signe positif = énergie DÉPENSÉE.

| poste / agent-tick | intact | `grab_off` | Δ |
|---|---|---|---|
| **`carry` (portage)** | **+0.6418** | **+0.0000** | **−0.6418** |
| `metab` | +1.8792 | +1.8792 | 0.0000 |
| `terrain` | +0.2557 | +0.2586 | +0.0029 |
| `autres` (revenus nets) | −1.1792 | −0.9994 | +0.1798 |
| `action` (grab, lancer, signal) | −0.1222 | −0.2430 | −0.1208 |
| `mouvement` | +0.4987 | +0.4528 | −0.0459 |
| `brain` | +0.0107 | +0.0104 | −0.0003 |
| **TOTAL** | **+1.9848** | **+1.3586** | **−0.6262** |

**La taxe de portage seule vaut 0.6418 quand le différentiel total vaut 0.6262 — soit 102 %.** Tout le
reste se compense. Elle pèse **34.2 % du métabolisme de base** (0.6418 / 1.8792).

⚠️ **Ce que cette table N'EST PAS.** Les deux bras divergent dynamiquement dès le premier tick : ce
décompte dit OÙ l'énergie est passée dans chaque bras, ce n'est **pas** une partition causale du
différentiel. On peut nommer le canal DOMINANT ; on ne peut pas attribuer les 39 % à un poste au
pourcentage près.

⚠️ **`metab` identique aux 4 décimales n'est pas un contrôle sur le MONDE** : `base_metabolism ×
phenotype_energy_drain` est une constante de génome, donc son quotient par le nombre de bio-ticks est
constant par construction. Son égalité valide le **dénominateur** de la normalisation, rien de plus.
C'est dit ici pour qu'on ne le lise pas comme davantage.

## Pourquoi la taxe est si lourde : le grab ne CHOISIT pas ce qu'il ramasse

Deux lignes du moteur suffisent, et elles sont vérifiées sur le code par un test gelé :

* `_spawn_rocks` pose des rochers de poids `uniform(1.0, 10.0)` — **moyenne 5.5** — **à l'initialisation**,
  donc en TÊTE de `self.items`. Les fruits sont ajoutés pendant le run (`world_1_stoneage.py:1179`), donc
  en QUEUE.
* Le grab prend `nearby_items[0]` : **le premier de la liste**, jamais le meilleur.

Le grab est donc un **ramasse-rochers par ordre de liste**, pas un choix. Vérification arithmétique du
bouclage : 59 % des objets portés sont des rochers (4 549 / 7 699) × 5.5 ≈ 3.25, et le poids moyen par
objet **mesuré** est **3.46**. Le poste `carry` reproduit `0.5 × poids recensé` à **2.3e-16** près.

## Pourquoi le revenu est nul : le fruit est inatteignable DEUX fois

Ce n'est pas un fait sur la politique du champion, c'est un fait sur le monde — et il se chiffre :

* `_generate_trees` crée `max(1, size // 3) = 3` arbres, chacun fruitier avec probabilité
  `config.fruit_tree_ratio`. **Sur les 30 ères mesurées, 25 n'ont AUCUN arbre fruitier** (5/30 en ont un).
* Dans ces 5 ères, le cooldown initial vaut **139–140 ticks**, et il ne décrémente **que pendant
  l'abondance** (`food_regen_scale > 0`), soit 60 ticks par cycle de 100. La première récolte tombe donc
  vers le tick **219**. L'agent le plus âgé de tout le dispositif meurt au tick **198**.

D'où `fruits_monde = 0.0` **exact** et `fruits_sous_le_pied = 0` sur les deux bras : jamais un fruit n'a
existé au sol pendant qu'un agent vivait.

## Conséquence : ce record entre DANS une borne que [[EDR-WARM-008]] avait déjà déclarée

WARM-008 §4 écrivait : *« le grab nuit » n'est établi que dans un monde où grabber n'a AUCUN avantage
possible — et c'est le seul monde que le banc implémente. La validité externe reste OUVERTE.* Sa cause
identifiée était la même : *le monde n'engendre AUCUN item de type `Fruit`*, inventaire mesuré
`stick ×2, stick_short ×3, stick_long ×1, rock ×18`.

**Ma signature de types est la même, dans un banc pourtant différent** (FamineWorld, champion HoF,
`cognitive_demand=False`, là où WARM-008 était en `cognitive_demand=True`). La borne est donc
**répliquée sur un troisième banc**, et il faut le dire : la question « grabber paie-t-il quand grabber
nourrit ? » reste **OUVERTE, et aucun banc de ce dépôt ne peut y répondre**.

Ce que ce record AJOUTE à WARM-008 est le point de **dose élevée** qui lui manquait :

| population | `carry` / métabolisme | gain de survie à retirer le grab |
|---|---|---|
| bootstrap-oracle (WARM-008) | 2.4 – 9.5 % | **NUL** (18 → 19, 6+/6−, ratio 1.000) |
| champion HoF, FamineWorld (ici) | **34.2 %** | **+39 %** (28+/2−, p = 8.7e-07) |

WARM-008 avait explicitement prédit la condition — *« retirer un puits à ~5 % ne sauve pas un agent qui
meurt de métabolisme ; le ×2.06 de WARM-005 venait d'un génome à inventaire lourd »*. C'est le génome
lourd qui est mesuré ici. **Le signe traverse les populations, l'amplitude non** : la thèse centrale de
WARM-008, vue depuis l'autre extrémité de la dose.

## Contrôles

* **Ancrage (E19 occ. 6)** — la boucle recensée rend une survie **exactement égale** à celle de
  `run_condition`, l'instrument audité qui a produit le verdict. Sans quoi le bilan décrirait un autre
  monde. Établit au passage que `trace_energy_sinks=True` est un **no-op sur la dynamique**.
* **Plancher de bruit EXACTEMENT NUL** — `NullGrabOffMamba` et l'observateur `GrabCensusMamba` réécrivent
  la valeur lue : bit-identiques au bras intact. Écrire une constante dans une sortie ne consomme aucun
  tirage, contrairement à `derange_rows` de la sonde sœur (bande [0.92 ; 1.06]).
* **Bouclage comptable** — le poste `carry` du moteur reproduit `0.5 × poids recensé` à **2.3e-16**. ⚠️ La
  première version recensait l'inventaire en tête de tick, donc AVANT le grab : bilan parfaitement
  cohérent avec lui-même, et **facteur 3.7** d'écart avec le moteur. Un recensement qui ne boucle pas
  produit une attribution de canal.
* **Hypothèse du scaffold RÉFUTÉE.** Le banc pose `current_era = 10 000`, donc `anneal = 0` et la prime de
  ramassage `scaffold_grab` vaut **exactement zéro** — alors qu'elle valait ~0.967 pendant les ères où le
  champion a évolué. Le grab pouvait donc n'être qu'un comportement payé à l'évolution et non payé à la
  mesure. **Testé** à `current_era = 1` (prime effective **0.9667**) : `grab_off` gagne encore, **46 contre
  31**, et l'écart s'**élargit**. Une prime ponctuelle ne compense pas une taxe permanente.
* **Taux de grab in situ = 0.5547** (mesuré, l'explication que la v1 déclarait « plausible et NON
  MESURÉE »). Le champion tente un grab sur 55 % des agent-ticks : le forcer ne peut le porter qu'à
  100 % — moins d'un facteur 2 — tandis que le retirer va à 0. L'asymétrie observée entre `grab_off`
  (p = 8.7e-07) et `grab_force` (p = 0.185) est cohérente avec ce point de fonctionnement.

## ⚠️ Ce qui n'est PAS établi, et qui compte

* **L'intervention n'est PAS minimale.** `GrabOffMamba` vide l'inventaire, et l'inventaire conditionne
  aussi le **lancer** (`world_1_stoneage.py:1404` — `if do_throw and len(agent["inventory"]) > 0`). Le bras
  ablaté ne peut donc **jamais lancer**. Les +39 % sont le net de (taxe retirée) − (capacité de lancer
  retirée) ; le poste `autres`, plus favorable de **0.18/tick** au bras intact, en est la trace probable.
  Le signe n'est pas en cause, la surgicalité l'est.
* **Le grab a donc un bénéfice réel, simplement 3.5× trop petit** : ~0.18/tick de revenu net contre
  0.64/tick de taxe.
* **Validité externe** : famine dure seulement, `night_enabled=False`, `benchmark_mode=True`, et — c'est
  le point principal — un monde sans fruit atteignable.
* **Unité de réplication** : l'ÈRE. Les 10 ères d'un champion sont sériellement dépendantes ; la lecture
  conservatrice (n = 3 seeds) garde le signe (3/3) mais tombe sous `n_floor = 12`.

## Ce que ça ouvre

Le bras qui manque est maintenant **spécifié**, et c'est le « bras à revenu d'inventaire réel » de P4.2 :
un monde où (a) `fruit_tree_ratio` garantit au moins un arbre fruitier, (b) le premier cooldown est
inférieur à l'espérance de vie, et (c) le grab peut **choisir** sa cible. Tant que les trois manquent,
« grabber nuit » restera vrai et sans portée.

## Matériel

`tools/grab_mechanism_probe.py` (`GrabCensusMamba`, `GrabCensusWorld`, `run_census_arm`,
`anchor_against_run_condition`) · 14 cas dans `tests/sandbox/test_grab_mechanism.py`, dont 12 sans
aucune simulation · mesures brutes `results/p41_grab_mechanism.json` (banc) et
`results/p41_grab_mechanism_era1.json` (contrôle scaffold) · verdict de survie et ses 4 bras :
`tools/s2_demand_ablation.py`, `results/p41_grab_famine.json`. Sous bail `kuzu`.
