# Troisième arête MESURÉE du graphe AGI-Taxonomy : « language demands memory » (ablation de SUBSTRAT, jalon functional_aliasing)

**Date** : 2026-07-28
**Statut** : design validé, prêt pour plan d'implémentation
**Vision parente** : AGI-Taxonomy (backlog P4.3). Troisième arête réelle de `demands.json` (après
`language→perception` SP-2 et `memory→perception` MEM-PERCEPTION). **Premier usage RÉEL du garde
`functional_aliasing='pass'` de CALIB-ALIAS** — le jalon que les deux premières arêtes ont contourné via
l'ablation d'ENTRÉE (`functional_aliasing='n/a'`). Cf. [[agi-taxonomy-os-taxonomy-bridge]],
[[functional-aliasing-guard]] (CALIB-ALIAS).

---

## 1. Objectif

Mesurer et graver l'arête **« language demands memory »** — une capacité de code/coordination appris
route-t-elle par la rétention ? — sur un proxy torch de code-appliqué-différé, par une ablation de
**SUBSTRAT** (reset de l'état récurrent porté) montrée **CHIRURGICALE** via le garde `functional_aliasing`.

## 2. Pourquoi c'est le cas dur (et pourquoi le garde functional_aliasing est requis, pas 'n/a')

Les deux premières arêtes ablataient une ENTRÉE (dérangement d'un one-hot) : aucune écriture substrat →
`functional_aliasing='n/a'` honnête. Ici on ablate la MÉMOIRE = le portage récurrent `(1-δ)·H` (la règle
LTC `H_new=(1-δ)·H+δ·tanh(H·W_off)`, δ=σ(diag W) = porte d'oubli). C'est une **écriture d'état** → une
perturbation d'état fuit rarement de façon chirurgicale dans un substrat APPRIS. `functional_aliasing='n/a'`
serait donc MALHONNÊTE. L'arête n'est valide que si l'ablation est prouvée **SURGICAL** :
`functional_aliasing='pass'` (le garde comportemental de CALIB-ALIAS, `assert_no_functional_aliasing`).

**Le garde AUTO-DÉCIDE la gravabilité** : ablation chirurgicale (le contrôle survit) → arête gravée avec
`functional_aliasing='pass'` (jalon atteint). Ablation qui FUIT → finding honnête (« une ablation d'état
n'est pas chirurgicale dans le substrat appris » — le garde bloque correctement). Les deux issues sont
scientifiques ; on ne force pas.

## 3. Le proxy : delayed-code-application à DEUX readouts (torch CPU, self-contained)

`tools/language_memory_demand_probe.py` (NOUVEAU) — ne modifie AUCUN probe existant. Réutilise `MambaAgent`,
`make_population(backend="torch")`, `learn_episode`, `tools/demand_marker.ablation_verdict`,
`tools/experiment_preflight.assert_no_functional_aliasing`.

Un épisode = une séquence, l'état `H` porté à travers les ticks (reset UNE fois au début de l'épisode) :

1. **Encodage** (t=0) : l'agent perçoit un CODE `key ∈ [0,K)` (one-hot dans des slots d'entrée dédiés) →
   doit le retenir.
2. **Délai** (D ticks) : obs = bruit/zéros.
3. **Usage** (dernier tick) : obs = concat(QUÊTE `q ∈ [0,K)` dans les slots-query, CIBLE-CONTRÔLE
   `c ∈ [0,K)` dans les slots-control). L'agent produit DEUX readouts (deux tranches disjointes des O
   sorties) :
   - `readout_lang` = les K premiers logits → réponse attendue **`(q + key) mod K`** (mémoire-DÉPENDANT :
     exige le code retenu ET la quête courante).
   - `readout_control` = les K logits suivants → réponse attendue **`c`** (copie ; mémoire-INDÉPENDANT,
     feedforward : ne dépend que de l'entrée courante).

Métrique par readout = accuracy `argmax == cible`. `floor = 1/K`. Paramètres de départ (tunés au smoke) :
`K=6`, `D=2`, `n_agents=16`, `episodes~1200`, `lr=0.02`.

## 4. L'ablation de MÉMOIRE (substrat, within-subject)

Point d'intervention : **au tick d'USAGE, remettre `agent.H` à zéro AVANT le step** (l'injection d'entrée
`H[:, :I]=obs_t` du `_step` réinjecte la quête+contrôle courants ; le portage `(1-δ)·H` de l'état retenu est
effacé). → le `key` retenu disparaît → `readout_lang` s'effondre. La cible-contrôle `c` est injectée fraîche
→ `readout_control` survit SSI sa voie est feedforward (calculable en un step). À L'ÉVAL uniquement
(within-subject : entraîner sur mémoire intacte, puis évaluer intact vs H-reset-à-l'usage).

**C'est une ablation de SUBSTRAT** (écriture d'état) → `functional_aliasing` doit être testé et valoir
`'pass'`, PAS `'n/a'`.

## 5. Les DEUX gardes (le cœur)

### 5.1 Demande (`ablation_verdict` sur `readout_lang`)
- Condition MEMORY-DEMAND : `readout_lang` intact vs H-reset → attendu **X_DEMANDED** (intact VIVANT >
  `1/K+0.15`, ablé ≈ hasard).
- Contrôle de spécificité NO-MEMORY : le `key` est RE-MONTRÉ dans l'obs au tick d'usage → la rétention est
  inutile → H-reset est **inerte** sur `readout_lang` (métrique VIVANTE) → `specificity_control='pass'`.
  ⚠️ Vue re-montrée BRUITÉE (comme MEM-PERCEPTION : éviter le plafond, piège WARM-002) ; ET le canal encodé
  DÉCOUPLÉ de la réponse à l'entraînement dans la condition NO-MEMORY (leçon MEM-PERCEPTION : sinon confond
  d'entraînement — l'agent exploiterait le code retenu ; diagnostic = plafond « obs-usage seul »).

### 5.2 Aliasing fonctionnel (`assert_no_functional_aliasing` sur `readout_control`)
- `leakage = |acc_control_intact − acc_control_ablated|`. Le garde EXIGE `leakage ≈ 0` (tol) → **SURGICAL**.
- `x_response = |acc_lang_intact − acc_lang_ablated|` > 0 (ablation NON vacue = générateur A : elle change
  bien la capacité propre `readout_lang`).
- verdict : `SURGICAL` (leakage≈0, x_response>0) → `functional_aliasing='pass'` ; `FUNCTIONAL_LEAK`
  (leakage>0) → l'arête n'est PAS gravée (finding honnête) ; `VACUOUS_ABLATION` (x_response≈0) → l'ablation
  ne fait rien, contrôle raté.

**Unité = seed**, `n >= 12`. La sonde `run_language_memory_demand_probe(...)` (nom `run_*probe` → trippe le
cliquet) renvoie `{"lang_demand": <verdict>, "nomem_specificity": <verdict>, "nomem_alive": bool,
"specificity_control": "pass"|"fail", "functional_aliasing": "pass"|"fail", "leakage": float,
"x_response": float, "n": int, + les listes par-seed lang_intact/lang_ablated/control_intact/control_ablated/
nomem_intact/nomem_ablated}`.

## 6. Calibration de la sonde (obligatoire — la sonde trippe le cliquet)

Vérité-terrain par contrôle injecté (générateur A), seam `memory_mode ∈ {"learned", "oracle", "random"}` +
un seam de contrôle `control_mode ∈ {"feedforward", "leaky"}` :

- **memory ORACLE** (rétention parfaite du `key` → `readout_lang` = `(q+key)%K` par fiat) → ablater
  l'état effondre `readout_lang` → X_DEMANDED. Contrôle positif de la DEMANDE.
- **memory ALÉATOIRE** (`readout_lang` décorrélé) → ablation inerte → PAS X_DEMANDED. Contrôle négatif.
- **control LEAKY** (vérité-terrain pour le garde) : la cible-contrôle est FORCÉE de dépendre de l'état
  retenu (p.ex. `readout_control` attendu = `key` retenu, pas `c`) → ablater l'état casse AUSSI le contrôle
  → `leakage>0` → le garde functional_aliasing DOIT tirer (FUNCTIONAL_LEAK). Prouve que le garde SAIT
  détecter une fuite (sinon un `functional_aliasing='pass'` serait vacux).
- **control FEEDFORWARD** = le mode de mesure normal (le garde passe SSI le substrat appris a une voie
  contrôle feedforward).

Cas dans `tests/sandbox/test_instrument_calibration.py` + entrée `CALIBRATED`. oracle/random/leaky
utilisables avec `episodes` modeste (oracle/random bypassent l'agent ; leaky teste le garde sur le calcul).

## 7. Bornage du coût (rituel — leçons SP-2/MEM-PERCEPTION gravées)

Pur torch **CPU**, **aucun bail `kuzu`, aucun monde**. Pré-vol `experiment_preflight`
(`declare_design(unité=seed, n=12)`, générateur A oracle/aléatoire/leaky, `assert_not_degenerate`). **Smoke
D'ABORD** (mécanisme + débit). **Run-verdict n=12 en FOREGROUND** (jamais background — run perdu ~92 min sur
SP-2 ; sur MEM-PERCEPTION le contrôleur a dû faire un run de récup) avec `episodes`/`n_agents`/`D` PLAFONNÉS.
Provenance : verdict de la fonction CALIBRÉE réelle. Persister les accuracies + `_params` (leçon revue
MEM-PERCEPTION) dans `results/lang_memory_edge_accuracies.json`.

## 8. Livrable final : l'arête (SI ET SEULEMENT SI chirurgicale)

Écrire dans `data/agi_taxonomy/demands.json` (AJOUTER : le fichier passe à 3 arêtes) **SSI** `lang_demand
== X_DEMANDED` ET `functional_aliasing == 'pass'` ET `specificity_control == 'pass'` ET `lang_intact`
médian > `1/K+0.15` :

```json
{
  "capability": "language",
  "prerequisite": "memory",
  "strength": "hard",
  "evidence": {
    "ablation_verdict": "X_DEMANDED",
    "ratio": 0.0,
    "n": 12,
    "functional_aliasing": "pass",
    "record": "docs/EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md"
  }
}
```

(Note : avec `functional_aliasing='pass'`, `specificity_control` n'est PAS requis par le validateur SP-1
— mais on le mesure et le rapporte quand même, par rigueur.) `ratio` = mesuré réel. `check_agi_taxonomy`
doit afficher `3 arêtes, 0 violations`. Record EDR gravé.

**Si l'ablation FUIT** (`functional_aliasing='fail'` / FUNCTIONAL_LEAK) : arête NON écrite, record NÉGATIF
honnête (« l'ablation d'état n'est pas chirurgicale dans le substrat appris — le garde de CALIB-ALIAS a
bloqué une ablation non-chirurgicale, exactement son rôle »). Ne pas forcer.

## 9. Fichiers

- `tools/language_memory_demand_probe.py` (NOUVEAU) — la sonde (2 readouts, ablation d'état, 2 gardes).
- `tests/test_language_memory_probe.py` (NOUVEAU) — smoke unitaire (forme + `functional_aliasing` présent).
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — calibration oracle/aléatoire/leaky + `CALIBRATED`.
- `results/lang_memory_edge_accuracies.json` (NOUVEAU) — accuracies + `_params` persistés.
- `data/agi_taxonomy/demands.json` (MODIFIÉ) — 3ᵉ arête ajoutée (si gravée).
- `docs/EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md` (NOUVEAU) — le record.

## 10. Critères de succès

1. Sonde calibrée : oracle → X_DEMANDED, aléatoire → inerte, **leaky → garde functional_aliasing TIRE**
   (FUNCTIONAL_LEAK) — le garde prouvé sensible (générateur A dans les deux dimensions). Sous cliquet.
2. Run-verdict (n=12) : `lang_demand` X_DEMANDED (intacte VIVANTE) + `functional_aliasing` mesuré (pass OU
   fail — les deux sont un résultat).
3. Si pass : `demands.json` = 3 arêtes, `check_agi_taxonomy` valide (`functional_aliasing='pass'`, 1er usage
   réel du garde). Si fail : record négatif honnête, arête non écrite.
4. Record EDR gravé, `check_record_links` non-orphelin.

## 11. Hors scope

- Le vrai jeu référentiel sender/receiver (single-agent code-application suffit à capturer « code appris
  demande mémoire » — YAGNI ; sender/receiver = itération ultérieure si besoin).
- Une ablation d'état plus fine que « reset H à l'usage » (p.ex. cibler les dims code-porteuses) — si le
  reset total FUIT, une ablation ciblée serait le suivant, pas ce livrable.

## 12. Risques et pièges

- **L'ablation d'état FUIT** (`readout_control` chute aussi) : ce n'est PAS un échec du projet — c'est un
  RÉSULTAT (le substrat appris route le contrôle par l'état porté). Le graver honnêtement. Le contrôle LEAKY
  de calibration garantit que le garde qui le détecte est VALIDE.
- **`readout_lang` n'émerge pas** (le code+quête n'est pas appris) : le contrôle positif ORACLE tranche
  « banc incapable » vs « pas assez d'épisodes ». Précédent MEM-PERCEPTION : la rétention S'APPREND.
- **Confond d'entraînement sur le contrôle NO-MEMORY** (leçon MEM-PERCEPTION) : découpler le canal encodé de
  la réponse dans NO-MEMORY ; diagnostiquer par le plafond « obs-usage seul ».
- **VACUOUS_ABLATION** (`x_response≈0`) : le reset n'affecte pas `readout_lang` → l'ablation ne mord pas →
  contrôle raté (à attraper au smoke).
- **Coût** : smoke d'abord, run borné FOREGROUND, persister, provenance réelle.
- **Sonde non calibrée = résultat fabriqué** : la calibration (oracle/aléatoire/leaky) est un livrable.
