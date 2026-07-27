---
id: EDR-160
type: EDR
title: "Le gate MULTIPLICATIF sigmoïde N'AMÉLIORE PAS l'additif pour le binding — tentative de fixer la contamination S1 résiduelle d'EDR-159. Comparaison appariée (3 seeds, 600ép) : scopé mult +0.322/hit 0.175 vs additif +0.286/hit 0.278 (conditionnement marginalement plus tranchant mais −37% accomplissement) ; uniforme mult +0.177/hit 0.081 vs additif +0.236/hit 0.154 (PIRE sur les deux + 1 seed collapse). L'init NÉGATIF de b_gate est essentiel (sinon le mult casse). L'additif linéaire (158/159) reste la primitive prod. Clôt la question de la forme du gate"
status: accepted
gate: null
verdict: MULTIPLICATIVE_GATE_DOES_NOT_IMPROVE_ADDITIVE
---

# EDR 160 : le gate multiplicatif sigmoïde n'améliore pas l'additif (l'additif reste la primitive)

## Contexte

EDR-159 a livré le binding TASK-AGNOSTIQUE (gate uniforme s'auto-scopant depuis H) mais avec un coût
résiduel : le gate additif uniforme se déclenche parfois à l'étape « means » (S1), supprimant X →
accomplissement plus bas (hit/p_x) que le gate scopé. Hypothèse : un gate MULTIPLICATIF (sigmoïde,
`SCALE·σ(H·w+b) ∈ [0,SCALE]`) — le sens littéral d'une porte (LSTM/GRU) — pourrait sortir ~0 hors-contexte
(suppression PROPRE) et ~SCALE en contexte, éliminant la contamination S1 sans coût.

## Méthode

`GATE_MULT`/`GATE_SCALE` dans `backend_torch.py` : `_gate_value` renvoie `SCALE·σ(H·w+b)` (mult) vs `H·w+b`
(additif), routé dans forward/`_td_update`/`learn_episode`. Point CRITIQUE découvert au smoke : le mult
avec `b_gate=0` démarre à `σ(0)=0.5 → SCALE/2` PARTOUT (always-on) et doit désapprendre → dégrade
(scopé mult tombe à −0.001). Fix : **init `b_gate=−4`** → `σ≈0.018` → gate démarre ÉTEINT (bon prior de
porte). Comparaison appariée gate additif vs multiplicatif, × {scopé, uniforme}, 3 seeds, 600 ép,
crédit épisodique, `binding_gap = P(Y|X) − P(Y|¬X)`.

## Constat

| gate épisodique (3 seeds, 600 ép) | additif gap / hit | multiplicatif gap / hit |
|---|---|---|
| scopé (`gate_last_only`) | +0.286 / **0.278** | +0.322 / 0.175 |
| uniforme (self-scope H) | **+0.236** / **0.154** | +0.177 / 0.081 |

`VERDICT = MULTIPLICATIVE_GATE_DOES_NOT_IMPROVE_ADDITIVE`. Scopé : mult marginalement plus tranchant en
conditionnement (+0.322 vs +0.286) mais −37% d'accomplissement (hit 0.175 vs 0.278). Uniforme
(task-agnostique) : mult PIRE sur les DEUX axes (gap +0.177 vs +0.236, hit 0.081 vs 0.154), avec 1 seed
qui s'effondre (−0.15).

## Lecture

- **Le multiplicatif n'améliore pas l'additif** : il échange de l'accomplissement contre un
  conditionnement marginalement plus pur (scopé) ou régresse carrément (uniforme). L'hypothèse « le mult
  fixe la contamination S1 sans coût » est RÉFUTÉE.
- **Cause mécanique** : la sigmoïde à init négatif démarre « éteinte » → Y supprimé par défaut → le gate
  ne déclenche Y que fortement conditionné = conditionnement tranchant mais Y globalement RARE (hit bas).
  Le biais additif non borné pousse Y plus librement → plus d'accomplissement pour un gap comparable.
- **La contamination S1 d'EDR-159 n'est PAS une faiblesse de forme du gate additif** — la rendre
  multiplicative ne la corrige pas, elle déplace le compromis. La contamination résiduelle vient de
  l'apprentissage du self-scope, pas de la non-bornitude du gate.
- **Insight réutilisable** : un gate sigmoïde exige un init de biais NÉGATIF (démarrer éteint) ; à init
  neutre il démarre always-on et casse le binding (−0.001). Vrai pour toute porte apprise.

## Conséquences

- **Primitive prod du binding CONFIRMÉE = gate ADDITIF linéaire** (158/159) : `CONDITION_GATE` +
  `GATE_TARGET` + `ANTISAT>0` + `learn_episode`. `GATE_MULT` reste dispo (flag OFF) mais non recommandé.
- **Question de la forme du gate CLOSE** : additif suffit et domine le sigmoïde multiplicatif pour ce
  binding ; inutile de ré-explorer cette piste. La faiblesse résiduelle (accomplissement du régime
  task-agnostique) est à traiter côté crédit/apprentissage du self-scope, pas côté forme de porte.
- Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-160`.

## Caveats

1. **Tâche DURE** (hit absolu bas) : le robuste est la COMPARAISON appariée additif vs mult (mêmes seeds,
   mêmes 600 ép), pas l'absolu.
2. 600 ép (vs 1000 ép en 158/159) pour l'appariement rapide ; le mult scopé dépasse déjà l'additif-1000
   en gap dès 600 ép → l'écart d'accomplissement n'est pas un artefact d'épisodes (c'est structurel :
   sigmoïde éteinte par défaut).
3. Un seul régime testé (`SCALE=8`, `b0=−4`, gate additif one-hot sur le logit cible) ; d'autres
   paramétrisations multiplicatives (SCALE appris, gate sur toute la distribution) non explorées —
   bornage, mais l'additif étant déjà simple ET meilleur, la charge de preuve incombe au mult.
4. means→ends 2-pas synthétique (cf. 147/158/159) ; substrat 172-nœuds dégénéré.
