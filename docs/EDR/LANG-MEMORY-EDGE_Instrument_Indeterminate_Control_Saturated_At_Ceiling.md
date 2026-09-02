---
id: EDR-LANG-MEMORY-EDGE
type: EDR
title: "3ᵉ arête language→memory : INDÉTERMINÉ D'INSTRUMENT — les deux bras porteurs PASSENT, mais le contrôle d'alias sature au plafond (le cas calibré E3 occ.3 tire en production)"
status: active
verdict: EDGE_INSTRUMENT_INDETERMINATE_CONTROL_SATURATED
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question et règle scellée

L'arête « language DEMANDE memory » tient-elle sur le substrat BILINÉAIRE au point-référence S1 —
3ᵉ arête du graphe AGI-Taxonomy, première par ablation SUBSTRAT (H-reset) ? Règle scellée AVANT le
run : `docs/preregistrations/LANG-MEMORY-EDGE.json` — ordre de lecture IMPOSÉ (garde d'alias
d'abord, puis PRESENT, puis PRINCIPAL, puis barre ; la première branche qui mord ARRÊTE).
Point de fonctionnement scellé : lr=0.002, 3600 épisodes, D=0, K=6, n=12 seeds — établi par le
balayage S1 (`results/lang_memory_sweep.json` : référence 0,744 à D=0 ; **lr=0.02 mort partout** ;
**D=2 : 3/3 à la chance au même point** — la rétention 2-délais reste hors du régime, cf.
[[EDR-LOCK-001]] 4ᵉ manifestation).

## Résultats (n=12, `results/lang_memory_edge.json`)

| bras | verdict `ablation_verdict` | intact méd | ablaté méd | ratio |
|---|---|---|---|---|
| PRINCIPAL (learned) | **X_DEMANDED** | 0,750 | 0,161 | **4,66** |
| PRESENT (specificity) | **X_DECOY** | 0,773 | 0,656 | 1,18 |
| CONTROL (garde `alias_guard_verdict`) | **DEGENERATE_CONTROL** → functional_aliasing=**fail** | ~0,99 | 1,000 | — |

`leakage`=0,016, `leak_seeds`=0 ; barre : `coord_intact`=0,750 ≥ `emergence_bar`=0,5 (AU-DESSUS).

## Verdict

**`EDGE_INSTRUMENT_INDETERMINATE_CONTROL_SATURATED`** — branche scellée « instrument_indetermine » :
la garde d'alias rend DEGENERATE_CONTROL, la lecture s'arrête, **AUCUNE arête n'entre dans le
graphe**, malgré trois branches aval positives.

1. **La garde a tiré sur SON cas calibré.** Le bras CONTROL vit collé au plafond (~0,99/1,000 des
   deux côtés) : `leakage ≈ 0` y est arithmétiquement FORCÉ, un `pass` serait vide de sens — c'est
   littéralement le cas gelé `[1.0]*3 vs [1.0]*3` (E3 occ.3, `results/lang_memory_diagnostic.json`)
   qui a motivé la branche DEGENERATE_CONTROL le 2026-09-01. Première fois qu'elle mord en
   production, un jour après sa pose : la tâche CONTROL (feedforward, c montré directement) est
   TROP FACILE au point de fonctionnement qui rend LANG apprenable.
2. **Ce qui est acquis et REND LA REPRISE COURTE** : la spécificité — le bras dont l'issue négative
   était réellement atteignable — a PASSÉ (PRESENT : même ablation, information redondante,
   0,773→0,656, X_DECOY net). Le mur de l'ancienne sonde (substrat plain, plafond 0,3889) est bien
   levé : la référence apprend à 0,750, au-dessus de la barre. Il ne manque QUE un contrôle d'alias
   vivant sous plafond.
3. **Un négatif d'instrument n'est pas un négatif d'arête** : rien ici ne dit que l'arête est
   fausse — elle est NON GRAVABLE au standard de la porte (`check_agi_taxonomy` : ablation substrat
   → functional_aliasing='pass' exigé, 'n/a' interdit).

## Reprise (exige un RE-SCELLEMENT — clause de la règle)

Durcir la tâche CONTROL pour qu'elle vive SOUS le plafond au même point de fonctionnement
(candidats, par simplicité : K_control > K ; ou éval CONTROL à budget d'entraînement réduit ; ou
cible c bruitée) — puis re-sceller `LANG-MEMORY-EDGE-bis` et NE REJOUER QUE le bras CONTROL si le
protocole des deux autres bras est inchangé (les 24 cellules mesurées restent valides, persistées).

## Portée

* Diagnostic d'instrument, pas de substrat ; les hedges du point S1 s'appliquent (D=0 seulement,
  crédit REINFORCE, tâche `(q+key)%K`).
* Le smoke seed-0 du bras PRESENT (0,767/0,655) avait prédit le comportement du n complet — la
  chute résiduelle ~0,11 confirmée reste dans la bande decoy (confond déclaré d'avance : tranché,
  la spécificité tient).
* CONTROL ablaté (1,000) légèrement > intact (~0,99) : le H-reset retire la nuisance portée — sens
  attendu pour une tâche feedforward, sans poids.
