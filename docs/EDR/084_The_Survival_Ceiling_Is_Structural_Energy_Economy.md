---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-084
type: EDR
title: "Le plafond de survie est STRUCTUREL (économie d'énergie), pas évolutif"
status: legacy
gate: foundational
---

# EDR 084 : Le plafond de survie est STRUCTUREL (économie d'énergie), pas évolutif

## Contexte

EDR 082/083 : le langage ne paye pas car les agents MEURENT avant que la coordination paye
(survivants=0). Dernier verrou identifié = la **survie soutenue**. On l'attaque de front : évolution
robuste (K=4) sur 40 générations + diagnostic des causes de mort + test du levier nourriture.

## Résultat 1 — la survie PLAFONNE, plate sur 40 générations

| génération | 5 | 10 | 20 | 30 | 40 |
|---|---|---|---|---|---|
| survie (ticks) | 46.0 | 41.8 | 43.2 | 43.3 | 47.5 |

> **Pente +0.04 tick/gén — totalement plat.** La survie plafonne à ~45 ticks (cap d'ère = 400). **Le
> verrou est STRUCTUREL, pas évolutif** : plus d'évolution n'y change rien (contrairement à la compétence
> de chasse, qui elle grimpait, 081).

## Résultat 2 — diagnostic : 79 % meurent de FAIM

| cause de mort (38 morts, 1 ère) | part | état à la mort |
|---|---|---|
| **FAIM** (énergie → 0) | **79 %** | énergie moy ≈ 8 |
| combat (hp → 0) | 21 % | hp moy ≈ 121 (intacts) |

> Les agents **starvent** : ils ne foragent pas assez pour compenser le métabolisme. Ce n'est pas le
> danger (riposte) qui les tue, c'est le **bilan énergétique**.

## Résultat 3 — le levier nourriture aide mais SATURE

| target_prey_count | 15 | 40 | 80 | 150 |
|---|---|---|---|---|
| survie (ticks) | 54 | 68 | 71 | 73 |

> Plus de nourriture : 54 → 73 ticks (+35 %) puis **plafonne**. **La nourriture seule ne débloque pas la
> survie longue** — au-delà d'une densité, le foraging (compétence) ou le métabolisme redeviennent le
> goulot.

## Conclusion — le dernier verrou est une ÉCONOMIE D'ÉNERGIE à re-designer

> **Le plafond de survie (~45-73 ticks) est une propriété STRUCTURELLE de l'économie d'énergie**
> (métabolisme × efficacité de foraging × densité de nourriture) — *ni* évolutive (40 gens plats) *ni*
> résoluble par la seule abondance (sature à 73). C'est le diagnostic précis du verrou d'EDR 082/083 :
> les agents ne vivent jamais assez longtemps (~70 ticks) pour qu'une chasse coordonnée par le langage
> paye.

> **Tension de design** (lien audit `010` cause B) : le monde doit être **assez dur** pour exiger
> l'intelligence (pas d'énergie subventionnée) MAIS **assez soutenable** pour que des agents compétents
> survivent longtemps (sinon les comportements complexes — langage, coordination — n'ont pas le temps de
> payer). Le réglage actuel est du côté « trop dur pour la survie soutenue ». **Il faut viser le SWEET
> SPOT.**

## Suite (le levier, concret)

Re-designer l'**économie d'énergie** pour un point d'équilibre soutenable :
1. **Métabolisme** : baisser le drain par tick (biome drains) ou le rendre proportionnel à l'activité.
2. **Payoff de foraging** : rendre une proie efficace nettement nutritive (la compétence DOIT suffire à
   se sustenter).
3. **Densité** : garder modérée (la sur-abondance retire la pression d'intelligence — cause B).
   Objectif : un agent COMPÉTENT survit quasi-indéfiniment ; un incompétent meurt. *Alors* la survie
   longue débloque le re-test du bénéfice du langage (082).

## Honnêteté

- Diagnostic décisif (40 gens plats, 79 % faim, saturation nourriture) ; le *réglage* du sweet spot
  reste à faire (variable d'expérience, Commandement 15 : 1 levier, valide ou revert).
- **Cohérence avec 081** : la survie oscille ~45-55 ticks (écart-type ~8-13, cf. 080) ; le « +12.4 » de
  081 était *dans cette bande de bruit*. Sur 40 gens + n_eval=12, le signal net est un **plateau** ~47.
  Ce qui grimpait clairement en 081, c'était la *chasse* (compétence), pas la *durée de vie* brute — deux
  métriques distinctes, et c'est la durée de vie qui plafonne structurellement.
- Lien direct : c'est la cause-racine B de l'audit `010` (« énergie subventionnée ») vue par l'autre
  bout — ici le problème n'est pas la subvention mais la **dureté qui empêche la survie soutenue**.

## Statut

- `long_survival.py` (trajectoire + diagnostic + levier nourriture). **Survie longue = verrou
  structurel d'économie d'énergie**, à débloquer par re-design du métabolisme/payoff (pas par
  l'évolution). Dernier verrou du langage fonctionnel, désormais précisément localisé.

## Variables d'expérience

Métabolisme (drain/tick), payoff de foraging (nutrition par proie), densité de nourriture, sweet spot
dureté↔soutenabilité, durée de vie cible, re-test langage (082) sur substrat à survie longue.
