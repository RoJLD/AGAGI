# E34-IDENTITY-CELL v6.1 — vérification de la table des correctifs contre le commit

- **Cible** : commit `07427edb15dc895bc94750bf9d8713702cf832e1` (parent `2b921f79`, fusion de d1), HEAD du worktree
  `.worktrees/e34` au moment de la vérification ; fichiers testés propres (`git status` vide sur R, C, H,
  `tools/learning_events.py`, TC, TS, TR, `tests/conftest.py`).
- **Table** : `docs/reviews/2026-09-29-E34-IDENTITY-CELL.v6.correctifs.md` (13 lignes), lue au sha.
- **Règle v6.1** : brouillon NON scellé, hors dépôt, `scratchpad/E34-IDENTITY-CELL.v6.1.json` de la session
  5d7a8f62. Première passe sur la version de 10:01 (28 372 octets) ; seconde passe, après correction de l'écart de la
  ligne 12, sur la version RECONSTRUITE au même chemin (28 389 octets, 10:47). Le tableau et les vérifications 1 et 4
  ci-dessous portent sur la version reconstruite ; la sortie recopiée de la vérification 2 est celle de la première passe.
- **Date** : 2026-09-29.
- **Nature** : vérification ciblée par un agent, pas une revue adversariale. Aucun nouveau défaut n'a été cherché ; la
  table est confrontée au diff du commit et au JSON de la règle, puis les tests nommés sont relancés.

Chemins (ceux de la table) : `R` = `tools/evo_runs/e34_identity_cell.py`, `H` = `tools/evo_runs/s2_credit_retention.py`,
`C` = `tools/rng_census.py`, `TC` = `tests/sandbox/test_e34_identity_cell.py`, `TS` = `tests/sandbox/test_e34_slot_identity.py`,
`TR` = `tests/sandbox/test_rng_census.py`. Numéros de ligne : fichier au sha.

## Table confrontée

