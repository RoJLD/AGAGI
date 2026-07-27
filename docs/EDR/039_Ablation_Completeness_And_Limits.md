---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-039
type: EDR
title: "Ablations complétées — et les LIMITES de l'ablation (Vague 1bis / honnêteté)"
status: legacy
gate: foundational
---

# EDR 039 : Ablations complétées — et les LIMITES de l'ablation (Vague 1bis / honnêteté)

## Contexte

Question de l'utilisateur : « a-t-on essayé *toutes* les ablations ? » Réponse honnête : **non**.
L'EDR 032 en couvrait 8 ; il manquait le **scaffold d'approche**, le **World Model**, et surtout
la **coopération** (récompense de groupe, le mécanisme central de l'EDR 028). On les ajoute (flag
`world.coop_reward`), et on apprend bien plus qu'un classement.

## Résultat — un classement… qui ne veut pas dire ce qu'on croit

Pop mûre (post-EDR 038), rareté 12, crit/scaffolds **pleins** (`current_era=1`), n=5 :

| Mécanisme ablé | Δ proies_moy | Lecture naïve |
|---|---|---|
| `nouveauté` | **−0.30** | compte (mais a **flippé** : +0.15 en EDR 032 !) |
| `cooperation` | **−0.01** | « neutre » ⚠️ |
| `crit` | −0.07 | léger |
| `curiosité` | −0.08 | léger (flippé vs EDR 032) |
| `scaffold_craft` / `seuils` / `router` | +0.35 / +0.32 / +0.22 | les retirer *aide* (distraient l'expert) |

## Trois pièges révélés (la vraie valeur de cet EDR)

1. **Substituabilité.** La coopération sort « neutre » car le **crit est plein** : crit et coop
   sont deux voies *redondantes* de survie face à l'apex (EDR 022/028). Ablater l'une pendant que
   l'autre compense ne montre rien. L'EDR 028 a prouvé que la coop compte **au sevrage** (crit=0).

2. **La métrique change la réponse.** Confirmation à crit=0 : retirer la coop **augmente** les
   kills bruts (0.60 → 2.00) — car la prime de groupe **rassasie tout le pack** (moins de re-chasse).
   Donc `big_kills` (kills bruts) **n'est pas** la bonne métrique pour la coop : sa valeur est la
   **persistance/survie évolutive** (EDR 028), pas le compte immédiat.

3. **Dérive de population.** `nouveauté` et `curiosité` ont **inversé leur signe** entre l'EDR 032
   et maintenant (population différente). Un verdict d'ablation n'est pas absolu — il **dérive**.

> **Leçon (honnêteté, esprit Vague 1) :** l'ablation à *un seul point de fonctionnement et une
> seule métrique* donne des verdicts **trompeurs** pour un système dont les mécanismes sont
> substituables, dépendants du contexte, et dont la « valeur » dépend de la question posée
> (kills vs survie vs persistance). Même notre outil de mesure a des limites — on vient de les
> cartographier.

## Conséquences

- **Réponse à l'utilisateur :** ablations désormais complètes (11 mécanismes), mais à lire avec ces
  trois caveats. Le « classement » n'est valable qu'*à ce point précis*.
- **Amélioration de l'outil (future) :** ablation **multi-points** (crit plein *et* sevré) +
  **multi-métriques** (proies, mammouth, persistance) + suivi de la dérive de population. Sans quoi
  on se ment avec des chiffres.
- La coopération **compte** (EDR 028) ; l'ablation naïve ne pouvait pas le voir — c'est l'ablation
  qui avait tort, pas l'EDR 028.

## Variables d'expérience

Point de fonctionnement (crit plein/sevré), métrique (proies/mammouth/persistance), population
(naïve/mûre/dérivée), n_eras.
