---
id: EDR-112
type: EDR
title: Le monde EXIGE l'intelligence — stoneage et soup passent G0 (champion survit ~4x l'aleatoire)
status: validated
gate: G0
tests: [SDR-G0]
verdict: EXIGE
---

# EDR 112 : Le monde EXIGE l'intelligence — G0 passe sur stoneage et soup

## Contexte

Porte **G0** du fil directeur AGI (`SDR-G0`) : avant de mesurer le transfert (G1, north-star), prouver
que les mondes cibles **discriminent réellement la politique** — sinon `transfer_ratio` mesure du bruit
(cause-racine B). L'instrument **existait déjà** (« S2 », `tools/s2_demand.py` + `baseline_models.py` +
`s2_stats.py`, pré-enregistré `docs/superpowers/specs/2026-06-14-S2-World-Demands-Intelligence-design.md`)
mais n'avait **jamais été lancé jusqu'à un verdict**. Ce run l'exécute et consigne le résultat.

## Méthode

Champion #1 du HoF (172 nœuds) vs **3 baselines** : `random_action` (politique aléatoire, corps
identique), `random_genome` (réseau frais), `reflex` (heuristique naïve/prudente). 4 mondes. Survie
INDIVIDUELLE censurée + life_score, **appariement seedé** (Harness D1), **power analysis** (pilote →
K=12), verdict **IUT** (le champion doit battre TOUS les baselines) + correction **Holm** (FWER), Cliff δ,
IC du ratio. `benchmark_mode` (cohorte fixe, pas de reproduction/mutation/HGT), nuit OFF, scaffolds OFF.
seed=2026, 20 agents, max_ticks=400, 0% censure partout (max_ticks suffisant).

## Constat — G0 PASSE sur le substrat de prod

| Monde | Verdict | p_monde (Holm) | Cliff δ (vs random_action) | ratio survie | censure |
|---|---|---|---|---|---|
| **stoneage** (prod) | **EXIGE** | **0.003** | **+0.92** | **3.74–4.67×** | 0% |
| **soup** | **EXIGE** | 0.003 | +0.97 | 4.38–5.25× | 0% |
| agricultural | VOID | — | — | — | 0% |
| industrial | EXIGE | 0.003 | +0.92 | 3.74–4.67× | 0% |

Le champion bat **les trois** baselines (random_action, random_genome, reflex) en stoneage et soup —
effet quasi-maximal (Cliff δ → 1.0), survie ~4× supérieure, significatif après Holm. **Le monde de
production (stoneage) EXIGE l'intelligence : le substrat sur lequel G1 (transfert) démarrera n'est PAS
factice.** G0 est franchie pour les mondes qui comptent.

## Caveats (honnêteté)

1. **industrial = chiffres byte-identiques à stoneage** (δ=+0.92, ratio[3.74,4.67], p identiques) →
   `IndustrialWorld` délègue très probablement la dynamique à `Biosphere3D` ; son EXIGE n'est PAS une
   preuve indépendante. À traiter comme « stoneage déguisé » tant que la divergence n'est pas établie.
2. **agricultural = VOID** : le garde-fou de cohérence life_score de l'instrument a échoué (life_p=0.092)
   → indécis, **pas factice**. À re-régler (pas un verdict de monde factice).
3. **Reproductibilité partielle** : la mémoire ambiante KuzuDB reste active PENDANT l'ère (le tool ne
   stoppe `memory_retriever` qu'APRÈS chaque ère, cf. [[biosphere-ambient-memory-nonrepro]]) ; erreurs de
   clé dupliquée AGENT_THOUGHT observées = contention sessions parallèles → bruit, non-déterminisme
   résiduel. Le verdict (survie médiane sur K=12 ères, effet δ≈0.92) est robuste à ce bruit, mais une
   re-mesure ambient-OFF serait plus propre.
4. **Bug d'instrument corrigé en contournement** : `s2_demand._print_table` plante sur stdout non-utf8
   (Windows cp1252) à l'impression de « Cliff δ » → run via `PYTHONIOENCODING=utf-8`. Suivi : rendre le
   print Windows-safe.

## Conséquences

- **G0 franchie pour stoneage (prod) + soup** → débloque **G1** (transfert zéro-shot, north-star) sur
  stoneage. `SDR-G0` passé à `status: validated`.
- **Plan-suivi (backlog G0)** : (a) monde **Lewis** (config létale, régime dur EDR 110) + garde-fou
  **INCONCLUSIF au plancher** (`docs/superpowers/specs/2026-06-29-G0-World-Demand-Benchmark-design.md`) ;
  (b) trancher industrial vs stoneage ; (c) re-régler agricultural (VOID) ; (d) print Windows-safe.
