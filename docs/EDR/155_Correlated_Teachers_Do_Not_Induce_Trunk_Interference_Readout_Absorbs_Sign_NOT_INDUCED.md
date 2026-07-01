# EDR 155 (V2) — Les profs corrélés N'INDUISENT PAS d'interférence de trunc : le readout linéaire absorbe le signe (NOT_INDUCED, prédit avant le run)

> **Date** : 2026-07-01. **Verdict pré-enregistré** : Axe A `INDUCED` si cosinus-conflit `≤ −0.05` sur majorité ;
> Axe B `CREDIT_ROBUST` recovery≥0.50 / `ARCH_MATTERS` ≤0.20 / `CREDIT_PARTIAL`.
> **Résultat** : **NOT_INDUCED+CREDIT_ROBUST** — à ρ=0.95, cosinus-conflit moyen **+0.015** (par-seed
> [−0.002, +0.003, +0.004, +0.033, +0.039], **0/5 ≤ −0.05**). Corréler les profs par sous-espace partagé signé
> **ne crée aucune interférence de trunc mesurable** ; le readout linéaire appris absorbe le signe.
> **Prédiction opus PRÉ-ENREGISTRÉE** (revue finale, dry-run K=5 ρ=0.95) : `cos ∈ [−0.002, +0.039]`, NOT_INDUCED —
> **le run officiel la confirme au chiffre près**.
> **Outil** : `tools/disjoint_heads_correlated.py` (réutilise `disjoint_heads_ab` 152 + `disjoint_heads_confound` 153).
> **Run** : K=5, base=2200, ρ∈{0.0, 0.6, 0.95}, STEPS=2000, `set_num_threads(1)`, `use_deterministic_algorithms(True)`,
> **2 passes byte-identiques**. **Spec/Plan** : `docs/superpowers/{specs,plans}/2026-07-01-disjoint-heads-correlated*`.

## 1. Question — répondre au caveat I2 d'EDR 152

EDR 152 : les têtes disjointes battent le plat (+43 %) MAIS cosinus-conflit ≈ 0 → interférence réfutée. **Caveat
I2** : les 3 profs étaient **indépendants** (quasi-orthogonaux) → pas d'interférence à trouver ; la conclusion « archi
ne compte pas » (153/154) est peut-être **bornée au régime orthogonal**. V2 induit une vraie interférence (profs
corrélés par sous-espace partagé signé, `SIGMA=(+1,+1,-1)`, sweep ρ) et re-teste : quand le cosinus devient négatif,
le crédit-équilibrage **plat** (FLAT_NORM, 153) recouvre-t-il encore l'avantage DISJOINT, ou l'archi compte-t-elle ?

## 2. Résultat (run pré-enregistré, 2 passes byte-identiques)

```
  rho  | cos    | improv | recovery | (gain FLAT-DISJ v/p a rho=0.95)
  0.00 | -0.002 | +0.356 | +0.886   |
  0.60 | -0.000 | +0.351 | +1.072   |
  0.95 | +0.015 | +0.187 | +2.501   | ~0.003 / ~0.005  (denominateur degenere)
  cos par-seed a rho=0.95 : [-0.002, +0.003, +0.004, +0.033, +0.039]  ->  0/5 <= -0.05
  VERDICT : NOT_INDUCED+CREDIT_ROBUST
```

## 3. Lecture

1. **NOT_INDUCED, net.** Le cosinus reste ~0 à travers tout le sweep (−0.002 → −0.000 → +0.015), **aucune tendance
   négative**. Corréler les cibles côté profs (les colonnes `w1` action↔pred atteignent −0.95 à ρ=0.95) **ne se
   traduit PAS** en conflit de gradient sur le trunc partagé.
2. **Mécanisme (revue opus, vérifié en dry-run) : le readout linéaire absorbe le signe.** Le cosinus mesure
   `∂L_k/∂trunk.weight = head_k.weight^T · (dérivée) ⊗ x` ; la matrice de readout apprise `head_k.weight`
   (`nn.Linear(H,out)`) est **libre d'inverser le signe**. Le student sert le **même** sous-espace de trunc et flippe
   le signe dans le readout, au lieu d'opposer les gradients du trunc → gradients de trunc quasi-orthogonaux quel que
   soit ρ. C'est exactement le risque nommé au spec §1 / caveat (b), et il se réalise. **Avec un trunc surdimensionné
   (H=48) + readouts libres, il n'y a tout simplement pas d'interférence à induire** : les 3 tâches sont conjointement
   satisfiables.
3. **Corrélation = aide, pas conflit.** L'avantage disjoint **DÉCROÎT** avec ρ (improv 0.356 → 0.351 → 0.187) et le
   gain FLAT−DISJ s'effondre à ρ élevé : partager un sous-espace rend les tâches **plus conjointement apprenables**
   (le plat en profite), l'inverse d'un conflit.
