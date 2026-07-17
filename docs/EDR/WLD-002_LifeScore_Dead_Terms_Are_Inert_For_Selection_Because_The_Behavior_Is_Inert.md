---
id: EDR-WLD-002
type: EDR
title: Les termes morts de life_score sont INERTES pour la sélection — parce que le COMPORTEMENT est inerte, pas parce que les poids sont faux
status: accepted
gate: G0
verdict: LIFESCORE_DEAD_TERMS_INERT_FOR_SELECTION
---

# EDR-WLD-002 : « Réparer la métrique life_score » est un NON-LEVIER

> Territoire WLD. Probe d'impact de contamination `tools/life_score_contamination_probe.py`
> (tooling-only, `git diff src/` VIDE). Mesure le blast-radius AVANT toute mutation du cœur de
> sélection partagé. K=12 seeds, cohorte évoluée (réutilise `_evolve_champions`+`_make_cfg` sweet
> = mêmes conditions qu'EDR 125). PR #156.

## Question

`calculate_life_score` ([`src/seed_ai/persistence.py:36-47`](../../src/seed_ai/persistence.py)) est la
**fitness de sélection de PROD** (appelée par `save_to_hall_of_fame` + `robust_hof`) :

```
age·0.1 + preys_eaten·50 + altars_solved·20 + spears_crafted·300 + mammoth_kills·400 + ref·REF_FITNESS_WEIGHT
```

Deux EDR ont **asserté** que des termes sont morts/inertes, sans jamais le mesurer au niveau
**sélection** : EDR 096 (`altars_solved` ≡ 0 en stoneage, dead-code) et EDR 125 (`spears_crafted`
« largement inerte », ~1.1 % craftent). Le lever proposé (« réparer la métrique » = retirer/repondérer
ces termes) exigerait de **muter la fitness partagée** (haut blast-radius : change la sélection de
toutes les sessions //, invalide les comparaisons HoF, contesté par la thèse crédit). **Question :
retirer un terme change-t-il réellement QUELS agents la sélection favorise (classement top-K) ?**

## Méthode

Sur une cohorte évoluée (cliquet top-5, régime sweet 0.25/3.0), classer les agents (`env.agents +
dead_agents`) par `life_score` **full** vs variantes à un terme annulé (`drop_altars`/`drop_spears`/
`drop_both` — copies locales de dict, la fitness de prod n'est **jamais** mutée). Mesurer si le
classement bouge : `kendall_tau` (tau-b, corrige les ex-aequo) sur tout le classement + `topk_jaccard`
sur le **top-25 %** (le tier qui repro/entre au HoF). Verdict `INERTE`/`CONTAMINEE`/`AMBIGU` par
variante, garde-fou anti-évaporation (aucun CONTAMINEE sous K=12). Garde repro au niveau MESURE +
fail-soft (`repro_ok`). Corroborant HoF : absent (pas de HoF en prod) → `None`.

## Résultat (K=12, `repro_ok=True`)

**Taux de craft réaliste** : crafteurs présents dans **3/12 seeds seulement** (seed0=2, seed2=2,
seed10=1 ; total 5/360 agents ≈ **1.4 %** — reproduit EDR 125). `altars_solved` = 0 sur **les 12 seeds**.

| variante | médiane jac | médiane τ | seeds à τ<1 (rang) | seeds à jac<1 (**sélection**) | verdict |
|---|---|---|---|---|---|
| `drop_altars` | 1.000 | 1.000 | **0 / 12** | **0 / 12** | INERTE (exact) |
| `drop_spears` | 1.000 | 1.000 | 3 / 12 | **1 / 12** | INERTE (médian) |
| `drop_both`  | 1.000 | 1.000 | 3 / 12 | 1 / 12 | INERTE |

Détail `drop_spears` sur les 3 seeds à crafteur : seed0 (2 craft) τ=0.986 jac=1.000 ; seed2 (2 craft)
τ=0.986 jac=1.000 ; **seed10 (1 craft) τ=0.911 jac=0.778** (1 agent déplacé du top-8). Les 9 seeds sans
crafteur : τ=1.000 jac=1.000 (trivial).

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT (altars)** : retirer `altars_solved·20` est un **no-op EXACT** de sélection (τ=1.0, jac=1.0 sur
  les 12 seeds). C'est la **1ʳᵉ preuve au niveau sélection** (pas juste une observation de compteur) du
  dead-code d'EDR 096 : le terme est mort parce que `altars_solved` n'est jamais incrémenté en stoneage.
- **FAIT (spears)** : `spears_crafted·300` **réordonne TOUJOURS** le rang d'un crafteur (τ<1 sur les 3/3
  seeds à crafteur — +300 ≈ 6 proies), mais ne franchit la frontière **top-K de sélection** que dans
  **1/12 seeds** (jac<1). Au médian (0 crafteur), l'effet est 0 → INERTE.
- **INTERPRÉTATION** : les termes suspects sont inertes **parce que le COMPORTEMENT est inerte**, PAS
  parce que les poids sont faux. La métrique reflète fidèlement une population qui ne crafte quasi jamais
  (1.4 %) et ne résout aucun autel (0 %). **« Réparer la métrique » (096/125) est donc un NON-LEVIER** :
  retirer `altars` est cosmétique (no-op garanti) ; retirer `spears` a un impact de sélection négligeable
  (1/12 seeds) mais reste l'unique — quoique impotente — pression vers le craft (intention EDR 016/017),
  donc c'est une décision de design, pas de l'hygiène. Dans les deux cas, **muter la fitness partagée
  n'aurait rien débloqué** — le verrou est en amont (crédit/comportement means→ends), cohérent avec la
  synthèse canonique `FIL_DIRECTEUR_AGI.md` (« le substrat REPRÉSENTE mais ne CONVERTIT pas — faute de
  crédit »).
- **VALIDE CAUSALEMENT la méthode** : « mesurer le blast-radius d'abord » a évité un travail inutile sur
  le cœur de sélection (~toutes les sessions //) et a converti une assertion en test falsifiable.

## Portée / Bornage

1. **Verdict médian vs sporadique** : `INERTE` est un énoncé au **médian**. Le lecture par le signe
   (garde-fou anti-évaporation, [[power-evaporation-guardrail]]) précise : `spears` contamine la
   sélection dans une **minorité** de seeds (1/12 ≈ 8 %), pas zéro. « Inerte pour la sélection
   systématique », pas « aucun effet possible ».
2. Cohorte **fraîchement évoluée en stoneage** (pas le HoF de prod, absent) : mesure la distribution
   qu'une sélection en cours de course voit. Un HoF réel (déjà filtré) pourrait avoir une composition
   différente — le corroborant HoF est prévu mais sans données ici.
3. `benchmark_mode` fige la repro en phase de mesure (114b) ; l'évolution amont utilise la repro ON
   canonique. Régime sweet = borne conservatrice (events les plus fréquents → si inerte ici, inerte au
   régime dur aussi).
4. `frac_topk=0.25` (tier de repro/HoF). Un seuil plus serré (top-5 %) capterait davantage de
   déplacements de la frontière — non testé.

## Suite

- **Décision-relevant** : NE PAS muter `calculate_life_score`. Retirer `altars_solved·20` serait un
  no-op propre si on veut de l'hygiène cosmétique, mais ça ne débloque rien. Le levier reste le
  crédit/substrat (le comportement ne se produit pas), pas la pondération de la fitness.
- Si l'axe craft est repris : c'est un problème de **rétention/plasticité** (EDR-CRAFT-001 : one-shot
  non répété, policy-locked) et de crédit means→ends (fil torch), pas de métrique.
- Le probe est réutilisable pour tout terme candidat (langage `ref_distinction`, futurs KPI mondes 2/3)
  et pour re-mesurer si le taux de craft monte un jour (le verdict spears basculerait CONTAMINEE si les
  crafteurs devenaient fréquents).

Lignée : converge [[world-floor-survivability-gate]] (mur du craft, métrique morte) + la thèse CRÉDIT de
[[lineage-divergence-d1-vs-main]] (représentation ≠ conversion). Étend [[s2-world-demand-thread]] (le
gate de cohérence S2 était une AUTRE affaire, déjà réparé #132 ; ici c'est l'intégrité de la métrique au
niveau sélection). Recoupe [[research-backlog-and-gaps]] (ferme le candidat WLD « réparer le gate/la
métrique »).
