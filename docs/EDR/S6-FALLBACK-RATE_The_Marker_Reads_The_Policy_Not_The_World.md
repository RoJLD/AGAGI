---
id: EDR-S6-FALLBACK-RATE
type: EDR
title: "Le marqueur within-subject mesure une propriété de la POLITIQUE, pas du MONDE — dans une cellule où le corps SUFFIT, l'ablation mord sur 8 seeds sur 12 dès que l'init n'est plus nulle"
status: active
verdict: MARKER_READS_THE_POLICY_NOT_THE_WORLD
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER, REF-EXPERIMENT-PREFLIGHT]
corrects: [EDR-S2-006]
---

## Question — ce que le protocole d'origine ne POUVAIT pas mesurer

[[EDR-S2-006]] (foundational) tient sa moitié « nécessité » de cellules NULLES : retirer une condition
rend l'ablation inerte. Le 2026-09-07, en forme close et sans aucun run, ces cellules se sont révélées
**définitionnelles** : `survive` fait `E += gain - metab` puis `if E <= 0` — la survie ne dépend que du
SIGNE du gain net, c'est une **métrique-SEUIL** — et `fit_policy` part de `W = zeros` avec acceptation
STRICTE `sc > best`. Dans toute cellule à corps suffisant (`body_gain > metab`), la politique INITIALE
survit déjà au plafond : **aucune candidate n'est jamais acceptée**, `|W| = 0.0000` est l'**init**, et
l'ablation est un no-op LITTÉRAL (classe E1).

> **Le neutre était-il un fait sur le monde, ou l'ombre d'une init nulle ?**

Règle scellée AVANT le run : `docs/preregistrations/S6-FALLBACK-RATE-bis.json`.

## Méthode

`tools/s2_fallback_rate_probe.py` — pur numpy, aucun import de monde, aucun bail (garde `assert_no_world`
**statique** : elle lit les imports du fichier, pas `sys.modules`). Le MESUREUR est IMPORTÉ
(`survive`, `_obs`, `_ablate`) ; seul l'ENTRAÎNEUR est copié (`fit_policy_sigma`), car l'init EST la
variable indépendante. 5 cellules × 12 seeds × 24 vies × 4 barreaux ; CRN par vie ; plancher **mesuré**
(politique corps seule, mêmes `RandomState`), jamais importé. 60 points, 360 s, résumable.

**DV = `permuted`, et ce choix est un résultat** : mesuré sur les 60 points, le barreau `zero` produit
des **faux négatifs** — l'obs mise à zéro rend la politique CONSTANTE, et si son action par défaut tombe
sur le corps, le sujet survit au plafond et le barreau lit 1.00 pendant que `permuted` effondre 2,9× à
7,1× (5 seeds concernés). Les trois barreaux sont publiés : le choix du DV ne se cache pas.

## Résultats

| cellule | σ | k(`permuted`) | k(`noise`) | k(`zero`) | ratio méd. | `n_accepted` |
|---|---|---|---|---|---|---|
| c1-N (corps SUFFISANT) | 0 | **0/12** | 0/12 | 0/12 | 1.00 | 0 |
| c1-N | 0.1 | **6/12** | 6/12 | 5/12 | 2.43 | 4 |
| c1-N | 0.3 | **8/12** | 8/12 | 6/12 | 4.15 | 2 |
| c1-N | 1.0 | **8/12** | 9/12 | 6/12 | 5.87 | 6 |
| c1-P (corps INSUFFISANT) | 0.3 | **12/12** | 12/12 | 12/12 | 10.17 | 5 |

**Les quatre contrôles scellés passent.** `assert_intervention_perturbs_input` vérifie que les trois barreaux perturbent bien l'ENTRÉE et que `true` la laisse intacte (spécificité) — la question 1 du pré-vol, vérifiée au lieu d'être affirmée. Le gate d'admissibilité pré-enregistré PASSE : contrôle positif c1-P k=12/12 (exigé ≥ 10) ; ancre
σ=0 k=0 avec `|W|=0.0000` EXACT et `n_accepted=0` sur 12/12 — vérifiée **bit à bit** contre `fit_policy`
d'origine dans les DEUX cellules, y compris c1-P où le hill-climb ACCEPTE (sans quoi la comparaison
serait vide). Le plancher mesuré de c1-P rend **30.0 exact**, retrouvant par mesure la constante
`PLANCHER_AVEUGLE = 30.0` codée en dur dans le probe.

