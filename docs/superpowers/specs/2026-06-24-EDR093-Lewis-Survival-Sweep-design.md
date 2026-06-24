# EDR 093 — Un premier barreau survivable en Lewis existe-t-il ? Sweep de l'économie d'énergie

**Statut :** pré-enregistrement (gelé avant données).
**Date :** 2026-06-24.
**Lignée :** 087→088→089→**090** (curriculum de létalité = NEGATIF PROFOND : pas de premier barreau survivable) → **093**.
**Numéro :** 091 (curriculum_transfer) et 092 (dreaming) pris par des sessions parallèles → ce travail = **093**.

## 1. Motivation

EDR 090 a montré que le curriculum de létalité échoue parce qu'**il n'y a pas de premier barreau survivable** :
les champions stoneage ne survivent pas au monde de Lewis, même à létalité minimale. Le diagnostic
post-090 (cette session) a établi le **mécanisme** :

> Les champions meurent de **FAMINE** (`energy ≤ 0`) en ~5-7 ticks (médiane), **pas** de combat (`hp ≤ 0`
> quasi-nul). Le drain d'énergie est ~13-16/tick (≈64× le métabolisme de base 0.25). Gros postes
> (`world_1_stoneage.py` step) : action 6 = **soin (−10)** et **lancer/attaquer (−10, l.1122)**. Dans un
> Lewis dense en apex (12 Mammouth/Ours), les champions **spamment des actions chères** → drain >> apport
> de forage (`forage_payoff=3.0`) → banqueroute → famine.

Le sweet-spot énergie d'EDR 085 (métab 0.25 / payoff 3.0) était calibré pour *stoneage* et **ne transfère
pas** à Lewis. **EDR 093 mesure si — et à quel apport énergétique — un premier barreau survivable existe**,
en balayant le knob de revenu de l'économie. Pas d'évolution, pas de langage : pure mesure de survie.

## 2. La prétention (1 variable — Commandement 15)

> Sur Lewis à **létalité 0** (apex présents, **pas de Leurres mortels** → on isole l'énergie de la
> létalité), il **existe** un niveau de `forage_payoff` où les champions stoneage survivent (survie médiane
> > 120 ticks). On mesure *si* et *où* le seuil est franchi.

**Variable manipulée :** `forage_payoff` ∈ `(3, 6, 12, 24, 48)` (de la valeur 085 vers ×16). Mécaniquement,
c'est le **multiplicateur de nutrition par proie mangée** (`world_1_stoneage.py:692` :
`reward = prey_reward(hp) * forage_payoff`) — le knob de **revenu par kill** de l'économie.

**Tout le reste fixe :** `base_metabolism = 0.25`, `N_APEX = 12`, `leurre_frac = 0`, champions HoF
(`_load_champions`), **pas d'évolution** (on mesure la survie brute des champions répliqués), pas de
langage (`use_ref_head=False`, `decode_act=False`).

**Pourquoi `forage_payoff` et pas `N_APEX` / coûts d'action :** c'est le knob de **revenu pur**, et le
résultat tranche les deux côtés de l'économie. Si un payoff modeste (6-12) débloque la survie → l'économie
manquait de revenu (barreau facile). Si même ×16 échoue → la **dépense compulsive** (actions −10) est le
mur, et le levier bascule côté coûts/densité d'apex (EDR suivant). Un seul balayage diagnostique « revenu
vs dépense ».

## 3. Métriques & règle de verdict (gelées)

- **Métrique primaire :** survie médiane (ticks) des champions par niveau de `forage_payoff`, sur R×n_eval
  ères seedées (appariées par seed entre niveaux : même monde initial à seed donné).
- **Tendance :** Jonckheere-Terpstra (la survie croît-elle avec le payoff ?), one-sided.
- **Sous-produit diagnostique (gratuit) :** décomposition cause de mort par niveau (famine `energy≤0` vs
  combat `hp≤0`, lue dans `env.dead_agents`) — confirme que la famine recule quand le revenu monte.

| Condition | Verdict |
|---|---|
| survie médiane > 120 à un `forage_payoff` ≤ 24 (×8) | **BARREAU TROUVÉ** — premier rung survivable à payoff X ; devient la base d'un curriculum corrigé (re-test 090). |
| survie > 120 **seulement** à 48 (×16) | **BARREAU TROP CHER** — un rung existe mais le monde doit être absurdement riche ; économie profondément cassée pour ces champions. |
| survie ≤ 120 **même** à 48 | **PAS DE RUNG PAR LE REVENU** — la dépense (actions −10 × densité apex) est le mur ; pivot vers coûts d'action / `N_APEX` (EDR suivant). |

