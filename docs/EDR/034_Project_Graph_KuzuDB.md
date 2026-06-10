# EDR 034 : Graphe-projet KuzuDB — la carte des dimensions devient requêtable

## Contexte — Vague 1, finition du graphe

La carte des dimensions (4 familles, 10 axes) existait en **mermaid** (humain, roadmap). On la
double d'un **graphe machine** dans KuzuDB, en réutilisant l'ontologie branchée (EDR 032). Pendant
naturel : le mermaid se *lit*, le graphe KuzuDB se *requête*.

## Décision (V18.21)

- `ExperimentGraph` : `ensure_project_schema` (tables `Dimension`, `EDR`, rel `TOUCHES`) +
  `log_dimension` / `log_edr` / `link_edr_dimension`.
- `tools/build_project_graph.py` : peuple **10 dimensions** (les axes) + **25 EDR** (010→034) et
  leurs liens `EDR-[:TOUCHES]->Dimension`, puis lance des requêtes de preuve.

## Résultat — le graphe confirme la frontière, chiffres à l'appui

| Famille | # EDR | | Axe le + travaillé | # EDR |
|---|---|---|---|---|
| D. Mécanismes | **12** | | D9 Scaffolds annealés | **8** |
| B. Développemental | 8 | | B4 Craft / D8 Intrinsèques | 5 |
| A. Temps | 7 | | A2 Phylogénèse / B5 Difficulté | 4 |
| **C. Méta-évolution** | **1** | | A1 Ontogénèse | 3 |

> **Axe jamais touché par aucun EDR : `C7 Architecture agent (NAS)` [frozen].**
>
> Le graphe *prouve* ce que la carte affirmait : la **frontière est C7 (NAS)** — seul axe à 0 EDR.
> On a massivement travaillé les mécanismes (D, 12) et le développemental (B, 8), réparé le temps
> (A, 7) ; mais *faire grandir l'architecture du cerveau* est resté intouché. Ce n'est plus une
> intuition — c'est une requête.

## Conséquences

- La structure du projet (dimensions × décisions) est **machine-lisible et navigable** : « quels
  EDR touchent l'axe Craft ? », « quels axes sont orphelins ? », « quelles hypothèses sont
  réfutées ? » (couplé à l'ontologie EDR 032).
- **Frontière objectivée** : la Vague 4 (NAS Macro/Meso) et la phylogénèse longue restent le grand
  large — désormais visible dans la donnée, pas seulement dans le discours.
- Réutilisable : tout nouvel EDR s'ajoute au graphe via `build_project_graph` (idempotent).

## Limites & suites

- Le mapping EDR→axes est éditorial (dans le script) ; il pourrait être extrait des en-têtes d'EDR.
- Étendre : lier `EDR`→`Hypothesis` (ontologie 032) et `EDR`→`Conclusion` pour un graphe de
  raisonnement complet.

## Variables d'expérience

Granularité des axes, mapping EDR→axes, requêtes d'analyse (centralité, axes sous-explorés).
