# EDR 101 — Première intervention : rescale `base_metabolism` débloque-t-il la survie en Lewis ?

**Statut :** pré-enregistrement (gelé avant données).
**Date :** 2026-06-24.
**Lignée :** 090→093→094→098→099→100 (drain = métabolisme du phénotype, `phenotype_energy_drain≈54`) → **101**.
**Numéro :** 101 vérifié libre.

## 1. Motivation

Six EDR (090-100) ont diagnostiqué le mur de survie de Lewis (famine au tick 5, ~12/tick à `N_APEX=0`) jusqu'à
une cause-racine : la phase biologie porte 90% du drain (099), et son sous-poste dominant est le **métabolisme**
(100) — `metab = base_metabolism(0.25) × phenotype_energy_drain`, avec `phenotype_energy_drain ≈ 54` (~50× les
autres sous-postes). EDR 101 est la **première intervention** de la chaîne, après six diagnostics : tester si
**réduire `base_metabolism` débloque la survie**.

`base_metabolism` est un **knob de monde** (config, indépendant du génome). Le sweep teste directement si le mur
métabolique est **supprimable par config** : à `base_metabolism = 0`, le terme métabolisme s'annule entièrement
(`metab = 0` peu importe `phenotype_energy_drain`).

**Caveat (interprétation, pas validité) :** `phenotype_energy_drain` dérive de `genome.W[0:5]`
(`phenotype_hp_bonus = sum(|W[0:5]|) × 10`, `mamba_agent.py:46-49`). Un finding parallèle (session NAS) indique
que `MambaAgent.from_genome` aplatit l'architecture du génome ; `phenotype_energy_drain ≈ 54` pourrait donc être
en partie un **artefact d'aplatissement**, pas un trait « purement évolué ». **Le sweep `base_metabolism` reste
valide quel que soit ce caveat** : il teste si le mur métabolique des agents *tels qu'exécutés* est supprimable.
La vérification `from_genome` (le trait change-t-il sous aplatissement ?) est designée **EDR 102** (séquence
décidée : réparer d'abord, comprendre l'origine du trait ensuite).

## 2. La prétention (1 variable — Commandement 15)

> Sur Lewis à `N_APEX=0` (monde vide), il **existe** une valeur de `base_metabolism` où les champions stoneage
> survivent (survie médiane > 120 ticks). On mesure *si* et *où* le seuil est franchi.

**Variable manipulée :** `base_metabolism` ∈ `(0.25, 0.1, 0.05, 0.025, 0.0)` (de la valeur 085 vers 0).
**Tout le reste fixe :** `N_APEX = 0`, `forage_payoff = 3`, `leurre_frac = 0`, `PREY_COUNT = 15`,
`max_ticks = 300`, `num_agents = 24`, champions HoF répliqués (`_load_champions` + `_reproduce`), pas
d'évolution, pas de langage (`use_ref_head=False`, `decode_act=False`).

**Pourquoi `base_metabolism`.** EDR 100 a montré que le métabolisme (`base × phenotype_energy_drain`) est ~90% du
drain. `base_metabolism` est le multiplicateur de monde, sweepable sans toucher le génome. Si le réduire débloque
la survie → le mur est **réparable par config** (premier barreau survivable). Si même `base_metabolism=0` échoue
→ le métabolisme n'est pas le seul mur (les champions ne foragent pas assez) → pivot comportement/forage.

## 3. Métriques & règle de verdict (gelées)

- **Métrique primaire :** survie médiane (ticks) par niveau de `base_metabolism`, R×n_eval ères seedées,
  appariées par seed entre niveaux.
- **Tendance :** Jonckheere-Terpstra one-sided — la survie **croît**-elle quand `base_metabolism` **décroît** ?
  (groupes en ordre de `base_metabolism` décroissant `0.25→0.0` = ordre naturel des niveaux).
- **Sous-produits diagnostiques (gratuits), par niveau :** famine/combat (cause de mort), kills moyens/agent.

| Condition | Verdict |
|---|---|
| survie médiane > 120 à un `base_metabolism > 0` | **RESCALE SUFFIT** — le mur métabolique est supprimable par config ; **premier barreau survivable trouvé** à `base_metabolism = X` (re-test du curriculum 090 possible). On rapporte le **plus haut** `base_metabolism` survivable. |
| survie > 120 **seulement** à `base_metabolism = 0` | **RESCALE EXTRÊME** — il faut un métabolisme **nul** pour survivre ; le trait est trop lourd, un rescale réaliste ne suffit pas. Pointe vers EDR 102 (le trait est-il un artefact `from_genome` ?) / ré-évolution du substrat. |
| survie ≤ 120 **même** à `base_metabolism = 0` | **PAS LE MÉTABOLISME SEUL** — supprimer entièrement le métabolisme ne sauve pas ; les champions ne foragent pas assez pour couvrir le drain résiduel (~1-2/tick). Pivot vers forage/comportement (le mur n'est pas que l'énergie dépensée). |

