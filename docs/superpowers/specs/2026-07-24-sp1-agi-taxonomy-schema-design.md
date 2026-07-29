# SP-1 — Schéma du graphe capability-demand d'AGI-Taxonomy (+ validateur-cliquet)

**Date** : 2026-07-24
**Statut** : design validé, prêt pour plan d'implémentation
**Vision parente** : AGI-Taxonomy (backlog P4.3). Socle que **SP-2 peuplera par ablation**. S'appuie sur
CALIB-SP3 (demand-marker) et CALIB-ALIAS (garde d'aliasing fonctionnel). Cf. [[agi-taxonomy-os-taxonomy-bridge]].

---

## 1. Contexte et raison d'être

L'arc AGI-Taxonomy vise un graphe de prérequis dont les nœuds sont des **capacités-demandes in-world**.
SP-3 a validé l'instrument qui MESURE une arête (ablation within-subject → `X_DEMANDED`) ; CALIB-ALIAS a
livré le garde qui garantit que cette ablation est **chirurgicale** et non une fuite de substrat. SP-1
livre le **modèle de données** que SP-2 va peupler avec ces mesures : un schéma de graphe capability-demand,
au format os-taxonomy, **plus un validateur-cliquet** qui rend chaque arête OPPOSABLE — une arête n'existe
que si elle porte sa preuve exécutable.

**Pourquoi non-décoratif** : le dépôt a appris que « toute règle documentée sans application EXÉCUTABLE
finit violée ». Un schéma de types seul laisserait affirmer une arête sans mesure. Le validateur-cliquet
**opérationnalise** la chaîne de rigueur des deux calibrations de l'arc en un format auto-vérifiable, sur
le patron de `check_record_links.py` / `check_instrument_calibration.py`.

## 2. Objectif

Livrer : (a) un schéma JSON (nœuds = capacités, arêtes = demandes) ; (b) un validateur
`tools/check_agi_taxonomy.py` qui REJETTE toute arête sans preuve mesurée complète ; (c) le vocabulaire v0
= les **4 capacités** déjà établies par des records réels, en nœuds ; `demands.json` **vide** (les arêtes
sont le livrable mesuré de SP-2).

## 3. Constat honnête qui borne v0

Les records de demande existants (S2-001 perception, MEM-001 mémoire, LANG-006 langage, G1-001
généralisation) établissent que **le monde demande une capacité** (task→capacité) et sont **antérieurs à
CALIB-ALIAS** : aucun ne porte le résultat du garde d'aliasing fonctionnel. Sous la règle stricte
(`functional_aliasing == "pass"`), **aucun n'est une arête capacité→capacité valide**. Conséquence assumée :

- v0 seede les **nœuds** (les 4 capacités, chacune avec son critère d'évidence + sonde + record réel).
- v0 ne seede **aucune arête** : `demands.json` est vide. Les arêtes capacité→capacité, prouvées via le
  garde, sont le livrable MESURÉ de SP-2. On ne fabrique pas de preuve pour peupler le format.
- L'enforcement d'arête est démontré sur **fixtures** (arête valide-de-forme vs invalides), pas sur des
  données réelles inexistantes.

## 4. Modèle de données (`data/agi_taxonomy/`, format os-taxonomy)

### 4.1 `capabilities.json` — nœuds

Liste d'objets :

```json
{
  "id": "perception",
  "title": "Perception (lecture de l'observation)",
  "description": "La politique lit l'observation et l'utilise causalement.",
  "evidence_criterion": "ablation within-subject de l'observation (obs randomisée/occultée) effondre la survie/le score",
  "probe": "tools/s2_demand.py",
  "record": "docs/EDR/S2-001_Within_Subject_Perception_Ablation_Is_The_Sound_Demand_Marker.md"
}
```

v0 : `perception` (S2-001), `memory` (MEM-001), `language` (LANG-006), `generalization` (G1-001).

### 4.2 `demands.json` — arêtes (VIDE en v0)

Forme d'une arête (peuplée par SP-2) — « `capability` demande `prerequisite` » :

```json
{
  "capability": "Y",
  "prerequisite": "X",
  "strength": "hard",
  "evidence": {
    "ablation_verdict": "X_DEMANDED",
    "ratio": 2.42,
    "n": 12,
    "functional_aliasing": "pass",
    "record": "docs/EDR/EDR-XXX_....md"
  }
}
```

## 5. Schéma (`data/agi_taxonomy/schema/`, JSON Schema)

- `capability.schema.json` : `id`, `title`, `description`, `evidence_criterion`, `probe`, `record` requis.
- `demand.schema.json` : `capability`, `prerequisite`, `strength ∈ {hard, soft}`, `evidence` requis ;
  `evidence` requiert `ablation_verdict`, `ratio` (number), `n` (integer), `functional_aliasing`, `record`.

**Sémantique de `strength` (levée d'ambiguïté)** : `strength` est un tag DESCRIPTIF de la magnitude du
ratio (`hard` = effondrement fort, `soft` = plus faible mais toujours au-dessus du seuil), il ne relâche
PAS la garde de verdict. **Toute arête valide, hard OU soft, exige `ablation_verdict == "X_DEMANDED"`** ;
une arête dont le ratio ne franchit pas le `collapse_factor` (verdict `INCONCLUSIVE`/`X_DECOY`) n'est PAS
une arête, quel que soit le tag. Le validateur n'a donc qu'une règle de verdict, identique pour hard et soft.

Le schéma décrit la FORME ; le validateur (§6) impose la SÉMANTIQUE de preuve.

## 6. Le validateur-cliquet (`tools/check_agi_taxonomy.py`) — le cœur

Calqué sur `check_instrument_calibration.py` (baseline gelée, `--report`, `--update-baseline`, exit 1 sur
NOUVELLE violation). Règles :

**Nœuds** : chaque capacité doit avoir `evidence_criterion` non vide, un `probe` pointant un fichier
existant, et un `record` pointant un `docs/EDR/*.md` existant.

**Arêtes (la garde qui compte)** : une arête n'est VALIDE que si son `evidence` porte, de façon exécutable :

- `ablation_verdict == "X_DEMANDED"` (jamais `INCONCLUSIVE`/`X_DECOY`) — le demand-marker de SP-3 ;
- `n >= 12` — le `n_floor` de `ablation_verdict` ;
- `functional_aliasing == "pass"` — le garde de CALIB-ALIAS : l'ablation était chirurgicale, pas une fuite
  de substrat ;
- `record` pointe un `docs/EDR/*.md` existant ;
- `capability` et `prerequisite` référencent des `id` présents dans `capabilities.json`.

Toute arête violant une règle → signalée, exit 1 (bloque). **Baseline gelée** pour la dette légataire —
vide au départ (aucune arête), donc aucune dette ; toute NOUVELLE arête doit être conforme d'emblée.

**Auto-référence évitée** : le fichier commence par `check_` → exclu du scan du cliquet de calibration
(comme `check_record_links.py`), pas d'instrument à calibrer.

## 7. Portée v0 (YAGNI)

Schéma (2 fichiers) + validateur + `capabilities.json` (4 nœuds réels) + `demands.json` vide (`[]`) +
tests. Pas de hook pre-commit obligatoire en v0 (proposé en option, activable comme les autres cliquets).
Pur JSON + validation, **aucun run coûteux, aucun bail**.

## 8. Tests

- **Nœuds** : `capabilities.json` v0 valide (4 nœuds, probes + records existants).
- **Enforcement d'arête sur FIXTURES** (générateur A — le validateur produit les DEUX issues) :
  - arête complète et conforme → ACCEPTÉE ;
  - `ablation_verdict = "INCONCLUSIVE"` → REJETÉE ;
  - `n = 8` (< 12) → REJETÉE ;
  - `functional_aliasing = "fail"` → REJETÉE ;
  - `record` inexistant → REJETÉE ;
  - `prerequisite` absent de `capabilities.json` → REJETÉE.
- **Baseline** : `demands.json` vide → 0 violation, exit 0.

## 9. Intégration

- `check_agi_taxonomy.py` suit le patron des cliquets existants (baseline, `--report`,
  `--update-baseline`). Documenté en REF (`docs/REF/REF-AGI-TAXONOMY.md`) et une ligne dans `CLAUDE.md`.
- **Pas d'EDR** : SP-1 est de l'INFRA (schéma + validateur), pas un verdict scientifique — comme
  `check_record_links` / `check_instrument_calibration`, qui n'ont pas de record.

## 10. Hors scope

- Peupler `demands.json` avec de vraies arêtes mesurées = **SP-2** (ablation + garde, par capacité).
- Publier/forker le graphe au format os-taxonomy = **SP-4**.
- Ré-établir les 4 records de demande SOUS le garde d'aliasing (pour qu'ils deviennent des arêtes valides
  task→capacité) = travail de SP-2, pas de SP-1.

## 11. Critères de succès

1. Schéma + validateur livrés ; `capabilities.json` (4 nœuds) passe ; `demands.json` vide passe.
2. Les 6 cas de fixtures d'arête (§8) se comportent comme attendu (1 acceptée, 5 rejetées).
3. `check_agi_taxonomy.py` exclu du cliquet de calibration (préfixe `check_`).
4. REF + ligne CLAUDE.md.

## 12. Risques et pièges

- **Schéma qui n'oppose rien** : évité par le validateur qui exige la preuve exécutable (le point du choix
  de design).
- **Fabrication de preuve pour « remplir »** : évité — `demands.json` reste vide tant qu'aucune arête n'a
  passé la chaîne complète (SP-2). L'anti-fabrication est structurel.
- **Référence fantôme** : `probe`/`record` sont vérifiés existants sur disque par le validateur.
