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
- **`specificity_control == "pass"` — TOUJOURS**, quelle que soit la valeur de `functional_aliasing` ;
- `functional_aliasing ∈ {"pass", "n/a"}` (garde CALIB-ALIAS), le `"n/a"` étant réservé aux ablations
  d'ENTRÉE : si `evidence.ablation_target == "substrate"`, `"pass"` est EXIGÉ ;
- `record` = un docs/EDR existant ; `capability`/`prerequisite` présents dans `capabilities.json`.

`strength` (hard/soft) est DESCRIPTIF (magnitude du ratio) et ne relâche PAS la règle de verdict.

### `evidence.ablation_target` — `input` | `substrate` (défaut `input` si absent)
Décrit CE QUI est coupé. Une ablation d'ENTRÉE n'écrit rien dans le substrat : il n'y a pas de fuite à
garder, `functional_aliasing = "n/a"` y est légitime (c'est le cas des 2 arêtes gravées, cf.
`tools/memory_perception_demand_probe.py:21`). Une ablation de SUBSTRAT peut au contraire dégrader du
calcul hors-demande : le `"n/a"` y est REFUSÉ, la garde CALIB-ALIAS doit être mesurée `"pass"`.
Le champ est optionnel — absent ⇒ `input` (compatibilité légataire, les arêtes déjà gravées ne le
portent pas).

### Pourquoi `specificity_control` sans exception (durcissement 2026-09-01)
L'ancienne règle acceptait `functional_aliasing == "pass"` SEUL et n'exigeait `specificity_control` que
dans la branche `"n/a"` — une 3ᵉ arête aurait donc été gravée à un standard STRICTEMENT INFÉRIEUR à
celui des 2 arêtes déjà en place. Raison : le bras PRINCIPAL d'une arête de demande est
**arithmétiquement forcé** — une fois l'entrée nécessaire ablatée, l'agent ne peut plus dépasser le
plancher `1/K`, donc `X_DEMANDED` tombe mécaniquement dès que le bras intact est vivant. Ce bras ne peut
pas produire l'issue négative, il ne prouve donc rien (pré-vol, question A). Le seul bras dont l'issue
négative est RÉELLEMENT atteignable est le contrôle de demande — même ablation, mais information
redondante disponible ailleurs : NO-COORD pour `language->perception`, PRESENT pour
`memory->perception`. Preuve que l'alternative existe : l'itération 1 de MEM-PERCEPTION a **échoué** ce
contrôle (ratio 4.329) et a dû être corrigée.

Contre-exemples gelés + non-régression des 2 arêtes gravées :
`tests/sandbox/test_agi_taxonomy_gate.py`.

## Ajouter une arête
Interdit de l'affirmer : il faut la MESURER (ablation within-subject + garde d'aliasing + **contrôle de
demande**), écrire le record, puis ajouter l'objet dans `demands.json` avec son `evidence` (y compris
`ablation_target` si l'ablation vise le substrat). Le cliquet rejette toute arête incomplète.
