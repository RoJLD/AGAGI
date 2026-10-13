# E34-IDENTITY-CELL v6 → v6.1 — table des correctifs de la revue v6

- **Revue** : `docs/reviews/2026-09-29-E34-IDENTITY-CELL.v6.md` (34 critiques, 13 confirmées).
- **Classement** : NON bloquant, confirmé par Master 2 le 2026-09-29. La règle d'arrêt déposée avant la revue
  (Avancement de P2.132) n'est donc pas déclenchée. La v6.1 ne change ni les bras, ni la bande, ni la décision MATERIEL ;
  elle déclare, garde et publie.
- **Témoins de la revue v6** : 3 défauts connus retrouvés sur 3, plancher de fausses retrouvailles 0/5, **INDISCRIMINANT**
  (le témoin cru sain rend 7 critiques recevables, autant que le moins noté des défectueux). Lecture de Master 2, écrite
  telle quelle : l'indiscrimination porte sur la SPÉCIFICITÉ (le sain reçoit des critiques), la SENSIBILITÉ tient (3/3) ;
  un « rien de bloquant » reste informatif, les 13 confirmées pèsent moins.
- **Vérification** : un agent, pas une revue, confronte cette table au diff du commit v6.1 et lance les tests nommés, avant
  le sceau (`docs/reviews/2026-09-29-E34-IDENTITY-CELL.v6.verification.md`).

Chemins : `R` = `tools/evo_runs/e34_identity_cell.py`, `H` = `tools/evo_runs/s2_credit_retention.py`,
`C` = `tools/rng_census.py`, `TC` = `tests/sandbox/test_e34_identity_cell.py`, `TS` = `tests/sandbox/test_e34_slot_identity.py`,
`TR` = `tests/sandbox/test_rng_census.py`, règle = `E34-IDENTITY-CELL` v6.1 (scellée après la vérification).

