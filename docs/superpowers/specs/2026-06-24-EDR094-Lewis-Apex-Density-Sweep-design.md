# EDR 094 — Un premier barreau survivable par la DENSITÉ d'apex ? Sweep de `N_APEX`

**Statut :** pré-enregistrement (gelé avant données).
**Date :** 2026-06-24.
**Lignée :** 090 (curriculum létalité = NEGATIF PROFOND) → 093 (revenu réfuté : `forage_payoff` inerte, mur = dépense) → **094** (dépense : la densité d'apex est-elle le déclencheur ?).
**Numéro :** 091 (curriculum_transfer) et 092 (dreaming) pris par sessions parallèles ; 093 = sweep revenu → ce travail = **094**.

## 1. Motivation

EDR 093 a fermé le côté **revenu** de l'économie d'énergie de Lewis : balayer `forage_payoff` ×16 est **inerte**
(survie médiane 5 ticks aux 5 niveaux, kills/agent ~0.18, JT non croissant). Les champions font banqueroute au
tick 5 **avant de manger** — le mur est la **DÉPENSE**, pas le revenu : spam d'actions chères (soin −10
`world_1_stoneage.py:666`, lancer −10 l.1122) dans un Lewis dense en apex (12 Mammouth/Ours via `_setup_critical`).

Le diagnostic post-093 désigne deux composantes de la dépense : le **déclencheur** (densité d'apex `N_APEX`, qui
provoque le spam de lancers/soins) et le **tarif** (le coût −10 lui-même). EDR 094 teste **le déclencheur**, et lui
seul : balayer `N_APEX` à létalité 0. C'est le cut le plus diagnostique — il peut **innocenter ou incriminer
l'environnement d'un coup**, et requiert **zéro modification du code de production** (`N_APEX` est déjà un
paramètre propre de `_setup_critical(env, leurre_frac, n_apex=...)`), contrairement au tarif (−10 hardcodé).

## 2. La prétention (1 variable — Commandement 15)

> Sur Lewis à **létalité 0** (pas de Leurres mortels → on isole la dépense de la létalité), il **existe** une
> densité d'apex `N_APEX` où les champions stoneage survivent (survie médiane > 120 ticks). On mesure *si* et *où*.

**Variable manipulée :** `N_APEX` ∈ `(12, 9, 6, 3, 0)`. 12 = baseline 093 (mort au tick 5) ; 0 = Lewis vidé d'apex
(forage pur, `PREY_COUNT=15` proies régulières conservées). Mécaniquement, `N_APEX` règle le nombre d'apex
positifs (Mammouth/Ours alternés) instanciés par `_setup_critical`.

**Tout le reste fixe :** `forage_payoff = 3` (sweet-spot 085, et démontré sans effet par 093), `base_metabolism =
0.25`, `leurre_frac = 0`, `PREY_COUNT = 15`, `max_ticks = 300`, `num_agents = 24`, champions HoF répliqués
(`_load_champions` + `_reproduce`), **pas d'évolution, pas de langage** (`use_ref_head=False`, `decode_act=False`).

**Pourquoi `N_APEX` et pas le tarif −10 :** `N_APEX` est un knob de monde **sans modif de prod** ; et il tranche
en amont. Si baisser la densité débloque la survie → l'apex EST le déclencheur (un curriculum de densité peut
ramper 0→12). Si même `N_APEX=0` meurt au tick 5 → le mur est **intrinsèque** (métabolisme, brain_cost, ou
heal-spam non déclenché par une menace), pas l'environnement → le levier bascule vers le tarif/métabolisme
(EDR suivant). Un seul balayage diagnostique « déclencheur environnemental vs drain intrinsèque ».

## 3. Métriques & règle de verdict (gelées)

- **Métrique primaire :** survie médiane (ticks) des champions par niveau de `N_APEX`, sur R×n_eval ères seedées,
  appariées par seed entre niveaux (même monde initial à seed donné, seul `N_APEX` varie).
- **Tendance :** Jonckheere-Terpstra one-sided — la survie **décroît**-elle quand la densité **croît** ? (groupes
  fournis en ordre de `N_APEX` décroissant pour tester une survie croissante à mesure que la densité baisse).
