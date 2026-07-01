# Diagnostic de régime S2 — pourquoi le champion ≈ dummy ? — Design

**Date** : 2026-06-29
**Type** : outillage de diagnostic (exploratoire — **PAS** le S2 confirmatoire pré-enregistré).
**Statut** : design validé (brainstorm), prêt pour plan.

## Contexte (grounded)

Le benchmark S2 « le monde exige-t-il l'intelligence ? » est **déjà codé et pré-enregistré** :
- `tools/s2_demand.py` : champion HoF + 4 baselines × 4 mondes, survie individuelle censurée + life_score,
  appariement seedé (Harness D1), `run_condition`/`run_s2`, power-analysis par pilote (`required_k`).
- `src/seed_ai/s2_stats.py` : Cliff's delta + IC bootstrap, ratio de médianes, Wilcoxon signé apparié
  par ère, IUT min-test, Holm, table de décision `s2_verdict` (EXIGE / N'EXIGE PAS / ANTI-CORRÉLÉ /
  AMBIGU / VOID).
- Pré-enregistration : `docs/superpowers/specs/2026-06-14-S2-World-Demands-Intelligence-design.md`.

**Le seul run** (`results/s2_demand_2026.json`, 2026-06-15) est un **smoke test** : 1 monde (stoneage),
K=2 ères, ~6 individus. Verdict = **VOID** (`coherence_ok=false`, `life_p=1.0`) ; sur la survie le champion
est **négatif** (Cliff δ = −0.33 vs `random_action` ET vs `reflex`). Bref, à ce stade le champion HoF est
*indistinguable d'un dummy* en stoneage — mais le run est trop petit pour conclure.

**Fait de cadrage vérifié** : `main_biosphere` (évolution prod) instancie `WorldConfig()` **par défaut**
(`base_metabolism=1.0`, `forage_payoff=1.0` — cf. `src/environments/config.py:75-76`, « Défauts =
comportement historique »). Le benchmark S2 instancie aussi `world_cls()` par défaut. **Entraînement et
test sont au MÊME régime dur 1.0/1.0** → il n'y a pas de décalage entraînement↔test. Le sweet-spot 0.25/3.0
d'EDR 085 (survie ×4) a été *trouvé* mais **jamais câblé en défaut ni en prod**.

## Problème & objectif

Le VOID/négatif du smoke run a **trois explications candidates** qu'il faut séparer **avant** de dépenser
du compute sur le S2 confirmatoire :

- **H1 — sous-puissance** : K=2 / ~6 individus = bruit pur ; avec de la puissance le champion se détache.
- **H2 — effet plancher (régime)** : au régime dur 1.0/1.0, *tout le monde* meurt vite (79 % starvent,
  EDR 084 ; « pas de premier barreau survivable », EDR 090) → la survie ne peut pas discriminer champion
  vs dummy (équivalence **dégénérée**, pas informative).
- **H3 — n'exige pas réellement** : même à un régime survivable, le champion ≈ dummy → le monde n'exige
  pas l'intelligence (le verrou « répertoire-MONDE » de l'arc apex, mesuré pour la première fois).

**Objectif** : un diagnostic minimal qui tranche H1/H2/H3 et **dicte comment lancer le S2 confirmatoire**
(quel régime, pré-enregistré tel quel ou via addendum daté).

## Principe & garde-fous

- **Exploratoire, pas confirmatoire** : ce diagnostic n'amende PAS la pré-enregistration S2. S'il conclut
  « lancer au sweet-spot », *cela* devient un **addendum daté** à la pré-reg S2 avant le run confirmatoire.
- **Réutilise l'existant** : `run_condition` (s2_demand) pour la mesure, `s2_stats` pour Cliff/Wilcoxon —
  aucune nouvelle machinerie statistique.
- **Footguns hérités** de `run_condition` (déjà corrects) : `benchmark_mode=True` (cohorte fixe),
  `night_enabled=False`, `current_era=10_000` (scaffolds OFF), `memory_retriever.stop()` (déterminisme
  KuzuDB — cf. mémoire « biosphère : mémoire ambiante = non-repro »).
- **Monde unique = stoneage** (celui du smoke run, monde canonique dont héritent les autres). Le S2
  confirmatoire fera les 4 mondes ; le diagnostic n'en a pas besoin (YAGNI).
