---
id: EDR-EVO-001
type: EDR
title: "La sélection par la survie n'ENRICHIT PAS la dynamique du substrat : les champions évolués sont aussi CONTRACTIFS que des agents frais (et 60× plus sparses) — le verrou du gap in-world est l'OBJECTIF, pas la capacité du substrat"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-DREAM-005]
---

## Question
[[EDR-DREAM-005]] a établi que le substrat récurrent est **contractif** (sous entrée constante, l'état
`H` converge vers un point fixe — il se fige). Le gap dominant du dépôt est « proxy 9 / in-world 0 »
(pas de cognition in-world), et [[EDR-S2-012]] a montré que la survie n'a **aucun contenu cognitif**
(gradient de sélection nul pour la cognition). Question de synthèse, décisive entre deux verrous
concurrents :

* **Verrou = SUBSTRAT** : le substrat manque de richesse dynamique pour calculer ; l'évolution
  voudrait l'enrichir mais ne peut pas. → on attendrait des champions MOINS contractifs que des frais.
* **Verrou = OBJECTIF** : la survie ne récompense pas le calcul récurrent, donc l'évolution ne
  développe **aucune** richesse dynamique. → champions AUSSI contractifs que des frais.

## Méthode
Mesure HORS-MONDE, avec l'instrument **calibré** `measure_convergence`
(`tools/substrate_attractor_probe.py`, cf. DREAM-005) : piloter chaque génome dans le batch model sous
**entrée constante** (zéro ET obs aléatoire fixe), 60 ticks, et mesurer si `H` converge (pas de queue
`|dH|`). Structure-agnostique : on mesure la dynamique RÉELLE, pas une propriété du câblage. Sujets :
8 agents FRAIS vs les **10 champions du HoF principal** (`data/hall_of_fame.pkl`).

## Résultats

| régime d'entrée | FRESH converge | CHAMPION converge | tail `|dH|` (fresh / champ) |
|---|---|---|---|
| zéro | 6/6 | 9/10 | 0.0 / 0.0 |
| obs aléatoire fixe | 4/6 | 6/10 | 2.2e-4 / 3.4e-4 |

Les non-convergents stricts (sous obs non nulle) ont une queue **~2-3e-4** = quasi-figés. Champions et
frais sont **indiscernables** en contractivité, dans les deux régimes.

Fait structurel corroborant (rayon spectral / densité du connectome) : les 10 champions ont une densité
de W de **0.017** (vs **1.0** pour un agent frais dense) — l'évolution **sparsifie ~60×** — sans pour
autant enrichir la dynamique (⚠️ le rayon spectral « caché » n'est PAS calculable : les champions ont
`N < I+O`, entrées/sorties chevauchées, `hidden = N−I−O = −18` — d'où le recours à la mesure EMPIRIQUE
de convergence, seule fiable ici).

### Robustesse : 4 lignées, 2 objectifs (le hedge « une seule lignée » tombe)
Répliqué sur **3 lignées famine indépendantes** (`hof_famine_harsh_s{42,43,44}`, objectif « survie
FAMINE DURE » — un second objectif de type survie) : elles sont **aussi largement contractives** et
sparses.

| lignée / objectif | converge (zéro / obs fixe) | densité W |
|---|---|---|
| HoF principal (survie) | 9/10 · 6/10 | 0.017 |
| famine s42 | 8/10 · 7/10 | 0.064 |
| famine s43 | 4/10 · 5/10 | 0.064 |
| famine s44 | 5/10 · 5/10 | 0.064 |

Les lignées famine varient un peu plus (5-8/10 stricts), mais les queues des non-convergents restent
**~1e-3 = quasi-figées** — aucune ne développe de dynamique riche. **Deux objectifs de type survie, 4
lignées : tous produisent des substrats contractifs + sparses.**

## Verdict
**`SURVIVAL_SELECTION_DOES_NOT_ENRICH_SUBSTRATE_DYNAMICS`** → **le verrou est l'OBJECTIF, pas la
capacité du substrat.**

L'évolution sous survie **élague** le connectome (sparse) et **conserve** un substrat contractif/figé —
elle ne construit **aucune** richesse calculatoire, exactement parce que la survie ne la récompense pas.
C'est la confirmation de [[EDR-S2-012]] (« survie = aucun contenu cognitif ») **au niveau de la dynamique
du substrat** : le substrat SÉLECTIONNÉ n'a pas plus de richesse qu'un substrat ALÉATOIRE.

## Conséquence stratégique
Changer le SUBSTRAT/l'architecture ne débloquera PAS la cognition in-world : même si on dote le substrat
d'une capacité récurrente plus riche, l'évolution ne l'utilisera pas tant que l'objectif ne la récompense
pas (elle l'élaguerait, comme elle élague déjà les 5 nœuds cachés → structure plate, cf.
[[from-genome-flattens-architecture]] et [[intelligence-typing-flat-connectome]]). **Le levier est
l'OBJECTIF** : il faut une tâche à contenu cognitif EXPLICITE que le corps ne court-circuite pas (la
prescription de [[EDR-S2-012]]) — le régime `cognitive_demand` in-world en est le candidat instrumenté.

## Portée (hedges)
* ~~Une seule lignée~~ **RÉPLIQUÉ sur 4 lignées, 2 objectifs de survie** (HoF principal + 3 famine
  s42/43/44) — cf. section Robustesse. Ce qui reste NON testé : un objectif qui RÉCOMPENSE le calcul
  (mémoire/récurrence). ⚠️ le régime `cognitive_demand` in-world est un XOR **statique** (2 bits dans
  l'obs courante) → il ne demande PAS de récurrence, donc il ne trancherait PAS. Le test discriminant
  exige une tâche à demande de MÉMOIRE temporelle (cf. [[memory-architecture-audit]] MEM-001).
* **Contractivité mesurée sous entrée CONSTANTE** (caricature ; in-world l'entrée varie). Comme dans
  DREAM-005, c'est un proxy de la tendance du substrat à se figer, pas une preuve de l'absence de calcul
  in-world.
* Corroborant, pas preuve : un substrat contractif PEUT calculer (mémoire courte) ; le point est
  COMPARATIF (champion ≈ frais), et c'est la comparaison qui tranche entre les deux verrous.

Converge [[EDR-DREAM-005]], [[EDR-S2-012]], [[from-genome-flattens-architecture]],
[[intelligence-typing-flat-connectome]], [[research-backlog-and-gaps]], REF-EXPERIMENT-PREFLIGHT.
