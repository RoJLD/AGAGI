---
id: EDR-177
type: EDR
title: Factoriel 2^4 des confounds — la CONSOMMATION est le verrou maître du binding in-world (pas multi-causal égal) ; la cellule tout-propre BINDE → substrat capable in-world
status: accepted
gate: G1
verdict: CONSOMMATION_VERROU_MAITRE_CELLULE_PROPRE_BINDE_CONFIRME_K12
---

# EDR-177 : le factoriel TRANCHE EDR-176 — un verrou dominant (consommation), pas quatre égaux

> Territoire BIND/torch. Clôt l'arc throw-gate in-world (172→177). Banc `tools/torch_throw_gate_inworld_ab.py`
> (`compare_factorial`, `_factorial_effects`, mode CLI `factorial`). **Auto-correction d'EDR-176.**

## Contexte

EDR-176 (contrôle positif) a conclu que l'échec du binding in-world du throw-gate est **multi-causal /
sur-déterminé**, mais **sans isoler** les 4 confounds nommés (bornage point 4) : (F1) consommation de
l'action, (F2) poids-portage (détresse-contexte), (F3) densité-payoff (`r·P`), (F4) crédit marginal-vs-
conditionnel. Ce banc les isole par un **factoriel complet 2⁴** et pose le **test décisif** : la cellule
tout-propre (les 4 confounds retirés) fait-elle émerger le binding ?

## Méthode

`compare_factorial` : 16 cellules = produit des 4 facteurs binaires (True = niveau « propre »), chacune ×
K seeds × {ON, SHUFFLE}, `diff = gap_ON − gap_SHUFFLE`, verdict `compute_ab_verdict` (band 0.02). Régime
**couche-1 neutralisée + non-biaisé** (energy=250, base_metabolism=0.05, night=False, penalty=0.0,
antisat=0.3, respawn_p=0.06, spear_weight=2.0) — **seuls les 4 facteurs varient**. `_factorial_effects` :
effets principaux (moyenne poolée des diffs par niveau) + interactions 2-way. Chaque facteur = une méthode
monde pure testable, défaut OFF, gated par `torch_throw_gate` (18/18 tests verts, revue subagent-driven +
whole-branch opus). Tag cellule `NWDK` = no_consume / Weightless / Dense / conditional_Kredit.
K=8 (carte, ticks=120) ; **K=12 (confirmation garde-fou power-evaporation) : voir §Confirmation**.

## Résultat — carte K=8 (dichotomie parfaite sur la consommation)

**Effets principaux** (diff propre − diff confound) :

| facteur | effet | lecture |
|---|---|---|
| **no_consume (F1)** | **+0.460** | **DOMINANT** — retirer la consommation bascule le binding |
| dense (F3) | +0.159 | modulateur secondaire (`r·P`) |
| weightless (F2) | +0.021 | négligeable |
| conditional_credit (F4) | +0.019 | négligeable |

**Interactions 2-way** : `no_consume×dense` **+0.103** (la densité aide PLUS quand non-consommateur) ; toutes
les autres ≈ 0 (|·| ≤ 0.057).

**Séparation parfaite par F1** — les 8 cellules `no_consume`-ON bindent, les 8 `no_consume`-OFF anti-bindent :

| cellule | diff | verdict |
|---|---|---|
| N.D. / N.DK (no_consume + dense) | +0.371 | GRADIENT_GAGNE |
| **NWDK (tout-propre, cellule-0)** | **+0.332** | **GRADIENT_GAGNE, 8/8, sign_p=0.008** |
| N... / N..K (no_consume SEUL, sinon tout confond) | +0.105 | GRADIENT_GAGNE |
| NW.. / NW.K | +0.065 | GRADIENT_GAGNE |
| ...K / .... (baseline confond) | −0.09 / −0.14 | HEBBIEN |
| .WD. / ..D. / ..DK | −0.19 à −0.30 | HEBBIEN |
| .W.. / .W.K (weightless SANS no_consume) | −0.31 | HEBBIEN (le pire) |

## Confirmation K=12 (garde-fou power-evaporation)

Le garde-fou (« pas de verdict POSITIF sous n=12 ») a correctement bloqué la conclusion à K=8
(`BINDING_APPARENT mais n=8<12 → NON-CONCLUANT`). **Confirmation à K=12 : le résultat TIENT et se
renforce.**

