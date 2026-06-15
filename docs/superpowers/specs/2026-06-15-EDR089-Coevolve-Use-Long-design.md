# Design EDR 089 — « L'usage co-évolué du langage paye-t-il sur substrat à survie LONGUE ? » (pré-enregistrement)

> Spec de conception **et pré-enregistrement**. Power EDR 083 sur le levier #1 qu'il diagnostique
> lui-même : la **survie longue**. Issu de l'enchaînement 082 (imposer l'usage échoue) → 083 (co-évoluer
> l'usage : +0.29 sous 2 SE, sur substrat court, survivants=0) → 088 (le *contenu* ne paye pas même
> content-critique → re-pointe vers la *sélection de l'usage*). Brainstorm 2026-06-15. Commandement 15.
>
> **Pré-enregistrement** : métrique, R, gens, seuils, règle de décision **figés avant tout run**. Le
> verdict ne lira QUE ce fichier. Déviation post-hoc = EDR séparé.

## 1. Question & hypothèse

**Question** : quand les auditeurs **évoluent** à écouter (`in_hear`→action, *non imposé*, vs 082) sur un
substrat où ils **survivent assez longtemps** pour que la coordination paye, le signal **FIABLE** est-il
sélectionné — c.-à-d. la chasse évolue-t-elle mieux qu'avec un locuteur **BRUITÉ** ?

EDR 083 (powered R=4) : FIABLE−BRUITÉ = **+0.29 ± 0.65 SE** (sous 2 SE, 75 % des runs positifs) — sur le
substrat **par défaut** (`WorldConfig()`), où la survie est courte (survivants=0). Son propre diagnostic :
*« le goulot n'est plus le code ni la compétence, mais la durée de vie + l'intensité de sélection de
l'usage »*. EDR 085 a livré un **sweet-spot d'énergie** → survie longue, **jamais croisé avec la
co-évolution de l'usage** (087 testait le *contenu* sur substrat long ; 083 l'*usage* sur substrat court).

**Hypothèse (figée, directionnelle)** : sur le sweet-spot (nuit OFF), avec R≥8 répétitions appariées et
plus de générations, **FIABLE − BRUITÉ > 0 robustement** (Wilcoxon apparié, IC borne_inf > 0). La survie
longue déverrouille l'effet directionnel d'083.

> **Réfutabilité** : si l'effet reste sous le seuil même à survie longue, la survie n'était PAS le
> verrou → le goulot est la **sélection explicite de l'usage** (levier #2, EDR séparé), ou le langage
> fonctionnel n'émerge pas dans ce substrat (négatif robuste qui *consolide* 057/075/077/082/083/087/088).

## 2. La manipulation (1 variable principale vs 083)

Réutilise le moteur de co-évolution d'`tools/coevolve_language.py` (migré/apparié en D1) +
`_run_era_lewis` (`tools/lang_on_competent.py`). **Seul changement structurant vs 083 = le substrat.**

| | 083 | **089** |
|---|---|---|
| substrat | `WorldConfig()` défaut (survie courte) | **sweet-spot 085** : `base_metabolism=0.25`, `forage_payoff=3.0`, **`night_enabled=False`** |
| R (puissance) | 4 | **≥8** (figé post-pilote) |
| générations | 15 | **20** |
| num_agents / K | 24 / 4 | 24 / 4 (inchangé) |

Le **contraste mesuré** (FIABLE = têtes co-entraînées → `in_hear` cohérent ; BRUITÉ = connectome →
`in_hear` loterie) est **identique à 083** ; seul le substrat change. `decode_act=False` dans les deux
bras (l'usage **émerge**, n'est pas imposé — la distinction clé vs 082).

