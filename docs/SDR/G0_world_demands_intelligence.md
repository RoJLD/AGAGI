---
id: SDR-G0
type: SDR
title: Le monde EXIGE-t-il l'intelligence
status: open
gate: G0
motivates: [EDR-112, EDR-118]
---
# SDR-G0 — Porte de validité

Hypothèse falsifiable : un champion HoF survit significativement mieux qu'un agent
dummy/aléatoire dans chaque monde aval. KPI `survival_ratio(champion)/survival_ratio(dummy)`,
multi-seed appairé, powered. Si ≈1 → monde factice. Inclut le sous-chantier compute
(parallélisme/early-stopping) prérequis de G1. Réf : spec §3 G0.

**VALIDÉE par EDR-112** (2026-06-29) : stoneage (prod) **EXIGE** — champion survit 3.74–4.67× l'aléatoire
(Cliff δ=+0.92, p=0.003 Holm, bat les 3 baselines), soup EXIGE aussi. → G1 peut démarrer sur stoneage.
Caveats : industrial = stoneage déguisé (chiffres identiques) ; agricultural VOID ; Lewis = plan-suivi.

**ÉTENDUE par EDR-118** (2026-06-30) : **FamineWorld EXIGE** aussi (2 seeds, δ≈0.92, ratio ~4×, p=0.003,
0% censuré, cohérence OK ; red flag byte-match-stoneage investigué = δ saturé + p-plancher, ratio bouge
entre seeds). 1ᵉʳ vrai 2ᵉ monde distinct (vs agri VOID, indus=clone). ⭐ Caveat clé : le champion est
stoneage-évolué → l'EXIGE mesure le TRANSFERT de compétence générale, **pas** l'usage du stockage (mécanique
réelle mais inerte dans S2). Reste ouvert = la gratification différée est-elle **évolvable** ? (évoluer
DANS famine, puis G1 transfert).