| # | critique | changement (PRÉSENT/PARTIEL/ABSENT + preuve) | test (EXISTE/ABSENT + assertion citée) |
|---|---|---|---|
| 1 | P1.1 — sens du contrôle positif hérité, jamais mesuré | **PRÉSENT** — règle, `controle_positif` : « t1 est MESURÉ avant le sceau (281, levier 0,86), mais la DIRECTION attendue d'une coupe du crédit à t1 n'est MESURÉE par aucun résultat suivi (revue v6, P1.1) : elle est HÉRITÉE de bras où le crédit n'a jamais agi (a_frozen 31,5 ; b_zero [...]) [...] Prémisse DÉCLARÉE non mesurée : si elle est fausse, NON_MATERIEL devient inatteignable et la sonde rend NON_TRANCHE, jamais un faux verdict. » | déclaration (la table n'annonce aucun test) : vérifiée dans la règle, citation ci-contre |
| 2 | P1.2 — la bande exclut le bruit du monde de phase 2 | **PRÉSENT** — règle, `bande` : « Revue v6, P1.2 (déclaré) : la phase 2 repart de seed_at(2026, 1) dans les QUINZE bras, donc la bande mesure la variabilité des W appris après t1 sous un monde de phase 2 COMMUN ; elle exclut le bruit du monde de phase 2, que la dispersion entre seeds de P4.16 [...] inclut : les deux ne sont pas comparables. » | preuve de code EXISTE : `H:377` `e = _world(seed, 1)` dans `phase2_survive_mortal` (`H:370`), et `H::_world` appelle `seed_at(seed, era)` (`H:71`). H n'est pas touché par le commit (preuve seulement) |
| 3 | P1.3 — plafond de famine lu comme cause de mort | **PRÉSENT** — règle, `plancher` : « Le plafond de famine [...] est un MAJORANT (coût cérébral exclu) : il ne dit PAS la cause de mort (revue v6, P1.3 : aucun résultat ne la publie, et 5 des 12 âges publiés le dépassent) » | déclaration : vérifiée dans la règle |
| 4 | P4.1 — famille de deux tests, un seul taux déclaré | **PRÉSENT** — R, diff : `base["famille"]` publié dès l'entrée avec `materiel_a_tort_h0_borne` 2/14, `controle_positif_passe_par_hasard_borne` 1/14, `non_materiel_a_tort_double_nul_borne` = `K_REPS / ((K_REPS + 3) * (K_REPS + 2))` (12/210) ; `non_materiel_a_tort_double_nul_ex_aequo` ajouté APRÈS le test `dw_distincts` (BANDE_DEGENEREE) ; « why » de NON_MATERIEL : « famille de DEUX tests : NON_MATERIEL à tort sous double nul <= ... (12/210) » ; nouvelle `R::_non_materiel_a_tort_ex_aequo`. Règle : `fausse_alarme_h0` (« FAMILLE de DEUX tests [...] <= 12/210 »), `design` (« une FAMILLE de deux tests de rang contre la même bande »), branche 9c (« la note cite la famille de deux tests et le taux de NON_MATERIEL à tort sous double nul (<= 12/210 [...]) ») | **EXISTE** — `TC:300` `test_verdict_declares_and_publishes_the_family_of_two_tests` : `assert f["non_materiel_a_tort_double_nul_borne"] == pytest.approx(12 / 210)` ; `assert v["verdict"] == "NON_MATERIEL" and "famille de DEUX tests" in v["why"] and "0.057" in v["why"]`. `TC:315` `test_non_materiel_by_chance_rate_has_known_answers` : `R._non_materiel_a_tort_ex_aequo(20.0, 30.0, distinct) == pytest.approx(12 / 210)` ; `(7.0, 9.0, [7.0] * 13) == pytest.approx(14 / 210)` ; `(7.0, 7.0, [7.0] * 13) == 0.0` |
| 5 | P5.1 — contrôle positif réussi par hasard | **PRÉSENT** — idem 4 (borne `controle_positif_passe_par_hasard_borne` = 1/14 dans `famille` ; règle `controle_positif` : « il la dépasse par hasard au plus une fois sur 14 ») | **EXISTE** — idem 4 : `assert f["controle_positif_passe_par_hasard_borne"] == pytest.approx(1 / 14)` |
| 6 | P6.1 — seconde décision aléatoire non comptée | **PRÉSENT** — idem 4 | **EXISTE** — idem 4 |
| 7 | P7.1 — dose de 13 bras non confrontée ; reconstructions de phase 1 non comptées | **PRÉSENT** — R, `run_identity_cell` : `with compter_consensus() as cons, compter_reconstructions() as reco1:` puis `out["reconstructions_phase1"] = dict(reco1)` ; `identity_cell_verdict` : `dose_fausse = [a for a in ARMS if dose[a]["reconstructions_phase1"] != 1 or (a != "pos" and dose[a]["td_updates"] != int(ticks_learn) - 1) or (a in ("on",) + REPS and dose[a]["episode_updates"] != dose["off"]["episode_updates"])]` puis `raise ValueError`. Règle, branche 7 : « un autre bras dont `td_updates` n'est pas ticks_learn - 1, ou (correctif et répliques) dont `episode_updates` diffère du bras éteint ; une population construite plus d'UNE fois en phase 1 » | **EXISTE** — `TC:208` `test_verdict_refuses_a_harness_that_lies`, cas ajoutés `{"on": dict(td=TL - 2)}`, `{"rep_03": dict(td=TL - 2)}`, `{"rep_03": dict(episodes=249)}`, `{"pos": dict(reco1=2)}`, `{"off": dict(reco1=0)}`, assertion `with pytest.raises(ValueError): _v(rows)`. `TC:430` (injection) : `assert on["reconstructions_phase1"] == {"constructions": 0, "B": []}`. `TC:473` (monde réel) : `assert row["reconstructions_phase1"]["constructions"] == 1 and row["reconstructions_phase1"]["B"] == [2]`. `TS:693` : `assert tr["summary"]["episode_updates"] == ref["summary"]["episode_updates"] > 0` ; `TS:616` : `assert fix["summary"]["episode_updates"] == ref["summary"]["episode_updates"]` |
| 8 | P7.2 — `episode_updates` compte des APPELS | **PRÉSENT** — R : `"phase2_episode_calls": _p2(a, "episode_calls")`, plus aucune clé `phase2_episode_updates` ; la clé source existe : `tools/learning_events.py:89` `"episode_calls": int(self.episode_calls)` (publiée par `ev.summary()`, `H:394`). P2.154 inscrit : `PRIORITES_ET_DETTES.md:1762` « P2.154 [...] OUVERTE (2026-09-29, revue v6 [...] P7.2 ». `tools/learning_events.py` non touché (conforme à « NON corrigé »). Règle, `mesure_pre_sceau` (d) : « 1 APPEL épisodique, que tools/learning_events.py compte comme « mise à jour » [...] inscrit en P2.154 ; la sonde publie donc episode_calls en phase 2 » | **EXISTE** — `TC:270` `test_verdict_publishes_doses_per_arm_the_positive_contrast_the_floor_and_the_starvation_ceiling` : `assert v["dose"]["off"]["phase2_episode_calls"] == 1 and "phase2_episode_updates" not in v["dose"]["off"]` |
| 9 | P8.2 — égalité des corps ni gardée ni mesurée | **PRÉSENT** — R : nouvelles `_corps_du_bassin` (`phenotype_of(load_bassin())`) et `body_matches_bassin` (rend `conforme` None si un attribut manque ou n'est pas fini) ; `run_identity_cell` publie `corps_apres_phase1` et `corps_apres_phase2` ; verdict : `corps_faux = [a for a in ARMS if dose[a]["corps_apres_phase1"] is not True or dose[a]["corps_apres_phase2"] is not True]` puis `raise ValueError`. Règle, `mesure` : « le CORPS de chaque agent confronté au corps du bassin (phenotype_of) après chaque phase » ; branche 7 : « le corps d'un agent qui n'est plus celui du bassin après une phase, ou illisible » | **EXISTE** — `TC:337` `test_body_matches_bassin_has_known_answers` : `assert r["conforme"] is False and r["n_ecarts"] == 1 and r["ecart_rel_max"] == pytest.approx(0.01)` ; `assert R.body_matches_bassin([ag(), NS()], want)["conforme"] is None`. `TC:208` cas `{"rep_04": dict(corps2=False)}` et `{"on": dict(corps1=None)}` sous `pytest.raises(ValueError)`. `TC:473` (monde réel) : `assert row["corps_apres_phase1"]["conforme"] is True and row["corps_apres_phase2"]["conforme"] is True` |
| 10 | P10.1 — coupe de la phase B hors de l'évidence suivie | **PRÉSENT** — R, `_lire` (`R:499-500`) : `p_coupe = os.path.join(_cells_dir(smoke), "_coupe.json")` puis `coupe = json.load(...)`, transmis `identity_cell_verdict(..., coupe=coupe)` ; INCOMPLET : « la phase B a été COUPÉE au plafond ({coupe.get('mur_s')} s de mur, charge {coupe.get('charge')}) » ; `coupe` publié dans `base`. L'écriture de `_coupe.json` (`R:573`) préexistait. Règle, branche 3 : « une coupe au plafond PENDANT la phase B (_coupe.json) est relue et NOMMÉE avec son mur et sa charge (revue v6, P10.1) » | **EXISTE** — `TC:325` `test_verdict_INCOMPLET_names_a_persisted_budget_cut` : `assert v["verdict"] == "INCOMPLET" and "COUPÉE au plafond" in v["why"] and "10812.0" in v["why"]` ; sans coupe : `assert "une cellule manque" in [...]["why"]` |
| 11 | P10.2 — le recensement compte des appels, pas des tirages | **PRÉSENT** — C, `resume()` : `"appels_avant"` et `"appels_apres"` remplacent `tirages_*` ; docstring : « L'unité est l'APPEL, pas la valeur tirée (revue E34 v6, P10.2) ». R : `"rng_appels_apres_t1": _rng(a, "appels_apres")`. Aucune clé `tirages_avant`, `tirages_apres` ni `rng_tirages` restante dans R, C ou H au sha (grep : 0). Règle, `mesure_pre_sceau` (c) : « 164 345 APPELS (un appel peut tirer plusieurs valeurs [...] revue v6, P10.2) » ; `t1_repliques_et_controle` : « l'unité du recensement est l'APPEL, pas la valeur tirée : revue v6, P10.2 » | **EXISTE** — `TR:41` `test_the_unit_is_the_CALL_not_the_drawn_value` : `np.random.uniform(0, 1, size=4)` et `np.random.randint(0, 10, 2)` puis `assert rec.resume()["appels_apres"] == 2` |
| 12 | P10.3 — empreinte 94e779e8 non rejouable depuis l'arbre | **PRÉSENT** (règle reconstruite) — l'affirmation de certification est retirée et remplacée dans `mesure` : « revue v6 P10.3 : l'empreinte de trace locale que citait la v6 n'est pas rejouable depuis l'arbre et n'est plus citée — c'est le témoin de phase A qui certifie le chemin, au bit et à pleine échelle » ; la copie verbatim gelée (sha 5d534d44, TS) y est citée. Le hash n'y figure plus. En première passe : PARTIEL (voir « Écart corrigé avant le sceau ») | preuve annoncée **TENUE** — `grep -o 94e779e8` sur la règle reconstruite rend **0** occurrence ; le même motif de hash, validé sur un cas positif connu, trouve bien `5d534d44` (1 occurrence) (voir vérification 1 ci-dessous) |
| 13 | P10.4 — LIEU_MIXTE compare six clés, la branche en nommait trois | **PRÉSENT** — règle, branche 5 : « les SIX clés de lieu() : plateforme, version de python, version de torch, nombre de threads torch, AGAGI_CPU_LIMIT, AGAGI_IMAGE — revue v6, P10.4 » ; R, « why » de LIEU_MIXTE : « les six clés de `lieu` : plateforme, python, torch, threads torch, AGAGI_CPU_LIMIT, AGAGI_IMAGE » ; ces six clés sont bien celles de `R::lieu` (`R:123-124`) ; code de comparaison inchangé (`json.dumps(r.get("lieu"), sort_keys=True)`) | **EXISTE** (préexistant) — `TC:166` `test_verdict_LIEU_MIXTE_when_the_cells_come_from_two_places` : `assert _v(_rows(rep_03=_rep(8.0, 3, lieu=dict(LIEU, torch_threads=2))))["verdict"] == "LIEU_MIXTE"`. Il exerce la branche, pas le nouveau libellé du « why » (ce que la table n'annonçait pas) |

Bilan (règle reconstruite) : 13 PRÉSENT, 0 PARTIEL, 0 ABSENT. Tous les tests nommés existent sous leur nom au sha.
En première passe : 12 PRÉSENT, 1 PARTIEL (ligne 12).

**Écart corrigé avant le sceau** — ligne 12 (P10.3). Première passe (règle de 10:01, 28 372 octets) : la table donnait
pour preuve « aucune occurrence de 94e779e8 dans la règle v6.1 », et la règle en portait 1, dans la phrase même du champ
`mesure` qui annonçait que l'empreinte « n'est plus citée » ; ligne classée PARTIEL. Correction par le coordinateur : la
phrase dit désormais « l'empreinte de trace locale que citait la v6 n'est pas rejouable depuis l'arbre et n'est plus
citée ». Seconde passe (règle reconstruite au même chemin, 10:47, 28 389 octets) : 0 occurrence. Le commit 07427edb n'a
pas changé (HEAD du worktree relu : `07427edb15dc895bc94750bf9d8713702cf832e1`), donc les tests n'ont pas été relancés.
L'écart de taille, +17 octets, est exactement celui du remplacement de « l'empreinte locale 94e779e8 » (27 caractères)
par « l'empreinte de trace locale que citait la v6 » (44 caractères). C'est compatible avec « rien d'autre n'a bougé »,
sans le prouver : l'ancienne version n'a pas été conservée pour un diff. Les motifs cités par les lignes 1 à 13 ont
été retrouvés dans la version reconstruite (vérification 4 ci-dessous).

## Tests relancés

Avant le lancement, `python -m tools.jobs.doctor` depuis la racine du worktree :

```
bails : 0 vivant(s), 0 expiré(s) à détenteur VIVANT, 0 orphelin(s)

processus python du projet (hors moi et mes ancêtres) : 0
```

Commande (bail kuzu tenu par le parent, chaque fichier séparément, P2.142) :
`python .../scratchpad/e34_v6_tests.py "C:/Users/robla/VScode_Project/AGAGI/.worktrees/e34" tests/sandbox/test_e34_identity_cell.py tests/sandbox/test_e34_slot_identity.py tests/sandbox/test_rng_census.py` — code de sortie 0.

Lignes de résumé, recopiées telles quelles :

```
tests/sandbox/test_e34_identity_cell.py rc=0 :: 53 passed in 8.98s
tests/sandbox/test_e34_slot_identity.py rc=0 :: 42 passed in 30.25s
tests/sandbox/test_rng_census.py rc=0 :: 8 passed in 3.17s
```

0 sauté, 0 échoué dans les trois fichiers ; les comptes (53, 42, 8) sont ceux qu'annonce le message du commit.

## Vérifications en une commande

1. Occurrences de « 94e779e8 » dans la règle v6.1 reconstruite (10:47, 28 389 octets) — `grep -o 94e779e8 <règle v6.1> | wc -l`, avec le même motif validé sur un hash connu présent :

   ```
   occurrences 94e779e8 : 0
   validation du motif sur un cas positif connu (5d534d44) : 1
   ```

   Nouvelle phrase du champ `mesure` : « revue v6 P10.3 : l'empreinte de trace locale que citait la v6 n'est pas
   rejouable depuis l'arbre et n'est plus citée — c'est le témoin de phase A qui certifie le chemin, au bit et [...] ».
   **Attendu : 0. Obtenu : 0.** Première passe, sur la règle de 10:01 : 1 occurrence (voir « Écart corrigé avant le
   sceau »).

2. Le champ `fausse_alarme_h0` nomme 12/210 et « DEUX tests ». Première passe : `python -c` qui charge la règle et teste
   `'12/210' in f` et `'DEUX tests' in f` ; seconde passe, sur la règle reconstruite : couvert par la vérification 4
   (motifs « FAMILLE de DEUX tests » et « 12/210 » de `fausse_alarme_h0`, 5/5 retrouvés). Sortie de la première passe :

   ```
   12/210 : True ; DEUX tests : True
   ```

3. Fichiers touchés — `git show 07427edb15dc895bc94750bf9d8713702cf832e1 --stat --format=` :

   ```
    docs/REF/REGISTRE_ERREURS.md                       |  10 +-
    .../2026-09-29-E34-IDENTITY-CELL.v6.correctifs.md  |  32 +++
    docs/reviews/2026-09-29-E34-IDENTITY-CELL.v6.md    | 293 +++++++++++++++++++++
    docs/roadmap/PRIORITES_ET_DETTES.md                |  20 +-
    tests/sandbox/test_e34_identity_cell.py            |  87 +++++-
    tests/sandbox/test_e34_slot_identity.py            |  12 +-
    tests/sandbox/test_instrument_calibration.py       |  17 +-
    tests/sandbox/test_rng_census.py                   |  21 +-
    tools/evo_runs/e34_identity_cell.py                | 131 +++++++--
    tools/rng_census.py                                |   8 +-
    10 files changed, 583 insertions(+), 48 deletions(-)
   ```

   Aucun fichier hors périmètre : R, C, TC, TS, TR (nommés par la table), plus backlog, registre, deux revues sous
   `docs/reviews/` et `tests/sandbox/test_instrument_calibration.py` (déclarations de calibration). H, nommé par la table
   comme preuve de code seulement, n'est pas touché.

4. Champs cités toujours présents dans la règle reconstruite. Le script `scratchpad/e34_v61_champs.py`, lancé en une
   commande sur le JSON, cherche dans chaque champ les phrases citées plus haut (lignes 1, 2, 3, 4 et 13 demandées ; les
   autres lignes vérifiées en même temps) :

   ```
   ligne    1 | controle_positif         | 4/4 motifs
   ligne    2 | bande                    | 3/3 motifs
   ligne    3 | plancher                 | 3/3 motifs
   ligne    4 | fausse_alarme_h0         | 5/5 motifs
   ligne    4 | design                   | 1/1 motifs
   ligne    4 | branche 9c               | 2/2 motifs
   ligne    5 | controle_positif         | 1/1 motifs
   ligne  7/9 | branche 7                | 3/3 motifs
   ligne 8/11 | mesure_pre_sceau         | 4/4 motifs
   ligne    9 | mesure                   | 1/1 motifs
   ligne   10 | branche 3                | 2/2 motifs
   ligne   11 | t1_repliques_et_controle | 1/1 motifs
   ligne   12 | mesure                   | 3/3 motifs
   ligne   13 | branche 5                | 4/4 motifs
   TOTAL motifs absents : 0
   ```

Conclusion : CONFORME (13/13 présents, tests verts : 53 + 42 + 8 passés, 0 sauté, 0 échoué ; l'écart de la ligne 12 trouvé en première passe est corrigé dans la règle v6.1 reconstruite avant le sceau, 0 occurrence de 94e779e8 ; le commit ne touche aucun fichier hors périmètre).

## v6.2 — vérification ciblée de la ligne E19 (2026-10-13)

Objet : la v6.2, NON committée, posée sur HEAD 3d044c06 (worktree .worktrees/e34, branche tmp/e34). La chaîne « why » du
verdict NON_MATERIEL doit porter « au pas publié, invariance au pas non éprouvée (E19) », et le test
test_verdict_NON_MATERIEL_is_upward_only_and_cites_the_cell_and_both_doses doit l'exiger. Contexte (décision de Master 2) :
la porte 23 classe la règle « indéterminée » (un seul pas, déclaré en prose) ; la règle est gelée EN CONNAISSANCE et la v6.2
fait dire cette portée au verdict lui-même.

### 1. Le diff ne contient que l'insertion et l'assertion

Commande : git diff -- tools/evo_runs/e34_identity_cell.py tests/sandbox/test_e34_identity_cell.py (HEAD = 3d044c06).

```
--- a/tests/sandbox/test_e34_identity_cell.py
+++ b/tests/sandbox/test_e34_identity_cell.py
@@ -295,6 +295,8 @@ def test_verdict_NON_MATERIEL_is_upward_only_and_cites_the_cell_and_both_doses()
     v = _v(s_on=7.5, s_pos=20.0)
     assert v["verdict"] == "NON_MATERIEL" and "CETTE cellule" in v["why"] and "vers le HAUT" in v["why"]
     assert "40 commutations" in v["why"] and "30 lignes réindexées" in v["why"] and "vers le BAS, non éprouvé" in v["why"]
+    # v6.2 (porte 23, gel EN CONNAISSANCE décidé par Master 2) : un nul à UN seul pas le dit dans la chaîne rendue
+    assert "au pas publié, invariance au pas non éprouvée (E19)" in v["why"]

--- a/tools/evo_runs/e34_identity_cell.py
+++ b/tools/evo_runs/e34_identity_cell.py
@@ -432,7 +432,8 @@ def identity_cell_verdict(rows, witness, s_frozen, ticks_learn, band_publiee=Non
-                        "; vers le BAS, non éprouvé (plancher) ; famille de DEUX tests : NON_MATERIEL à tort sous double "
+                        "; vers le BAS, non éprouvé (plancher) ; au pas publié, invariance au pas non éprouvée (E19) "
+                        "; famille de DEUX tests : NON_MATERIEL à tort sous double "
```

Lecture : un seul hunk par fichier. Côté code, le littéral est coupé en deux littéraux concaténés implicitement ; le texte
rendu est celui d'avant, avec « ; au pas publié, invariance au pas non éprouvée (E19) » inséré entre « (plancher) » et
« ; famille de DEUX tests ». Aucune condition, aucun seuil, aucune valeur rendue autre que la chaîne « why » n'est touché.
Côté test, deux lignes ajoutées (un commentaire et une assertion), rien de retiré.

### 2. La chaîne est absente de HEAD et présente sur le disque

```
HEAD src  (git show HEAD:tools/evo_runs/e34_identity_cell.py | grep -c "invariance au pas non éprouvée") : 0
DISK src  (grep -c ... tools/evo_runs/e34_identity_cell.py)                                            : 1
HEAD test (git show HEAD:tests/sandbox/test_e34_identity_cell.py | grep -c ...)                        : 0
DISK test (grep -c ... tests/sandbox/test_e34_identity_cell.py)                                       : 1
contrôle du canal accentué (git show HEAD:... e34_identity_cell.py | grep -c "vers le BAS, non éprouvé") : 1
```

Le motif est validé sur deux cas positifs connus : le même grep rend 1 sur le disque, et un motif accentué de même forme
(« vers le BAS, non éprouvé ») rend 1 sur HEAD, donc le 0 de HEAD n'est pas un artefact d'encodage du canal
git show vers grep. Conséquence (déduite, non rejouée sur HEAD) : sans la ligne de code, la chaîne « why » ne contient
pas la phrase, et la nouvelle assertion du test échoue. Le test discrimine.

### 3. Tests sous le bail kuzu, interpréteur 3.13

Avant le lancement, python -m tools.jobs.doctor (lecture seule) :

```
bails : 0 vivant(s), 0 expiré(s) à détenteur VIVANT, 0 orphelin(s)

processus python du projet (hors moi et mes ancêtres) : 0
```

Aucun bail kuzu vivant : lancement autorisé. Le script prend lui-même le bail (hold("kuzu", owner="e34-v6-tests")).

```
interpréteur : C:\Users\robla\AppData\Local\Programs\Python\Python313\python.exe (python 3.13.12)
tests/sandbox/test_e34_identity_cell.py rc=0 :: 53 passed in 10.56s
exit=0
```

Conclusion v6.2 : CONFORME (diff limité à l'insertion E19 dans le « why » de NON_MATERIEL et à son assertion ; phrase 0 sur HEAD, 1 sur le disque, motif validé sur un cas positif ; 53 passés, 0 échoué sous bail kuzu, python 3.13.12 ; rien committé).
