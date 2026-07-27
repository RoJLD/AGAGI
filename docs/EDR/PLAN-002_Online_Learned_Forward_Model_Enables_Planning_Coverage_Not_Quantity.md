---
id: PLAN-002
type: EDR
title: "Un modèle de transition g appris EN LIGNE débloque le planning — le verrou est la COUVERTURE d'états, PAS la quantité de données (clôt le caveat 'fit offline/oracle' de PLAN-001/EDR-193). (1) Efficacité-échantillon : le g bilinéaire atteint le planning dès ~50 transitions (plat jusqu'à 3000) ; le linéaire = chance partout -> la quantité n'est pas le problème. (2) En ligne (ε-greedy, g appris des trajectoires de l'agent) : plafonne à 0.52 vs oracle 0.65 ; l'écart est INSENSIBLE à ε (0.4=0.7=1.0) = PAS l'exploration mais la distribution stationnaire (agir maintient sur l'ATTRACTEUR de la dynamique). (3) Des RESETS épisodiques (départs variés = respawns/cohortes) referment l'écart (0.52->0.615≈oracle) -> online débloque le planning SI diversité épisodique des départs, que la biosphère fournit nativement"
status: accepted
gate: null
verdict: ONLINE_G_ENABLES_PLANNING_WITH_EPISODIC_COVERAGE
---

# PLAN-002 : un g appris en ligne débloque le planning — verrou = couverture, pas quantité (G4)

## Contexte

PLAN-001 a montré qu'un g BILINÉAIRE fidèle rend le planning zéro-shot utile (linéaire ≈ hasard). MAIS g était
ajusté HORS-LIGNE sur 3000 transitions aléatoires (oracle) — caveat hérité d'EDR-193. In-world, g doit être
appris de PEU de données que l'agent GÉNÈRE lui-même. Deux questions : (1) combien de transitions ?
(efficacité-échantillon) ; (2) les propres trajectoires de l'agent couvrent-elles assez l'espace pour un g
généralisable ? (exploration/couverture). Note : les moindres carrés étant ordre-indépendants, apprendre en
ligne par stats suffisantes accumulées ≡ offline sur les mêmes données → le vrai défi en ligne = la COUVERTURE.

## Méthode

`tools/online_world_model_probe.py` (pur numpy). Même dynamique action-conditionnée que PLAN-001.
- **(1) Efficacité-échantillon** : fit sur N∈{50…3000} transitions aléatoires, succès planning zéro-shot,
  bilinéaire vs linéaire.
- **(2) En ligne** : agent ε-greedy (planifie avec le g courant sinon explore), g appris incrémentalement de
  SES trajectoires (`_OnlineBilinear`, stats suffisantes par action), refit périodique. Succès planning à
  divers horizons d'expérience. Sweep ε∈{0.4,0.7,1.0}. Bras RESET : ré-init de l'état à un point varié tous
  les 20 pas (= épisodes/respawns → couverture au-delà de l'attracteur). d=8, K=4, 5 seeds.

## Constat

**(1) Efficacité-échantillon (succès planning, fit sur N transitions) :**

| N | 50 | 100 | 200 | 500 | 1000 | 3000 |
|---|---|---|---|---|---|---|
| bilinéaire | 0.663 | 0.637 | 0.637 | 0.640 | 0.643 | 0.647 |
| linéaire | 0.323 | 0.353 | 0.323 | 0.313 | 0.340 | 0.307 |

**(2) En ligne (oracle offline = 0.647) :**

| condition | succès | écart oracle |
|---|---|---|
| sans reset (attracteur) | 0.520 | +0.127 |
| ε=0.4 / 0.7 / 1.0 (sans reset) | 0.520 / 0.520 / 0.520 | — (ε NEUTRE) |
| reset /20 pas (respawns) | 0.615 | +0.032 |
| reset /5 pas | 0.600 | +0.047 |

`VERDICT = ONLINE_G_ENABLES_PLANNING_WITH_EPISODIC_COVERAGE`.

## Lecture

- **La quantité de données n'est PAS le verrou.** Le g bilinéaire atteint le planning (~0.65) dès **50
  transitions** et reste plat jusqu'à 3000 — ultra sample-efficient (un agent récolte 50 transitions en
  quelques pas). Le linéaire reste au hasard quel que soit N. Côté VOLUME, le caveat « fit oracle » de
  PLAN-001/193 tombe.
