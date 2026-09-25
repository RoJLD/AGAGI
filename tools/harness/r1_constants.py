"""
tools/harness/r1_constants.py — constantes partagées entre `smoke_r1.py` et `seal_r1.py`.

Fix round 2/5 (revue contrôleur, tâche 10) point (3) : `B_SWEEP0_LR` était déclarée DEUX FOIS (une
constante par fichier, même valeur littérale `0.002`) — rien n'empêchait les deux de diverger en
silence si l'une était éditée sans l'autre. Module minuscule, sans autre dépendance que la
stdlib : source UNIQUE, importée par les deux.

`SMOKE_NAME` fixe le nom `Harness` du smoke (fix round 2, point 2) : `seal_r1.py` en dérive son chemin
par défaut, `smoke_r1.py` l'utilise pour sauvegarder — un seul littéral `"harness_r1_smoke"`, jamais
retapé.
"""

B_SWEEP0_LR = 0.002          # premier pas du sweep de la cellule B (bras full_eval == bras "A" de B)
SMOKE_NAME = "harness_r1_smoke"
SMOKE_SEED = 0
