# Handoff — résiduel d'hygiène du graphe de records (19 orphelins hors périmètre)

**Contexte.** La dé-orphanisation du legacy prose `001–104` est terminée (90/109 orphelins nettoyés, →19 ;
voir `RECORDS_HYGIENE_AND_GATES.md`). Les **19 orphelins restants sont hors du périmètre « mon poste »** : ils
touchent soit des collisions (décision robla + balayage de références), soit des records récents authored par
d'autres sessions //. Cette note liste **précisément quoi faire pour chacun**. Après correction, le graphe
tombe à ~0 orphelin.

**Après TOUTE correction** : `python tools/check_record_links.py --report` (doit montrer 0 orphelin/collision
restant) puis `python tools/check_record_links.py --update-baseline` (rétrécit la dette gelée) ; vérifier
`python tools/consolidate_records.py` (doit rester `problemes=0`).

---

## A. Collisions d'ID (5) — décision **robla** + balayage de références

Chaque numéro porte **deux EDR distincts**. Garder l'un, renuméroter l'autre vers un numéro libre, PUIS
corriger toutes les références (autres EDR, mémoire, PR, `results/`). Numéros libres (à re-vérifier libres
avant usage) : **106, 107, 110, 114, 123, 124, 127, 128, 131, 132, 133, 136, 142**.

| id | fichier A (garder ?) | fichier B (renuméroter ?) | cible proposée B |
|---|---|---|---|
| EDR-093 | `093_No_Income_Rung_The_Wall_Is_Action_Spending.md` | `093_Planning_Organ_Not_Dead_Weak_Underpowered_Revival_At_Sweet_Spot.md` | → **EDR-106** (G4 : planning) |
| EDR-094 | `094_Intrinsic_Wall_Survival_Is_Apex_Independent.md` | `094_Dream_Distress_Median_Washout_Dreaming_Is_A_Minority_Behavior.md` | → **EDR-107** (G4 : dreaming) |
| EDR-100 | `100_Champion_Deficit_Is_Monoculture_...md` | `100_Biology_Drain_Is_Evolved_Phenotype_Metabolism.md` | → **EDR-110** (foundational : énergie) |
| EDR-105 | `105_Topological_Growth_Does_Not_Lift_Apex_...md` | `105_Forage_Bottleneck_Is_Approach_Not_Capture_...md` | → **EDR-114** (foundational : forage) |
| EDR-135 | `135_Anticipation_G_Inert_InWorld_..._G4.md` | `135_LegacyCore_Control_Refutes_Organ_...md` | → **EDR-123** (foundational : learning rule) |

**Bonus G4** : 093/094 (twins planning/dreaming) portent les EDR d'anticipation → une fois dé-collisionnés et
raccordés `gate: G4`, ils remontent **G4 de 2 à ~4** (G4 est la porte la plus mince).

**Procédure par collision** (ex. B = 093_Planning...):
1. `git mv docs/EDR/093_Planning_Organ_Not_Dead_....md docs/EDR/106_Planning_Organ_Not_Dead_....md`
2. Corriger l'entête `# EDR 093 :` → `# EDR 106 :` dans le fichier ; ajouter/corriger `id: EDR-106` si frontmatter.
3. Balayer les références : `grep -rn "093" docs/ results/ src/ | grep -i planning` (et la mémoire projet).
4. Ajouter le frontmatter de raccordement (`gate:`/`tests:`) comme en B ci-dessous.
5. `python tools/check_record_links.py --update-baseline`.

> ⚠️ Le choix « garder A / renuméroter B » ci-dessus est une **proposition** (le twin le plus référencé devrait
> garder le numéro). À confirmer par robla avant `git mv`.

---

## B. Records récents orphelins (12) — **leurs sessions propriétaires**

Ces records (lignes compositionnelle-binding + torch in-world) sont authored par d'autres sessions //. La
remédiation est **quasi triviale** — la plupart ont déjà un frontmatter avec `gate: null` : il suffit de le
renseigner. Gate suggéré (à confirmer par l'auteur) : la majorité relève de **G2** (composition/binding).

| id | fichier | état | remédiation | gate suggéré |
|---|---|---|---|---|
| 109 | `109_Behavioral_Diversity_Confirms_Issue2_...` | **prose** (pas de frontmatter) | ajouter frontmatter complet | G2 (ou foundational) |
| 113 | `113_gamma_sweep_horizon_credit_no_op_issue2` | **prose** | ajouter frontmatter complet | G2 (ou foundational) |
| 117 | `117_Compositional_Learnability_Both_Fail_...` | `gate: null` | renseigner `gate:` | **G2** |
| 119 | `119_Hidden_Size_Sweep_Compositional_Not_Size` | `gate: null` | renseigner `gate:` | **G2** |
| 120 | `120_Compositional_Memory_Probe_...` | `gate: null` | renseigner `gate:` | **G2** |
| 122 | `122_Compositional_Curriculum_Discovery_...Legacy` | **YAML CASSÉ** (P2) | **quoter le `title:`** puis `gate:` | **G2** |
| 125 | `125_Compositional_Fade_Joint_Ceiling_...` | `gate: null` | renseigner `gate:` | **G2** |
| 163 | `163_Torch_InWorld_Integration_..._Neutral_...` | `gate: null` | renseigner `gate:` | G2/G3 (binding in-world) |
| 166 | `166_Gate_Persist_Across_Rebuild_Neutral_...` | `gate: null` | renseigner `gate:` | G2/G3 |
| 169 | `169_Binary_Gate_Mechanism_Trainable_...` | `gate: null` | renseigner `gate:` | G2/G3 |
| 171 | `171_Binary_Gate_Routes_Present_Context_...` | `gate: null` | renseigner `gate:` | G2/G3 |
| 172 | `172_Throw_Gate_Wired_Inworld_But_Substrate_...` | `gate: null` | renseigner `gate:` | G2/G3 |

**Fix `gate: null` (9 records)** : remplacer la ligne `gate: null` par `gate: G2` (ou la porte adéquate). 1 ligne.
**Fix prose (109, 113)** : préfixer le même bloc frontmatter que le legacy (voir `docs/EDR/README.md` §Règle).
**Fix 122 (P2)** : le `title:` contient un `:` non quoté (`SPLIT par substrat : DISCOVERY…`) → l'entourer de
guillemets doubles, PUIS renseigner `gate:`. Supprime le WARN récurrent de `consolidate_records.py`.

---

## C. ADR-002 (1)

`docs/ADR/002_preserve_dims_default_on.md` est orphelin (aucun EDR ne le déclenche). Deux options :
- **Recommandé** : ajouter `triggers: [ADR-002]` au frontmatter de l'EDR qui a décidé le défaut `preserve_dims`
  (ligne from-genome, PR #55/#58) → crée l'arête DECLENCHE.
- **Alternative** : ajouter `gate: foundational` au frontmatter de l'ADR (le validateur le tolère alors).

---

## Récap

| Bloc | Nombre | Propriétaire | Coût |
|---|---|---|---|
| A. Collisions | 5 ids (6 fichiers) | **robla** (décision + refs) | moyen |
| B. Records récents | 12 | **sessions //** | trivial (9× 1 ligne, 2× frontmatter, 1× YAML) |
| C. ADR | 1 | from-genome / robla | trivial |

Une fois A+B+C faits : `--update-baseline` → **0 orphelin, 0 collision**, la règle à cliquet garde le graphe
propre pour toujours.