Les trois branches sont informatives : succès = substrat fabriqué ; chaque échec localise le levier suivant
(revenu insuffisant trivialement, ou dépense incompressible).

## 4. Paramètres pré-enregistrés (gelés)

| Paramètre | Valeur | Note |
|---|---|---|
| `levels` (forage_payoff) | `(3, 6, 12, 24, 48)` | de 085 vers ×16 |
| `base_metabolism` | 0.25 | sweet-spot 085 (fixe) |
| `N_APEX` | 12 | comme 088/090 (fixe) |
| `leurre_frac` | 0 | isole l'énergie de la létalité |
| `max_ticks` | 300 | gate >120 valide à cette échelle (comme 089/090) |
| `num_agents` | 24 | comme 090 |
| `n_eval` | 8 | ères de mesure par (niveau, répétition) |
| `R` | 4 | répétitions appariées |
| gate de survie | 120 ticks | seuil de barreau survivable (089/090) |
| `max_population` | 150 | défensif (PR #29) ; jamais atteint ici (no-op avant merge #29) |

## 5. Outillage & architecture

- **Nouveau fichier** `tools/lewis_survival_sweep.py` (EDR 093). Aucune modification des artefacts existants.
- **Briques réutilisées (socle 090 mergé sur main) :**
  - `_setup_critical` (`tools/lewis_critical.py`) avec `leurre_frac=0`.
  - Runner déparasité façon `_run_era_clean` (`tools/lethality_curriculum.py`) : `memory_retriever.stop()`
    avant la boucle ; `_disable_kuzu()` avant toute création de monde.
  - `exp_stats` (`jonckheere_terpstra`, `bootstrap_ci`, médiane).
  - `Harness`, `seed_at` ; `_load_champions`, `_reproduce`.
- **Structure (esquisse, détail au plan) :**
  - `_cfg(forage_payoff)` → `WorldConfig` (métab 0.25, `forage_payoff=X`, `max_population=150`).
  - `_measure_survival(cfg, n_eval, base, leurre_frac=0, num_agents=24, max_ticks=300)` → lance n_eval ères
    propres (champions répliqués), renvoie `{ticks: [...], famine: k, combat: k}` (survies + décomposition
    cause de mort via `env.dead_agents`).
  - `_verdict(level_survivals)` → mappe (médianes par niveau, gate, seuils ×8/×16) vers les 3 branches.
  - `_report(h, table, levels, _return)` → médianes par niveau + JT + seuil franchi + verdict + `h.save`.
  - `main(levels, n_eval, R, seed, _return)` → boucle niveaux × répétitions seedées ; séquentiel (ères
    courtes, champions, pas d'évolution → rapide ; mp optionnel non requis).
- **Reproductibilité :** `seed_at(base, ·)` appariement entre niveaux ; `_disable_kuzu` ; pas d'évolution
  → pas de risque runaway-population (cap inutile mais posé par robustesse).

## 6. Tests (TDD)

- `_cfg` : pose `forage_payoff` et `max_population`.
- `_measure_survival` : renvoie `{ticks, famine, combat}`, longueurs correctes, reproductible (seedé).
- `_verdict` (pur) : 3 branches exactes (BARREAU TROUVÉ ≤24 / TROP CHER =48 / PAS DE RUNG >48).
- `main` : forme de sortie (table par niveau, verdict ∈ 3 valeurs), reproductible.

## 7. Plan d'exécution

1. Implémenter + tester (sub-agent-driven, TDD).
2. **Run direct** (pas de pilote lourd : ères courtes). `main(R=4)` → table survie × `forage_payoff`, verdict.
3. Écrire l'EDR 093 selon la branche de verdict atteinte.

## 8. Garde-fous

- `_disable_kuzu()` avant toute création de monde (contention KuzuDB mp, dette notée).
- `seed_at` appariement strict entre niveaux.
- Cause de mort lue post-ère dans `env.dead_agents` (energy≤0 = famine, hp≤0 = combat) — déjà validé cette
  session.
- Worktree `worktree-edr093-lewis-survival` sur `main` ; commits path-scopés (sessions parallèles).

## 9. Provenance attendue

`results/lewis_survival_sweep_<seed>.json` : `levels, R, n_eval, table (survies + causes par niveau),
medians, jt, threshold_payoff, verdict`. Outils : `tools/lewis_survival_sweep.py`, `src/seed_ai/exp_stats.py`.
