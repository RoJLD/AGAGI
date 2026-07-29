# SP-2 — Première arête MESURÉE du graphe : « coordination demande perception » (+ raffinement SP-1)

**Date** : 2026-07-24
**Statut** : design validé, prêt pour plan d'implémentation
**Vision parente** : AGI-Taxonomy (backlog P4.3). Peuple `demands.json` (livré vide par SP-1) de sa première
arête réelle. Compose CALIB-SP3 (demand-marker) + CALIB-ALIAS (aliasing) + SP-1 (validateur). Cf.
[[agi-taxonomy-os-taxonomy-bridge]].

---

## 1. Objectif

Mesurer et graver la première arête capacité→capacité — **« language/coordination demande perception »** —
sur le proxy bon marché du jeu référentiel de Lewis, et l'écrire dans `data/agi_taxonomy/demands.json` de
façon à ce qu'elle **passe le validateur SP-1**. Deux livrables :

- **A. Raffinement de SP-1** (petit) : autoriser `functional_aliasing == "n/a"` SI l'arête porte un
  `specificity_control == "pass"`.
- **B. La mesure** : ablation within-subject de la perception + contrôle de demande, verdict `X_DEMANDED`,
  écriture de l'arête + record.

## 2. Pourquoi ce raffinement de SP-1 (et pourquoi il reste rigoureux)

Le garde d'aliasing fonctionnel de CALIB-ALIAS exige une **capacité de contrôle indépendante DANS le même
agent**. Le *sender* de Lewis est mono-fonction (il n'émet qu'un signal depuis la cible) — pas de contrôle
within-agent. MAIS le garde défend contre une **fuite du mécanisme d'ablation via substrat partagé** (le bug
mémoire-vue EDR-WARM-007) ; une **ablation d'ENTRÉE** (dérangement du one-hot cible entre agents) n'écrit
rien dans le substrat → **aucune fuite possible**. Le contrôle de spécificité correct pour une ablation
d'entrée est le **contrôle de demande** : ablater la perception là où la coordination n'est PAS demandée →
doit être inerte.

Le raffinement reste principié : `n/a` n'est accepté que si l'arête PROUVE sa spécificité autrement
(`specificity_control == "pass"`). Ce n'est pas une échappatoire libre.

## 3. Raffinement SP-1 (deliverable A)

- `data/agi_taxonomy/schema/demand.schema.json` : `evidence.functional_aliasing ∈ {pass, n/a}` ;
  ajouter `evidence.specificity_control` (optionnel `∈ {pass, fail}`).
- `tools/check_agi_taxonomy.py::validate_edge` : remplacer la règle
  `functional_aliasing == "pass"` par : `functional_aliasing == "pass"` OU
  (`functional_aliasing == "n/a"` ET `specificity_control == "pass"`). Toute autre combinaison → rejetée.
- `docs/REF/REF-AGI-TAXONOMY.md` : documenter la règle raffinée.
- Tests : arête `n/a`+`specificity_control="pass"` → ACCEPTÉE ; `n/a` sans specificity (ou `fail`) →
  REJETÉE ; `pass` → toujours acceptée. (Ré-utilise le fichier `tests/test_agi_taxonomy.py`.)

## 4. La mesure (deliverable B)

### 4.1 Substrat et coordination

`tools/referential_game_probe.py` : sender/receiver = `TorchPopulationModel`/`MambaAgent` (I=59, O=108,
128 agents), entraînés par `learn_episode` (crédit épisodique). La perception de la cible = le one-hot
`_onehot(targets, K)` injecté dans les I premiers slots. Métrique = accuracy `guess == target`
(FIABLE ~0.77 à K=6, hasard 1/K).

### 4.2 Ablation de perception (within-subject)

