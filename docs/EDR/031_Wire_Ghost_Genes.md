---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-031
type: EDR
title: "Câbler (et non tuer) les gènes fantômes — hygiène *connective*"
status: legacy
gate: foundational
---

# EDR 031 : Câbler (et non tuer) les gènes fantômes — hygiène *connective*

## Contexte — Vague 1, et une objection juste

Audit (EDR 010) : `W_router`, `thresholds`, `bytecode` sont **mutés** (≈35 occurrences dans
`mutation.py`/`evolution.py`) mais **jamais lus dans le `forward`** (seulement copiés au
redimensionnement ; `thresholds` est même remis à zéro). Première intention : *tuer* (principe
« soustraction > addition »).

**Objection de l'utilisateur :** « Je veux faire émerger l'AGI — tuer des gènes n'est-il pas
contradictoire ? »

## Décision — câbler, pas tuer

> La bonne distinction n'est pas *mort vs vivant* mais **déconnecté vs connecté**. Un gène muté
> *sans chemin de lecture* n'est pas du potentiel latent — c'est un **void** que la sélection ne
> peut jamais saisir (aucune exaptation possible). Pour l'émergence, la matière première doit être
> **co-optable**. Donc on **CÂBLE** : leur donner un chemin de lecture transforme le poids mort en
> **substrat fonctionnel** que l'évolution *peut* exploiter. Tuer retirerait du potentiel ;
> câbler en ajoute. L'honnêteté évolutive est restaurée en rendant la mutation **signifiante**.

Câblages (V18.18) :
- **`thresholds`** (par nœud) : seuil d'excitabilité → `tanh(excitation − seuil)` (passe de base
  *et* branche dreaming). Chaque neurone acquiert une excitabilité propre, évolvable.
- **`W_router`** (`I×3`) : **neuromodulation** — l'obs produit 3 modulateurs qui ajustent le
  **gain** global du réseau (`gain = 1 + 0.3·tanh(x·W_router).mean ∈ [0.7,1.3]`), traitement
  dépendant du contexte. *La sémantique était laissée vide à l'origine → c'est un choix de design*
  (conservateur, évolvable, réversible).
- **`bytecode`** : nourrit `compiler.py` (metaprog) → câblage différé à la **Vague 2 (RSI)**.

## Résultat

- Tests dédiés (`test_wired_genes.py`) : deux agents identiques *sauf* un gène → états
  **différents** ⇒ le gène est **lu** (prouvé pour `thresholds` ET `W_router`) ; seuils nuls =
  identité (pas de régression silencieuse).
- **109 tests verts** ; smoke E2E (curriculum 2D) : la chaîne tient, pas de déstabilisation.

## Conséquences

La Vague 1 est **connective, pas soustractive** : on rend les mécanismes *honnêtes* en les
rendant *fonctionnels*, pas en les supprimant — ce qui sert l'objectif d'émergence (plus de
substrat co-optable) au lieu de le contredire. La mutation de `thresholds`/`W_router` influence
désormais le comportement → leur sélection devient interprétable.

## Suites

- **Ablation** (Commandement 15) : maintenant qu'ils sont vivants, mesurer leur *apport réel*.
- `bytecode` à câbler avec la RSI (Vague 2).
- Réglage possible du gain neuromodulateur / de la sémantique du router si l'ablation le motive.

## Variables d'expérience

Amplitude du gain (0.3), portée des seuils, sémantique de `W_router` (gain global vs gating par
canal), inclusion des nœuds d'entrée dans le seuillage.
