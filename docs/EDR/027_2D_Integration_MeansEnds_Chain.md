# EDR 027 : Intégration 2D (Monde × Craft) — la chaîne moyens→fins émerge bout à bout

## Contexte — Vague 0quater

L'EDR 026 a montré que les deux axes s'imbriquent : la **rareté extrême** (axe Monde) plafonne
la chasse simple et *devrait* forcer le passage au **gros gibier outillé** (axe Craft). Test : en
laissant le tooling disponible (craft L0 + crit) pendant qu'on rampe la rareté, la chaîne
moyens→fins émerge-t-elle ?

## Décision (V18.14)

- **Découplage du monde** (pour un monde *hybride*) : la nuit (`night_enabled`) et l'ε-greedy
  (`explore_eps > 0`) sont décorrélés de `training_mode`. → proies & matériaux **régénérés**
  (training_mode=None) MAIS nuit **off** (survivable) + ε **on** (explorer le grab).
- **Compteur d'apex** : `big_kills` ne compte que le **Mammouth** (`hp ≥ 50`) — le seul gibier
  qui exige une lance.
- `tools/curriculum_2d.py` : rampe la rareté (`target_prey_count` 20→12→6) avec craft L0 + crit
  disponibles ; mesure `proies_moy`, `crafts`, `mammouth`.

## Résultat — la chaîne complète émerge

| rareté | proies_moy | crafts | **mammouth** | statut |
|---|---|---|---|---|
| 20 | 1.64 → 1.79 | 1–3 | 1–2 | ✅ maîtrisé |
| 12 | jusqu'à 1.71 | 1–**5** | 0–1 | ✅ maîtrisé |
| 6 (mur EDR 026) | ~0.7, pics **1.09** | 1–3 | **0–3** | ❌ pas encore fiable |

> **Point décisif** : un Mammouth (hp100, riposte50) est **impossible à tuer sans lance**, même
> avec crit (mains nues ×3 = 30 dmg → l'agent meurt avant). Donc **chaque `mammouth > 0` prouve
> qu'un agent a crafté une lance puis l'a employée sur l'apex.** On observe `crafts` ET `mammouth`
> *ensemble*, sous pression de rareté — la chaîne *petit gibier rare → crafter une lance → tuer le
> gros gibier*. À rareté 6, là où la chasse simple plafonnait platement (EDR 026 : 0.65, **zéro**
> Mammouth), on a maintenant des **pics à 1.09 avec 3 Mammouths** et des ères longues (109 ticks).

## Conclusion — thèse du projet réalisée (puis à fiabiliser)

**La chaîne moyens→fins complète émerge bout à bout, pour la première fois** : le tooling
(crafté, pas donné) du gros gibier apparaît *sous la pression de la rareté*, exactement comme la
vision le prévoit. Toute la session converge ici — payoff combat (022), TD (023), population
saine (024), axes Craft (025) et Monde (026), et leur intégration (027).

**Mais ce n'est pas encore une stratégie dominante** : à rareté extrême (6), le chaînon émerge
**par intermittence** (Mammouths tués ~1 ère sur 2) sans verrouiller la maîtrise. La chaîne est
longue et stochastique (grab×2 → craft → trouver l'apex → l'engager → crit/survivre → manger)
dans des vies courtes.

## Suites — fiabiliser l'émergence

- **Persistance** (EDR réflexion) : faire émerger le **stun (jet)** et la **coopération** pour
  tuer l'apex *sans* dépendre du crit chanceux → stratégie robuste.
- **Cadencer le crit** (`crit_eras`) pour chevaucher cette émergence.
- Sélection plus longue / vies plus longues ; ramper aussi `craft_level` conjointement.

## Variables d'expérience

Paliers de rareté, `crit_base`/`crit_eras`, `explore_eps`, `craft_level`, max_eras, num_agents.