4. **Axe B moot / dégénéré.** À ρ=0.95 le gain FLAT−DISJ tombe à ~0.003 → le dénominateur de `recovery` dégénère
   (valeurs >1, jusqu'à 4.x) → **CREDIT_ROBUST ici n'est PAS interprétable** (caveat d). Surtout : **B n'a de sens que
   si A=INDUCED** (spec §5) ; A=NOT_INDUCED → **la question B n'est PAS testée** par ce banc.

## 4. Portée — honnête, à ne pas sur-vendre

- **Ce que V2 établit** : un fait **mécanistique** — dans un substrat plat surdimensionné à readouts linéaires, la
  corrélation de tâches par sous-espace partagé **ne produit pas** de conflit de gradient de trunc (le readout absorbe
  le signe). Cela **renforce mécaniquement** l'histoire « le gain disjoint n'est pas de l'interférence » (152).
- **Ce que V2 N'établit PAS** : que la conclusion « archi ne compte pas » (153/154) **tienne sous interférence
  réelle**. Le régime interférent n'a jamais été atteint → la prémisse du caveat I2 reste **ouverte, non réfutée**.
- **Ce qu'il faudrait pour tester B** (opus finding g, et **correction d'une erreur de conception** : réduire H
  **uniformément** PRÉSERVE la parité inter-bras — FLAT `D·H` et DISJOINT `3·(D·H/3)` scalent tous deux avec H) : une
  **pression de capacité** (H réduit) pour que le trunc NE PUISSE PAS servir toutes les têtes → vraie interférence →
  test réel de B. **Suite = EDR 156 (profs corrélés à H réduit).**

## 5. Caveats

- **(a)** Le knob ρ+signes était un *essai* d'induction ; le cosinus mesuré tranche — il ne fonctionne pas.
- **(b→e, promu)** **Sonde structurellement biaisée vers 0** : l'Axe A mesure `∂L/∂trunk.weight`, où le readout
  linéaire appris absorbe le signe imposé par SIGMA → **prédiction pré-enregistrée avant run** : cos≈0, NOT_INDUCED
  (dry-run opus K=5 ρ=0.95 : 0/5 ≤ −0.05, cos ∈ [−0.002, +0.039]) → **confirmée**. Un NOT_INDUCED atteste le
  comportement de la sonde, il ne teste PAS le régime interférent.
- **(f)** `w2` (readouts profs) **indépendants par tête, non modulés par ρ** → une part de l'orthogonalité des cibles
  survit à ρ=1 (corrélation induite seulement dans `w1`), atténuant encore le conflit atteignable.
- **(g)** Tester B exige de sonder `∂L/∂h` (pré-readout), OU geler les readouts, OU **pression de capacité (H
  réduit)** — cette dernière préserve la parité inter-bras (correction de l'écart initial) → **EDR 156**.
- **(c)** `SIGMA=(+1,+1,-1)` fixe/arbitraire. **(d)** dénominateur recovery petit (dégénère à ρ élevé, ici l'axe B est
  moot). Hérite 152/153/154 (proxy supervisé, têtes non appariées).

## 6. Sanity de sweep (revue opus, vérifié)

Même `TEACHER_SEED` pour tout ρ → seule la mixture change. `colnorm` (rescale chaque colonne à la norme de la colonne
indépendante) garde l'échelle des features comparable ; à ρ=0 le régime orthogonal est reproduit (cos ~0, profil
FLAT/DISJOINT proche de 152) → sweep **propre**. Pas de fuite RNG (`_train_arm`/`_train_flat_norm` re-seedent en
interne). Parité de params trunc FLAT vs DISJOINT préservée (H=48 inchangé).

## 7. Boucle EDR 152 → 155

- **152** : disjoint aide, cos≈0 (profs indépendants) → interférence réfutée.
- **153/154** : le gain = crédit-équilibrage (échelle/moments), pas l'archi.
- **155** : forcer la corrélation des profs **ne crée toujours pas** de conflit de trunc (readout absorbe le signe ;
  trunc surdimensionné) → le cos≈0 de 152 est **robuste mécaniquement**, MAIS le régime interférent reste inatteint →
  **EDR 156** (H réduit = pression de capacité) pour tester enfin si l'archi compte sous vraie interférence.

## 8. Provenance / non-périmètre

- `tools/disjoint_heads_correlated.py` (`main_correlated_check`, K=5, base=2200, ρ∈{0.0,0.6,0.95}, STEPS=2000,
  `set_num_threads(1)`) ; **2 passes byte-identiques** ; AUCUN test relancé après le run.
- **Tooling ADDITIF** : nouveau fichier + test + spec/plan/EDR uniquement ; `src/` VIDE ; `disjoint_heads_ab.py`
  (152) et `disjoint_heads_confound.py` (153) **intacts** (réutilisés par import). Ne touche NI le substrat torch
  (`torch_batch_model.py`/`backend_torch.py`/`substrate_*` — fil // torch).
- Subagent-driven : 2 tâches (SPEC conforme + qualité Approved chacune), revue finale **opus PRÊT À INTÉGRER OUI, 0
  Critical**, qui a **prédit NOT_INDUCED avant le run** (dry-run), validé le contrôle (sweep propre, parité, pas de
  fuite RNG) et posé les caveats e/f/g. Verdict pré-enregistré gelé avant le run.
- **Numérotation** : EDR 155 — bloc **150+**. 8e instrument per-type, suite d'EDR 152/153/154.
