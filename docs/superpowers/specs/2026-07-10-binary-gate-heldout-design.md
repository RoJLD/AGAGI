# Design — Gate binaire, test held-out sans confond (cran 2, Brique B1)

> Session 2026-07-10 (suite EDR-169). EDR-169 a montré que le harnais binaire jouet CONFOND binding et
> mémorisation (readout sur-paramétré + did_craft fixe + action hors H). B1 = refaire le test SANS le
> confond, en isolation, avant tout câblage biosphère (B2). Backlog : `../../BACKLOG.md` §Axe 1.

## Problème

EDR-169 : le gap gate-binaire élevé était de la mémorisation (contrôle shuffle : label faux binde autant).
Trois causes : (1) obs fixes → label fixe par agent, (2) S1 argmax déterministe, (3) action craft hors H.
**Question : quand le contexte (did_craft) est réellement présent dans l'état et mesuré en HELD-OUT, le
gate binaire binde-t-il throw dessus (distinct du shuffle) — ou le mécanisme est-il cassé ?**

## Architecture — harnais corrigé (fichier neuf)

`tools/torch_binary_gate_heldout_probe.py` : ne touche NI backend_torch NI la biosphère. Réutilise
`_energy_binary`, `_binding_gap` de `torch_binary_gate_probe` (DRY) + `make_population`,
`compute_ab_verdict`. Garde l'ancien harnais comme témoin du confond.

### Les 3 corrections (une par cause d'EDR-169)
1. **Obs VARIABLES par épisode** : `obs_a`, `obs_b` re-tirées à chaque épisode (RandomState qui avance) →
   plus de label fixe par agent → mémorisation d'identité éliminée (correction la plus fondamentale).
2. **S1 stochastique** : `move ~ softmax` échantillonné (pas argmax) → `did_craft = (move == CRAFT)`
   varie par épisode.
3. **did_craft encodé dans l'obs S2** : `obs_b[:, 0] = did_craft * signal_amp` (un canal porte le
   contexte, simule le spear-en-inventaire) → H_S2 le porte réellement ; le readout décode un contexte
   PRÉSENT, pas une identité.

### Held-out (le juge)
- Phase TRAIN (`train_ep` épisodes) : readout `w_throw`/`b_throw` entraîné par REINFORCE épisodique +
  anti-saturation (même mécanisme qu'EDR-169, machinerie validée).
- Phase TEST (`test_ep` épisodes) : readout GELÉ (`torch.no_grad`), obs FRAÎCHES, on collecte throw et
  did_craft, on calcule `binding_gap` sur ces données NON VUES. La mémorisation ne survit pas au held-out.

### Bras et verdict
- ON (vrai) : `z = H·w_throw + b`, did_craft réel.
- SHUFFLE : did_craft permuté (permutation fixe seedée) pour l'énergie ET le gap — contrôle du confond.
- KPI = `binding_gap` sur HELD-OUT. Verdict apparié = `gap_test(ON,vrai) − gap_test(ON,shuffle)` via
  `compute_ab_verdict`. **ON bat le shuffle sur held-out → mécanisme SAIN. Sinon → cassé.**

## Data flow
1. Init : pop torch (H), tête throw, Adam. RandomState(seed+1) pour les obs.
2. TRAIN : par épisode → nouvelles obs → S1 sampled → did_craft → obs_b encode did_craft → forward S1/S2
   → z, throw ~ Bernoulli → énergie (did_craft éventuellement shufflé) → REINFORCE + anti-sat → step.
3. TEST (readout gelé) : `test_ep` épisodes frais, mêmes étapes SANS update, collecte throw/did_craft.
4. `binding_gap` held-out + `comp_rate` + `throw_rate`.

## Error handling
- W gelé (H détaché) : gradient seulement via la tête throw.
- `σ` clampée (log(0) évité). Cohorte fixe, N stable.
- Held-out sur classes vides (did_craft tout True/False sur test) : `_binding_gap` gère (gardes `.any()`).

## Testing
- `run_arm(gate_on, shuffle_label, train_ep, test_ep, n_agents, seed) -> dict` : renvoie
  `binding_gap_heldout`, `comp_rate`, `throw_rate`, `gate_on`, `shuffle`.
- Smoke ON et SHUFFLE : structure + bornes, tourne vite.
- `compare` produit un verdict apparié `gap(vrai) − gap(shuffle)` sur held-out.
- did_craft encodé : test que `obs_b[:,0]` reflète did_craft (le canal porte bien le signal).

## Bornes (caveats)
- did_craft encodé dans un canal propre = décodage plus facile que la biosphère (contexte distribué via
  récurrence + obs riche) : B1 teste le MÉCANISME (router throw sur un contexte présent), pas la
  difficulté de représentation biosphère. Un ON≫shuffle held-out valide le mécanisme, pas le binding
  biosphère complet (= B2).
- Monde synthétique 2-pas. N stable. W gelé (isole la tête).
- Si ON ≈ shuffle même en held-out → le mécanisme ne route pas un contexte présent = résultat fort
  (le gate binaire est cassé, pas seulement le monde d'EDR-169).

## Contraintes projet
- Fichiers NEUFS (`tools/torch_binary_gate_heldout_probe.py`, `tests/sandbox/test_torch_binary_gate_heldout_probe.py`).
  NE PAS toucher backend_torch (sessions //). Commits PATH-SCOPED. DRY (réutilise `_energy_binary`/`_binding_gap`).

## Hors scope (B2, suivi)
Câblage du gate binaire dans `world_1_stoneage.py` (biais sur `logits[8]`, crédit throw in-world, did_craft
= spear en inventaire réel) ; KPI biosphère (kills-avec-outil, rétention craft) ; contexte distribué via
la vraie dynamique/récurrence.