Dérangement du one-hot cible du sender via `derange_rows` (`tools/s2_demand_ablation.py`, in-distribution,
ne mute pas l'entrée) — chaque agent voit la cible d'un pair. Point d'intervention : la construction de
`_onehot(targets, K)` avant `sender.forward(...)`.

### 4.3 Les deux conditions

- **COORD** : le receiver n'a AUCUNE vue directe de la cible, il doit lire le signal du sender. Ablater la
  perception du sender → signal non-informatif → la coordination s'effondre vers le hasard.
- **NO-COORD (contrôle de demande, VIVANT)** : le receiver reçoit une **vue directe BRUITÉE** de la cible
  (accuracy intermédiaire, p.ex. ~0.7, STRICTEMENT entre hasard et 1.0 — métrique VIVANTE) et ignore le
  signal. Ablater la perception du *sender* est **inerte** (le receiver n'en dépend pas). ⚠️ La vue directe
  doit être BRUITÉE : une vue parfaite plafonnerait l'accuracy à 1.0 et « inerte » serait un artefact de
  plafond (piège WARM-002), pas une vraie inertie.

### 4.4 Verdict

- `ablation_verdict(intact_accs, ablated_accs, floor=1/K, ...)` sur COORD → attendu **X_DEMANDED** (ratio
  ~0.77/0.17 ≈ 4.5).
- Sur NO-COORD → attendu **X_DECOY / inerte** → `specificity_control = "pass"` (la médiane intacte ≈ ablée,
  sur métrique vivante).
- **Unité = seed**, `n >= 12` (le `n_floor` de `ablation_verdict`). `intervention_verified=True` (le
  dérangement perturbe bien l'entrée).

### 4.5 La sonde

`tools/perception_coordination_demand_probe.py` : `run_perception_coordination_demand_probe(...)` (nom
`run_*probe` → trippe le cliquet) orchestre COORD/NO-COORD × intact/ablé sur ≥12 seeds et renvoie
`{coord_verdict, coord_ratio, nocoord_verdict, specificity_control, n, edge}`. `functional_aliasing = "n/a"`
(ablation d'entrée, pas de fuite de substrat).

## 5. Calibration de la sonde (obligatoire — la sonde trippe le cliquet)

Vérité-terrain par **contrôle positif/négatif injecté** (façon `partial_oracle`) :

- **Sender ORACLE** (émet toujours le signal correct) → coordination parfaite → ablater sa perception
  DOIT effondrer (X_DEMANDED). Contrôle positif : le banc SAIT produire l'effondrement.
- **Sender ALÉATOIRE** (signal indépendant de la cible) → pas de coordination (hasard) → ablater est inerte.
  Contrôle négatif : le banc ne fabrique pas un effondrement quand il n'y en a pas.
- Générateur A du pré-vol respecté (les DEUX issues). Cas dans `tests/sandbox/test_instrument_calibration.py`
  + entrée `CALIBRATED`.

## 6. Bornage du coût (rituel obligatoire — PREMIER vrai run de l'arc)

Les sous-projets précédents étaient analytiques ; celui-ci entraîne de vrais réseaux. Pur torch **CPU**,
**aucun bail `kuzu`, aucun monde**. Discipline :

- **Pré-vol** (`experiment_preflight`) : `declare_design(unité=seed, n=12)`, générateur A (oracle/aléatoire),
  no-op (contrôle NO-COORD), `assert_not_degenerate` (métriques vivantes).
- **Smoke D'ABORD** : 2-3 seeds, épisodes réduits, `n_agents` réduit — valider le mécanisme (COORD
  s'effondre, NO-COORD inerte, tous deux vivants) ET **mesurer le débit** (temps/seed).
- **Run-verdict borné** : 12 seeds, `episodes`/`n_agents` PLAFONNÉS (tunés au smoke pour atteindre FIABLE
  sans excès). Ne PAS extrapoler une tendance depuis un préfixe court (transitoire d'apprentissage).
- **Persister** les accuracies par seed (pour re-graver le record sans réentraîner).

## 7. Livrable final : l'arête

Écrire dans `data/agi_taxonomy/demands.json` (remplace `[]`) :

```json
[{
  "capability": "language",
  "prerequisite": "perception",
  "strength": "hard",
  "evidence": {
    "ablation_verdict": "X_DEMANDED",
    "ratio": 4.5,
    "n": 12,
    "functional_aliasing": "n/a",
    "specificity_control": "pass",
    "record": "docs/EDR/EDR-XXX_Coordination_Demands_Perception.md"
  }
}]
```

`python tools/check_agi_taxonomy.py` doit alors afficher `1 arête, 0 violation`. Record EDR gravé
(frontmatter `gate:`/`tests:`/`adopts:`), valeurs mesurées réelles (remplacer `ratio`/`record` par le mesuré).

## 8. Fichiers

- `tools/check_agi_taxonomy.py` (MODIFIÉ) — règle `n/a`+`specificity_control`.
- `data/agi_taxonomy/schema/demand.schema.json` (MODIFIÉ) — `functional_aliasing` enum + `specificity_control`.
- `data/agi_taxonomy/demands.json` (MODIFIÉ) — la première arête.
- `tools/perception_coordination_demand_probe.py` (NOUVEAU) — la sonde (COORD/NO-COORD × intact/ablé).
- `docs/EDR/EDR-XXX_Coordination_Demands_Perception.md` (NOUVEAU) — le record.
- `docs/REF/REF-AGI-TAXONOMY.md` (MODIFIÉ) — règle raffinée.
- `tests/test_agi_taxonomy.py` (MODIFIÉ) — cas `n/a`/specificity.
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — calibration de la sonde + `CALIBRATED`.

## 9. Critères de succès

1. SP-1 raffiné : `n/a`+`specificity_control="pass"` accepté ; `n/a` seul rejeté ; `pass` toujours accepté.
2. Sonde calibrée (oracle → X_DEMANDED, aléatoire → inerte), sous cliquet.
3. Run-verdict (n=12) : COORD X_DEMANDED (métrique vivante), NO-COORD inerte (métrique vivante).
4. `demands.json` contient l'arête ; `check_agi_taxonomy.py` la valide (1 arête, 0 violation).
5. Record EDR gravé avec valeurs mesurées.

## 10. Hors scope

- Les autres arêtes (perception→memory, etc.) = itérations ultérieures (YAGNI).
- Un contrôle d'aliasing fonctionnel WITHIN-AGENT sur un vrai substrat multi-capacité (ce que CALIB-ALIAS a
  différé) reste ouvert ; ici on l'évite légitimement (ablation d'entrée) via `n/a`+contrôle de demande.

## 11. Risques et pièges

- **NO-COORD plafonné/planché → inertie fausse** (piège WARM-002) : la vue directe du receiver DOIT être
  bruitée (métrique strictement entre hasard et 1.0). Asserter la vivacité avant d'interpréter l'inertie.
- **COORD n'émerge pas au smoke** → épisodes insuffisants ; le contrôle positif ORACLE (calibration) tranche
  « le banc ne sait pas produire l'effondrement » vs « la coordination n'a pas eu le temps d'émerger ».
- **n<12** → aucun verdict (garde `ablation_verdict`).
- **Coût non borné** : plafonner `episodes`/`n_agents`, smoke d'abord, persister les accuracies.
- **Sonde non calibrée = résultat fabriqué** (déficit dominant du dépôt) : la calibration oracle/aléatoire
  est un livrable, pas optionnelle.
