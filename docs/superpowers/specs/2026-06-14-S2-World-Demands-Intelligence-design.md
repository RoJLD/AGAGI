# Design S2 — « Le monde EXIGE-t-il l'intelligence ? » (pré-enregistrement)

> Spec de conception **et pré-enregistrement**. Issu du scan global (`docs/SCAN_GLOBAL.md`, item
> Science S2) et de la cause-racine B d'EDR 010. Brainstorm + revue adversariale du 2026-06-14
> (44 findings, 14 bloquants, panel 5 lentilles ancré dans le code). Méthode : Commandement 15.
>
> **Pré-enregistrement** : métrique, K, seuils et règle de décision sont figés **avant** de voir les
> données. Le verdict ne lira QUE ce fichier. Toute déviation post-hoc est un EDR séparé.

## 1. Objectif

Falsifier, monde par monde, l'hypothèse *« ce monde récompense réellement l'intelligence »*. Un monde
où un **réflexe non-cognitif suffit** rend toute mesure de « compétence » qui y est faite = du bruit
déguisé (cause-racine B, EDR 010). S2 = **test de fausseté** : comparer un **champion** à des
**baselines bêtes**. Si le champion ne bat pas le meilleur baseline, le monde est *factice*.

C'est aussi le **premier consommateur du `Harness` D1** (appariement seedé + provenance) → S2 valide D1
en production tout en produisant son verdict.

## 2. Décisions de design (figées)

| # | Fork | Choix |
|---|---|---|
| 1 | Baselines | **Échelle de 3** : RandomAction, RandomGenome (nouveau-né), Reflex (poursuite) |
| 2 | Mondes | **Les 4** : Soup, Stoneage *(sujet)*, Agricultural, Industrial *(contrôles assumés)* |
| 3 | Champion | **HoF réutilisé + test de cohérence** sur `life_score` |
| 4 | Régime | **Mode benchmark déparasité** (scaffolds OFF, reproduction/mutation/HGT OFF, nuit pré-réglée) |
| 5 | Métrique | **Survie individuelle** (âge à la mort), censurée à droite gérée |
| 6 | Effet | **Cliff's δ principal + IC bootstrap** ; ratio de médianes corroborant (borne_inf IC) |
| 7 | Test | **IUT min-test** par monde (`p_monde = max` des 3 p) ; Holm sur les **4 mondes** |
| 8 | K | **Pilote → power analysis → K** (plancher 12) |

## 3. La métrique (le fix central)

**Problème trouvé** : `run_era` renvoie `metrics['ticks']` = l'instant d'**extinction de la cohorte**
entière (un *max* sur 20-30 agents) — et comme un agent à `energy≥100` **se reproduit**
(`world_1:1276`), la lignée ne s'éteint jamais → `ticks` sature au cap 400 *quel que soit le QI*. La
« survie » du projet ne mesurait pas la survie.

**Décision** :
- Unité = **survie individuelle** : `age` (ticks vécus) de **chaque** agent, agrégé sur tous les agents
  × tous les seeds → vraie distribution → vraie médiane / Cliff's δ. *Pas* l'extinction-cohorte.
- Exposer `death_tick`/`age` par agent ; tout agent atteignant `max_ticks` est marqué `censored=True`.
- **Censure** : au pilote, vérifier que **< 5 %** des champions atteignent le cap. Sinon **augmenter
  `max_ticks`** jusqu'à décensurer (ou pré-enregistrer un test du log-rank / médiane Kaplan-Meier).
- `life_score` (`calculate_life_score`) calculé en parallèle = **métrique de cohérence** (§6).

## 4. Régime de mesure — mode benchmark déparasité

Un attribut `benchmark_mode=True` sur l'environnement, qui, pendant les ères S2 :
- **Scaffolds OFF** : `current_era ≫ scaffold_eras` (ou `scaffold_eps`/`crit_base=0` explicites) →
  `anneal≈0`. Sinon la récompense d'approche (+0.5/tick vers la proie) **subventionne les dummies**.
