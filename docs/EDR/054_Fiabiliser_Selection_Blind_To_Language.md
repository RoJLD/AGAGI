# EDR 054 : Fiabiliser l'émergence — la sélection est aveugle au langage

## Contexte

EDR 053 : l'émergence du langage est une loterie (~25 %, brisure de symétrie). Cible : la fiabiliser.
Levier le plus direct : **propager une lignée chanceuse** (effet fondateur).

## Étape 1 — une expérience confondue, attrapée

`tools/fiabiliser.py` comparait le taux d'émergence des descendants d'un **fondateur cristallisé** vs
d'un départ de **base**. Résultat : **arms byte-pour-byte identiques** (mêmes gains par seed,
t=0.00). Drapeau rouge → **artefact, pas verdict.** Cause : seeds identiques entre arms +
`np.random.seed(s)` rendant la continuation déterministe → l'effet du fondateur se *lave*. **On ne
conclut pas « propager ne marche pas » d'une expérience cassée.** (Réflexe imposé par la discipline
de mesure : un résultat « trop propre » est un signal d'alarme.)

## Étape 2 — le mécanisme révélé par le débogage (l'obstacle réel)

`save_to_hall_of_fame` garde le **top-10 par `life_score`** (âge, proies, mammouths) — **aveugle à
l'aptitude référentielle**. Donc :

> **On ne peut pas propager une convention via une sélection qui ne la voit pas.** Le HoF sélectionne
> les meilleurs *chasseurs*, pas les meilleurs *communicants*. La convention érode non par hasard,
> mais parce que **rien ne la sélectionne**.

## Étape 3 — test propre de stabilité (lignée continue)

`tools/conv_stability.py` : une lignée continue sous la demande de Lewis, MI(gain) tous les 8 ères :

| ère | 8 | 16 | 24 | 32 | 40 | 48 |
|---|---|---|---|---|---|---|
| gain | −0.004 | +0.007 | +0.004 | +0.018 | **+0.020** | +0.011 |

- La convention **se construit lentement** (~40 ères, pas une cristallisation soudaine), pic
  **modeste** (~0.02 MI), puis **reflue à ~moitié** (0.011).
- **Attracteur faible et partiellement persistant — pas un verrou.** « Amorcer une fois suffit »
  serait optimiste.
- ⚠️ **n=1 lignée, mesures par bloc bruitées** : c'est un *indice*, pas un verdict ferme (notre
  propre règle, EDR 052/053).

## Verdict (honnête)

- La convention est un attracteur **faible** ; elle se forme puis s'érode partiellement.
- **Raison de fond, solide** : la sélection (`life_score`) est **aveugle au langage** → rien ne
  maintient la convention.
- **Le levier de fiabilisation est donc clair** : **aligner la sélection sur la convention** —
  récompenser (un peu) l'aptitude référentielle dans la fitness, OU propager en sélectionnant *par*
  le trait référentiel (pas par `life_score`).

## Suites (ciblées)

1. **Sélection alignée** : ajouter un terme de fitness *référentiel* (faible, annealé) et re-mesurer
   le **taux d'émergence** *via le harnais* (multi-seed). Hypothèse : le taux bondit.
2. **Stabilité ferme** : refaire la trajectoire en **multi-seed** (harnais) avant de conclure
   persistance/érosion.
3. Ne pas oublier : `life_score`-aveuglité au langage est *exactement* le genre de désalignement
   fitness↔objectif qu'un #8 devrait pouvoir détecter et corriger.

## Variables d'expérience

Terme de fitness référentiel (force, anneal), critère de propagation (life_score vs référentiel),
nombre de seeds, durée.
