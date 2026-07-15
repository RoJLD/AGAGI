---
id: MEM-001
type: EDR
title: "La MÉMOIRE paie causalement SSI la tâche exige un RAPPEL DIFFÉRÉ — valide l'audit mémoire (« la mémoire ne paie pas in-world car les tâches n'exigent pas de rappel ») avec l'instrument within-subject (4e modalité). BPTT contourné : mémoire = substrat FIXE (intégrateur à fuite du passé), seul le readout feedforward s'apprend (softmax GD). Tâche de rappel différé, ablation = mémoire décorrélée. MEMORY-DEMAND (indice caché à la sonde) : ablation effondre le rappel (6-8×, poids_mém 2.0). MEMORYLESS (indice visible à la sonde) : ablation INERTE (1.0×) ET le readout n'a AUCUN poids sur la mémoire (0.000 exact). La mémoire n'est pas une capacité qui s'active, c'est un investissement lu SSI la tâche impose de retenir le passé"
status: accepted
gate: null
verdict: MEMORY_PAYS_IFF_TASK_DEMANDS_DELAYED_RECALL
---

# MEM-001 : la mémoire paie SSI la tâche exige un rappel différé (4e modalité de l'instrument)

## Contexte

L'audit mémoire ([[memory-architecture-audit]]) conclut : la mémoire PEUT payer en isolation (BPTT, EDR
064/067/123) mais NE PAIE PAS in-world (NTM inerte 134/135, long-terme neutralisable sans coût, tâches sans
demande mémoire 058/062) → verrou = crédit means→ends, PAS le délai. On teste causalement le maillon « les
tâches n'EXIGENT pas de rappel » avec l'instrument within-subject ([[within-subject-demand-marker]], après
perception/S2-001, communication/LANG-006, généralisation/G1-001).

## Méthode

`tools/memory_payoff_probe.py` (pur numpy, standalone). BPTT est numpy-impossible ; on contourne comme l'archi
réelle du projet (état `H_prev` porté + readout dessus, [[memory-architecture-audit]]) : la MÉMOIRE est un
SUBSTRAT FIXE (intégrateur à fuite `m ← λ·m + obs` sur le passé), seul le READOUT feedforward s'apprend
(softmax GD + weight-decay). Tâche de rappel différé : un indice apparaît, on sonde l'agent après un délai.
- **MEMORY-DEMAND** : l'indice n'est vu qu'au tick 0 puis CACHÉ ; à la sonde `obs=0` → répondre EXIGE la
  mémoire (`m = λ^(delay-1)·onehot(indice)`).
- **MEMORYLESS** : l'indice n'apparaît qu'à la SONDE (jamais dans le passé) → `m = 0`, `obs` courante suffit.

Marqueur causal = ablation de la mémoire (intégrateur d'un indice ALÉATOIRE, décorrélé). Corroborant = poids du
readout sur l'entrée mémoire. K∈{6,8}, délai∈{5,10}, λ=0.85, 8 seeds.

## Constat

| monde (K=6, délai=5) | mém. vraie | mém. ablée | poids_mém | PAIE(×) |
|---|---|---|---|---|
| MEMORY-DEMAND | 1.00 | 0.16 | 1.97 | 6.1× |
| MEMORYLESS | 1.00 | 1.00 | 0.000 | 1.0× |

(délai=10, K=8 : demand 8.2× / memoryless 1.0× ; poids_mém 1.39 vs 0.000.) `VERDICT =
MEMORY_PAYS_IFF_TASK_DEMANDS_DELAYED_RECALL`.

## Lecture

- **La mémoire paie causalement quand la tâche impose de retenir le passé.** En MEMORY-DEMAND, ablater la
  mémoire effondre le rappel de 1.00 à 0.16 (hasard) : sans le passé retenu, l'agent ne peut pas répondre. La
  mémoire vaut 6-8× la performance.
- **La mémoire ne paie PAS quand l'info est disponible maintenant — et alors le readout ne la lit même pas.**
  En MEMORYLESS, l'ablation est INERTE (1.00 → 1.00) et surtout **poids_mém = 0.000 EXACT** : le readout
  n'investit aucun poids dans une mémoire superflue. Signature identique au |W|=0 de S2-001, au MI=0 de
  LANG-006, au poids_θ→0 de G1-001.
- **Valide causalement l'audit mémoire.** Le maillon « in-world la mémoire ne paie pas car les tâches
  n'exigent pas de rappel » est confirmé : ce n'est PAS une incapacité du substrat (la mémoire-demand paie
  6-8×), c'est une propriété de la STRUCTURE DE TÂCHE. La mémoire est un investissement conditionnel, pas une
  capacité qui s'active.

## Conséquences

- **Reco in-world (clôt le maillon du backlog mémoire)** : pour que la mémoire paie dans la biosphère, il faut
  une tâche à RAPPEL DIFFÉRÉ (un indice maintenant, une décision plus tard, indice caché entre-temps — cache
  de ressource localisée, danger passé, engagement de coopération). Sans cette structure, la mémoire restera
  neutralisable sans coût (NTM inerte) — résultat NEUTRE attendu, PAS un échec de capacité. Instrument de
  vérification = ablation-mémoire within-subject (reset/randomisation de `H_prev`), bon marché.
- **Quatrième modalité de l'instrument within-subject** : perception (S2-001), communication (LANG-006),
  généralisation (G1-001), **mémoire (MEM-001)**. Même témoin causal (ablation de l'entrée porteuse) + même
  corroborant (poids → 0 quand la capacité n'est pas utilisée). L'instrument est validé sur 4 modalités.
- **Convergence transversale** : « X ne paie pas in-world » n'est presque jamais un manque de capacité, c'est
  l'absence de DEMANDE (structure de tâche) — recoupe [[warm-start-transversal-law]] et le motif « le verrou
  est en aval de la capacité ». Ici pour la mémoire spécifiquement.
- Relié : `REF-LTC -A_ADOPTER_POUR-> MEM-001` (le substrat mémoire = famille LTC/récurrente ; l'intégrateur à
  fuite en est l'instance minimale). Recoupe [[memory-architecture-audit]] + [[within-subject-demand-marker]].
  ID préfixé `MEM-`.

## Caveats

1. Proxy SYNTHÉTIQUE et IDÉALISÉ (rappel différé d'un indice unique, séparation nette DEMAND/MEMORYLESS) :
   établit la LOGIQUE (la mémoire paie SSI rappel demandé ; ignorée sinon), pas des magnitudes in-world.
2. Mémoire = intégrateur à fuite FIXE (non appris), readout feedforward appris — contourne BPTT (numpy-
   impossible) mais ne teste PAS l'apprentissage d'un mécanisme de mémoire ; teste si un readout EXPLOITE une
   mémoire disponible quand la tâche l'exige. La difficulté d'APPRENDRE à stocker (BPTT/crédit) est hors-cadre
   (c'est l'autre maillon de l'audit : verrou = crédit).
3. L'intégrateur à fuite retient une DIRECTION (un indice) ; il ne ferait pas un rappel précis parmi un flux
   d'items (limite réelle d'une mémoire additive). Le proxy vaut pour « retenir un indice sur un délai », pas
   pour la mémoire de travail structurée.
4. Ablation = mémoire d'un indice aléatoire (décorrélée), pas reset-à-zéro (qui donnerait un argmax dégénéré) ;
   standard « mémoire détruite en préservant la magnitude ». 8 seeds ; robuste au délai (5→10) et à K (6→8).