- **Appariement** : mêmes seeds pour les 3 agents d'un même régime (différences appariées par ère, idiome
  Harness/`seed_at` existant).

## Composants (responsabilité unique, testables)

### A — Hook de régime dans `run_condition` (modif chirurgicale, gatée)
`run_condition` fait aujourd'hui `env = world_cls()` (config par défaut). Or `base_metabolism`/
`forage_payoff` se lisent **à la construction**. Ajout d'un paramètre optionnel **`config=None`** :
`env = world_cls(config) if config is not None else world_cls()`. **Défaut `None` = comportement actuel
bit-exact** (non-régression ; `s2_demand.run_s2` inchangé). C'est la seule modification d'un fichier existant.

### B — Régimes & cellules (`s2_regime_diagnostic.py`)
- `REGIMES = {"defaut": (1.0, 1.0), "sweet": (0.25, 3.0)}` — `(base_metabolism, forage_payoff)`.
- `_make_config(base_metabolism, forage_payoff) -> WorldConfig` : construit un `WorldConfig` au régime
  voulu (sinon défauts).
- Agents : `champion` (HoF #1 via `load_champion_genome`), `reflex_naive` (`ReflexBatchModel`, baseline
  le plus fort), `random_action` (`RandomActionBatchModel`, plancher bruit pur).
- `run_diagnostic(seed, K, num_agents, max_ticks) -> dict` : pour chaque régime, lance les 3 agents via
  `run_condition(Biosphere3D, batch_model_cls, genome, seed, config=cfg_regime, n_eras=K, ...)`. Capture
  par cellule le dict `run_condition` complet (`survival`/`life_score` poolés + `era_*` par seed +
  `censored_frac`). Agrège dans `cells[regime][agent]`.

### C — Verdict (fonction PURE, cœur testé) — `regime_diagnostic_verdict(cells) -> dict`
Réutilise `s2_stats` :
- **Séparation** champion vs baseline le plus fort d'un régime (`reflex`/`random_action` à plus haute
  survie médiane, comme `s2_verdict`) : `p` = Wilcoxon signé apparié sur `era_survival` ; `cliff` =
  `cliffs_delta` sur les individus poolés. « Champion bat » ⇔ `p < ALPHA` ET `cliff ≥ CLIFF_THRESH`.
- **Survivabilité d'un régime** (détecte le plancher) :
  - médiane d'âge du champion `m = median(survival)`.
  - `survivable(regime)` ⇔ `m ≥ SURV_FLOOR_FRAC * max_ticks` (par défaut 0.5) **OU**
    `censored_frac ≥ CENSORED_SURV` (par défaut 0.25).
  - `lift` = `median(champ@sweet) / median(champ@defaut) ≥ LIFT_RATIO` (par défaut 1.5).

