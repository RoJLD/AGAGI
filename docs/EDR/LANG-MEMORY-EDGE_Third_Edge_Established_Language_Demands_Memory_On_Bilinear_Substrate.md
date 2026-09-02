---
id: EDR-LANG-MEMORY-EDGE-BIS
type: EDR
title: "3ᵉ arête ÉTABLIE — language DEMANDE memory sur le substrat bilinéaire (4,97×, n=12, garde d'alias SURGICAL) : première arête par ablation de SUBSTRAT du graphe AGI-Taxonomy"
status: active
verdict: LANGUAGE_DEMANDS_MEMORY_EDGE_ESTABLISHED
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
extends: [EDR-LANG-MEMORY-EDGE]
---

## Question et règle scellée

Reprise prescrite par [[EDR-LANG-MEMORY-EDGE]] (INDÉTERMINÉ D'INSTRUMENT : contrôle saturé au
plafond). Règle re-scellée AVANT le run : `docs/preregistrations/LANG-MEMORY-EDGE-bis.json` —
identique à l'originale (mêmes branches, MÊME ordre : alias → PRESENT → PRINCIPAL → barre) plus le
correctif d'instrument : **bruit d'entrée à dose connue sur CONTROL** (`control_input_noise`=0,15,
l'entrée montrée ment avec prob 0,15, la cible reste vraie) → plafond structurel (1−p)+p/K = 0,875
des DEUX bras, entraînement complet donc robuste au H porté. Le sous-échantillonnage seul était un
piège arithmétique MESURÉ (ci<0,95 ∧ ca=1,0 ⇒ leakage>tol forcé). RE-RUN COMPLET des 3 bras, n=12 —
pas de mélange de populations ; la première mesure reste gravée (`results/lang_memory_edge.json`).

## Résultats (n=12, `results/lang_memory_edge_bis.json`)

| bras | verdict `ablation_verdict` | intact méd | ablaté méd | ratio |
|---|---|---|---|---|
| PRINCIPAL (learned) | **X_DEMANDED** | **0,819** | 0,165 | **4,97** |
| PRESENT (specificity) | **X_DECOY** | 0,829 | 0,695 | 1,19 |
| CONTROL (garde `alias_guard_verdict`) | **SURGICAL** → functional_aliasing=**pass** | ≈0,87 | ≈0,87 | `leakage`=0,003 |

`leak_seeds`=0 · barre : `coord_intact`=0,819 ≥ `emergence_bar`=0,5 · point : lr=0.002, 3600 ép.,
D=0, K=6, bilinéaire (`EVO`-point S1, `results/lang_memory_sweep.json`).

**Calibration prédictive du correctif, validée au n complet** : plafond prédit en forme close 0,875 ;
contrôle mesuré ≈0,866 des deux côtés — l'injection à dose connue s'est comportée exactement comme
annoncé au smoke (0,853/0,870, seed 0).

## Verdict

**`LANGUAGE_DEMANDS_MEMORY_EDGE_ESTABLISHED`** — branche scellée « arete_etablie » (les quatre
lectures positives, dans l'ordre imposé) :

1. **« Language demande memory » est causalement établi sur le substrat bilinéaire** : effacer l'état
   porté (H-reset) entre l'encodage et l'usage effondre la tâche référentielle à la chance
   (0,819 → 0,165), pendant que le MÊME reset laisse indemnes (a) la tâche à information redondante
   (PRESENT, 0,829 → 0,695 : la clé re-montrée compense) et (b) la tâche feedforward (CONTROL,
   leakage 0,003). C'est la **3ᵉ arête** du graphe AGI-Taxonomy — la première par ablation de
   SUBSTRAT (`ablation_target=substrate`, `functional_aliasing='pass'` exigé et obtenu) et la
   première refusée-puis-rouverte par levée de verrou (l'ancien refus mesurait le substrat plain,
   prouvablement incapable — plafond 0,3889).
2. **La chaîne de gardes a fait exactement son travail, dans les deux sens** : la V1 a été REFUSÉE
   par la garde de dégénérescence (contrôle saturé) malgré trois branches positives ; la V2 passe
   parce que l'instrument a été réparé par une injection à dose connue et PRÉDICTIVE — pas parce
   que le seuil a bougé (aucun n'a bougé, sceau à l'appui).
3. Note d'interférence, rapportée sans poids : LANG intact monte de 0,750 (V1) à 0,819 (V2) — le
   contrôle bruité entraîne un W partagé moins interférent. Les deux mesures restent des
   populations distinctes, jamais fusionnées.

## Portée (hedges — hérités du point S1, inchangés)

* **D=0 seulement** (rétention 1-tick) : à D=2 la référence n'apprend pas au même point (3/3 à la
  chance) — le mur [[EDR-LOCK-001]]. L'arête dit « l'usage référentiel immédiat demande la
  mémoire portée » ; elle ne dit rien de la rétention longue, qui reste verrouillée.
* Crédit REINFORCE, tâche proxy `(q+key)%K`, K=6, un seul jeu de fenêtres — pas un verdict
  in-world (la demande in-world hors perception reste le gap S3).
* Bruit CONTROL p=0,15 : constante d'instrument, calibrée par prédiction ; hors de ce réglage la
  garde d'alias doit être re-confrontée.
* `measure` : les 24 cellules persistées et versionnées permettent tout recalcul
  (`ablation_verdict` floor=1/K, ceiling=1,0, tol=0,05 — instruments calibrés, aucun modifié).

Converge [[EDR-LANG-MEMORY-EDGE]] (l'indéterminé qui a prescrit ce run), [[EDR-BILINEAR]] (la
capacité-antécédent), [[EDR-RETAIN-COMPOSE-LR]] (le pas), [[EDR-LOCK-001]] (la borne D=2),
REF-DEMAND-MARKER (le gabarit within-subject).
