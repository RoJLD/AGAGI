# EDR 093 : L'organe de planification n'est pas mort — réveil faible et sous-puissant au sweet spot

## Contexte

EDR 092 a corrigé deux bugs d'instrument de la sonde de dreaming (mesure des survivants → vide sous
extinction totale ; semis d'organe non fiable) et recadré Q1 en **prévalence de l'organe parmi TOUS
les agents** (reproduction différentielle = sélection). Re-run à 5 seeds (`stoneage`, 40 agents,
400 ticks, déterministe, quiet-log).

## Verdict (gate) : SURVIT_ET_PAYE — mais le label surestime

| Mesure | Valeur | per-seed |
|---|---|---|
| Q1 Δprévalence sweet | **+0.059** | `[0.067, 0.059, 0.138, -0.024, -0.005]` |
| Q1 Δprévalence létal | +0.012 | `[0.012, -0.012, 0.0, 0.012, 0.012]` |
| Q1 pression (sweet−létal) | **+0.047** | — |
| Q2b ratio survie ON/OFF | **1.087** (4/5 favorables) | `[1.037, 0.828, 1.318, 1.13, 1.087]` |
| Q2b significativité | **sign_p = 0.375** | NON significatif (n=5) |
| Q2a compétence rêveurs − non-rêveurs | **−0.040** | — |
| total_dreams_seen | **2978** | — |

Le gate 4-cas déclenche `SURVIT_ET_PAYE` (survives = Δsweet > −0.05 ET pression > 0 ; pays = q2b >
1.02), mais ses seuils sont **volontairement coarse/directionnels**. La décomposition dit la vérité.

## Lecture honnête — trois faits

1. **L'organe n'est PAS mort.** 2978 rêves se déclenchent (vs « 0 » du premier run, qui était un
   artefact de mesure des survivants vides, EDR 092). La prévalence de l'organe persiste/croît par
   reproduction. Le dreaming **s'active** quand l'organe est présent.

2. **Réveil faible et sous-puissant.** Au sweet spot, l'organe est légèrement favorisé (Δprév +0.059,
   pression +0.047 vs létal ~0), MAIS **2/5 seeds sont négatifs** et la population ON ne survit que
   ~9% mieux (q2b 1.087) avec **sign_p = 0.375 → non significatif**. Direction encourageante, preuve
   insuffisante.

3. **Paradoxe rêveurs vs porteurs (Q2a < 0).** La population *portant* l'organe survit marginalement
   mieux (q2b 1.087), mais les agents qui *rêvent effectivement* ont une compétence PLUS BASSE que
   les non-rêveurs de la même population (q2a −0.040). Donc l'avantage de l'organe **n'est pas
   expliqué par « le dreaming paye »** : soit corrélat (les porteurs diffèrent autrement), soit le
   rêve est une **réponse de détresse** (les agents en difficulté rêvent davantage). À élucider.

## Signification

> L'hypothèse d'EDR 091 (l'organe, mort en létal, ressuscite au sweet spot) est **soutenue
> directionnellement** : l'organe est vivant et faiblement favorisé par l'énergie. Mais c'est
> **sous-puissant (n=5, sign_p 0.375) et interne­ment contradictoire** (Q2a négatif). Le gate vert
> seul serait du théâtre ; la décomposition — imposée par le design — révèle un signal fragile, pas
> une victoire. C'est un résultat *honnête et exploitable*, pas un drapeau planté.

## Statut

- Sonde de dreaming réparée (EDR 092) et opérationnelle ; barreau 0 livré.
- Verdict : **réveil de l'organe SUGGÉRÉ mais non confirmé**. Ne PAS construire les barreaux 1-3
  (réparation effective) sur cette base avant confirmation.
- **Prochain** : (1) puissance ≥ 12 seeds ; (2) trancher le paradoxe Q2a/Q2b — le dreaming
  *cause*-t-il un meilleur sort (intervention : forcer do_dream on/off à organe constant) ou n'est-ce
  qu'un corrélat / une détresse ? ; (3) si confirmé, mesurer si le dreaming ravivé fait émerger des
  autels (barreau 1, le vrai but).

## Variables d'expérience

Nombre de seeds (puissance), grandeur de survie (prévalence reproduction vs âge censuré), seuils du
gate, intervention causale sur `do_dream_logit`/`surprise_momentum` à organe constant, cible
(stoneage vs autres barreaux).