| # | critique confirmée (revue v6) | classe | changement | test ou preuve |
|---|---|---|---|---|
| 1 | P1.1 — le sens du contrôle positif à t1 est hérité, jamais mesuré | E8 (occ. 8) | règle, champ `controle_positif` : t1 = 281 cité comme MESURÉ ; la direction est une prémisse DÉCLARÉE non mesurée, héritée de a_frozen / b_zero ; si elle est fausse, NON_TRANCHE, jamais un faux verdict | déclaration (pas de code) ; vérifiable dans la règle |
| 2 | P1.2 — la bande exclut le bruit du monde de phase 2 | E35 (inscription laissée à agagi-32) | règle, champ `bande` : la phase 2 repart de `seed_at(2026, 1)` dans les quinze bras ; la bande mesure les W appris sous un monde de phase 2 COMMUN, non comparable à la dispersion entre seeds | déclaration ; preuve de code : `H::phase2_survive_mortal` → `_world(seed, 1)` |
| 3 | P1.3 — le plafond de famine lu comme une cause de mort | E8 | règle, champ `plancher` : MAJORANT (coût cérébral exclu), ne dit pas la cause (5 âges sur 12 le dépassent) | déclaration |
| 4 | P4.1 — famille de deux tests, un seul taux déclaré | E23 (5) | `R::identity_cell_verdict` : `famille` (trois bornes : 2/14, 1/14, 12/210) publiée dès l'entrée, `non_materiel_a_tort_double_nul_ex_aequo` publié APRÈS BANDE_DEGENEREE, cité dans le « why » de NON_MATERIEL ; `R::_non_materiel_a_tort_ex_aequo` ; règle : `fausse_alarme_h0`, `design`, branche 9c | `TC::test_verdict_declares_and_publishes_the_family_of_two_tests`, `TC::test_non_materiel_by_chance_rate_has_known_answers` (12/210 exact, 14/210 et 0 sur ex-aequo connus) |
| 5 | P5.1 — contrôle positif réussi par hasard | E23 (5) | idem 4 | idem 4 |
| 6 | P6.1 — seconde décision aléatoire non comptée | E23 (5) | idem 4 | idem 4 |
| 7 | P7.1 — dose de 13 bras non confrontée ; reconstructions de phase 1 non comptées | E8 (occ. 8) | `R::run_identity_cell` : `compter_reconstructions` en phase 1 (`reconstructions_phase1`) ; `R::identity_cell_verdict` LÈVE si une construction de phase 1 ≠ 1, si `td_updates` ≠ ticks_learn − 1 hors contrôle positif, si l'épisodique du correctif ou d'une réplique ≠ bras éteint ; règle, branche 7 | `TC::test_verdict_refuses_a_harness_that_lies` (cas `on`/`rep_03` td, `rep_03` épisodes, `pos` reco1 = 2, `off` reco1 = 0) ; `TC::test_run_identity_cell_passes_the_arm_treatment_the_census_and_the_phase2_dose` ; `TC::test_run_identity_cell_real_world_minimal_publishes_the_audit_the_census_and_the_phase2_dose` (1 construction réelle) ; égalité de dose en monde réel : `TS::test_real_world_reseeded_replicas_diverge_from_off_and_from_each_other`, `TS::test_with_a_head_death_the_reindex_fix_changes_what_is_learned` |
| 8 | P7.2 — `episode_updates` compte des APPELS | aucune (instrument partagé) | la dose de phase 2 est publiée sous `phase2_episode_calls` ; le défaut de `tools/learning_events.py` (`:16` contre `:186`) est inscrit en **P2.154**, NON corrigé ici (classement Master 2) ; règle, `mesure_pre_sceau` (d) | `TC::test_verdict_publishes_doses_per_arm_the_positive_contrast_the_floor_and_the_starvation_ceiling` (`phase2_episode_calls`, aucune `phase2_episode_updates`) |
| 9 | P8.2 — égalité des corps ni gardée ni mesurée | E26 | `R::body_matches_bassin`, `R::_corps_du_bassin` ; `R::run_identity_cell` publie `corps_apres_phase1` / `corps_apres_phase2` ; le verdict LÈVE sur un corps non conforme ou illisible ; règle, `mesure` et branche 7 | `TC::test_body_matches_bassin_has_known_answers` ; `TC::test_verdict_refuses_a_harness_that_lies` (`rep_04` corps2 faux, `on` corps1 illisible) ; conformité en monde réel dans le test minimal |
| 10 | P10.1 — coupe de la phase B hors de l'évidence suivie | E13 | `R::_lire` relit `_coupe.json` ; `R::identity_cell_verdict(coupe=)` : INCOMPLET NOMME la coupe, son mur et sa charge ; règle, branche 3 | `TC::test_verdict_INCOMPLET_names_a_persisted_budget_cut` |
| 11 | P10.2 — le recensement compte des appels, pas des tirages | aucune | `C` : clés `appels_avant` / `appels_apres`, docstring ; `R` : `rng_appels_apres_t1` ; règle, `mesure_pre_sceau` (c) et `t1_repliques_et_controle` | `TR::test_the_unit_is_the_CALL_not_the_drawn_value` |
| 12 | P10.3 — empreinte 94e779e8 non rejouable depuis l'arbre | E10 | l'affirmation est RETIRÉE de la règle (champ `mesure`) ; le chemin par défaut y est certifié par la copie verbatim gelée des tests et par le témoin de phase A | déclaration ; vérifiable : aucune occurrence de 94e779e8 dans la règle v6.1 |
| 13 | P10.4 — LIEU_MIXTE compare six clés, la branche en nommait trois | aucune | règle, branche 5 : les SIX clés de `lieu()` ; « why » de LIEU_MIXTE les nomme ; code de comparaison inchangé | `TC::test_verdict_LIEU_MIXTE_when_the_cells_come_from_two_places` (existant) |