- **Reproduction / mutation / HGT OFF** : cohorte **fixe** → la survie individuelle n'est pas
  contaminée par la natalité ni plafonnée à 400.
- **Nuit** : pré-réglée — `night_enabled=False` par défaut (le feu est impossible dans Soup → la nuit
  pénaliserait *uniformément* et tronquerait la distribution au même tick pour toutes les conditions).
  Si une variante « nuit ON » est testée, reporter la survie segmentée jour/nuit en diagnostic (et
  vérifier que la nuit est *résoluble* dans chaque monde avant de l'activer).
- **Apprentissage intra-vie** : `compute_policy_gradient` **reste actif** pour toutes les conditions
  (il fait partie du fait d'« être un agent fonctionnel »). RandomGenome est donc un **nouveau-né qui
  peut apprendre intra-vie**, pas un connectome gelé (interprétation pré-enregistrée, §5).

> **Caveat pré-enregistré** : le champion HoF a été *entraîné* avec scaffolds ON + reproduction, mais
> *mesuré* en régime déparasité. Le **test de cohérence** (§6) est le garde-fou : si le champion ne se
> comporte plus en champion dans ce régime, son verdict est *void*.

## 5. Les baselines (échelle de 3)

Toutes passent par `env.add_agent` ; les non-connexionnistes via le seam `BaselineBatchModel` (§9).

1. **RandomAction** — logits aléatoires à chaque tick, tirés de `np.random.*` (flux global **déjà
   seedé** aux frontières par le Harness — *jamais* un RNG privé, sinon l'appariement casse).
   *Zéro politique.*
2. **RandomGenome** — `MambaAgent()` frais à poids aléatoires, pipeline champion normal (pas de seam).
   *Architecture non sélectionnée, mais qui apprend intra-vie* (cf. §4). Isole : *la sélection
   évolutive apporte-t-elle quelque chose qu'un nouveau-né apprenant n'a pas ?*
3. **Reflex** — heuristique câblée **exécutable depuis l'obs réelle**. L'obs n'expose *pas* de carte de
   valeurs, seulement `dn/ds/de/dw` = direction vers la proie la plus proche (`world_1:380-385`) +
   `on_apex_type` si adjacent. Donc **réflexe de poursuite** : `move = argmax(dn,ds,de,dw)` ; `grab` si
   `in_nearby_item_count>0`. Pré-enregistrer **2 variantes** — *naïf* (fonce) et *prudent* (fuit si apex
   adjacent hostile) — et prendre le **meilleur des deux** comme borne réflexe (un réflexe qui fonce sur
   un apex qui riposte sous-estimerait la barre).

`BaselineBatchModel.forward` doit, en plus de `(logits, compute_spent=zeros)`, **écrire `surprise=0.0`
et `surprise_momentum=0.0`** sur tous les agents (passe identique à `mamba_agent.py:633-642`) — sinon
`step()` relit des valeurs *gelées* → coût cérébral / récompense de curiosité = artefacts figés.

## 6. Le champion — HoF réutilisé + test de cohérence

- **Source** : `load_hall_of_fame()` → `data/hall_of_fame.pkl` → `MambaAgent().from_genome(g)`.
  Pour les **contrôles** (Soup/Agri/Industrial), le même génome Stoneage transféré (ils sont des
  contrôles, pas des sujets — §7).
- **Test de cohérence (garde-fou du mismatch fitness/métrique)** : par monde, calculer la comparaison
  champion-vs-baselines sur **deux** métriques :
  - **(P) Survie individuelle** — métrique principale du verdict.
  - **(C) `life_score`** — l'axe qui a *forgé* le champion.
  - **Règle** : si le champion ne bat **pas** le meilleur baseline sur **(C)** dans un monde, son verdict
    de survie y est marqué **VOID** (le champion ne se comporte pas en champion dans ce régime →
    ininterprétable). Empêche de conclure « monde factice » sur un simple mismatch d'objectif.
- **Provenance** : hash du génome champion + version du HoF logués (§13).

## 7. Les mondes (4, dont 3 contrôles assumés)

| Monde | Rôle | Verdict attendu (pré-enregistré) |
|---|---|---|
| **Stoneage** | **Sujet** (HoF natif, outils, crafting, apex) | EXIGE (à confirmer) |
| **Soup** | Contrôle (Stoneage **sans outils**) | proche de « n'exige pas » |
| **Industrial** | Contrôle (Stoneage + `pollution+=0.01` *inerte, jamais lue*) | « n'exige pas » (≈ Stoneage) |
| **Agricultural** | Contrôle (Stoneage + hiver ; *l'agriculture est du code mort* — `_apply_action` appelle un `super` inexistant, le semis ne se déclenche jamais) | « n'exige pas » (= Stoneage + hiver passif) |

> **Pré-enregistré** : Soup/Stoneage/Industrial partagent la **même économie** (mêmes proies,
> métabolisme, respawn). Une survie quasi-identique sur ces trois est **attendue** (tautologie du même
> moteur), pas un échec. Un négatif sur les contrôles **valide le pouvoir falsificateur de S2**. Rendre
> Agri/Industrial réellement exigeants = travail **S5** (hors Phase 0).

## 8. Protocole statistique

Tout est codé **et testé unitairement** dans un module versionné **avant** le run (l'infra n'existe pas
dans `eval_harness`, qui ne fait qu'un Welch non-apparié sans p-value).

- **Apariement** : pour chaque seed `s`, `d_s = survie_champion(s) − survie_baseline(s)` (mêmes seeds via
  `SeedManager`). On teste la **différence appariée**, pas deux échantillons indépendants.
- **Test** : **Wilcoxon signed-rank** sur les `d_s` (non-paramétrique, adapté à la survie
  asymétrique/censurée). *Le mot « Welch » est banni de S2.*
- **Effet principal** : **Cliff's δ** (sans échelle, robuste à la censure commune), seuil pré-enregistré
  **δ ≥ 0.33** (« large », Romano), avec **IC bootstrap** (ré-échantillonnage des seeds).
- **Effet corroborant** : **ratio des médianes** avec **IC bootstrap 95 %** ; exiger **borne_inf(IC) ≥
  1.3**, pas le point ponctuel (bruité à petit K). *Corroboration, non gate dur — si Cliff's δ et le
  ratio divergent, Cliff tranche et on le documente.*
- **Règle de décision par monde (IUT min-test)** : le champion « bat les baselines » SSI il bat les
  **3** → `p_monde = max(p_vs_RandomAction, p_vs_RandomGenome, p_vs_Reflex)`. Ce max contrôle déjà le
  type-I à α **sans correction** (propriété Intersection-Union). *Pas de Holm sur les 3 baselines —
  c'était une erreur de structure (Holm protège « au moins un », l'inverse d'un critère conjonctif).*
- **FWER global** : si on veut contrôler l'erreur sur les **4 verdicts**, **Holm sur les 4 `p_monde`**
  (famille = 4 mondes, m=4), **pas** sur 12.
- Reporter aussi les **3 comparaisons baseline séparément** (table monde × baseline) — l'appariement
  n'est valide qu'au **monde initial** (block-pairing D1), à documenter.

## 9. K & analyse de puissance

- Défaut harness = K=3 → **proscrit** (le régime sous-puissant évaporé 5 fois : 057/075/077/082/083).
- **Étape obligatoire** : pilote `K≈5` → estimer `std(d_s)` **par monde** (la variance diffère entre
  Soup et Industrial) → calculer le K requis pour **puissance ≥ 0.8** à l'effet pré-enregistré
  (`δ≥0.33`), α=0.05 → `K = max` sur les 4 mondes, **plancher 12** (référence EDR 087).
- K figé dans ce pré-enregistrement après le pilote (un addendum daté).

## 10. Table de décision (3 issues pré-enregistrées)

Le cas le plus probable *et* le plus important est l'ambigu (« champion > hasard mais ≈ réflexe ») —
c'est *précisément* la cause-racine B. Verdict binaire insuffisant. Trois issues :

1. **EXIGE l'intelligence** — champion > **Reflex** (le baseline le plus fort), `p_monde` significatif
   **ET** `δ ≥ 0.33` (IC) **ET** ratio borne_inf ≥ 1.3.
2. **N'EXIGE PAS** — champion **≈ Reflex** : test de **non-infériorité/équivalence** dont la **marge**
   est figée dans l'addendum post-pilote (§9), au même titre que K (le réflexe suffit). *Verdict négatif
   explicite, pas une absence de résultat.*
3. **ANTI-CORRÉLÉ (alarme)** — champion **< Reflex** : le monde punit ce que la sélection a optimisé →
   investigation (probable confond de régime ou objectif).

`VOID` si le test de cohérence (§6) échoue.

## 11. Architecture & seam d'injection

- **Seam (2 lignes, rétro-compatible)** : dans `Biosphere3D.__init__`, ajouter
  `self.batch_model_cls = MambaBatchModel` ; en `world_1:945`, remplacer l'instanciation en dur par
  `batch_model = self.batch_model_cls(models, world_model=self.world_model)`. Le runner S2 fait
  `env.batch_model_cls = RandomActionBatchModel / ReflexBatchModel` après construction. **Zéro fork,
  zéro monkeypatch.** RandomGenome ne touche pas ce seam.
- `BaselineBatchModel` implémente **uniquement** `forward(batch_obs, env_surprise_batch=None) →
  (logits, compute_spent)` (+ écriture `surprise=0`) et `compute_policy_gradient(...)` **no-op**. Ce
  sont les **seules** méthodes appelées sur `batch_model` (vérifié : `:952`, `:1383`).

## 12. Compute & exécution

- **Runner minimal** sur le patron de `robust_evaluate` (instancier monde, boucler `step` jusqu'à
  extinction/cap, lire survie individuelle, stopper le retriever), `with_db=False`. **Ne pas** réutiliser
  `main_biosphere` (`MAX_ERAS=30` + `robust_rank` K-éval = ~58 min parasites).
- **Parallélisme par PROCESSUS** (pas threads : `np.random.seed` est global).
- **Early-stopping** : arrêter une paire (monde, baseline) dès que la séparation est décisive.
- **Cap wall-time dur** : abort si > 2× l'estimation du pilote. Grille cœur estimée ~14 min séquentiel à
  K=20 (~2-3 min multiprocess).

## 13. Provenance & pré-enregistrement

- `Harness.save` étendu : **seed + commit court + hash du génome champion + hash de config + version du
  HoF + flag `git-dirty`** (l'arbre est actuellement *sale* → committer ou enregistrer l'état exact).
- Ce fichier de design est **commité avant tout run**. Le K final (post-pilote) est un addendum daté.
- Sortie : `results/s2_demand_<seed>.json` (table monde × condition → survie médiane, δ+IC, ratio+IC, p,
  verdict) + un **EDR 088**.

## 14. Gestion d'erreurs

- `try/except` par monde : un monde qui crash est loggé + sauté + marqué dans le rapport (pas d'abort
  global).
- `load_hall_of_fame` : **corriger le `except: pass`** silencieux → `raise` si HoF vide.
- **Smoke-run 1 seed par monde** avant la grille complète (vérifie instanciation des 4 mondes + des 3
  baselines).
- Dégradation gracieuse KuzuDB (déjà fournie par `Harness`, `with_db=False` ici de toute façon).

## 15. Critères de succès

1. Module stats (Cliff's δ + IC, ratio médianes + IC, Wilcoxon apparié, IUT, Holm-4) livré **et testé
   unitairement** avant tout run S2.
2. Seam `batch_model_cls` + `BaselineBatchModel` (3 baselines) livrés, testés (forme des logits,
   `surprise=0`, reproductibilité au seed).
3. Survie **individuelle** censurée exposée et agrégée (plus d'extinction-cohorte).
4. Pilote exécuté → K figé par power analysis (≥12) → addendum daté.
5. Grille complète → `results/s2_demand_<seed>.json` + verdict par monde (1 des 3 issues, ou VOID) +
   EDR 088. Re-run au même seed → table identique (repro).

## 16. Hors périmètre (YAGNI)

- Rendre Agri/Industrial réellement exigeants (= S5, après Phase 0).
- Ré-évolution from-scratch d'un champion par monde (écarté : *HoF + cohérence* retenu).
- Flux RNG monde/agent séparés (chemin `Generator` — appariement parfait de trajectoire, différé D1).
- 4ᵉ baseline « connectome strictement gelé » (RandomGenome-qui-apprend suffit ; à rouvrir si (b)
  ambigu).

## 17. Dépendances

- **D1 Harness** (Tasks 1-3 : `SeedManager` + `Harness` + `eval_robust`/`save`) — *quasi terminé*. S2
  n'exige **pas** la migration complète des tools (D1 Tasks 7-8).
- `load_hall_of_fame`, `MambaAgent.from_genome`, `add_agent` — éprouvés (`robust_eval.py`).

## 18. Traçabilité — les 14 bloquants → traitement

| Bloquant (panel) | Traité en |
|---|---|
| Mismatch fitness/métrique | §6 test de cohérence |
| Métrique = extinction-cohorte + censure | §3 |
| Reproduction/mutation/HGT actifs | §4 benchmark_mode |
| Scaffolds à 97 % | §4 |
| Infra stats inexistante | §8 (codée+testée avant run) |
| « Welch apparié » / structure du test | §8 Wilcoxon + IUT |
| K non fixé / pas de power | §9 |
| Stub Agri = code mort | §7 contrôle assumé |
| Pas de table de décision (cas ambigu) | §10 |
| Qualité champion hétérogène | §7 (contrôles, pas sujets) |
| Mondes non distincts | §7 |
| Réflexe mal spécifié | §5 |
| RandomGenome apprend | §4/§5 (interprétation pré-enregistrée) |
| Seam d'injection / `surprise=0` | §11 |

## 19. Addendum post-revue (2026-06-15) — corrections de la revue adversariale finale

> Une revue indépendante de l'implémentation a trouvé un **bloquant statistique** et deux raffinements.
> Corrigés avant tout run. Ces déviations du contrat §8/§10 sont **tracées ici** (intégrité du
> pré-enregistrement). Aucune donnée n'avait encore été produite.

- **B1 — appariement par seed (corrigé).** Le test de signification était calculé sur les **individus
  poolés** (tous les âges, toutes ères) index-par-index, alors que §8 fige l'appariement **par seed**.
  Correctif : `run_condition` expose `era_survival`/`era_life` (médiane de survie/life **par ère**) ;
  `s2_verdict` apparie ces K médianes par ère pour le **Wilcoxon signé** et l'**IC bootstrap du ratio**
  (ré-échantillonnage des seeds). **Cliff's δ + son IC** restent calculés sur les **individus poolés**
  (effet de dominance robuste, §6). Effet et significativité sont ainsi mesurés à la bonne granularité.
- **I1 — le ratio est corroborant, non bloquant (corrigé).** §8 dit « Cliff tranche, le ratio
  corrobore » mais §10 le listait en gate conjonctif de `EXIGE`. Aligné sur §8 : **`EXIGE` = `p<α` ET
  `Cliff δ ≥ 0.33`** ; `ratio_lo`/`ratio_hi` sont rapportés mais ne bloquent plus le verdict.
- **I2 — équivalence bornée (corrigé).** `N'EXIGE PAS` exige désormais `|Cliff δ| < marge` **ET**
  `p ≥ α` (pas de différence détectable), au lieu d'un point-estimate nu. L'IC de Cliff
  (`cliff_lo`/`cliff_hi`) est calculé et rapporté pour un TOST complet à calibrer au pilote.
- **4e issue `AMBIGU` (pré-enregistrée ici).** Complète les 3 issues du §10 : effet réel **sous-seuil**,
  ou **significatif mais négligeable** → inconclusif (ni EXIGE, ni équivalence, ni anti-corrélé).
- **Placeholders pilote inchangés** : `CLIFF_THRESH=0.33` et `EQUIV_MARGIN=0.147` restent à confirmer
  dans l'addendum **post-pilote** (§9), avec la marge d'équivalence définitive du TOST.
