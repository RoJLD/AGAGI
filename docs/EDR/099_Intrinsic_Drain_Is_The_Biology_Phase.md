---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-099
type: EDR
title: "TARIF=BIOLOGIE : le drain intrinsèque de Lewis est la phase biologie (90%)"
status: legacy
gate: foundational
---

# EDR 099 — TARIF=BIOLOGIE : le drain intrinsèque de Lewis est la phase biologie (90%)

## Contexte

Quatre EDR ont réfuté quatre leviers du mur de survie de Lewis (famine au tick 5, drain ~12-16/tick, même à
`N_APEX=0`) : létalité (090), revenu `forage_payoff` (093), densité d'apex `N_APEX` (094), `brain_cost`
surprise-amplifié (098). **Leçon répétée : deviner le poste mène à des faux.** EDR 099 cesse de deviner et
**décompose** le bilan énergétique par tick à `N_APEX=0` (monde vide) en phases instrumentées, pour **nommer**
le poste dominant. Pré-enregistrement : `docs/superpowers/specs/2026-06-24-EDR099-Intrinsic-Drain-Decomposition-design.md`.

Instrumentation opt-in (`trace_energy_sinks`, défaut OFF → inerte) : 5 captures d'énergie aux frontières de phase
dans `world_1_stoneage.py:step()`, décomposant le drain par tick et par agent en **4 phases** :
`brain` (coût de calcul) | `action` (throw + signal) | `biologie` (`_resolve_biology` = métab + terrain + carry) |
`mouvement` (pénalité de move bloqué, l.1288).

## Le verdict : TARIF=BIOLOGIE

La phase **biologie** porte **90%** du drain. Pas le throw (que j'avais désigné comme suspect principal), pas le
mouvement, pas le calcul.

| phase | énergie/tick/agent | % du net | poste |
|---|---|---|---|
| brain | −0.01 | −0.1% | `brain_cost` (098 : négligeable, ici ≈0) |
| action | 0.71 | 5.9% | throw (−10/−5) + signal |
| **biologie** | **10.81** | **90.1%** | **métabolisme + terrain + carry** (`_resolve_biology`) |
| mouvement | 0.48 | 4.0% | friction de move bloqué (murs) |
| **NET** | **11.99** | — | (budget famine : E=80 / mort ~tick 5-7 ≈ 12-16/tick ✓) |

(R=4, n_eval=8, seed=199, n=1631 agents, commit `be61606`.)

## Le mécanisme : le coût biologique de base, pas une action chère

Le drain n'est **pas** une action coûteuse spammée (le suspect post-098 était le throw, à −10). Le throw ne pèse
que 5.9% — les champions ne lancent presque pas. Le mur est le **coût biologique structurel** appliqué à chaque
tick par `_resolve_biology` : métabolisme de base (`base_metabolism × phenotype_energy_drain`, l.631), drain de
terrain (biome, l.634), poids porté (`carry_weight × 0.5`, l.645). À `N_APEX=0` (pas de combat, heal gardé off),
ce coût biologique de fond — ~10.8/tick — dépasse de loin l'apport de forage, et tue par famine au tick 5.

C'est cohérent avec toute la lignée : le mur est **intrinsèque** (094) parce que le coût biologique du phénotype
champion, transplanté de stoneage dans Lewis, est trop lourd pour l'économie de forage de Lewis. Le sweet-spot
énergie d'EDR 085 (`base_metabolism=0.25`) était calibré pour *stoneage* ; en Lewis, la phase biologie nette
(après forage) reste fortement déficitaire.

## La correction de couverture (3 → 4 phases, avant données)

La première instrumentation (3 phases) ne traçait que `[e0 … après _resolve_biology]` et **ratait la pénalité de
move bloqué** (l.1288). La revue finale du code l'a détecté **avant tout run gelé** (défaut d'instrument, pas un
résultat). On a amendé l'instrument (phase `mouvement` ajoutée, span étendu à la fin de l'itération, avant le
reset de reproduction `energy=50` l.1308) — méthodologiquement propre puisque aucune donnée officielle n'existait.

> **La revue estimait le trou à ~51% du drain ; la mesure le réduit à 4.0%.** L'écart venait d'une confusion : la
> revue englobait le **reset de reproduction** (`energy=50` quand un agent énergie-maxé enfante, −30 ponctuel)
> dans le « drain ». Ce reset n'est **pas** un drain (c'est un mécanisme de reproduction) et les champions mourant
> de famine ne l'atteignent jamais ; l'instrument 4-phases le capture `e_fin` **avant** ce bloc. Le vrai trou —
> la friction de mouvement bloqué — n'est que 0.48/tick. Le verdict TARIF=BIOLOGIE (90%) tient avec **couverture
> complète** et marge confortable au-dessus du seuil gelé (50%) : aucun résidu ne peut le renverser.

## Le vrai levier (re-pointé) : l'économie biologique de Lewis

EDR 099 localise le drain à la phase **biologie**. Le levier suivant — enfin ciblé, plus à l'aveugle — est
l'**économie biologique de base de Lewis**. EDR 100 doit décomposer la phase biologie **plus finement**
(métabolisme vs terrain vs carry) pour isoler le sous-poste dominant, puis rééquilibrer :
- **métabolisme** (`base_metabolism × phenotype_energy_drain`) — recalibrer pour le phénotype champion en Lewis ;
- **drain de terrain** (biome) — la géographie de Lewis est-elle plus coûteuse que stoneage ?
- **carry** (`carry_weight × 0.5`) — les champions traînent-ils trop d'inventaire ?

**Corroboration croisée :** une session NAS parallèle a réfuté le **coût métabolique de compute** (coefficient sur
le brain) — cohérent avec notre phase `brain` ≈ 0%. Le drain est la biologie de **fond**, pas le calcul.

## Honnêteté & méthode

- **Mesure, pas supposition.** La valeur d'EDR 099 est d'avoir **mesuré** le poste après quatre suppositions
  réfutées (heal, brain_cost, throw, …). Le throw — mon suspect principal — pèse 5.9%, pas 90%. La décomposition
  a vaincu l'intuition.
- **Couverture complète, vérifiée.** `net = 11.99/tick` couvre le budget famine (E=80, mort ~tick 5-7). Les 4
  phases télescopent exactement vers le net (par construction). La pénalité de mouvement et le reset de
  reproduction sont correctement traités (l'un compté, l'autre exclu).
- **Instrumentation inerte.** Les 5 captures sont gardées par `trace_energy_sinks` (défaut OFF) → zéro impact sur
  087-098 et les sessions parallèles partageant `world_1_stoneage.py` (non-régression : 11 tests verts, flag
  jamais posé hors mesure).
- **Reproductibilité.** `_disable_kuzu()` + `Harness(with_db=False)` ; `seed_at` par ère ; lecture `_e_phases`
  read-only ; normalisation par âge (anti-biais survivants).
- **Limite connue.** La décomposition s'arrête à la phase biologie (granularité phase, pas sous-poste) ; quel de
  métab/terrain/carry domine est la question d'EDR 100.

## Variables d'expérience

Phase **biologie** (le coupable) → décomposer en **métabolisme / terrain / carry** (EDR 100), puis rééquilibrer.
Outils : `tools/lewis_survival_sweep.py` (`main_decompose`, `_measure_drain`, `_verdict_drain` 5 branches),
`src/worlds/world_1_stoneage.py` (5 hooks opt-in `trace_energy_sinks`), `src/environments/config.py` (flag).
Provenance : `results/lewis_drain_decompose_199.json` (R=4, n_eval=8, TARIF=BIOLOGIE). Lignée : 090→093→094→098→**099**.
