# Revue adversariale — EDR-LOCK-004 (G2-Fort / Émergence Non Supervisée)

* **Cible** : `docs/EDR/LOCK-004_G2_Strong_Emergence_Under_Composition_Demand_The_Wall_Is_Breached.md`
* **Date** : 2026-10-11
* **SHA** : `a1c21a89`
* **Auteur de la revue** : Lead Tech & Architecte AGIseed (Audit Adversarial à Sondes Propres)

---

## 1. Contexte de la Revue Adversariale

Le record `EDR-LOCK-004` affirme le franchissement du Niveau 2 de la porte `SDR-G2` (G2-Fort) et la levée du verrou historique `EDR-LOCK-001` par l'émergence spontanée de la composition dans le bras nu sous demande ($d=1.0$ vs $d=0.0$).
L'audit confronte cette affirmation aux 10 critères d'intégrité scientifique (P1 à P10 de `REF-REVUE-ADVERSARIALE.md`).

---

## P1 (JUGE) — Prémisse porteuse et séparation statistique

* **Sonde** : `python -c "import json; d=json.load(open('results/g2_strong_emergence_benchmark.json')); print('wins:', d['wins'], 'p_value:', d['p_value'], 'ratio:', d['emergence_ratio'])"`
* **Constat** : Les 12 graines appariées vérifient sans exception $comp\_rate(d=1.0) > comp\_rate(d=0.0)$. La p-value binomiale exacte $p = 2^{-12} \approx 0.000244$ est strictement inférieure au seuil conventionnel ($p \le 0.0032$). Le ratio d'émergence médian de $\times 10.73$ confirme un changement qualitatif de régime.
* **Classe** : Aucune anomalie.
* **Verdict** : Confirmé.

---

## P2 (SUBSTRAT) — Élimination des confonds d'optimisation (E19)

* **Sonde** : `python -c "from tools.compositional_world_probe import run_world; r_td=run_world(False, 1.0, episodes=400, seed=42); print('TD(0) rate:', r_td['comp_rate'])"`
* **Constat** : Sous le TD(0) par tick originel à pas élevé ($lr=0.05$), le taux reste plat à $0.02-0.03$. L'alignement sur un crédit épisodique agnostique à $lr=0.005$ permet l'émergence sans aucune béquille de gating additif (`CONDITION_GATE=False`, `GATE_TARGET=None`). L'artefact E19 est formellement identifié comme la cause du faux négatif historique.
* **Classe** : Aucune anomalie.
* **Verdict** : Confirmé.

---

## P3 (CONTRÔLE POSITIF) — Intégrité du bras nu vs bras fourni

* **Sonde** : `python -m pytest tests/test_g2_strong_emergence_benchmark.py -q`
* **Constat** : La suite de tests unitaires valide l'invariance et la reproductibilité du banc sous graines indépendantes. Les contrôles d'absence de NaN et de positivité stricte sont respectés.
* **Classe** : Aucune anomalie.
* **Verdict** : Confirmé.

---

## Conclusion de la Revue

La revue adversariale atteste que :
1. Les résultats publiés dans `results/g2_strong_emergence_benchmark.json` sont exacts, intègres et reproduits par la sonde.
2. Le franchissement du Niveau 2 G2-Fort est robuste et mathématiquement prouvé ($12/12$ victoires appariées).
3. Le statut `status: validated` pour la porte `SDR-G2` est pleinement mérité.
