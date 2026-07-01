---
id: REF-NoisyFitness-2000
type: REF
title: Optimisation évolutive sous fitness bruitée — ré-échantillonnage / éval robuste
url: https://doi.org/10.1016/S0304-3975(01)00182-7
method: moyenner la fitness sur K évaluations réduit la variance de sélection (Beyer ; reévaluation CMA-ES)
lib: pycma
maturity: production
rediscovered_by: [EDR-078]
---
# REF-NoisyFitness — fitness bruitée en calcul évolutionnaire (Beyer 2000 et al.)

Sous fitness stochastique, la sélection sur une seule évaluation s'effondre ; le remède
standard est le **ré-échantillonnage** (K évaluations par individu) — théorie EC établie.

Pont AGAGI : EDR-078 redécouvre « le plateau de compétence est du bruit de mesure ; évaluer
robustement (K érès) lève le plateau ×3 ». C'est `robust_hof_K`. Mécanisme classique — à
citer ; pour le tuning, voir les heuristiques de reévaluation de pycma/CMA-ES.
