# Backlog priorisé — gaps de recherche (dérivé du cartographe)

> Source : `rapport-2026-07-01.md` (1er passage cartographe) + arbitrage humain 2026-07-01.
> Priorité effective = impact × faisabilité × **ownership** (un gap en territoire activement piloté par
> une session parallèle est déprioritisé pour cette session : risque de collision/duplication).
> Le cartographe DÉTECTE ; cette backlog PRIORISE (curée à la main) ; les fils EXÉCUTENT.

## À faire ici (territoires dormants / non contestés — ownables proprement)

| # | Gap | Territoire | Impact | Statut |
|---|-----|-----------|--------|--------|
| **P1** | Rétention du craft : le craft est ATTEINT mais non re-crafté en cohorte fixe (EDR 127) — quel mécanisme fait re-crafter (mémoire de recette ? incitation ?) | CRAFT (dormant) | moyen-haut | **EN COURS** |
| P2 | Gate de cohérence `life_score` : le verdict S2 était VOID car « survivant ≠ marqueur » — re-spécifier le gate pour qu'un survivant ne suffise pas | WLD (dormant) | moyen | à faire |
| P3 | Réveil NAV : densité-verrou #2 (51) mais dormant ; mur navigation = politique/substrat, pont SUB non tiré | NAV (dormant) | moyen (gros banc) | à faire |

## À coordonner (haute impact MAIS territoire activement piloté par une session parallèle)

| # | Gap | Territoire | Note collision |
|---|-----|-----------|----------------|
| C1 | Crédit multi-tête → substrat torch-prod (GradNorm-lite / lr-par-tête dans le PLAT, PAS la refonte #5) | COG→SUB/PROD | Fil disjoint-heads ACTIF (EDR 152-155, planifie 156). `lr-par-tête` proxy non testé (caveat EDR 154) = seul angle proxy encore libre. |
| C2 | Recette gate+anti-saturation (BIND) → prod : activer EDR-148 (flag OFF), valider hors banc jouet | BIND→PROD | Fil compositional // ; port prod entamé (EDR-148). |
| C3 | BPTT fenêtré in-world (persister le graphe K ticks) | SUB | Fil torch ACTIF (EDR 145/146 BPTT). |

## Verdicts à tenir à jour

| # | Item | Statut |
|---|------|--------|
| V1 | EDR-151 / P4-ToM | **OUVERT** (investigation 2026-07-01) : actionnable causal (incitation ToM→`life_score`) NON testé, différé migration torch (bloqué sur `src/`). |
| V2 | EDR-121 storage-evolvability | **RÉSOLU-PAR-AVAL** (155/157) — annoté (PR #128). |

## Fait

- EDR-INFRA : parser `legacy_edr` durci (liste propre en tête) — PR #129.
- Rattachements registre 152-157 + FAM dormant→actif + P4-ToM corrigé — PR #128.

## Convention

Nouveaux records = ID préfixé `EDR-<PREFIX>-nnn` (cf. `SPECIALITES.md`). Les fils // coordonnent via ce
registre ; les gaps « à coordonner » ci-dessus se prennent par la session qui possède le territoire.
