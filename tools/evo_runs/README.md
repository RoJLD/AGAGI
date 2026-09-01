# Sondes de l'arc EVO-005→020

## ⛔ Les runners d'expérience sont PERDUS (constat du 2026-08-04)

Une revue adversariale a signalé que les commits des records EVO-016→020 ne contenaient **que de la
doc** : aucun de leurs chiffres n'était reproductible depuis le dépôt. Le constat est en réalité pire.

Les runners (`evo016_run.py` … `evo020_run.py`, et leurs pré-vols) vivaient dans le **scratchpad de
session**, vidé au redémarrage. **Ils n'existent plus nulle part.** Les résultats d'EVO-016 à EVO-020 sont
donc définitivement non reproductibles — les réécrire produirait un autre banc, pas une reproduction.

**Correctif de processus, appliqué à partir d'ici** : un runner d'expérience vit dans le dépôt dès sa
PREMIÈRE exécution, jamais dans un répertoire temporaire. Un record ne doit pas être committé sans le
code qui l'a produit.

Ce qu'il reste : les paramètres et les chiffres sont intégralement décrits dans les records et dans les
règles scellées (`docs/preregistrations/*.json`), et le banc lui-même
(`tools/evo_cognitive_objective.py`) est committé — mais les scripts d'orchestration ne le sont pas.

## Sondes conservées

Écrites le 2026-08-04 et sauvées à temps. Chaque script tient le bail `kuzu`. Lancer depuis la racine :

    PYTHONPATH=. python -u tools/evo_runs/<script>.py

| script | ce qu'il mesure |
|---|---|
| `probe_reflex_confound.py` | l'avantage de survie vient-il de la LECTURE ou de la diagonale réflexe ? (93 % / 7 %) |
| `probe_addnode_fragility.py` | `add_node` décale-t-il le bloc d'entrée ? (non : 0/3000) et un lecteur y survit-il ? |
| `probe_reader_fragility.py` | robustesse d'un lecteur câblé à UN `add_node` (6/10 le perdent) + mécanisme |

## ⚠️ Défauts connus des runners perdus, conservés ici pour l'audit

* le compteur d'arêtes E→S d'EVO-019/020 était **invalide** : il comparait `W[:I, N-O:]` avant/après, or
  `add_node` change N et décale le bloc des sorties — d'où les valeurs négatives des tableaux. Les
  affirmations de manipulation reposent sur des re-mesures séparées, pas sur ce compteur ;
* le plafond de coût était en **SECONDES par seed**, ce que la clôture d'E13 proscrit (elle prescrit un
  plafond en NOMBRE D'AGENTS, déterministe). La censure qui en résulte est corrélée au succès évolutif —
  cf. la correction portée à `EVO-019`.
