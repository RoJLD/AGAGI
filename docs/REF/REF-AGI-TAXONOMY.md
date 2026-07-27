# REF — AGI-Taxonomy : graphe capability-demand

Modèle de données de l'arc AGI-Taxonomy (backlog P4.3), au format `withmarbleapp/os-taxonomy`.

## Fichiers
- `data/agi_taxonomy/capabilities.json` — nœuds (capacités). Chaque nœud porte un `evidence_criterion`
  (le test de demande within-subject), un `probe` (la sonde) et un `record` (docs/EDR) — tous vérifiés existants.
- `data/agi_taxonomy/demands.json` — arêtes « Y demande X ». **Vide tant qu'aucune arête n'a passé la
  chaîne de preuve** (peuplé par SP-2, par ablation mesurée).
- `data/agi_taxonomy/schema/*.json` — contrat de forme (JSON Schema, pour lecture + publication SP-4).

## Le cliquet — `tools/check_agi_taxonomy.py`
Calqué sur `check_record_links` / `check_instrument_calibration` (baseline gelée, `--report`,
`--update-baseline`, exit 1 sur nouvelle violation). **Une arête n'existe que si elle porte sa preuve
mesurée COMPLÈTE** :
- `ablation_verdict == "X_DEMANDED"` (demand-marker, cf. CALIB-SP3) ;
- `n >= 12` (n_floor de `ablation_verdict`) ;
- `functional_aliasing == "pass"` (garde `assert_no_functional_aliasing`, cf. CALIB-ALIAS) ;
- `record` = un docs/EDR existant ; `capability`/`prerequisite` présents dans `capabilities.json`.

`strength` (hard/soft) est DESCRIPTIF (magnitude du ratio) et ne relâche PAS la règle de verdict.

## Ajouter une arête
Interdit de l'affirmer : il faut la MESURER (ablation within-subject + garde d'aliasing), écrire le record,
puis ajouter l'objet dans `demands.json` avec son `evidence`. Le cliquet rejette toute arête incomplète.
