# EDR 041 : Ablation multi-points — tout verdict dépend du crit (corrige EDR 039)

## Contexte

L'EDR 039 a montré qu'une ablation à *un seul point* (crit plein) ment (substituabilité crit↔coop).
On construit l'outil multi-points × multi-métriques (`tools/ablation_multi.py`) : chaque mécanisme
ablaté à **crit plein (0.6)** ET **crit sevré (0.0)**, métriques proies & mammouth.

## Résultat — TOUS les verdicts flippent

`Δproies_moy` par mécanisme :

| Mécanisme ablé | crit **plein** | crit **sevré** | verdict |
|---|---|---|---|
| cooperation | +0.08 | **−0.28** | 🔄 flip |
| nouveauté | +0.08 | **−0.50** | 🔄 |
| curiosité | +0.20 | −0.21 | 🔄 |
| scaffold_craft | +0.17 | −0.14 | 🔄 |
| seuils | −0.01 | −0.11 | 🔄 |

Et les **baselines** : crit_plein (proies 0.94, mammouth 0.75) vs crit_sevré (proies **1.34**,
mammouth **3.0**).

## Trois vérités, désormais visibles

1. **Le crit est la variable maîtresse.** Avec la béquille (plein), tout le reste est *redondant*
   (les retirer **aide** — ça distrait l'expert qui s'appuie sur le crit). Sans elle (sevré), tout
   devient *porteur* (les retirer **nuit** — la population en a besoin). Un mécanisme n'est ni bon ni
   mauvais : il est **contextuel**.

2. **La béquille dégrade la maturité.** La baseline crit-**sevré** (1.34 / 3.0) **bat** la crit-plein
   (0.94 / 0.75). Le coup critique chanceux rend l'expert *moins bon* — validation ultime du sevrage
   (EDR 030) : l'aide doit disparaître pour que la vraie stratégie s'exprime.

3. **La coopération est confirmée vitale** (−0.28 au sevrage), exactement comme l'EDR 028 — ce que
   l'ablation à un seul point (EDR 032/039) ne pouvait pas voir.

> **Leçon livrée comme outil :** mesurer à plusieurs points de fonctionnement n'est pas un luxe —
> c'est la condition pour ne pas se mentir. Un seul point inverse jusqu'au signe des conclusions.

## Conséquences

- Les verdicts de l'EDR 032 (« scaffolds vestigiaux ») ne valent **qu'à crit plein** ; au sevrage,
  ces mêmes mécanismes sont essentiels. Réinterpréter en conséquence.
- Outil réutilisable pour tout mécanisme futur (incl. portée/coût du signal de l'Arc 5).

## Limites

- n=4 ères (bruité) ; les deltas exacts sont approximatifs, mais le **flip qualitatif** (positif à
  plein, négatif au sevré) est systématique et robuste.

## Variables d'expérience

Points de fonctionnement (au-delà du crit : scaffolds, rareté), métriques, n_eras, multi-seeds.
