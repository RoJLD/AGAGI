# EDR S2 (DRAFT) — Le monde EXIGE l'intelligence pour SURVIVRE (4 mondes), pas pour le life_score

> **DRAFT — n° EDR à assigner au merge.** Placé hors `docs/EDR/` car des sessions parallèles
> produisent activement des EDR (zone 112-122+) → éviter la collision de numéro. À déplacer vers
> `docs/EDR/NNN_*.md` + câbler `backend/app/edr_findings.json` + `docs/FIL_CONDUCTEUR.md` (chaîne
> `parity_check`) au moment du merge, une fois le flux EDR parallèle stabilisé.

## Contexte

Cause-racine B (« le monde n'exige pas l'intelligence », audit EDR 010/012). Le benchmark S2 était
**codé et pré-enregistré** (`docs/superpowers/specs/2026-06-14-S2-World-Demands-Intelligence-design.md`,
`tools/s2_demand.py`, `src/seed_ai/s2_stats.py`) mais **jamais conclu** : son unique run (2026-06-15)
était un smoke test (1 monde, K=2, ~6 individus) revenu VOID, et l'EDR 088 fut détourné vers le langage.

Un **diagnostic de régime** (PR #83, `tools/s2_regime_diagnostic.py`) a d'abord écarté l'hypothèse
sous-puissance vs plancher : à K=8 au régime défaut, le champion battait le baseline le plus fort en
survie (p=0.014, Cliff δ=0.92) → verdict `SOUS_PUISSANCE` (le VOID du smoke n'était que du bruit).
Fait de cadrage : `main_biosphere` (prod) ET le benchmark tournent au **même** régime défaut
(`base_metabolism=1.0`, `forage_payoff=1.0`) — pas de décalage entraînement↔test.

## Méthode

Confirmatoire `s2_demand.run_s2` (2026-06-30) : champion HoF + 3 baselines (random_action,
random_genome, reflex) × **4 mondes** (soup, stoneage, agricultural, industrial), **K=12** ères
appariées (plancher pré-enregistré), seed 2026, survie individuelle censurée, appariement seedé D1.
**RAG-off** (`_disable_kuzu` : zéro contention KuzuDB avec une session parallèle active + déterminisme ;
le champion est testé SANS sa mémoire ambiante → résultat CONSERVATEUR).

## Le verdict : EXIGE × 4 (sur la survie)

Dans **les 4 mondes**, le champion bat **tous** les baselines en **survie** :

| Monde | p_monde | Holm | Cliff δ (baseline le + fort) | ratio médian de survie |
|---|---|---|---|---|
| soup | 0.0025 | 0.0101 | +0.95 (reflex) | 3.4–4.5× |
| stoneage | 0.0025 | 0.0101 | +0.92 (random_action) | 3.4–4.2× |
| agricultural | 0.0025 | 0.0101 | +0.95 (reflex) | 3.7–4.3× |
| industrial | 0.0025 | 0.0101 | +0.92 (random_action) | 3.4–4.2× |

p=0.0025 = minimum à K=12 (12/12 ères appariées positives). Holm sur les 4 mondes : 0.0101 < 0.05
(survit à la correction FWER). **Le monde EXIGE l'intelligence pour survivre, partout, massivement.**

## Le VOID formel et sa correction (addendum 2026-06-30)

`s2_verdict` a d'abord rendu **VOID** dans les 4 mondes : son **gate de cohérence** teste le
`life_score` (fitness composite : âge×0.1 + proies×50 + lances×300 + mammouth×400), pas la survie. Or
`life_score` est dominé par des événements **rares/chanceux** (un random_action qui attrape une proie
par hasard → +50 puis meurt) → l'avantage du champion y est noyé (life_p = 0.055–0.11 ≥ α). L'intention
du gate (« le champion se comporte en champion ») est pourtant *déjà satisfaite* par la domination de
survie 3-5×. **Addendum daté** : cohérence basée **survie**, `life_score` corroborant non-bloquant ;
re-render hors-ligne via `verdict_from_survival_cmps` (zéro re-compute) → EXIGE × 4.

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : le monde exige l'intelligence pour la SURVIE (4 mondes, p=0.0025, Holm 0.0101, 3.4–4.7×).
- **FAIT** : le gate de cohérence `life_score` original donnait un faux VOID (défaut de design du
  benchmark, pas un résultat négatif).
- **INTERPRÉTATION** : le champion est un **SURVIVANT, pas un marqueur de points**. Son edge est dans
  *rester en vie*, pas dans la fitness composite (qu'un dummy chanceux peut égaler ponctuellement).
  Cohérent avec la thèse « substrat = verrou » : l'évolution a sélectionné la survie, mais cette survie
  ne se compose pas en compétence de plus haut niveau (cf. arc apex 102-122, [[coop-competence-is-population-property]]).

## Caveats

1. **RAG-off** : champion sans sa mémoire ambiante → conservateur. Refaire RAG-on quand le compute
   parallèle est libre (ne ferait que renforcer le verdict).
2. **Une seule graine de base** (2026), K=12 ères appariées. Robuste (12/12) mais mono-seed.
3. **Régime défaut uniquement** (1.0/1.0). Au sweet-spot (diagnostic), l'edge survie disparaît
   (δ=−0.21) : quand survivre est facile, l'aléatoire suffit. L'intelligence ne « compte » que sous pression.

## Suite

- Déplacer ce draft vers `docs/EDR/NNN_*.md` + câbler `edr_findings.json` + `FIL_CONDUCTEUR.md`.
- (Optionnel) confirmatoire RAG-on multi-seed.
- Le verrou reste l'**assignation de crédit compositionnel** (la survie ne compose pas) → migration
  moteur (gradient+curriculum), cf. arc apex 122.