## Verdict

**`MARKER_READS_THE_POLICY_NOT_THE_WORLD`** — branche scellée « k(σ>0) ≥ 2 sur au moins un σ » :

1. **Le NEUTRE des cellules nulles était celui de σ=0 SEULEMENT.** Dans le MÊME monde, avec le MÊME
   corps suffisant, l'ablation mord sur **8 seeds sur 12** dès que l'init n'est plus nulle. Ce que
   S2-004/005/007/008 lisaient comme « le monde n'exige pas X » était « CETTE politique-là, née de
   `W=zeros`, n'a jamais eu de raison de lire X ».
2. **Ce n'est pas un défaut du marqueur : c'est son OBJET.** L'ablation within-subject mesure si **la
   politique** a un repli survivable sans X — une propriété du SUJET, pas du MONDE. Deux politiques
   également survivantes dans le même monde rendent des verdicts opposés selon leur init. La recette de
   S2-006 se reformule donc : *X est marqué demandé ssi la politique n'a pas de repli survivable sans X*.
3. **Le protocole d'origine rend une ÉGALITÉ sur ces mêmes données** : 6 seeds SENSIBLE contre 6
   INDÉTERMINÉ à σ=0.3 et σ=1 — sa majorité dépend alors de l'ordre d'itération, donc de
   `PYTHONHASHSEED`. Un verdict de cellule non reproductible, invisible tant qu'on ne compte pas par seed.

## Portée (hedges)

* ⚠️ **σ ne balaye PAS la « force de lecture » de l'init** : l'argmax est invariant par multiplication
  positive, donc σ=0,1 / 0,3 / 1,0 donnent la MÊME politique initiale à seed fixe (mesuré :
  `init_score` identique). σ balaye le RAPPORT entre l'échelle de l'init et le pas du hill-climb, donc
  **k(0,1) vs k(1,0) ne se lit pas comme une dose-réponse**. La seule discontinuité RÉELLE est σ=0 vs σ>0.
* ⚠️ **En corps suffisant, `ablation_verdict` ne peut structurellement pas rendre `X_DECOY`** : le
  plancher mesuré (300) ÉGALE le plafond de ticks, donc tout ratio ≈ 1 y devient
  `INCONCLUSIVE_DEGENERATE` — à juste titre. La grandeur lisible y est `k`, comptée HORS du verdict.
  Le « NEUTRE » de ces cellules n'est donc pas seulement un artefact de σ=0 : il est **illisible à tout
  σ** avec ce mesureur-SEUIL.
* Mini-monde jouet (K=5, métrique-seuil) : ces chiffres ne se transportent pas tels quels in-world —
  c'est précisément l'erreur E8 que S2-006 avait déjà commise. Ce qui se transporte est la STRUCTURE de
  l'argument, pas le taux.
* `n_accepted` non monotone en σ (4, 2, 6) : le hill-climb n'est pas plus « actif » à σ élevé, ce qui est
  cohérent avec l'invariance d'échelle ci-dessus.

## Ce que ce record change

* [[EDR-S2-006]] : la moitié **nécessité** perd son statut mesuré (bandeau posé le 2026-09-07) ; la
  moitié **suffisance** tient — un positif ne se fabrique pas par cette identité.
* `REF-DEMAND-MARKER` : le marqueur doit être lu comme un test **sur la politique**. Un « X_DECOY » ne
  dit pas « le monde n'exige pas X », il dit « CE sujet a un repli ».
* L'explication du gap **proxy 9 / in-world 0** revient au CHEMIN ([[EDR-LOCK-001]], [[EDR-EVO-016]]),
  pas au contenu de l'objectif : une fois soutenable, plus rien ne sélectionne la lecture — le gradient
  est nul sur tout l'ensemble soutenable (face « objectif » du même mur).

Converge [[EDR-S2-004]], [[EDR-S2-006]], [[EDR-LOCK-001]], REF-DEMAND-MARKER, REF-EXPERIMENT-PREFLIGHT.
