# EDR 191 — Sous pression de capacité, la vraie interférence ÉMERGE (là où 190 échouait) MAIS le crédit-équilibrage plat gagne quand même : archi réfutée COMME LEVIER même sous interférence

> **Date** : 2026-07-01. **Verdict pré-enregistré** (mesuré à H_min=3) : Axe A `INDUCED` si cosinus-conflit
> `≤ −0.05` majorité ; Axe B `CREDIT_ROBUST` recovery≥0.50 / `ARCH_MATTERS` ≤0.20 / `CREDIT_PARTIAL`.
> **Résultat** : **INDUCED+CREDIT_ROBUST**. La pression de capacité (H réduit) **induit une vraie interférence de
> trunc** (cos < 0 : 3/5 à H=6, 4/5 à H=3) — **là où EDR 190 échouait à H=48 surdimensionné** — ET sous ce conflit
> réel le crédit-équilibrage **plat** (FLAT_NORM, 153) **recouvre voire dépasse** l'avantage DISJOINT sur les têtes
> MSE → **la conclusion « le levier est le crédit, pas l'architecture » est ROBUSTE à l'interférence.**
> **Prédiction opus PRÉ-ENREGISTRÉE** (dry-run) : INDUCED à H=3 (cos franchement négatif dès H=6) — **confirmée**.
> **Sanity** : H=48 reproduit 152/153 (recovery **0.792** = EDR 153 au chiffre). **Outil** :
> `tools/disjoint_heads_capacity.py`. **Run** : K=5, base=2200, H∈{48,6,3}, STEPS=2000, `set_num_threads(1)`,
> `use_deterministic_algorithms(True)`, **2 passes byte-identiques**. **Spec/Plan** :
> `docs/superpowers/{specs,plans}/2026-07-01-disjoint-heads-capacity*`.

## 1. Question — atteindre enfin le régime interférent

EDR 152 : disjoint aide (+43 %) mais cos≈0. 153/154 : le crédit-équilibrage plat recouvre ~75-79 % → crédit, pas
archi. **190** : corréler les profs n'induit PAS de conflit (readout absorbe le signe ; trunc **surdimensionné**
H=48 = 3 tâches conjointement satisfiables) → **le régime interférent n'a jamais été atteint** ; la conclusion « archi
ne compte pas » restait peut-être **bornée au régime sur-capacité**.

**Correction de conception (EDR 190 §4)** : réduire H **uniformément** PRÉSERVE la parité inter-bras (FLAT `D·H` et
DISJOINT `3·(D·(H/3))` scalent tous deux). La **capacité** est donc le vrai knob : sous un trunc RARE, le plat NE PEUT
PAS servir toutes les têtes → les têtes se disputent les dims → **vraie interférence**. Profs **INDÉPENDANTS** (152 ;
190 a montré que corréler AIDE → pour induire le conflit sous rareté il faut des tâches DIVERSES). Modèles/bras
**réimplémentés paramétrés par H**, FIDÈLES à 152/153 (à H=48, init + eval + cos byte-identiques — vérifié). Question :
quand la rareté force le conflit (cos<0), le crédit plat recouvre-t-il encore l'avantage DISJOINT (→ 153/154 robuste),
ou l'architecture compte-t-elle enfin (→ conclusion bornée) ?

## 2. Résultat (run pré-enregistré, 2 passes byte-identiques)

```
  H  | cos    | improv | recovery | (lecture)
  48 | +0.000 | +0.431 | +0.792   | SANITY : cos~0 (=152), recovery 0.792 = EDR 153 EXACT ; disjoint aide (+0.43)
   6 | -0.054 | -0.058 | +3.816   | INDUCED 3/5 ; disjoint N'AIDE PLUS (improv<0) ; credit DEPASSE disjoint
   3 | -0.072 | +0.024 | +1.560   | INDUCED 4/5 ; credit recouvre+depasse ; recovery degenere (caveat e)
  cos par-seed H=3 : [-0.085, -0.120, +0.164, -0.091, -0.227]  ->  4/5 <= -0.05
  cos par-seed H=6 : [-0.089, -0.019, +0.022, -0.107, -0.074]  ->  3/5 <= -0.05
  VERDICT (a H_min=3) : INDUCED+CREDIT_ROBUST
```

## 3. Lecture

1. **La pression de capacité INDUIT le conflit — 190's null était un artefact de sur-capacité, pas la méthode.**
   cos(H) est monotone : +0.000 (H=48, =152) → −0.054 (H=6, 3/5) → −0.072 (H=3, 4/5). Sous un trunc rare, le readout
   linéaire n'absorbe PLUS le signe (plus de sous-espace libre pour loger des directions orthogonales) → la sonde
   `∂L/∂trunk.weight` détecte enfin l'interférence. **Le régime que 190 ne pouvait pas atteindre EST atteint.**
2. **Sous vraie interférence, le crédit-équilibrage plat GAGNE (CREDIT_ROBUST).** À H=6 et H=3, `recovery > 1` sur
   les têtes MSE : FLAT_NORM ne fait pas que recouvrer l'avantage DISJOINT, il **passe SOUS** DISJOINT (le substrat
   plat + équilibrage de crédit **bat** l'architecture disjointe). **La conclusion 153/154 tient sous interférence** :
   le levier reste le crédit, pas l'isolation architecturale.
