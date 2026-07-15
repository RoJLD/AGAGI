---
id: EDR-176
type: EDR
title: Monter r·P (densité de proies) n'RESCUE PAS le binding du throw-gate — le blocage in-world est MULTI-CAUSAL, r·P nécessaire mais pas suffisant (contrôle positif)
status: accepted
gate: G1
verdict: RP_NECESSARY_NOT_SUFFICIENT_BINDING_IS_MULTICAUSAL
---

# EDR-176 : le contrôle positif RAFFINE EDR-175 — r·P aide (dose-réponse) mais ne suffit pas

> Territoire BIND/torch. Contrôle POSITIF de l'arc 172-175. Banc `tools/torch_throw_gate_inworld_ab.py`
> (`compare_rp_sweep`, knob `prey_count`, additif). **Auto-correction d'EDR-175.**

## Contexte

EDR-175 a clos l'arc throw-gate (172-175) avec une explication UNIFIÉE : le throw-gate échoue au bootstrap
(cold) ET à la rétention (warm) pour la MÊME raison — la densité de récompense in-world est sous le plancher
`r·P` (loi rétention-167). **Contrôle positif nécessaire** : si `r·P` est LA cause, monter `r·P` doit faire
ÉMERGER le binding. On monte `r·P` en inondant le monde de proies (⇒ P(hit) ↑ ⇒ kills ↑), toutes les autres
variables tenues constantes (gate cold, non-biaisé, sparse, mêmes knobs couche-1).

## Méthode

`compare_rp_sweep` : sweep `target_prey_count ∈ {15, 100, 400}` (knob `prey_count`, régen jusqu'au plafond).
Gate **cold + non-biaisé + récompense sparse** (hit=+1) — `r·P` monté par les PROIES, PAS par la forme du
signal ni l'init. Par niveau : verdict `binding_gap` ON-vs-SHUFFLE + `kills` médian (proxy observé de `r·P`).
K=4. Détail élégant : l'observation `num_preys` sature à 20 ⇒ au-delà l'agent ne « voit » pas plus de proies
mais ses throws touchent plus ⇒ découple perception et payoff, isolant `r·P`.

## Résultat (K=4)

| prey | kills médian (r·P ↑) | throw | gap_ON médian | diff (ON−shuffle) | verdict |
|---|---|---|---|---|---|
| 15  | 6.0  | 0.10 | −0.624 | −0.442 | HEBBIEN (anti-bind) |
| 100 | 30.5 | 0.12 | −0.346 | −0.269 | HEBBIEN |
| 400 | 28.0 | 0.08 | −0.277 | −0.241 | HEBBIEN |

`r·P` monte ~5× (kills 6→30) ; le `gap_ON` **reste NÉGATIF partout** (jamais GRADIENT_GAGNE) MAIS **s'améliore
monotoniquement** (−0.62 → −0.35 → −0.28). Le contrôle positif ÉCHOUE : forte densité ne fait pas émerger le
binding.

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : monter `r·P` ~5× n'produit PAS de binding positif (gap négatif, HEBBIEN, 3/3 niveaux). MAIS le gap
  remonte monotoniquement avec `r·P` (dose-réponse partielle).
- **INTERPRÉTATION (auto-correction d'EDR-175)** : `r·P` est un levier RÉEL et directionnellement causal
  (l'amélioration monotone confirme la direction d'EDR-175) mais **PAS SUFFISANT** (ne franchit jamais zéro).
  L'échec du binding in-world est **MULTI-CAUSAL / sur-déterminé**, pas le plancher `r·P` unique. Verrou
  co-dominant qui persiste à haut `r·P` — au moins un de : (a) **consommation** (throw consomme le spear ⇒
  P(throw|¬spear) gonflé mécaniquement, EDR-174) ; (b) **poids-spear** (spear pèse ⇒ contexte-spear = détresse
  énergétique ⇒ `logits[8]` de base plus bas, que le gate ne surmonte pas) ; (c) **crédit MARGINAL** (la
  récompense apprend « throw paie » pas « throw-SI-spear » — le conditionnel n'est pas crédité).
- **La simplification d'EDR-175 corrigée** : « le throw-gate échoue au bootstrap ET à la rétention pour la
  MÊME raison (r·P) » devient « r·P est UN facteur (dose-réponse réelle) parmi plusieurs ; le blocage est
  sur-déterminé ». La loi rétention-167 tient sur sa moitié (r·P a un effet) mais n'explique pas tout in-world.

## Portée / Bornage (honnêteté)

1. K=4, `sign_p` par niveau 0.125-0.625 (HEBBIEN pas fortement significatif par niveau, mais **consistant
   3/3 niveaux + K=1**) → le claim ROBUSTE = « pas de binding positif », pas « anti-binding significatif ».
2. `throw_rate` bas et instable (0.08-0.12, anti-sat) : les gaps sont estimés sur peu de throws (bruités) ;
   la magnitude exacte est incertaine, le SIGNE (négatif) est robuste.
3. `prey_count` = proxy grossier de `r·P` (kills non-parfaitement monotone : 30→28 de 100→400 = saturation/
   bruit). L'amélioration du gap est SUGGESTIVE, pas prouvée dose-réponse propre.
4. Les 3 co-verrous (consommation / poids-spear / crédit-marginal) ne sont PAS isolés ici — c'est le prochain
   découpage si le fil reprend.

## Suite

- **CLÔT l'arc throw-gate in-world (172→176) avec un verdict MULTI-CAUSAL.** Le binding in-world d'une action
  **CONSOMMATRICE à payoff rare** (throw-outil) est sur-déterminé-difficile : `r·P` + consommation +
  entanglement poids/détresse + crédit-marginal. La biosphère (throw balistique consommateur) est un mauvais
  banc de binding.
- **Leçon générale affinée** (met à jour EDR-175 sur la roadmap) : avant un binding in-world, vérifier NON
  SEULEMENT `r·P` mais aussi (i) l'action est-elle CONSOMMATRICE (biaise P(y|x) mécaniquement), (ii) le
  contexte-means est-il ENTANGLÉ à d'autres facteurs (coût/détresse), (iii) le crédit est-il CONDITIONNEL
  (means→ends) ou seulement marginal. Une action NON-consommatrice, à contexte-means propre, à payoff dense,
  et à crédit conditionnel serait le bon banc — pas la balistique actuelle.
- Découpage propre possible (si repris) : (a) action non-consommatrice / reseed-à-la-décision ; (b) spear
  sans poids ; (c) crédit du conditionnel. Séparables. Banc `compare_rp_sweep`/`compare_warmstart` réutilisables.

Lignée : **RAFFINE / auto-corrige [[torch-inworld-integration-plan]] (EDR-175)** — r·P nécessaire-pas-suffisant,
binding in-world multi-causal. Nuance [[warm-start-transversal-law]] (r·P est un des locks in-world, pas le seul).
Converge la thèse CRÉDIT de COS Phase B en la précisant (crédit CONDITIONNEL means→ends, pas seulement dense).
