---
id: EDR-173
type: EDR
title: Débiaser la récompense du throw-gate (NAV-005) est NÉCESSAIRE mais PAS SUFFISANT in-world — le verrou résiduel est la rareté du kill-outil, pas le signe
status: accepted
gate: G1
verdict: DEBIAS_NECESSARY_NOT_SUFFICIENT_KILL_SPARSITY
---

# EDR-173 : le correctif de biais de NAV-005, porté in-world, ne produit PAS de binding

> Territoire BIND/torch (fil in-world, suite d'EDR-172). Banc `tools/torch_throw_gate_inworld_ab.py`
> (`compare_debias`, additif) + knob `src` `torch_throw_penalty` (flag-guardé, défaut rétro-compatible).

## Contexte

- **EDR-172** : le throw-gate câblé in-world NE BINDE PAS (`gap_ON` bruit, parfois négatif). Diagnostic =
  substrat 2 couches : (1) la cohorte fraîche s'éteint avant l'horizon d'apprentissage ; (2) le crédit
  kill-avec-outil est trop rare. Récompense : throw+kill → +1, throw sans kill → **−0.5**, sinon 0.
- **EDR-NAV-005** (session //, offline, H figé) : raffine la couche 2 — le mur n'est pas la rareté mais le
  **BIAIS** −0.5 (sous `p_success < 1/3`, `E[throw|spear] < 0` → le readout ÉVITE le bon geste). Correctif
  prédit : récompense NON-biaisée (0.0 au lieu de −0.5) → le gate binde **même à leur rareté** (p=0.02-0.03).

**Question** : porté in-world, débiaser la récompense (`−0.5 → 0`) produit-il le binding ?

## Méthode

- **`src`** (2 lignes, flag-guardé) : `torch_throw_penalty` (défaut −0.5 = EDR-172 ; 0.0 = non-biaisé).
- **Banc** : `compare_debias` apparié **biaisé (−0.5) vs non-biaisé (0.0)**, chaque bras ON-vs-SHUFFLE
  (shuffle = témoin d'artefact), verdict via `compute_ab_verdict`.
- **Couche 1 neutralisée** (sinon confond survie et crédit — EDR-172) : énergie initiale 250 + spears
  lourds (contraste spear/¬spear) + `base_metabolism=0.05` + nuit OFF → survie ~150-200 ticks (vs t≈77
  pour la cohorte fraîche). Fenêtre de mesure t∈[40,150], K=6, sweet forage.

## Résultat (K=6, couche 1 levée)

| bras | verdict | median_diff | commentaire |
|---|---|---|---|
| biaisé (−0.5) | **NEUTRE** | 0.000 | `gap_ON` ≈ 0 (pas d'artefact non plus) |
| non-biaisé (0.0) | **NEUTRE** | 0.000 | `gap_ON` **jamais positif** |

**Densité du crédit** : `kills` = **1-6** par run sur `spear_n` ≈ 500-2400 throws → **p_success ≈ 0.001-0.003
in-world**, soit **~10-20× plus rare** que le sweep offline de NAV-005 (p=0.02-0.03). Donnée de contraste : en
régime **cohorte mourante** (fenêtre courte, throws fréquents), le bras biaisé donnait `gap_ON` fortement
**négatif** (−0.34, −0.85) — la signature EDR-172 ; couche 1 levée, il remonte à ≈0 (peu de throws → le −0.5
mord rarement). Le non-biaisé, lui, reste ≈0 dans **tous** les régimes.

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : ni le biaisé ni le non-biaisé ne bindent une fois la couche 1 levée (`gap_ON` ≈ 0, K=6). Le kill-
  outil in-world est ~10-20× plus rare que dans le modèle offline de NAV-005.
- **INTERPRÉTATION (raffine NAV-005 in-world)** : le débias est **NÉCESSAIRE mais PAS SUFFISANT**. Il retire le
  drive **nuisible** (le biaisé ne pousse plus `gap_ON` négatif — confirmé par le contraste régime-mourant),
  mais ne peut pas créer le **positif** : à `p_success ≈ 0.001`, même la récompense non-biaisée donne
  `E[correct] ≈ 0.001·1 ≈ 0` → gradient REINFORCE négligeable → le gate throw mais n'apprend pas à conditionner
  sur le spear. NAV-005 adresse UN des deux sous-verrous couche-2 d'EDR-172 (le **biais**) ; l'AUTRE (la
  **rareté extrême** du kill-outil) domine in-world et son modèle offline (H figé, p_success « donné ») l'abstrait.
- **CONVERGE la thèse CRÉDIT** (COS Phase B [2] CRÉDIT-ATTRIBUÉ) — mais précise : ici le crédit EXISTE et n'est
  pas mal signé (après débias), il est **trop peu DENSE pour être attribué**. Le verrou in-world est la
  **densité** du signal, pas son signe.

## Portée / Bornage (honnêteté)

1. **Résultat NÉGATIF sous une calibration in-world spécifique** — pas une réfutation de NAV-005 (dont la
   prédiction offline tient à p=0.02-0.03). Je n'ai pas balayé l'anti-saturation (`torch_throw_antisat=6.0`
   prod) ni densifié artificiellement les kills ; à antisat plus bas / proies plus denses le verdict pourrait
   bouger.
2. **Contraste imparfait** : sur 3/6 seeds `nospear_n` est faible (spears quasi-omniprésents) ; mais les seeds
   à contexte valide (`nospear_n` 42-109) donnent aussi ≈0.
3. **Couche 1 levée artificiellement** (énergie 250, métab 0.05, nuit off) = régime survivable isolant, pas la
   prod. `p_success` estimé sur 1-6 kills = bruité.
4. `K=6` < 12 : aucun verdict POSITIF ne serait autorisé de toute façon (garde-fou) ; ici les deux sont
   NEUTRES, robustes au signe et au régime, donc la puissance suffit pour la conclusion « pas de bascule ».

## Suite

- Le levier résiduel in-world est la **DENSITÉ du crédit kill-outil**, pas le signe : shaping vers un proxy
  plus dense (récompenser le throw **dirigé vers une proie** / l'approche, pas seulement le kill), ou une tâche
  où l'outil paie plus souvent. Recoupe le fil densité-de-signal (EDR-NAV-004 : la rareté non-biaisée est
  indulgente **jusqu'à un plancher** ; ici on est sous le plancher).
- Le knob `torch_throw_penalty=0.0` reste le bon défaut pour toute reprise (retire le nuisible sans coût).
- **Ne PAS** relancer le throw-gate in-world tel quel espérant le binding : les deux sous-verrous couche-2 sont
  identifiés (biais ✓ réparé ; densité ✗ ouverte).

Lignée : raffine [[torch-inworld-integration-plan]] (EDR-172, couche 2) ; porte in-world le correctif offline de
NAV-005 ; converge la thèse CRÉDIT ([[lineage-divergence-d1-vs-main]], COS Phase B) en la précisant (crédit
présent mais trop peu DENSE). Étend [[coop-competence-is-population-property]] (crédit means→ends).