- **Cellule-0 (tout-propre NWDK) : diff=+0.348, gap_ON=+0.369 → GRADIENT_GAGNE, sign_p=0.00049 (12/12
  seeds).** Garde-fou levé → `CONCLUSION: SUBSTRAT_BINDE_IN_WORLD_PROPRE`.
- **Effets principaux stables** : no_consume **+0.465** (K=8 : +0.460), dense **+0.168** (+0.159),
  weightless **+0.014** (+0.021), conditional_credit **+0.008** (+0.019). Interaction `no_consume×dense`
  **+0.118** (+0.103) ; autres ≈ 0.
- **Séparation toujours parfaite** : les 8 cellules F1-ON = GRADIENT_GAGNE (sign_p 0.0005-0.006), les 8
  F1-OFF = HEBBIEN. Aucune inversion vs K=8.

Le verdict positif est donc **confirmé au seuil de puissance requis** (n=12, sign-test, [[power-evaporation-guardrail]]).

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : effet principal `no_consume` = +0.46, écrasant (dense +0.16 ; weightless +0.02 ; conditional
  +0.02). Séparation PARFAITE : F1-ON ⇒ GRADIENT_GAGNE (8/8 cellules), F1-OFF ⇒ HEBBIEN (8/8). Retirer la
  consommation SEULE (cellule `N...`, tous autres confounds présents) suffit à basculer positif (+0.105).
  La cellule tout-propre binde fort (+0.332, 8/8 seeds, sign_p=0.008).
- **INTERPRÉTATION (auto-correction d'EDR-176)** : l'échec du binding in-world n'était **PAS multi-causal
  à parts égales** — il était **DOMINÉ par UN confound mécanique : la consommation**. Jeter le spear en le
  lançant met l'agent en contexte ¬spear, gonflant `P(throw|¬spear)` et anti-bindant (EDR-174 avait vu
  l'anti-bind de la densité-shaping ; le factoriel montre que la CAUSE racine est la consommation, pas la
  densité). La densité (`r·P`) est un **modulateur réel mais secondaire** (+0.16, et interaction
  `no_consume×dense` +0.10 : elle aide surtout une fois la consommation levée). **Surprise majeure : le
  crédit conditionnel (F4) — hypothèse posée comme le levier means→ends clé — est NÉGLIGEABLE (+0.02).**
  Ce n'était pas le régime de crédit ; c'était l'artefact mécanique de consommation.
- **Le test décisif est tranché POSITIF (confirmé K=12, 12/12, sign_p=5e-4)** : la cellule tout-propre
  binde → **le substrat EST capable de binder means→ends dans la vraie boucle biosphère**. L'échec 172-176 était le **BANC**
  (action consommatrice), pas une incapacité du substrat. C'est la preuve in-world la plus forte de la
  thèse « verrou = banc/crédit, pas capacité » (converge COS Phase B [[decisive-substrate-thesis-test]]).

## Portée / Bornage (honnêteté)

1. Verdict cellule-0 POSITIF **confirmé K=12** (12/12, sign_p=5e-4 ; garde-fou power-evaporation levé,
   [[power-evaporation-guardrail]]). Reproduit à K=8 (8/8) et K=12 : la séparation par F1 est identique aux
   deux résolutions.
2. Régime couche-1 neutralisée (energy=250, metab=0.05) : le binding est établi **quand la survie n'est pas
   le verrou** — cohérent avec l'objectif (isoler le crédit/banc), mais ne dit rien du régime létal.
3. `binding_gap` estimé sur `throw_rate` modéré (0.04-0.38) ; le SIGNE et l'ordre des effets sont robustes
   (séparation parfaite), les magnitudes exactes moins.
4. F1 « no_consume » = reseed (le spear lancé reste au sol + un neuf est semé → +1 matière/throw). Matched
   ON/SHUFFLE donc ne biaise pas le témoin ; c'est la sémantique « reseed-à-la-décision », pas la
   conservation stricte.
5. F4 négligeable **dans ce régime** (crédit dense de kill-outil disponible via la densité) ; ne réfute pas
   le crédit conditionnel là où le payoff est vraiment rare — mais le dé-priorise fortement in-world.

## Suite

- **CLÔT l'arc throw-gate in-world (172→177)** avec un verdict DÉCISIF et une auto-correction : le binding
  in-world d'une action outil échoue par **CONSOMMATION** (verrou maître), pas par un faisceau égal de 4
  causes ni par le régime de crédit. Un banc propre (action non-consommatrice) binde.
