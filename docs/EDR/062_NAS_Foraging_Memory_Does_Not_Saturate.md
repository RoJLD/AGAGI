# EDR 062 : NAS — le foraging-mémoire ne sature pas (la conclusion robuste, après 6 EDR)

## Contexte

EDR 060 : la spéciation protège l'innovation (archis 173-174 persistent) mais ne suffit pas à 20 ères
sur 1 bit de mémoire. On donne au NAS ce qui manquait : **plus de bits** (3 types d'apex à retenir via
l'indice transitoire) + **plus de maturation** (36 ères) + **spéciation** (protection). A/B mémoire ON
vs OFF, 5 seeds.

## Résultat — toujours pas de prolifération

| | nodes (moy ± σ) | max | preys |
|---|---|---|---|
| OFF (sans mémoire) | 172.08 ± 0.11 | 174 | 0.36 |
| MEM (3 types) | 172.12 ± 0.11 | 174 | 0.37 |

t=0.58, d=0.37 → non significatif. Et les **174 apparaissent dans les DEUX arms** (même OFF) : c'est
la *spéciation* qui les préserve (niche), **pas la demande de mémoire**. La moyenne reste ~172 — les
grandes archis ne *prolifèrent* jamais.

## Conclusion robuste (046 → 062)

| EDR | Configuration | Croissance utile ? |
|---|---|---|
| 046 | add_node forcé, monde de base | non (pas de demande) |
| 049 | monde exigeant (perception) | non |
| 058 | 1 bit mémoire, sans protection | non (innovation tuée) |
| 060 | 1 bit + spéciation | préservée, pas utile |
| **062** | 3 bits + 36 ères + spéciation | **toujours pas** |

> **Le monde-foraging ne sature fondamentalement PAS 172 nœuds.** Retenir 3 types tient dans ~5 nœuds
> cachés ; la tâche est *réactive* (percevoir→agir), sa composante mémoire est peu profonde. La
> spéciation a **résolu la protection** (la croissance est *possible*), mais **aucune demande ne
> l'utilise**. Pour saturer le connectome, il faudrait une **tâche-mémoire DÉDIÉE** (séquences
> longues, nombreux items simultanés) — qui n'existe pas dans le foraging.

## Verdict (honnête)

- **L'obstacle du NAS était DOUBLE** : (1) protection de l'innovation — *résolue* par la spéciation
  (EDR 060) ; (2) demande qui sature — *non réparable dans ce substrat* (EDR 062).
- Ce n'est **pas un échec** : c'est un « il faut changer de tâche ». Le NAS dans AGIseed exige un
  **substrat de tâche différent** (mémoire/computation profonde), pas un réglage du foraging.
- Acquis conservés : `transient_apex` (la demande *mord*, perf ↓), la **spéciation** (protection
  réutilisable, vaut pour toute innovation structurelle).

## Suites

- **Tâche-mémoire dédiée** (hors foraging) : delayed-match-to-sample, rappel de séquence, n-back —
  là, la capacité serait le goulot, et spéciation + add_node devraient enfin faire grandir l'archi.
- C'est typiquement une **demande qu'un #8 pourrait proposer** (`kind="world_demand"` étendu à des
  mini-tâches cognitives), évaluée via le harnais.

## Variables d'expérience

Substrat de tâche (foraging vs mémoire dédiée), profondeur mémoire (délai, items simultanés),
spéciation, maturation.