> **Nuit OFF** : impératif (087/086) — sinon drain nocturne ×2.5 → régime létal qui re-courcirait la
> survie et invaliderait le test (le verrou qu'on lève).

## 3. Métrique & appariement

- **Primaire** : **Mammouths tués** par les champions évolués (moyenne sur `n_eval` ères propres) —
  **continuité stricte avec 083** → le +0.29 est directement comparable.
- **Secondaires (diagnostic)** : **net = kills − leurre_hits** (leçon 088 : l'évitement fait partie de
  l'usage) ; **survie** (`ticks`/`survivants` — `_run_era_lewis` les expose) pour vérifier le gate.
- **Apparié** : à la répétition `r`, FIABLE et BRUITÉ co-évoluent sous le **même seed de base** (via
  `Harness`/`seed_at`, frontières disjointes par bras) → même séquence de mondes. Différence appariée
  `d_r = kills_FIABLE(r) − kills_BRUITÉ(r)`.

## 4. Protocole statistique (pré-enregistré, réutilise `src/seed_ai/exp_stats.py`)

- `{d_r}` sur R≥8 répétitions → **Wilcoxon signed-rank apparié** (`exp_stats.wilcoxon_signed_rank`) +
  moyenne ± SE + win-rate (`paired_summary`) + **IC95 bootstrap** (`bootstrap_ci`, seedé).
- *« Welch » banni* (cohérent S2/088). Le test primaire = Wilcoxon apparié sur la métrique Mammouths.
- **Gate de validité (figé)** : survie médiane des champions évolués **> 120 ticks** sur les ères de
  mesure (substrat réellement long). Échec → **VOID** (≠ négatif ; re-régler le substrat).

## 5. Table de décision (3 issues figées)

1. **USAGE SÉLECTIONNÉ (083 résolu en positif)** : Wilcoxon p<0.05 **ET** médiane(d)>0 **ET** IC95
   borne_inf > 0. → *écouter un signal fiable est sélectionné quand la survie est longue ; le langage
   fonctionnel émerge sous sélection (la vraie réponse à 053/082).*
2. **NÉGATIF ROBUSTE** : d≈0 / IC inclut 0 même à survie longue (gate survie OK). → *la survie n'était
   pas le verrou ; le goulot est la sélection EXPLICITE de l'usage (levier #2) — ou le langage
   fonctionnel n'émerge pas ici. Consolide la série de négatifs.*
3. **VOID** : gate survie échoue (<120) → substrat pas assez long ; re-régler (énergie), ce n'est pas un
   résultat sur l'hypothèse.

## 6. Implémentation & architecture

- **Nouveau tool** `tools/coevolve_use_long.py` — **n'altère pas** `coevolve_language.py` (artefact 083).
  Réutilise/importe ses fonctions feuilles (`coevolve`, `_measure`) + `_run_era_lewis` + `new_head`/
  `train_population` + `_load_champions`/`_reproduce`. Ajoute : un **cfg sweet-spot** (+ nuit OFF), la
  **boucle R appariée** (FIABLE et BRUITÉ au même seed par répétition), l'appel à `exp_stats`, et
  `Harness` (provenance, `with_db=False`).
- Si une fonction feuille de `coevolve_language` est devenue privée/incompatible après la migration D1,
  la **copier** dans le nouveau tool plutôt que d'altérer 083 (isolation).
- Sortie : `Harness.save` → `results/coevolve_use_long_<seed>.json` (seed, commit, hash champion, R, par
  répétition : kills/net/survie FIABLE & BRUITÉ, `d_r`, Wilcoxon, IC, verdict) + **EDR 089**.

## 7. Compute & exécution

- ⚠️ **Le plus lourd de la session.** Par répétition : 2 co-évolutions × 20 gens × (1 ère + K=4 ré-évals)
  + 2 mesures × `n_eval` ères, le tout en biosphère. × R≥8.
- **Pilote R=3 d'abord** → estimer `std(d_r)` ET le **temps/répétition** → figer R (puissance 0.8 à
  l'effet visé, plancher 8) + **décider la faisabilité** (multiprocess par processus ; `np.random`
  global → pas de threads ; early-stop si séparation décisive ; **cap wall-time dur**).
- **Worktree isolé** (en place) ; commits path-scoped (index partagé par sessions //).

## 8. Provenance & pré-enregistrement

- Ce fichier commité **avant tout run**. R final (post-pilote) = addendum daté.
- Re-run au même seed → table identique (repro D1). Provenance complète dans le JSON.

## 9. Critères de succès

1. `tools/coevolve_use_long.py` (sweet-spot + boucle R appariée + `exp_stats` + Harness) livré, testé
   (repro d'un bras au seed ; gate survie exposé).
2. Pilote R=3 → `std(d_r)` + temps/rép → R figé (≥8) → addendum daté.
3. Grille R figé → `results/coevolve_use_long_<seed>.json` + verdict (1 des 3 issues) + EDR 089.
   Re-run même seed → identique.

## 10. Hors périmètre (YAGNI)

- **Sélection EXPLICITE de l'usage** (terme de fitness récompensant l'usage du signal) — c'est le levier
  **#2** d'083, un EDR distinct ; à ouvrir si issue #2 (négatif robuste à survie longue).
- Beaucoup plus de générations / ré-évolution from-scratch par bras au-delà du dosage figé.
- Toute modification de `world_1`/du seam S2.