- **Le verrou en ligne est la COUVERTURE D'ÉTATS, pas l'exploration.** L'agent en ligne plafonne à 0.52 (vs
  oracle 0.65). L'écart est **insensible à ε** (0.4=0.7=1.0 → 0.520 exact) : ce n'est donc PAS la politique
  d'exploration. La cause = la distribution STATIONNAIRE de la dynamique : elle est contractante (rayon ~0.9)
  → *agir* (n'importe quelle politique) maintient l'agent sur l'ATTRACTEUR, une région plus étroite que
  l'échantillonnage i.i.d. de l'oracle (qui « téléporte » n'importe où — irréaliste in-world).
- **La diversité épisodique referme l'écart.** Des RESETS vers des états variés (= épisodes/respawns/nouvelles
  cohortes) portent l'online de 0.52 à **0.615 ≈ oracle 0.647** (écart 0.03). La couverture au-delà de
  l'attracteur vient des DÉPARTS variés, pas de plus de données ni de plus d'exploration. Or la biosphère
  FOURNIT nativement cette diversité (cohortes qui respawnent, nouveaux agents à états initiaux variés).

## Conséquences

- **Caveat « fit offline/oracle » de PLAN-001/193 substantiellement LEVÉ** : un g bilinéaire appris EN LIGNE,
  de peu de données auto-générées, débloque le planning zéro-shot — À CONDITION d'une diversité épisodique des
  états de départ (fournie par la biosphère). Le levier G4 (forme du modèle) est donc actionnable in-world.
- **Reco in-world précise** : pour apprendre un world-model utile en ligne, ce qui compte est la COUVERTURE
  d'états (via respawns/cohortes/épisodes courts), pas le volume de données ni l'ε d'exploration. Si la
  couverture manque, la curiosité/RND (que le projet possède, [[sota-gap-substrate]]) viserait la NOUVEAUTÉ
  D'ÉTAT — mais ici le simple reset épisodique suffit.
- **Complète le diptyque G4** : PLAN-001 (la FORME du g détermine le comportement) + PLAN-002 (le g est
  apprenable en ligne sous couverture épisodique) → l'anticipation instrumentale est une capacité atteignable
  du substrat sous crédit épisodique ; reste = le bénéfice de survie in-world (brancher un g bilinéaire sur la
  boucle, frontière #3 « vrai planning »).
- Relié : `REF-LTC -A_ADOPTER_POUR-> PLAN-002`. Prolonge [[fil-directeur-agi-gates]] §G4 (EDR-193) et
  [[planner-depth1-refuted]]. Motif commun avec [[warm-start-transversal-law]] : une capacité « qui ne paie
  pas in-world » débloquée en identifiant le vrai verrou en aval (ici : couverture, pas capacité/quantité).

## Caveats

1. Proxy SYNTHÉTIQUE (dynamique action-conditionnée tanh(W_a·s)) hérité de PLAN-001 : établit le PRINCIPE
   (quantité≠couverture ; resets referment l'écart), pas la magnitude in-world.
2. La contractivité (rayon 0.9) crée un attracteur net → l'écart online/oracle est prononcé ; une dynamique
   moins contractante aurait un attracteur plus large (moins de gap). Le RÉSULTAT robuste = l'insensibilité à
   ε + la fermeture par resets, pas les décimales.
3. Reset = ré-init i.i.d. de l'état (idéalisation du respawn) ; in-world les états de spawn ne sont pas i.i.d.
   mais restent DIVERS (positions/énergies variées) → couverture partielle mais réelle. Non mesuré in-world.
4. g bilinéaire = fit par action (suppose K actions discrètes connues) ; horizon depth-1 ; 5 seeds. Le vrai
   test reste in-world (apprentissage conjoint g + politique sous survie).
