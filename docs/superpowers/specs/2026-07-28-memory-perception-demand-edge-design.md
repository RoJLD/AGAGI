# Deuxième arête MESURÉE du graphe AGI-Taxonomy : « memory demands perception »

**Date** : 2026-07-28
**Statut** : design validé, prêt pour plan d'implémentation
**Vision parente** : AGI-Taxonomy (backlog P4.3). Deuxième arête réelle de `demands.json` (la 1ère,
`language→perception`, est livrée par SP-2). Compose CALIB-SP3 (demand-marker) + SP-1 (validateur raffiné).
Cf. [[agi-taxonomy-os-taxonomy-bridge]], [[memory-demand-builds-retaining-substrate]].

---

## 1. Objectif

Mesurer et graver l'arête capacité→capacité **« memory demands perception »** — la rétention APPRISE
route-t-elle par la perception ? — sur un proxy torch bon marché de rappel différé, et l'écrire dans
`data/agi_taxonomy/demands.json` de façon à ce qu'elle **passe le validateur SP-1**. Miroir méthodologique
de SP-2 (ablation d'ENTRÉE within-subject + contrôle de demande), sur une nouvelle modalité (mémoire).

## 2. Pourquoi torch (mémoire APPRISE) et pas le proxy numpy MEM-001

Le monde numpy de MEM-001 (`memory_demand_world_probe.py`) a la mémoire `m = leak·m + perception` :
la mémoire y EST de la perception intégrée **par construction**, donc « memory demands perception » y est
vrai **tautologiquement** — ablater la perception corrompt trivialement l'accumulateur. Le graver depuis là
serait une mesure faible.

Le proxy torch teste la mémoire comme l'**état récurrent APPRIS** du MambaAgent : l'agent apprend à encoder
l'indice dans son état et à le restituer après un délai. « La rétention apprise route-t-elle par la
perception ? » est alors une **mesure émergente**, pas une construction. Précédent que la tâche est
apprenable : un objectif à rappel différé fait maîtriser la mémoire (MEM-001/EVO-002, 1.00 sur 8/8 seeds).
Un seul substrat (comme SP-2) — YAGNI. Le monde numpy reste disponible comme éventuelle vérité-terrain de
calibration ultérieure, PAS comme mesure de cette arête.

## 3. Le proxy : delayed-match-to-sample (torch CPU, self-contained)

`tools/memory_perception_demand_probe.py` (NOUVEAU) — **ne modifie PAS** `memory_demand_world_probe.py` ni
`referential_game_probe.py`. Réutilise `MambaAgent`, `make_population(backend="torch")`, `learn_episode`,
`tools/s2_demand_ablation.derange_rows`, `tools/demand_marker.ablation_verdict`.

Un épisode = une séquence de ticks, l'état récurrent `H` **porté** à travers les ticks (remis à zéro
UNIQUEMENT au début de l'épisode) :

1. **Encodage** (t=0) : l'agent perçoit un indice `cue` (one-hot sur K dans les slots d'entrée).
2. **Délai** (D ticks) : obs = bruit/zéros (aucune info sur l'indice) ; `H` porte l'indice retenu.
3. **Test** (dernier tick) : l'agent produit une sortie sur K ; métrique = accuracy `argmax(sortie) == cue`
   (fiable ; hasard = `1/K`).

Paramètres de départ (tunés au smoke) : `K=6`, `D=2` ticks de délai, `n_agents=16`, `episodes~800`,
`lr=0.05`. `floor = 1/K`.

## 4. Les deux conditions (recall)

- **DELAYED** (rétention DEMANDÉE) : l'obs de test ne montre RIEN de l'indice → il FAUT que `H` ait retenu
  l'indice encodé. Ablater l'encodage → `H` retient du bruit → le rappel s'effondre vers le hasard.
- **PRESENT** (contrôle de demande, VIVANT) : l'obs de test montre une **vue directe BRUITÉE** de l'indice
  (via `flip_p` : avec proba `flip_p`, un référent aléatoire) → la rétention est **inutile** (l'info est
  disponible au test). Ablater l'encodage est **inerte** (l'agent lit l'obs de test).
  ⚠️ La vue de test DOIT être bruitée : une vue parfaite plafonnerait l'accuracy à 1.0 et « inerte »
  serait un artefact de plafond (piège WARM-002). `flip_p` réglé pour une accuracy médiane STRICTEMENT
  entre `1/K` et ~0.9.

## 5. Ablation d'ENTRÉE (within-subject)

Point d'intervention : le one-hot de l'indice au tick d'**ENCODAGE**, dérangé par `derange_rows`
(in-distribution, ne mute pas l'entrée) — chaque agent encode l'indice d'un pair. **À L'ÉVAL uniquement**
(within-subject : entraîner sur perception intacte, puis évaluer perception d'encodage intacte vs dérangée).
Une ablation d'ENTRÉE n'écrit rien dans le substrat → **`functional_aliasing = "n/a"`** (aucune fuite de
substrat à garder ; cf. CALIB-ALIAS, dont le garde défend contre une fuite via substrat PARTAGÉ, absente
ici).

## 6. Verdict

- `ablation_verdict(intact, ablated, intervention_verified=True, floor=1/K, ceiling=1.0)` sur DELAYED →
  attendu **X_DEMANDED** (intact VIVANT > `1/K+0.15`, ablé ≈ hasard).
- Sur PRESENT → attendu **X_DECOY / inerte** (métrique VIVANTE) → `specificity_control = "pass"`.
- **Unité = seed**, `n >= 12` (`n_floor`). `intervention_verified=True`.

La sonde `run_memory_perception_demand_probe(...)` (nom `run_*probe` → trippe le cliquet de calibration)
renvoie `{"delayed": <verdict dict>, "present": <verdict dict>, "present_alive": bool,
"specificity_control": "pass"|"fail", "functional_aliasing": "n/a", "n": int, "delayed_intact": [...],
"delayed_ablated": [...], "present_intact": [...], "present_ablated": [...]}`.

## 7. Calibration de la sonde (obligatoire — la sonde trippe le cliquet)

Vérité-terrain par contrôle positif/négatif injecté (façon SP-2), via un seam
`memory_mode ∈ {"learned", "oracle", "random"}` :

- **memory ORACLE** (rétention PARFAITE de l'indice encodé — au test, la sortie reflète directement
  l'indice encodé, possiblement dérangé) → DELAYED parfait → ablater l'encodage DOIT effondrer
  (X_DEMANDED). Contrôle positif : le banc SAIT produire l'effondrement.
- **memory ALÉATOIRE** (sortie de test décorrélée de l'indice encodé) → pas de rétention → ablater est
  inerte (PAS X_DEMANDED). Contrôle négatif : le banc ne fabrique pas d'effondrement inexistant.
- Générateur A du pré-vol respecté (les DEUX issues). `oracle`/`random` **n'entraînent pas** le substrat
  (mais donner au receiver/lecteur assez d'épisodes pour lire le canal, si nécessaire — leçon SP-2 :
  `episodes=0` laisse le lecteur non entraîné, contrôle positif vacux ; utiliser un `episodes` modeste).
- Cas dans `tests/sandbox/test_instrument_calibration.py` + entrée `CALIBRATED`.

## 8. Bornage du coût (rituel obligatoire)

Pur torch **CPU**, **aucun bail `kuzu`, aucun monde**. Discipline (leçons SP-2) :

- **Pré-vol** (`experiment_preflight`) : `declare_design(unité=seed, n=12)`, générateur A (oracle/aléatoire),
  no-op (contrôle PRESENT), `assert_not_degenerate` (métriques vivantes).
- **Smoke D'ABORD** : 2-3 seeds, épisodes/n_agents réduits — valider le mécanisme (DELAYED s'effondre,
  PRESENT inerte, tous deux vivants) ET **mesurer le débit** (temps/seed).
- **Run-verdict borné** : 12 seeds, `episodes`/`n_agents` PLAFONNÉS au smoke (viser DELAYED émergent :
  `delayed_intact` médian > `1/K + 0.15`). **En FOREGROUND** (leçon SP-2 : un run en background a été
  perdu par le harness, ~92 min gaspillées). Ne PAS extrapoler depuis un préfixe court.
- **Provenance** : le verdict gravé doit venir de la fonction CALIBRÉE réelle, pas d'un driver de récup
  (leçon SP-2).
- **Persister** les accuracies par seed (`results/mem_perception_edge_accuracies.json`).

## 9. Livrable final : l'arête

Écrire dans `data/agi_taxonomy/demands.json` (AJOUTER à l'arête SP-2 existante — le fichier devient une
liste de 2 arêtes) :

```json
{
  "capability": "memory",
  "prerequisite": "perception",
  "strength": "hard",
  "evidence": {
    "ablation_verdict": "X_DEMANDED",
    "ratio": 0.0,
    "n": 12,
    "functional_aliasing": "n/a",
    "specificity_control": "pass",
    "record": "docs/EDR/EDR-MEM-PERCEPTION_Memory_Demands_Perception.md"
  }
}
```

`ratio` = valeur mesurée réelle. `python tools/check_agi_taxonomy.py` doit alors afficher `2 arêtes,
0 violations`. Record EDR gravé (frontmatter `gate:`/`tests:`/`adopts:`, valeurs mesurées réelles).

**Si le run est un NUL honnête** (DELAYED n'émerge pas ou pas d'effondrement sur métrique vivante) :
graver le record NÉGATIF, arête NON écrite. Ne pas forcer.

## 10. Fichiers

- `tools/memory_perception_demand_probe.py` (NOUVEAU) — la sonde.
- `tests/test_memory_perception_probe.py` (NOUVEAU) — smoke unitaire (forme + `functional_aliasing='n/a'`).
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — calibration oracle/aléatoire + `CALIBRATED`.
- `results/mem_perception_edge_accuracies.json` (NOUVEAU) — accuracies persistées.
- `data/agi_taxonomy/demands.json` (MODIFIÉ) — 2ᵉ arête ajoutée.
- `docs/EDR/EDR-MEM-PERCEPTION_Memory_Demands_Perception.md` (NOUVEAU) — le record.

## 11. Critères de succès

1. Sonde calibrée (oracle → X_DEMANDED, aléatoire → inerte), sous cliquet.
2. Run-verdict (n=12) : DELAYED X_DEMANDED (métrique intacte VIVANTE > 1/K+0.15), PRESENT inerte
   (métrique VIVANTE) → `specificity_control="pass"`.
3. `demands.json` contient 2 arêtes ; `check_agi_taxonomy.py` valide (2 arêtes, 0 violations).
4. Record EDR gravé avec valeurs mesurées ; `check_record_links` non-orphelin.

## 12. Hors scope

- L'arête à ablation de SUBSTRAT (`language→memory`, exerçant le garde `functional_aliasing='pass'` de
  CALIB-ALIAS) = itération ultérieure (candidate B du brainstorm).
- Convergence multi-substrats (torch + numpy sur la même arête) = extension possible, PAS ce livrable
  (YAGNI ; SP-2 = un substrat).

## 13. Risques et pièges

- **DELAYED n'émerge pas** (le substrat contractif ne retient pas — S2/EVO le documentent in-world) : le
  contrôle positif ORACLE tranche « le banc ne sait pas produire l'effondrement » vs « la rétention n'a
  pas eu le temps d'émerger ». Précédent MEM-001/EVO-002 : le rappel différé PEUT être maîtrisé.
- **PRESENT plafonné/planché → inertie fausse** (WARM-002) : vue de test BRUITÉE obligatoire, vivacité
  assertée avant d'interpréter l'inertie.
- **Multi-tick / crédit temporel** : l'état `H` doit être porté à travers les ticks (pas remis à zéro dans
  la séquence). Vérifier au smoke que la rétention s'apprend.
- **Sonde non calibrée = résultat fabriqué** (déficit dominant du dépôt) : la calibration oracle/aléatoire
  est un livrable, pas optionnelle.
- **Coût** : smoke d'abord, run borné FOREGROUND, persister, provenance depuis la fonction réelle.