- **Sous-produits diagnostiques (gratuits), par niveau :** famine (`energy≤0`) vs combat (`hp≤0 ∧ energy>0`) lus
  dans `env.dead_agents` ; kills moyens/agent. À `N_APEX` bas (et 0), les kills tendent trivialement vers 0 (peu/pas
  d'apex à frapper) ; le signal-clé devient alors **la famine persiste-t-elle au tick ~5 sans apex à frapper ?**
  (oui → drain intrinsèque ; non → la dépense déclenchée par l'apex était bien le mur).

| Condition | Verdict |
|---|---|
| survie médiane > 120 à un `N_APEX > 0` | **BARREAU TROUVÉ** — rung survivable à densité réduite ; base d'un curriculum de densité (ramper vers 12, re-test 090). On rapporte le **plus haut** `N_APEX` qui franchit (le plus proche du Lewis cible). |
| survie > 120 **seulement** à `N_APEX = 0` | **RUNG DÉGÉNÉRÉ** — survie uniquement dans un Lewis **vidé d'apex** (pas le monde-cible) ; les apex sont un mur absolu, aucune densité positive n'est survivable. |
| survie ≤ 120 **même** à `N_APEX = 0` | **MUR INTRINSÈQUE** — pas l'environnement ; le drain est intrinsèque (métabolisme / brain_cost / heal-spam) ; pivot vers coût d'action (−10) / métabolisme (EDR suivant). |

Les trois branches sont informatives : succès = substrat fabriqué + curriculum de densité ; chaque échec localise
le levier suivant (apex absolu, ou drain intrinsèque).

## 4. Paramètres pré-enregistrés (gelés)

| Paramètre | Valeur | Note |
|---|---|---|
| `levels` (`N_APEX`) | `(12, 9, 6, 3, 0)` | 12 = baseline 093 ; 0 = Lewis vidé |
| `forage_payoff` | 3 | 085, et inerte (093) — fixe |
| `base_metabolism` | 0.25 | sweet-spot 085 (fixe) |
| `leurre_frac` | 0 | isole la dépense de la létalité |
| `PREY_COUNT` | 15 | forage régulier conservé à tous les niveaux |
| `max_ticks` | 300 | gate >120 valide à cette échelle (089/090/093) |
| `num_agents` | 24 | comme 093 |
| `n_eval` | 8 | ères de mesure par (niveau, répétition) |
| `R` | 4 | répétitions appariées |
| gate de survie | 120 ticks | seuil de barreau survivable |
| `max_population` | 150 | défensif (PR #29) ; jamais atteint ici |

## 5. Outillage & architecture

- **Généralisation de `tools/lewis_survival_sweep.py`** (mergé sur main via PR #31 ; plus aucun propriétaire de
  session parallèle) — **pas de duplication** (DRY) :
  - `_measure_survival(cfg, seeds, leurre_frac=0.0, n_apex=N_APEX, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS)` :
    ajout d'un paramètre `n_apex` (défaut = `N_APEX`), threadé dans `_setup_critical(env, leurre_frac, n_apex=n_apex)`.
    **Rétro-compatible** : le `main` de 093 (sweep forage) reste inchangé dans son comportement.
  - `APEX_LEVELS = (12, 9, 6, 3, 0)` ; `_verdict_apex(levels, medians, gate=GATE)` → 3 branches §3 (le **plus haut**
    `N_APEX>0` franchissant = BARREAU TROUVÉ ; seulement 0 = DÉGÉNÉRÉ ; aucun = MUR INTRINSÈQUE).
  - `main_apex(levels=APEX_LEVELS, n_eval=8, R=4, seed=None, _return=False)` : balaye `n_apex` à `forage_payoff=3`
    fixe → `_measure_survival(_cfg(3), seeds, n_apex=lv)`. Mêmes seeds entre niveaux (appariement).
  - `_report` paramétré par le **label du knob balayé** (pour réutiliser la même fonction d'impression/provenance
    entre le sweep forage et le sweep apex) — petit refactor rétro-compatible.
- **Briques réutilisées (inchangées) :** `_cfg`, `_disable_kuzu`, `_setup_critical` (`leurre_frac=0`),
  `_load_champions`, `_reproduce`, `Harness`, `seed_at`, `st.jonckheere_terpstra`.
- **Reproductibilité :** `_disable_kuzu()` + `Harness(with_db=False)` ; `memory_retriever.stop()`+`clear()` ;
  `seed_at(s,0)` par ère ; mêmes seeds entre niveaux.

## 6. Tests (TDD)

- `_measure_survival` accepte `n_apex` : un sweep à `n_apex=0` vs `n_apex=12` produit des sorties **différentes**
  (le paramètre est réellement câblé), chacune reproductible (seedée). Forme `{ticks, famine, combat, kills}` conservée.
- `_verdict_apex` (pur) : 3 branches exactes (TROUVÉ à `N_APEX>0` en rapportant le plus haut franchissant /
  DÉGÉNÉRÉ seulement à 0 / MUR INTRINSÈQUE si aucun).
- `main_apex` : forme de sortie (table par niveau de densité, verdict ∈ 3 valeurs, `jt` présent), reproductible.
- **Non-régression 093 :** le `main` (sweep forage) existant reste vert (les 4 tests de 093 passent).

## 7. Plan d'exécution

1. Généraliser + tester (sub-agent-driven, TDD).
2. **Run direct** : smoke réduit, puis `main_apex(seed=<S>)` aux params gelés → table survie × `N_APEX`, verdict.
3. Écrire l'EDR 094 selon la branche atteinte (TROUVÉ / DÉGÉNÉRÉ / MUR INTRINSÈQUE).

## 8. Garde-fous

- `_disable_kuzu()` avant toute création de monde (contention KuzuDB mp).
- `seed_at` appariement strict entre niveaux ; mêmes seeds réutilisés à chaque `N_APEX`.
- Cause de mort lue post-ère dans `env.dead_agents` (energy≤0 = famine, hp≤0 = combat).
- `N_APEX=0` validé contre `_setup_critical` : `n_pos = 0` → aucun apex instancié, proies régulières conservées
  (forage pur) — config valide, non dégénérée côté code.
- Worktree `worktree-edr094-apex-sweep` sur `main` (inclut #31) ; commits path-scopés (sessions parallèles).

## 9. Provenance attendue

`results/lewis_apex_sweep_<seed>.json` : `levels (N_APEX), R, n_eval, table (survies + causes + kills par niveau),
medians, jt, verdict`. Outils : `tools/lewis_survival_sweep.py` (généralisé), `src/seed_ai/exp_stats.py`.
