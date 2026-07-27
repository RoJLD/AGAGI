---
id: EDR-EVO-002
type: EDR
title: "Un objectif qui EXIGE la mémoire produit un substrat qui la RETIENT (rappel différé maîtrisé 8/8) — le TEST DISCRIMINANT de EVO-001 confirme causalement que le verrou est l'OBJECTIF, pas le substrat"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
extends: [EDR-EVO-001]
---

## Question
[[EDR-EVO-001]] a conclu — sur la contractivité de champions de SURVIE — que « le verrou du gap in-world est
l'OBJECTIF, pas la capacité du substrat », et a laissé UN hedge décisif ouvert : **jamais testé, un objectif
qui RÉCOMPENSE le calcul (mémoire temporelle).** C'est la falsification directe de sa propre thèse :

* **Verrou = OBJECTIF** : si la survie n'enrichit pas parce qu'elle ne récompense pas le calcul, alors un
  objectif qui EXIGE la mémoire DOIT produire un substrat qui la construit. → prédiction : maîtrise.
* **Verrou = SUBSTRAT/RECHERCHE** : si l'évolution ne construit PAS la mémoire même quand l'objectif la
  récompense, la thèse de EVO-001 tombe (le verrou serait la capacité ou la recherche, pas l'objectif).

## Le piège d'instrument évité (méthodologie)
Le réflexe eût été de réutiliser `measure_convergence` (l'instrument de EVO-001) : « le substrat évolué
est-il moins contractif ? ». Il est **inutilisable ici** : une MÉMOIRE parfaite est un état qui NE BOUGE
PAS (forget-gate δ→0 : `H_new=H`), que `measure_convergence` classe « gelé/contractif », CONFONDANT
rétention et oubli (une mémoire à attracteur-ligne « converge » aussi). On a donc conçu un instrument de
rétention `measure_retention_separation` (sep(D) = séparation de deux histoires après D pas d'entrée nulle),
calibré PAR PRÉDICTION (sep=(1−δ)^D sur génome diagonal ; cf. `test_instrument_calibration`).

**Puis on l'a RÉFUTÉ par calibration-contre-tâche** : le rappel se lit sur `sign(preds)`, et le signe
SURVIT à une contraction uniforme ((1−δ)^D rétrécit l'amplitude, garde le signe). sep(init aléatoire) mesure
la rétention d'une perturbation GÉNÉRIQUE, pas le sous-espace signé bas-dim que la tâche exploite. Mesure à
l'appui (ci-dessous) : DEMAND maîtrise (acc 1.0) avec sep≈0.70, **indiscernable** de MLESS/FRESH.
→ **Instrument primaire = la CAPACITÉ DE RAPPEL elle-même** (la grandeur qui agit), sep relégué au rang de
corroborant — et de cas d'école : un proxy dynamique plausible qui **n'agit pas**.

## Méthode (`tools/evo_memory_enrichment.py`, ni DB ni Biosphere)
Neuro-évolution (élitisme + `apply_mutations`) du VRAI substrat récurrent (`recurrent_forward`) sur une tâche
de **rappel parallèle différé** : encoder K=2 bits, D=3 pas d'entrée NULLE (seule la récurrence porte),
puis restituer. Trois sources de génomes, MÊME opérateur / dims (I=O=8), MÊME test DEMANDING — **seul
l'objectif d'évolution change** :
- **DEMAND** : cible encodée puis CACHÉE à la sonde → la récurrence est la seule mémoire.
- **MLESS (contrôle inverse)** : à l'encode un LEURRE aléatoire, la cible n'apparaît qu'à la SONDE → mémoire
  INUTILE (feedforward). Manipulation INVERSE (REF-EXPERIMENT-PREFLIGHT règle 1) qui REND la mémoire inutile,
  pas qui « ne la demande pas » — sinon l'évolution la bâtit quand même (tenir 2 bits/3 ticks est trivial).
- **FRESH** : génomes non évolués → plancher.
Accuracy mesurée HORS-ÉCHANTILLON (seed d'éval décalé → pas de fuite train/test). Unité de réplication =
**le SEED** (lignée), n=8. Pré-vol passé (declare_design sans maillon inféré ; contrôle positif DEMAND=1.00 ;
la manipulation change l'issue vs FRESH).

## Résultats (8 seeds, K=2, D=3, gen=40, pop=32 ; chance=0.5)

| source (objectif d'évolution) | test DEMANDING | notes |
|---|---|---|
| **DEMAND** | **1.00** (8/8 seeds) | maîtrise parfaite, chaque lignée |
| FRESH (pas d'évolution) | 0.495 (médiane ; 0.24–0.76) | ~chance : le substrat brut ne rappelle pas |
| MLESS → sa PROPRE tâche | 1.00 | il a bien APPRIS (son échec en xeval = « pas de mémoire », pas « rien appris ») |
| MLESS → test DEMANDING (xeval) | 0.474 (médiane) | ~chance : **6/8 seeds** ; 2 fuites incidentes (1.00) |

- **DEMAND > FRESH : 8/8 seeds, sign_p = 0.0078** (< 0.05, garde de puissance franchie).
- **Spécificité** : médiane MLESS-xeval 0.474 ≈ chance ≪ DEMAND 1.00 → la mémoire est bâtie **spécifiquement**
  sous la demande, pas par l'évolution en général.
- Corroborant SECONDAIRE (sep, DOCUMENTÉ trompeur) : DEMAND 0.70 · MLESS 0.70 · FRESH 0.47. sep tracke
  « a été évolué » (0.70 vs 0.47), PAS « a de la mémoire » (DEMAND=MLESS) — confirme sa réfutation.
- Le connectome grandit modérément (nodes 19→30 médiane), mais le mécanisme porteur est le **forget-gate**
  (rétention sur nœuds existants), pas la taille : recoupe [[EDR-058/064 mem_nas]] (la demande de mémoire ne
  fait PAS grandir l'archi — ici elle bâtit la FONCTION sans exiger la TAILLE).

## Les DEUX fuites incidentes (une donnée, pas un bug)
2/8 génomes MLESS résolvent quand même le test DEMANDING (1.00). Mécanisme : ils ont appris « sortie =
entrée-sonde si présente, SINON encode tenu » — une mémoire de SECOURS non sélectionnée. Loin d'affaiblir la
thèse, cela la RENFORCE : **le substrat construit la mémoire si facilement qu'elle apparaît même NON
récompensée** → le substrat n'est en rien le verrou ; il est un constructeur de mémoire naturel que seule la
survie n'a jamais sollicité. (D'où le choix de tester la MÉDIANE, robuste à ces fuites, et de baser la
puissance sur DEMAND vs FRESH — propre sur les 8 seeds.)

## Verdict
**`OBJECTIVE_IS_LEVER`** → **le verrou est bien l'OBJECTIF, pas la capacité du substrat ni la recherche.**

L'évolution — l'opérateur RÉEL du dépôt — bâtit une mémoire différée PARFAITE dès que l'objectif l'exige,
là où (a) la survie n'enrichissait RIEN ([[EDR-EVO-001]] : champions contractifs = frais), (b) l'absence
d'évolution laisse le substrat à chance, (c) une évolution sans demande de mémoire n'en construit pas (sur la
médiane). Le substrat est CAPABLE, l'évolution TROUVE la solution quand elle est récompensée — donc ni le
substrat ni la recherche ne sont le verrou. **Reste l'objectif**, exactement la prescription de EVO-001 et de
[[EDR-S2-012]].

## Conséquence stratégique
Confirme causalement, au niveau de la CAPACITÉ (et non plus seulement de la dynamique), la thèse transversale :
**ne pas investir dans une archi plus riche ; investir dans un OBJECTIF à contenu cognitif que le corps ne
court-circuite pas.** La suite naturelle est de porter cette demande de mémoire IN-WORLD (une tâche de survie
qui exige un rappel différé, cf. la recette de `memory_demand_world_probe` : corps INSUFFISANT + rappel
DIFFÉRÉ + gain EN ÉNERGIE) et vérifier que l'évolution in-world y construit la mémoire — le pont proxy→monde.

## Portée (hedges)
* Tâche HORS-MONDE (banc cognitif pur), comme EVO-001 était hors-monde sur la dynamique. Le pont in-world
  reste à faire (la contribution suivante).
* Régime EASY choisi À DESSEIN (K=2/D=3 → DEMAND maîtrise) pour un contrôle positif FORT et un contraste
  propre ; à K≥4 l'évolution ne maîtrise que partiellement (0.84, plafond ES) — ce qui poserait la question
  substrat-vs-recherche que ce régime écarte en montrant la maîtrise possible.
* Contrôle inverse MLESS avec fuite incidente 2/8 (traitée par la médiane + puissance sur DEMAND vs FRESH).
* sep(D) : instrument RÉFUTÉ comme mesure de capacité, conservé calibré comme corroborant dynamique et cas
  d'école (calibration-contre-tâche).

Converge [[EDR-EVO-001]], [[EDR-S2-012]], [[EDR-DREAM-005]], [[memory-architecture-audit]] (MEM-001),
[[within-subject-demand-marker]], [[from-genome-flattens-architecture]], REF-EXPERIMENT-PREFLIGHT.
