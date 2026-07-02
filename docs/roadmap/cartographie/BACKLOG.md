# Backlog priorisé — gaps de recherche (dérivé du cartographe)

> Source : `rapport-2026-07-01.md` (1er passage cartographe) + arbitrage humain 2026-07-01.
> Priorité effective = impact × faisabilité × **ownership** (un gap en territoire activement piloté par
> une session parallèle est déprioritisé pour cette session : risque de collision/duplication).
> Le cartographe DÉTECTE ; cette backlog PRIORISE (curée à la main) ; les fils EXÉCUTENT.

## À faire ici (territoires dormants / non contestés — ownables proprement)

| # | Gap | Territoire | Impact | Statut |
|---|-----|-----------|--------|--------|
| ~~P1~~ | Rétention du craft (EDR 127) — mémoire de recette ? incitation ? | CRAFT | moyen-haut | **FAIT → EDR-CRAFT-001 : POLICY_LOCKED** (aucun levier environnemental n'aide ; re-craft≈0 ; verrou = politique figée/substrat → levier = plasticité torch, backlog C1-C3). Axe tooling CLOS. |
| ~~P2~~ | Gate de cohérence `life_score` : verdict S2 VOID « survivant ≠ marqueur » | WLD | moyen | **FAIT → PR #132** : le gate survie (`verdict_from_survival_cmps`) existait mais n'était pas câblé dans le runner (faux VOID). Câblé nativement, `life_p` corroborant, `_print_table` ASCII-safe. Relancer = EXIGE ×4. |
| ~~P3~~ | Réveil NAV : mur navigation = politique/substrat, pont SUB non tiré | NAV | moyen (gros banc) | **FAIT → EDR-NAV-001 : READOUT_GAP** (probe linéaire : H décode la direction ~0.81 mais la tête d'action l'ignore, émise==correct ~2-3% ; encodeur OK). Cible torch précise = tête d'action par gradient (pont SUB, handoff C1-C3). |

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