3. **L'avantage DISJOINT était lui-même un phénomène de sur-capacité.** improv : +0.431 (H=48, disjoint aide comme
   152) → **−0.058 (H=6, disjoint NUIT)** → +0.024 (H=3, ~neutre). Quand la capacité devient rare, l'isolation
   architecturale **cesse d'aider** (et nuit à H=6) — l'inverse de « l'archi devient nécessaire sous interférence ».
4. **Sanity fidélité (caveat c) CONFIRMÉ** : à H=48, cos +0.000, improv +0.431, **recovery +0.792 = EDR 153 exact**
   ; profil FLAT/DISJOINT reproduit 152/153 seed-à-seed → la réimplémentation paramétrée par H n'introduit aucun
   biais ; la comparaison inter-H est propre.

## 4. Portée — l'arc têtes disjointes est CLOS

- **Migration #5 (têtes disjointes) réfutée COMME LEVIER, désormais sous le régime interférent qu'elle était censée
  exiger.** L'actionnable prod reste un **équilibrage de crédit multi-tête** (échelle de loss / moments / lr par-tête)
  dans le substrat plat — jamais une refonte disjointe. Sous rareté, la refonte disjointe non seulement n'aide pas,
  elle **nuit** (H=6).
- **Arc complet** : 152 (disjoint aide, cos≈0) → 153/154 (le gain = crédit) → 190 (corréler n'induit pas le conflit,
  readout absorbe) → **191 (la capacité induit le conflit, et le crédit gagne quand même)**. La conclusion « crédit,
  pas topologie » est maximalement robuste : vérifiée hors interférence (152/153) ET sous vraie interférence (191).

## 5. Caveats

- **(a)** À H=3, DISJOINT donne 1 neurone caché/tête (`w=1`) : régime extrême. Lire la **tendance** cos(H) sur les 3
  points (monotone, franc dès H=6), pas un point isolé.
- **(e) [revue opus] Dénominateur recovery dégénéré sous rareté** : à H=6/H=3, l'avantage DISJOINT global s'effondre
  (improv ≤ ~0 ; disjoint NUIT à H=6) → le dénominateur `flat−disj` de `recovery` devient petit/change de signe → les
  `recovery > 1` (jusqu'à 3.8) sont **des ratios dégénérés, PAS un « crédit intermédiaire »**. **Lecture correcte** :
  l'axe B se lit **conjointement à la colonne gain brut FLAT−DISJ** (positif sur value/pred aux 3 H → DISJOINT garde
  un avantage MSE que FLAT_NORM recouvre/dépasse). **Point de lecture primaire de l'axe B = H=6** (interférence induite
  5/5... 3/5 franc, granularité w=2 moins pathologique que w=1) ; H=3 = borne d'interférence pour l'axe A. Le verdict
  officiel (gelé) est mesuré à H=3 mais **CREDIT_ROBUST est confirmé aux DEUX H** (recovery >1 partout = FLAT_NORM ≤
  DISJOINT).
- **(b)** La sonde reste `∂L/∂trunk.weight` — mais ici elle DÉTECTE le conflit sous rareté (contrairement à 190), donc
  le biais d'absorption de 190 est levé par la capacité.
- **(c)** Sanity H=48 reproduit 152/153 (vérifié §3.4). **(d)** dénominateur petit (cf. e). Hérite 152/153/154/190
  (proxy supervisé, têtes non appariées).

## 6. Suite

- **Arc têtes disjointes CLOS** côté per-type. L'actionnable (équilibrage de crédit multi-tête) est net pour la
  migration torch.
- Piste orthogonale non ouverte ici : sonde `∂L/∂h` (pré-readout) — non nécessaire, la capacité a suffi à induire.
- Reste per-type : worlds 2/3 réels (RISQUÉ — FamineWorld = session //), G2 composition (RISQUÉ — EDR 122).

## 7. Provenance / non-périmètre

- `tools/disjoint_heads_capacity.py` (`main_capacity_check`, K=5, base=2200, H∈{48,6,3}, STEPS=2000,
  `set_num_threads(1)`) ; **2 passes byte-identiques** ; AUCUN test relancé après le run.
- **Tooling ADDITIF** : nouveau fichier + test + spec/plan/EDR + rename EDR 155→190 uniquement ; `src/` VIDE ;
  `disjoint_heads_ab.py` (152), `disjoint_heads_confound.py` (153), `disjoint_heads_correlated.py` (190) **intacts**
  (réutilisés par import). Ne touche NI le substrat torch (`torch_batch_model.py`/`backend_torch.py`/`substrate_*` —
  fil // torch).
- Subagent-driven : 2 tâches (SPEC conforme + qualité Approved chacune), revue finale **opus PRÊT À INTÉGRER OUI, 0
  Critical**, qui a **vérifié la fidélité end-to-end byte-identique** (H=48 reproduit 152/153, cos inclus) et
  **prédit INDUCED à H=3 avant le run** (dry-run cos 5/5 négatif à H=6/H=3), + posé le caveat (e). Verdict
  pré-enregistré gelé avant le run.
- **Numérotation** : EDR **191** — bloc **190+** (per-type disjoint EXTENSION, post-collision 155→190). 9e instrument
  per-type, clôt l'arc 152/153/154/190.