- **Leçon générale** (met à jour EDR-176) : avant de conclure « le substrat ne binde pas in-world »,
  vérifier D'ABORD si l'action **consomme son propre indice-contexte** (biais mécanique de `P(y|x)`) ; c'est
  le confound dominant, largement devant densité, poids et conditionnalité du crédit. Une action
  non-consommatrice à contexte-means propre est le bon banc.
- Ouvertures : (a) régime létal (couche-1 active) — la consommation reste-t-elle le verrou maître ? (b) le
  crédit conditionnel (F4) redevient-il pertinent quand le payoff est vraiment rare (densité basse + kill
  rare) ? Le factoriel donne l'instrument pour trancher.

Lignée : **TRANCHE / auto-corrige [[torch-inworld-integration-plan]] (EDR-176)** — pas multi-causal égal ;
consommation = verrou maître ; cellule propre binde. Confirme in-world [[warm-start-transversal-law]] +
[[decisive-substrate-thesis-test]] (substrat capable, verrou = banc/crédit pas capacité). Instrument :
`compare_factorial` (PR #164, amont #162).

---

> **Note de portage (2026-09-15, P2.60, seconde passe).** Record écrit le 2026-07-15 sur
> `chantier/throw-gate-factorial` (tag `keep/edr-177-throw-gate-factorial`, ancêtre du tag
> `keep/edr-177-178-factorial-regime-sweep`), porté dans HEAD — texte et chiffres ci-dessus INCHANGÉS.
> **L'instrument est porté AVEC lui, par FUSION 3-voies** (`git merge --no-commit --no-ff
> keep/edr-177-178-factorial-regime-sweep`, base `111c1c0`) : AUCUN conflit (`git merge-tree --write-tree`
> rend l'arbre `39aa160`), 12 fichiers, +1933/−4. Les deux fichiers partagés avaient DIVERGÉ côté HEAD
> depuis la base (+129/−28 : `src/worlds/world_1_stoneage.py` 69/23, `tools/torch_throw_gate_inworld_ab.py`
> 60/5) et la fusion CONSERVE ce que HEAD y avait posé — les 6 gardes d'arguments en tête (`run_arm`,
> `compare`, `compare_debias`, `compare_density`, `compare_warmstart`, `compare_rp_sweep`) et les défauts
> `seeds=(0,1,2,3,4)` des 5 `compare*` (P2.49) — ET apporte `compare_factorial`, `_factorial_effects`, le mode
> CLI `TTG_MODE=factorial`, les 3 kwargs de `run_arm` (`no_consume` / `weightless` / `conditional_credit`),
> les trois leviers du monde F1/F2/F4 (`torch_throw_no_consume`, `torch_throw_weightless`,
> `torch_throw_conditional_credit`, portés par `_maybe_reseed_spear`, `_carry_weight`, `_throw_advantage`) et
> leurs 4 tests (`tests/sandbox/test_torch_throw_gate_world.py`, 10 → 14). Une première passe de portage avait
> gravé ici que « les fichiers ont divergé, le diff est rapporté au backlog, pas appliqué » SANS lancer le
> `merge-tree` que l'entrée de backlog prescrivait : classe **E8** (inférence substituée à la mesure),
> corrigée dans cette passe — les chiffres ci-dessus sont RE-EXÉCUTABLES depuis HEAD
> (`TTG_MODE=factorial python tools/torch_throw_gate_inworld_ab.py`). Deux défauts de l'instrument corrigés
> AU portage, chacun avec son cas dans `tests/sandbox/test_edr177_178_calibration.py` (injection à dose
> connue, AUCUN monde) : `_factorial_effects` rendait `0.0` sur un pool VIDE (porte 14 — l'absence de mesure
> prenait la valeur « aucun effet ») → `nan`, et n'a qu'UNE définition (le driver d'EDR-178 l'importe) ;
> `compare_factorial` n'avait pas de garde d'arguments en tête et son défaut `seeds=(0,1,2,3)` était SOUS le
> plancher n ≥ 5 de `compute_ab_verdict` (classe E2, corrigée sur les autres `compare_*` le 2026-09-09) →
> garde posée AVANT le monde, défaut relevé à 5. Les chiffres publiés ici sont à K=8 et K=12, donc
> au-dessus de ce plancher.
