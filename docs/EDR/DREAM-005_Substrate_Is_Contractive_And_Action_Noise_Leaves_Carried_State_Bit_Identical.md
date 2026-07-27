---
id: EDR-DREAM-005
type: EDR
title: "Corroboration dynamique hors-monde : le substrat récurrent est CONTRACTIF (point fixe sous entrée constante = une seule action) et le bruit d'action laisse l'état porté BIT-IDENTIQUE à off — la diversité d'action n'est PAS le mécanisme"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
corroborates: [EDR-DREAM-004]
---

## Question
[[EDR-DREAM-004]] a conclu « échappement d'attracteur sur l'état porté, pas exploration d'action », en
mesurant in-world que le bruit d'action reproduit le fourrage (83 %) mais pas la reproduction (13 %).
Cette conclusion a une **conséquence dynamique directe, testable sans monde ni KuzuDB** : sous entrée
constante, l'état récurrent `H` doit converger vers un point fixe (substrat contractif), le bruit
d'action doit laisser `H` inchangé (il n'écrit jamais dans l'état), et le bruit porté doit faire errer
`H`.

## Méthode
Sonde purement numpy (`tools/substrate_attractor_probe.py`) : 12 génomes du substrat, organe ON,
conduits `T=50` ticks sous **entrée constante** (zéro, puis obs aléatoire fixe), dans trois bras —
`off`, `action` (`ACTION_NOISE=8`), `H` (`FORCE_DREAM=8, DREAM_NOISE=0.2`). Mesures par agent : la
trajectoire de l'état `self.H_prev_batch` et l'action de déplacement (`argmax` des 8 logits).

**Détecteur auto-calibré** dans le fichier : un système contractif connu (`H←0.5·H`) doit être classé
« converge », une marche aléatoire connue « ne converge pas ». Sinon un détecteur cassé fabriquerait
le verdict.

## Résultats (identiques sous entrée zéro ET obs aléatoire fixe)

| | off | action | H (porté) |
|---|---|---|---|
| **P1** agents dont `H` converge (/12) | 9-12 | 9-12 | **0** |
| **P2** `H(off) == H(bras)` bit-à-bit (/12) | — | **12** | 0 (divergence 2.2-3.6) |
| **P3** diversité d'action (distinctes/agent) | **1.0** | 8.0 | 7-8 |

## Verdict
**`SUBSTRATE_CONTRACTIVE__ACTION_NOISE_LEAVES_CARRIED_STATE_IDENTICAL__DIVERSITY_IS_NOT_THE_MECHANISM`**

1. **Le substrat est contractif** : sous entrée constante, `H` converge vers un point fixe (off &
   action gèlent, pas → 0 ou ~1e-6), et au point fixe **l'agent émet une seule action pour toujours**
   (diversité 1.0) — un attracteur comportementalement passif.
2. **Le bruit d'action laisse l'état porté BIT-IDENTIQUE à off** (12/12, les DEUX régimes d'entrée),
   parce que le seam écrit dans les logits APRÈS `self.H_prev_batch = H`. L'action jitter, l'état reste
   *exactement* aussi figé. C'est la raison mécaniste, indépendante de l'entrée, du 7.4× d'échec de
   DREAM-004.
3. **La diversité d'action n'est PAS le mécanisme.** Action et porté maximisent tous deux la diversité
   (8.0 vs 7-8), pourtant DREAM-004 mesure l'action à 13 % du bénéfice. Si la diversité comptait,
   l'action marcherait. Seul le **mouvement de l'état porté** agit — que le bruit d'action ne peut pas
   produire par construction.

## Portée — ce qui est rigoureux, ce qui est illustratif
* **P2 est rigoureux et indépendant de l'entrée** : c'est une propriété du POINT D'INJECTION du bruit,
  pas du régime. C'est le cœur du corroborant.
* **P1/P3 sont des démonstrations sous entrée CONSTANTE.** In-world l'entrée varie à chaque tick, donc
  le « point fixe passif → une seule action » est illustratif du régime dynamique du substrat, **pas une
  preuve** que l'attracteur passif domine in-world. Un corroborant peut être un artefact du régime de
  test (règle [[floor-pinned-verdict-and-retroactive-gap]]) ; on ne re-prouve pas DREAM-004, on montre
  que le substrat a la dynamique que DREAM-004 postule.

## Leçon (registre) — piège attrapé sur ma propre sonde
Première version : P2 tombait à 0/12 sous obs aléatoire, 12/12 sous obs zéro — apparence d'un effet
« dépendant de l'entrée ». **C'était un confondant de POPULATION** : `MambaAgent()` tire `W` sur le
`np.random` GLOBAL (`mamba_agent.py:23`), et créer les trois bras en séquence sans re-seeder donnait
des génomes DIFFÉRENTS par bras. Sous entrée zéro tous convergent vers le même point fixe (H→0,
indépendant de `W`) → faux bit-identique ; sous entrée non nulle le point fixe dépend de `W` → faux
0/12. Corrigé (seed global identique avant création) → 12/12 dans les deux régimes. **Classe E9/E15 :
comparer des bras, c'est d'abord vérifier qu'ils portent la MÊME population** — le piège exact que le
dépôt a payé trois fois sur l'arc WARM, ici sur mon propre outil de diagnostic.

## Dette — FERMÉE dans la même passe
La sonde produit une affirmation scientifique (« le substrat est contractif ») → c'est un INSTRUMENT.
Plutôt que de la laisser dans le scratchpad (hors du cliquet, angle mort connu de
[[instrument-calibration-ratchet]]), elle est **promue dans `tools/substrate_attractor_probe.py`** et
son cœur `measure_convergence` **calibré** dans `tests/sandbox/test_instrument_calibration.py`
(déclaration `CALIBRATED`) : contractif connu → CONVERGE, marche aléatoire connue → NON, + monotonie du
pas de queue en la contraction, + borne trajectoire-trop-courte. Cliquet : 80/11 → **81/12**, 0 nouveau
non calibré. La promotion applique à cette sonde la discipline que le record lui-même réclame.

Converge [[EDR-DREAM-004]], [[EDR-DREAM-003]], [[planner-depth1-refuted]], REF-EXPERIMENT-PREFLIGHT.