**Table de décision (ordonnée)** :
1. champion **bat** au régime **défaut** → **`SOUS_PUISSANCE`** (H1), `regime_recommande="defaut"` →
   lancer le S2 confirmatoire **au défaut, pré-enregistré tel quel** (le VOID n'était que du bruit).
2. sinon (pas de séparation au défaut) :
   a. `defaut` **non survivable** (plancher) ET `sweet` **survivable** (`lift`) ET champion **bat** au
      `sweet` → **`CONFOND_PLANCHER`** (H2), `regime_recommande="sweet"` → S2 confirmatoire au sweet-spot
      (**addendum daté** à la pré-reg).
   b. `sweet` **survivable** ET champion **ne bat pas** au `sweet` → **`N_EXIGE_PAS_REEL`** (H3),
      `regime_recommande=None` → finding fort : le monde n'exige pas l'intelligence même quand survivable.
   c. sinon → **`AMBIGU`** (ni régime survivable, ou cas contradictoire) → rapporter ; re-powerer/inspecter.

Renvoie `{verdict, regime_recommande, per_regime: {regime: {survivable, champ_median, censored_frac,
strongest_baseline, p, cliff, beats}}, lift, thresholds}`.

### D — CLI & sortie
`run_diagnostic_main(seed, K, num_agents, max_ticks) -> dict` : orchestre B → C sous un `Harness`
(`with_db=False`), `h.save(report)` → `results/s2_regime_diagnostic_<seed>.json`, imprime une table ASCII
+ **une ligne d'interprétation actionnable** (« verdict X → lancer le S2 confirmatoire au régime Y »).
`if __name__ == "__main__"` : `seed = int(os.getenv("EXPERIMENT_SEED", "2026"))`.

## Seuils (diagnostic, exploratoire)

```
ALPHA = 0.05            # repris de s2_stats
CLIFF_THRESH = 0.33     # "large" (Romano), repris de s2_stats — séparation
SURV_FLOOR_FRAC = 0.5   # médiane d'âge ≥ 50% de max_ticks -> survivable (absolu)
CENSORED_SURV = 0.25    # OU ≥25% censurés (survivants à max_ticks) -> survivable
LIFT_RATIO = 1.5        # sweet relève la survie ≥1.5× le défaut -> "off the floor"
```
Ce sont des seuils **de diagnostic** (exploratoire), ajustables ; **distincts** des seuils confirmatoires
pré-enregistrés de S2. Ils sont nommés et figés dans le code (pas magiques).

## Flux de données

`HoF champion + REGIMES → run_condition(config=régime) ×(2 régimes × 3 agents) → cells →
regime_diagnostic_verdict → report → results/s2_regime_diagnostic_<seed>.json + table + reco régime`

## Paramètres par défaut (run réel)

`seed=2026, K=8, num_agents=20, max_ticks=400` (cohérent avec s2_demand). K=8 ≫ K=2 du smoke run pour
sortir du bruit ; restable à la hausse si `AMBIGU`. ~2 régimes × 3 agents × 8 ères = 48 ères courtes.

## Tests / non-régression

- **Unitaires (PUR, sans sim)** : `regime_diagnostic_verdict` sur des `cells` **synthétiques** couvrant
  les 4 verdicts (SOUS_PUISSANCE / CONFOND_PLANCHER / N_EXIGE_PAS_REEL / AMBIGU) + les bascules de seuil
  (survivable on/off, lift on/off, beats on/off). Construire les cellules à la main (listes `survival`/
  `era_survival`/`censored_frac`) — zéro environnement.
- **Non-régression `run_condition`** : un test prouve que `run_condition(..., config=None)` est
  inchangé (même chemin que `s2_demand`) ; un test prouve que passer un `config` au régime sweet modifie
  bien `env.base_metabolism`/`forage_payoff` à la construction.
- **Intégration (pilote)** : `run_diagnostic` à petit `max_ticks`/`num_agents`/K avec `_disable_kuzu()`
  (idiome `tools/lethality_curriculum.py`) + `monkeypatch.chdir(tmp_path)` (ne pollue pas `results/`) ;
  vérifie la structure du report (2 régimes × 3 agents, clés présentes) — pas le verdict (dépend du HoF).
- HoF vide → `load_champion_genome` lève (déjà : pas d'`except: pass` silencieux).

## Risques

1. **HoF absent/instable** → `load_champion_genome` lève explicitement (blocker honnête, pas de fallback
   aléatoire silencieux). Le run réel exige un HoF évolué (`main_biosphere`).
2. **Aucun régime survivable** (champion meurt vite même au sweet) → `AMBIGU` honnête, pas de verdict
   forcé ; piste = élargir les régimes (futur, hors-périmètre).
3. **Seuils diagnostic arbitraires** → assumé : outil exploratoire ; les seuils sont nommés, figés,
   rapportés dans le report ; la décision *confirmatoire* repassera par la pré-reg S2.
4. **Contention KuzuDB / non-repro** (sessions parallèles) → `memory_retriever.stop()` hérité de
   `run_condition` + `_disable_kuzu()` en test ; commits **path-scopés** (tree partagé).

## Hors-périmètre

- Lancer le S2 confirmatoire lui-même (étape suivante, conditionnée au verdict de ce diagnostic).
- Les 4 mondes (diagnostic = stoneage seul) ; le balayage complet de la courbe d'énergie (approche C
  écartée — YAGNI).
- Câbler le sweet-spot en prod / changer les défauts `WorldConfig` (décision séparée).
- Toute mutation des docs EDR canoniques ou de la pré-reg S2 (interdit ; addendum daté seulement).
