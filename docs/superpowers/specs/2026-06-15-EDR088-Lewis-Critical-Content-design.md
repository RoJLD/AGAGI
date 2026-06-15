# Design EDR 088 — « Le contenu paye-t-il quand la distinction devient décisive ? » (pré-enregistrement)

> Spec de conception **et pré-enregistrement**. Issu du levier explicite d'**EDR 087** (« le contenu du
> langage ne paye pas — c'est du téléguidage ») : *« un monde où le contenu est décisionnellement
> critique (Leurres ≫ proies positives, ou apex indistinguables sans le mot) → alors re-tester FIABLE
> vs BROUILLÉ »*. Brainstorm du 2026-06-15. Méthode : Commandement 15.
>
> **Pré-enregistrement** : métrique, niveaux du sweep, K, seuils et règle de décision sont **figés avant
> de voir les données**. Le verdict ne lira QUE ce fichier. Toute déviation post-hoc = EDR séparé.

## 1. Question & hypothèse

**Question** : le CONTENU d'un signal référentiel confère-t-il un avantage **quand le monde rend la
discrimination décisionnellement coûteuse** ?

EDR 087 (12 seeds, apparié, 3 bras) a montré que le contenu **ne paye pas** dans un monde équilibré
(FIABLE−BROUILLÉ = +2.0 ± 4.1 SE, sous 2 SE) : le bénéfice apparent était du **téléguidage spatial**.
Diagnostic d'087 : *Mammouth ET Ours sont positifs (approcher est presque toujours bon), le Leurre est
rare → discriminer ne sert presque à rien → le contenu est redondant avec le mécanisme*. L'obs rend
déjà les apex **indistinguables à distance** (seule la direction `dn/ds/de/dw` est exposée ;
`on_apex_type` n'apparaît qu'**adjacent**) — le verrou n'est donc pas la distinguabilité mais
l'**économie décisionnelle**.

**Hypothèse directionnelle (figée)** : le contraste **FIABLE − BROUILLÉ** (score net) **croît avec la
fraction de pièges**. Basse criticalité (≈087) → ≈0 ; haute criticalité → > 0. Signature dose-réponse à
**pente positive** — la définition d'un monde de Lewis (le signal paye ssi la distribution des référents
rend la distinction coûteuse).

> **Réfutabilité** : si même à 0.83 de pièges (la plupart des apex sont des Leurres, indistinguables sans
> le mot) FIABLE ≈ BROUILLÉ, c'est un **négatif plus profond qu'087** — les agents n'exploitent pas le
> contenu *même quand il est décisif*.

## 2. La manipulation (le sweep)

Réutilise le moteur 3-bras apparié de `tools/relang_sweet.py` (087). **Variable indépendante = fraction
de Leurres-pièges parmi les apex.**

