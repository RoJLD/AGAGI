# EDR 052 : Harnais d'évaluation puissant — et la recalibration de nos verdicts à 1 run

## Contexte

EDR 051 : un itérateur (#8) ne vaut que ce que vaut sa mesure ; 1 run sous-puissant classe le bruit.
On construit le **harnais d'évaluation puissant** (multi-seeds + agrégation + signification), puis on
rejoue le classement des demandes *à travers lui*.

## Construit (`src/seed_ai/eval_harness.py`)

- `powered_eval(conditions, run_seed_fn, seeds)` : réplicats indépendants (np.random.seed) → moyenne
  ± écart-type.
- `welch` / `verdict` : statistique de Welch + taille d'effet de Cohen (sans scipy) → « réel » vs
  « bruit ».
- `rank` / `is_robust_winner` : le meilleur ne gagne que s'il bat le 2ᵉ *significativement*.
- 5 tests (synthétiques) : le harnais flagge correctement signal vs bruit. (133 tests au total.)

## Épreuve du feu — le classement des demandes, puissant

3 seeds × 18 ères (vs 1 run × 12 ères en EDR 051) :

| Demande | MI (moy ± σ) | par seed |
|---|---|---|
| referential_pressure (045 « échec ») | 0.0158 ± 0.0198 | 0.0056 / **0.0386** / 0.0032 |
| lewis_2ref (047 « succès ») | 0.0127 ± 0.0094 | 0.0189 / **0.0019** / 0.0174 |
| speaker_reciprocity (050) | 0.0088 ± 0.0067 | 0.0161 / 0.0077 / 0.0027 |

**Verdict : t=0.24, d=0.20 → AUCUN gagnant robuste.** Les demandes ne se séparent pas à cette
puissance.

## La recalibration (le vrai résultat)

> **Nos verdicts à 1 run étaient statistiquement non fiables.**

- `lewis_2ref` (le « succès » EDR 047) : selon le seed, MI = 0.019 / **0.002** / 0.017. Un seed donne
  **0.0019 = RIEN**. Les 0.033 de l'EDR 047 étaient un **tirage favorable** ; la vraie moyenne à cette
  échelle est ~**0.013 ± 0.009**.
- `referential_pressure` (le « échec » EDR 045) a un seed à **0.039** — *meilleur que 047*.
- **Le succès de 047 ET l'échec de 045 étaient en partie du bruit.** Les trois demandes vivent dans le
  même régime **faible et bruité** (~0.01 MI, σ≈0.01), indistinguables ici.

## Ce que ça change (honnêtement)

1. **Le harnais marche** : il refuse de conclure du bruit, là où l'EDR 051 (sous-puissant) désignait
   un gagnant avec une fausse confiance.
2. **L'émergence du langage (047) est plus faible/bruitée que le run unique le suggérait** : réelle en
   *moyenne* (0.013 > baseline 0.0006), mais fortement seed-dépendante. À re-confirmer, pas à survendre.
3. **Le coût réel d'une évaluation fiable est élevé** : à cet effet (~0.01 MI) et cette variance
   (σ≈0.01), séparer deux demandes demande **≫ 3 seeds** (SE ∝ σ/√n) — ou une évolution plus longue,
   ou une métrique moins bruitée. **C'est la contrainte chiffrée de tout #8.**

## Conséquence — la priorité, re-confirmée

Avant d'armer le #8 (ou de conclure NAS/langage) :
1. **Évaluation puissante par défaut** (ce harnais), avec un budget seeds/ères *suffisant pour
   l'effet visé* — mesuré, pas deviné.
2. **Re-confirmer 047 sous puissance** (≥ 8 seeds) avant d'en faire une pierre angulaire.
3. *Ensuite* seulement, NAS-mémoire et #8 — sur une base mesurée fiable.

## Limites

- 3 seeds × 18 ères reste modeste : « pas de séparation » peut vouloir dire *vraiment proches* OU
  *encore sous-puissant*. Le harnais le dit honnêtement ; trancher demande plus de seeds.

## Variables d'expérience

Nombre de seeds, ères/réplicat, métrique (MI vs autre), seuils Welch/Cohen, budget total.
