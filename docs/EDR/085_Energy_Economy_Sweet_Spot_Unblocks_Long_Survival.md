# EDR 085 : Le sweet spot de l'économie d'énergie débloque la survie longue

## Contexte

EDR 084 : le plafond de survie (~70 ticks) est structurel — 79 % starvent, la nourriture seule sature.
Levier = l'économie d'énergie. On rend deux knobs configurables (gated, défaut = comportement
historique) : `base_metabolism` (drain par tick) et `forage_payoff` (nutrition d'une proie), puis on
sweep pour trouver le SWEET SPOT (dur pour les incompétents, soutenable pour les compétents).

## Résultat — survie des champions (cap d'ère = 400)

| `base_metabolism` | `forage_payoff`=1 | `forage_payoff`=3 |
|---|---|---|
| 1.0 (défaut) | 58 | 64 |
| 0.5 | 81 | 89 |
| **0.25** | 116 | **227** |

> Baisser le métabolisme débloque massivement la survie : **58 → 227 ticks** (×4) à métab=0.25/payoff=3.

## C'est un VRAI sweet spot (pas de l'énergie gratuite)

| à métab=0.25 / payoff=3 | survie |
|---|---|
| **champions** (compétents) | **163-227 ticks** |
| **agents FRAIS** (incompétents) | **44 ticks** |

> **~5× de séparation** : le monde EXIGE toujours la compétence (les frais meurent à 44) MAIS récompense
> enfin la compétence par une **vie longue** (163-227). C'est exactement la tension d'EDR 084 résolue :
> assez dur pour demander l'intelligence, assez soutenable pour que l'intelligence paye.

## Implémentation (gated)

- `config.base_metabolism` (défaut 1.0), `config.forage_payoff` (défaut 1.0). Câblés dans
  `world_1_stoneage` (`_resolve_biology` ligne ~608 ; payoff ligne ~684) via `getattr` → **défaut =
  comportement historique, 146 tests verts**.
- Réglage recommandé pour la survie longue : **`base_metabolism≈0.25`, `forage_payoff≈3`**. Laissé hors
  défaut (changement de monde majeur ; choix de l'utilisateur, comme `robust_hof_K`).

## Signification

> **Le dernier verrou d'EDR 082/083/084 cède.** Les agents peuvent enfin vivre 160-227 ticks (vs ~45-70)
> — assez longtemps pour qu'une chasse coordonnée par le langage ait le temps de payer. Le re-test du
> bénéfice du langage (082) sur ce substrat à survie longue devient enfin valide (EDR 086).

## Honnêteté

- Sweep décisif (métab domine, sweet spot net) ; les valeurs exactes (0.25/3) restent une *variable
  d'expérience* (Commandement 15) — le re-test 086 dira si elles suffisent à faire payer le langage.
- Survie 163-227 < cap 400 : on n'a pas la survie *indéfinie*, mais on a quitté la zone létale (~45) où
  rien de complexe ne pouvait émerger.

## Statut

- `base_metabolism` + `forage_payoff` (gated). **Sweet spot trouvé (0.25/3 → 5× compétents/frais)** :
  survie longue débloquée. Prochain : re-tester le langage (082) sur ce substrat.

## Variables d'expérience

base_metabolism × forage_payoff (sweet spot fin), densité de nourriture, durée de vie cible vs cap,
re-test langage (086) au sweet spot, activation par défaut.