- **Niveaux pré-enregistrés** : `LEURRE_FRAC ∈ {0.33, 0.50, 0.67, 0.83}` (0.33 = baseline ≈087).
- **Nombre total d'apex FIXE** : `N_APEX = 12` par monde (le sweep ne change QUE le ratio, pas la
  densité totale — sinon confond fréquence-d'apex et criticalité). Composition : `n_leurre =
  round(LEURRE_FRAC·12)` Leurres ; les `12 − n_leurre` restants répartis Mammouth/Ours (positifs).
- **Référents** : 3 (Mammouth, Ours, Leurre), infra `referential_head` M=3 inchangée. Mammouth+Ours =
  *food* (approcher) ; Leurre = *piège* (éviter). Le token encode lequel.
- **Constant sur tous les niveaux** (hérité d'087, non manipulé) : sweet-spot énergie
  (`base_metabolism=0.25`, `forage_payoff=3.0`, EDR 085) ; **nuit OFF** (`night_enabled=False`,
  correctif audit 086) ; `hear_radius=3` ; PreyConfig Leurre/Ours d'087.

> **Caveat pré-enregistré** : monter `LEURRE_FRAC` réduit mécaniquement le nombre de Mammouths → moins
> de kills possibles *dans l'absolu* à tous les bras. C'est pourquoi le verdict porte sur la **différence
> appariée FIABLE−BROUILLÉ** (les deux bras voient le même monde/même n_mammouth), **pas** sur le niveau
> absolu de kills. La métrique nette (§3) et l'appariement neutralisent ce confond.

## 3. Les bras & la métrique (1 variable, apparié)

**3 bras** (identiques à 087), **appariés** par seed via `SeedManager` (D1) → monde identique entre bras
d'un même seed (placements, proies, crit, gumbel) :

| Bras | `use_head` | `decode_act` | `scramble` | Sens |
|---|---|---|---|---|
| **FIABLE** | ✓ | ✓ | ✗ | contenu vrai + décode-et-agis |
| **BROUILLÉ** | ✓ | ✓ | ✓ | **même mouvement**, contenu aléatoire |
| **SOLO** | ✓ | ✗ | ✗ | n'agit pas sur le signal |

- **Métrique pré-enregistrée** : `net = Σ mammoth_kills − Σ leurre_hits` (niveau-run, sommé sur la
  cohorte). Capture les **deux** faces du contenu : approcher le Mammouth (kills↑) ET éviter le Leurre
  (hits↓) — en monde-pièges, l'évitement est le bénéfice principal que `mammoth_kills` seul (087)
  raterait.
- **Diagnostics reportés séparément** : `Σ mammoth_kills` et `Σ leurre_hits` (décompose approche vs
  évitement), plus `decode_act_fires` (le mécanisme s'est-il déclenché ?).
- **Contraste clé à chaque niveau** : `d_s = net_FIABLE(s) − net_BROUILLÉ(s)` (apparié, le CONTENU seul,
  mouvement identique). Secondaire : `net_FIABLE − net_SOLO` (guidage+contenu mêlés, comme 087).

## 4. Protocole statistique (pré-enregistré)

Module stats versionné **et testé unitairement avant tout run** (l'infra n'existe pas dans `eval_harness`).

- **Par niveau** : diff appariée `{d_s}` sur ≥12 seeds → moyenne ± SE, win-rate (`P(d_s>0)`),
  **Wilcoxon signed-rank** (non-paramétrique, adapté ; *« Welch » banni*), + IC bootstrap (ré-échant.
  des seeds).
- **Test central — la pente (dose-réponse)** : la médiane des `d_s` croît-elle avec `LEURRE_FRAC` ?
  → **Jonckheere-Terpstra** (test de tendance ordonnée) sur les 4 niveaux. *Corroboration* : régression
  OLS de `d_s` sur `LEURRE_FRAC` (pente + IC bootstrap). Tendance positive significative = « le contenu
  paye quand la distinction devient critique ».
- **Multi-comparaisons** : si on déclare un verdict par niveau (4 Wilcoxon), **Holm sur les 4** (FWER).
  Le test de tendance (1 test) est le verdict primaire ; les 4 par-niveau sont descriptifs.
- **Appariement** : valide au **monde initial** (block-pairing D1) — documenté comme limite (trajectoires
  divergent après le 1er tirage genome-dépendant).

## 5. K & analyse de puissance

- Défaut harness K=3 **proscrit** (sous-puissance évaporée 5×, réf. 057/075/077/082/083/087).
- **Étape obligatoire** : pilote `K≈5` par niveau → estimer `std(d_s)` **par niveau** (la variance diffère
  selon la fraction) → K pour **puissance ≥ 0.8** à l'effet pré-enregistré, α=0.05 → `K = max` sur les
  4 niveaux, **plancher 12** (réf. 087). K figé en **addendum daté** post-pilote.
- **Gates par niveau** (hérités 087, conditions de validité) : survie des champions **> 120 ticks** ET
  `decode_act_fires ≥ 5`/run. Un niveau qui échoue un gate est marqué **VOID** (pas un négatif).

## 6. Table de décision (issues pré-enregistrées)

1. **Arc 4 CLOS — le contenu paye quand critique** : Jonckheere-Terpstra **significatif** (tendance
   positive) **ET** `d_s` robuste au niveau haut 0.83 (médiane > 0, Wilcoxon significatif, IC borne_inf
   > 0). → *le contenu référentiel confère un avantage dès que la distinction est décisionnellement
   coûteuse.*
2. **Négatif profond** : tendance **plate/nulle**, FIABLE ≈ BROUILLÉ même à 0.83 → les agents
   n'exploitent pas le contenu *même décisif*. Résultat majeur (ré-ouvre « pourquoi pas » : capacité de
   décodage ? pression de sélection sur l'usage, cf. EDR 083 ?).
3. **Partiel / gaté** : tendance présente mais sous-puissante, OU certains niveaux VOID (gate) → reporter
   honnêtement + re-régler (énergie/N_APEX) ; ce n'est pas une absence de résultat.

## 7. Implémentation & architecture

- **Nouveau tool** `tools/lewis_critical.py` — **n'altère pas** `relang_sweet.py` (artefact 087).
  Réutilise/importe son moteur : `evolve`, `_run_era` (3-bras), `_load_champions`, `new_head`/
  `train_population`. Ajoute : `_setup_critical(env, leurre_frac, n_apex)` (compose les apex selon le
  ratio) + la boucle de sweep + l'appel au module stats + `Harness` (provenance).
- **Module stats** `src/seed_ai/exp_stats.py` (neuf, versionné, testé) : `wilcoxon_signed_rank`,
  `cliffs_delta`/`bootstrap_ci`, `jonckheere_terpstra`, `paired_summary`. Sans scipy si possible (le
  projet évite scipy ; sinon dépendance documentée). **Tests unitaires sur cas connus** avant run.
- **Harness D1** : `with_db=False` ; `Harness.save` → `results/lewis_critical_<seed>.json` (seed, commit
  court, hash génome champion, niveaux, table niveau×bras → net/kills/hits/fires, d_s, Wilcoxon, JT,
  verdict).
- **Seam de composition d'apex** : `_setup_critical` réutilise `env._spawn_prey_instance(ref)` et
  `env.config.preys[...]` (comme `relang_sweet._setup_balanced`) — **runtime, zéro modif de
  `world_1`** (évite toute collision avec la session S2 qui touche le seam `batch_model_cls`).

## 8. Compute & exécution

- **Lourd** (sweep 4 niveaux × ≥12 seeds × 3 bras × biosphère + évolution des champions). Machine à
  **4 sessions parallèles** → prudence.
- **Pilote d'abord** (K≈5, 4 niveaux) → power analysis → grille complète.
- **Multiprocess par PROCESSUS** (`np.random.seed` global → pas de threads), **early-stopping** par
  niveau si la séparation est décisive, **cap wall-time dur** (abort si > 2× l'estimation pilote).
- **Worktree isolé** basé sur main (déjà en place). Commits path-scoped (index partagé par 4 sessions).

## 9. Provenance & pré-enregistrement

- Ce fichier est **commité avant tout run**. Le K final (post-pilote) = addendum daté en bas de ce
  fichier.
- Sortie : `results/lewis_critical_<seed>.json` + un **EDR 088** rédigé après le run (verdict = 1 des 3
  issues §6). Re-run au même seed → table identique (repro D1).

## 10. Critères de succès

1. Module `exp_stats` (Wilcoxon apparié, Jonckheere-Terpstra, bootstrap IC) livré **et testé
   unitairement** sur cas connus avant tout run.
2. `_setup_critical` + sweep livrés, testés (composition d'apex au ratio demandé ; reproductibilité au
   seed ; `net`/`kills`/`hits`/`fires` exposés).
3. Pilote exécuté → K figé par power analysis (≥12) → addendum daté.
4. Grille complète → `results/lewis_critical_<seed>.json` + verdict (1 des 3 issues) + EDR 088.
   Re-run même seed → table identique.

## 11. Hors périmètre (YAGNI)

- Rendre les apex *visuellement* indistinguables au niveau obs (ils le sont déjà à distance — §1).
- Flux RNG monde/agent séparés (appariement parfait de trajectoire — chemin `Generator`, différé D1).
- Co-évolution de l'USAGE du langage (pression de sélection sur l'écoute) — c'est le levier EDR 083,
  **distinct** ; à rouvrir si issue #2 (négatif profond).
- Toute modification de `world_1`/du seam `batch_model_cls` (réservé à la session S2).