Les trois branches sont informatives : succès = barreau survivable fabriqué par config ; chaque échec localise le
levier suivant (trait trop lourd → EDR 102 ; ou forage/comportement).

## 4. Paramètres pré-enregistrés (gelés)

| Paramètre | Valeur | Note |
|---|---|---|
| `levels` (`base_metabolism`) | `(0.25, 0.1, 0.05, 0.025, 0.0)` | de 085 vers 0 |
| `N_APEX` | 0 | monde vide (isole le métabolisme) |
| `forage_payoff` | 3 | 085 (fixe) |
| `leurre_frac` | 0 | létalité 0 |
| `PREY_COUNT` | 15 | forage régulier |
| `max_ticks` | 300 | gate >120 valide |
| `num_agents` | 24 | comme 093/094/098 |
| `n_eval` | 8 | ères par répétition |
| `R` | 4 | répétitions appariées |
| gate de survie | 120 ticks | seuil de barreau survivable |

## 5. Outillage & architecture

- **Extension DRY de `tools/lewis_survival_sweep.py`** (mergé) :
  - `_cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False, base_metabolism=METAB)` : ajout du
    param `base_metabolism` (défaut `METAB=0.25`) → pose `cfg.base_metabolism`. **Rétro-compatible** (les appels
    sans l'argument gardent 0.25).
  - `METAB_LEVELS = (0.25, 0.1, 0.05, 0.025, 0.0)` ; `_verdict_metab(levels, medians, gate=GATE) -> str` → 3
    branches §3 (même forme que `_verdict_apex` : un `base_metabolism>0` franchit → RESCALE SUFFIT ; seul 0 →
    RESCALE EXTRÊME ; aucun → PAS LE MÉTABOLISME SEUL).
  - `main_metab(levels=METAB_LEVELS, n_eval=8, R=4, seed=None, _return=False)` : balaye `base_metabolism` à
    `N_APEX=0` et `forage_payoff=3` fixes → `_measure_survival(_cfg(3, base_metabolism=lv), seeds, n_apex=0)`.
    Mêmes seeds entre niveaux (appariement).
  - `_report` réutilisé (déjà paramétré `knob`/`verdict_fn` depuis 094) → `knob="base_metabolism"`,
    `verdict_fn=_verdict_metab`.
- **Réutilisé inchangé :** `_measure_survival` (093, survie + causes + kills), `_setup_critical` (`n_apex=0` →
  correctif monde vide 094), `_disable_kuzu`, `_load_champions`, `_reproduce`, `Harness`, `seed_at`,
  `st.jonckheere_terpstra`.
- **Reproductibilité :** `_disable_kuzu()` + `Harness(with_db=False)` ; `memory_retriever.stop()`+`clear()` ;
  `seed_at(s,0)` par ère ; mêmes seeds entre niveaux.

## 6. Tests (TDD)

- `_cfg(3, base_metabolism=0.05).base_metabolism == 0.05` ; `_cfg(3).base_metabolism == METAB` (défaut).
- `_verdict_metab` (pur) : 3 branches exactes (RESCALE SUFFIT si un `base_metabolism>0` franchit / RESCALE EXTRÊME
  seulement à 0 / PAS LE MÉTABOLISME SEUL si aucun).
- `main_metab` : forme de sortie (table par niveau de `base_metabolism`, verdict ∈ 3 valeurs, `jt` présent),
  reproductible (seedé).
- **Non-régression :** les tests existants (093/094/098/099/100) restent verts (`_cfg` rétro-compatible).

## 7. Plan d'exécution

1. Implémenter + tester (sub-agent-driven, TDD).
2. **Run direct** : smoke réduit, puis `main_metab(seed=101)` aux params gelés → table survie ×
   `base_metabolism`, verdict.
3. Écrire l'EDR 101 selon la branche (RESCALE SUFFIT / RESCALE EXTRÊME / PAS LE MÉTABOLISME SEUL), et amorcer
   l'EDR 102 (vérification `from_genome` du trait) ou la branche pivot.

## 8. Garde-fous

- `_disable_kuzu()` avant toute création de monde ; `seed_at` appariement strict entre niveaux.
- `N_APEX=0` → correctif `_setup_critical` (monde vide) déjà validé 094.
- Cause de mort lue dans `env.dead_agents` (energy≤0 = famine, hp≤0 = combat).
- **Caveat `from_genome` documenté** dans l'EDR : `phenotype_energy_drain≈54` peut être altéré par l'aplatissement
  (finding NAS parallèle) ; le sweep teste l'intervention indépendamment ; EDR 102 vérifiera le trait.
- Worktree `worktree-edr101-metab-rescale` sur `main` (inclut #52) ; commits path-scopés.

## 9. Provenance attendue

`results/lewis_metab_sweep_<seed>.json` : `levels (base_metabolism), R, n_eval, table (survies + causes + kills
par niveau), medians, jt, verdict`. Outils : `tools/lewis_survival_sweep.py` (étendu), `src/seed_ai/exp_stats.py`.
Lignée : 090→093→094→098→099→100→**101**.
