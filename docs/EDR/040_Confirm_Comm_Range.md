---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-040
type: EDR
title: "Confirmation propre de la portée du signal (A/B simultané)"
status: legacy
gate: G3
---

# EDR 040 : Confirmation propre de la portée du signal (A/B simultané)

## Contexte

L'EDR 038 montrait que la portée du signal brisait l'impasse, mais par comparaison **inter-runs**
(vs EDR 037), pas en A/B contrôlé. On lève ce caveat.

## Méthode

Même HoF de **départ** (backup/restore), deux lignées **indépendantes** évoluant en parallèle, 16
ères chacune, **seule différence** : `hear_radius` (0 vs 3). Tout le reste identique (rareté 12,
LANGUAGE on, mêmes hyperparamètres).

## Résultat — confirmé

| Lignée | mammouth/ère | proies_moy |
|---|---|---|
| `radius 0` (pas de portée) | 1.25 | 1.04 |
| **`radius 3` (avec portée)** | **2.25** | **1.21** |
| **Δ** | **+1.00 (+80 %)** | **+0.17** |

> Toutes choses égales par ailleurs, la **portée du signal double presque** la chasse coopérative
> de l'apex (1.25 → 2.25). Le caveat inter-runs de l'EDR 038 est **levé** : l'effet est réel, pas un
> artefact de run. Le signal devient instrumental (recrutement du pack vers le Mammouth).

## Conséquences

- **B est confirmé** : un levier structurel minimal (portée) suffit à relancer la progression — le
  #8 (LLM) reste différé.
- Fondation solide pour pousser l'**Arc 5** (alignement référentiel, coût du signal).

## Limites

- L'effet est mesuré sur `mammouth`/`proies` ; l'**alignement référentiel** du token (le signal
  *signifie*-t-il « Mammouth ici » ?) reste à mesurer (Arc 5, étape suivante).
- 16 ères/lignée, n=1 paire (pas de répétition multi-seeds) — robuste mais perfectible.

## Variables d'expérience

`hear_radius`, nb d'ères/lignée, répétitions multi-seeds, métrique d'alignement.
