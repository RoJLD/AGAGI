---
id: SDR-G1
type: SDR
title: La competence generalise-t-elle (north-star)
status: open
gate: G1
motivates: [EDR-105, EDR-108, EDR-116]
requires_ref: true
---
# SDR-G1 — Généralisation zéro-shot (north-star)

Hypothèse : champion évolué en monde A atteint la compétence en monde B jamais vu mieux que
tabula-rasa, à compute égal. KPI `transfer_ratio`, test de signe, multi-seed appairé.
Outil existant `tools/curriculum_transfer.py`. Si NEUTRE/NUIT → verrou répertoire-monde
(EDR 105/108) → ADR enrichir-affordance. Réf : spec §3 G1.

**1ʳᵉ mesure (EDR-116, 2026-06-30) : NEUTRE sous puissance.** soup→stoneage (seuls 2 mondes réels
distincts après G0) ne transfère pas (n=8, médiane ratio 1.026, 4/8 fav, sign_p 1.0 ; le signal de
3 seeds s'est évaporé). → G1 reste `open` ; le verrou répertoire-monde est confirmé par mesure DIRECTE.
Prochaine piste = enrichir une affordance (2ᵉ monde genuinement distinct, pas une config du même moteur)
PUIS re-mesurer le transfert.

**2ᵉ monde livré (EDR-118) : FamineWorld EXIGE** (G0), mais via transfert de compétence générale, pas via
le stockage. **Évolvabilité du stockage (EDR-121) : INCONCLUSIVE.** Le probe d'ablation (évoluer en famine
+ cache ON/OFF + contrôle stoneage) ne tranche pas : (1) les champions famine meurent avant la famine
(`delta_famine=0`, 8/8 seeds) ; (2) le GA léger érode la compétence (warm-start stoneage 53-200 → 7-12,
×10, 8/8) = meltdown mutationnel, non isolable du substrat. Correctif : le cache-fruits d'EDR-118 est
inerte en jeu (moteur auto-mange) ; une **banque d'énergie** ablatable est livrée (1ʳᵉ affordance de
stockage atteignable). `SDR-G1` reste `open`. Test propre = pipeline biosphère complet (élitisme HoF) sur
famine → sous-chantier dédié (backlog).
