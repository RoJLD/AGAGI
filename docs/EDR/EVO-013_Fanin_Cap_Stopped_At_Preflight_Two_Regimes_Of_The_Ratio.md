---
id: EDR-EVO-013
type: EDR
title: "Plafonner le fan-in : ARRÊTÉ AU PRÉ-VOL — et la raison de l'arrêt révèle DEUX régimes du ratio R"
status: active
verdict: FANIN_CAP_INERT_TWO_REGIMES_OF_R
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-012]
---

## Question

[[EDR-EVO-012]] a montré que `R = |w_signal| / |logit|` sépare lecteur et porteur d'un facteur ~1500, mais
**aucune intervention n'a réussi à manipuler R**. Le levier nommé : plafonner le **fan-in des nœuds de
sortie** pendant l'évolution — purement structurel, sans connaissance de la tâche. Règle scellée :
`docs/preregistrations/EVO-013.json`, avec un **contrôle de manipulation obligatoire** (le plafond doit
réduire `|logit|`, sinon le bras ne teste rien).

## Pré-vol — et il dit NE PAS LANCER

| bras | fan-in moyen des sorties | `\|logit\|` médian |
|---|---|---|
| baseline | **0.69** | 0.626 |
| fanin=4 | 0.59 | **1.860** (monte) |
| fanin=1 | 0.37 | 0.000 |

* **Le fan-in du baseline est déjà 0.69** — les nœuds de sortie ont en moyenne **moins d'une** entrée.
  Plafonner à 4 est donc quasi inerte, et `|logit|` **augmente** au lieu de baisser : branche scellée
  « `|logit|` NE BAISSE PAS → le bras ne teste rien, NE PAS lire le taux de lecteurs ».
* Plafonner à 1 manipule réellement (`|logit|` → 0.000) mais laisse un fan-in de 0.37 : la plupart des
  sorties n'ont **aucune** entrée, le réseau est déconnecté de ses actions. Le levier devient destructif
  exactement là où il devient effectif.

Aucun run long n'a été lancé. C'est le 4ᵉ dispositif de la semaine arrêté ou invalidé au pré-vol, et le
1ᵉʳ à l'être **avant** toute dépense.

## Ce que l'arrêt révèle : R a DEUX régimes

Erreur que ce pré-vol corrige, et qui était mienne : je croyais les champions baseline encombrés de
concurrents. Les 65-75 entrées mesurées en [[EDR-EVO-010]] venaient du régime **densifié** `wake20`, pas
du baseline — dont le lecteur avait, comme le record le disait lui-même, **1 seul** concurrent.

| régime | fan-in des sorties | facteur limitant de R |
|---|---|---|
| **baseline** | ~0.7 | le **NUMÉRATEUR** — l'arête de signal n'est presque jamais créée (3 cibles / ~11 000) |
| **densifié** (`wake20`) | 65-75 | le **DÉNOMINATEUR** — les sorties saturent (`\|logit\|` 9-12.5) |

**Ça explique enfin pourquoi le volume d'[[EDR-EVO-010]] donne exactement zéro** : il aide le numérateur
(il crée bien l'arête — 4/4 champions la portent) **et** détruit le dénominateur (il sature les sorties).
Somme nulle. Aucune des deux moitiés de l'explication n'était visible depuis un seul régime.

## Verdict

**`FANIN_CAP_INERT_TWO_REGIMES_OF_R`** :

1. **Le plafond de fan-in est un NON-LEVIER** : inerte là où il faudrait agir (baseline, fan-in déjà < 1)
   et destructif là où il mord (K=1, sorties déconnectées).
2. **R a deux régimes**, et le facteur limitant change de côté. Un levier ne peut donc pas être universel :
   il doit agir sur le numérateur en régime clairsemé, sur le dénominateur en régime dense.
3. **Levier agnostique corrigé, à tester** : créer les arêtes **vers les sorties à FAIBLE fan-in** — ça
   monte le numérateur en laissant le dénominateur bas, sans aucune connaissance de la tâche. C'est
   structurellement ce que faisait le biais ciblé d'[[EDR-EVO-009]] (12/12), mais formulé sans savoir
   quelles arêtes comptent.

## Portée (hedges)

* Le fan-in baseline (0.69) est mesuré sur **une** lignée de 300 mutations, pas sur les champions de 12
  seeds. Les champions évolués pourraient différer — non vérifié.
* `|logit|` est mesuré sur un probe court (10 agents × 30 ticks) ; la non-monotonie baseline → K=4 pourrait
  être du bruit plutôt qu'un effet. Elle suffit néanmoins à déclencher la branche « ne pas lancer », qui
  était la question posée.
* La synthèse « deux régimes » est une lecture cohérente de trois records, pas un résultat mesuré en tant
  que tel : aucun run n'a comparé les deux régimes sous un même protocole.

Converge [[EDR-EVO-009]], [[EDR-EVO-010]], [[EDR-EVO-012]], REF-EXPERIMENT-PREFLIGHT.
