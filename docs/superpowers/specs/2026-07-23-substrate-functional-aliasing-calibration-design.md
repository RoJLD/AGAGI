# Calibration de l'aliasing FONCTIONNEL de substrat (garde `assert_no_functional_aliasing`)

**Date** : 2026-07-23
**Statut** : design validé, prêt pour plan d'implémentation
**Vision parente** : AGI-Taxonomy (backlog P4.3) — débloque **SP-2 mesuré**. Suite directe de [[agi-taxonomy-os-taxonomy-bridge]] / CALIB-SP3.

---

## 1. Contexte et raison d'être

CALIB-SP3 a établi (verdict GO) que l'ablation within-subject récupère un DAG de prérequis imposé et reste
spécifique **sous confond corrélé** — mais dans un monde analytique **A1 sans substrat partagé**. Sa portée
bornée l'a dit explicitement : *« l'aliasing de SUBSTRAT (représentation partagée) est HORS de portée de A1
→ reste à vérifier en SP-2 sur le substrat réel. »* Ce sous-projet lève ce report.

**Le risque concret.** Sur un vrai substrat récurrent, deux capacités X et Y peuvent partager des neurones.
Ablater le canal de X pour mesurer « Y demande-t-elle X ? » peut alors **endommager Y par la représentation
partagée**, produisant un FAUX POSITIF « Y demande X » qui n'est qu'un artefact de l'ablation non chirurgicale.
C'est exactement le mode d'échec que SP-2 (peupler le graphe par ablation) hériterait.

**Le trou d'instrument.** Le garde existant `assert_no_aliasing` (`tools/experiment_preflight.py`, via
`np.shares_memory`) n'attrape que l'aliasing **structurel de mémoire-vue** — le bug EDR-WARM-007, où
`TorchPopulationModel.forward` renvoie `logits = H_new[:, N-O:N]`, une VUE de l'état récurrent (toujours
active par défaut : le `.clone()` ne se déclenche que si le gate de conditionnement est ON, off par défaut).
Il ne voit **RIEN** de l'aliasing **fonctionnel** : buffers séparés, mais Y calcule via un neurone que
l'ablation de X perturbe. Ce sous-projet ajoute le garde manquant et le calibre.

## 2. Objectif et question

**Question** : l'ablation chirurgicale within-subject d'un canal d'entrée X reste-t-elle spécifique — une
capacité de CONTRÔLE Y, connue indépendante de X, ne bouge PAS — sur le vrai chemin récurrent d'AGAGI ? Et
un garde comportemental détecte-t-il la fuite quand X et Y partagent leur substrat, là où `np.shares_memory`
est aveugle ?

**Go / no-go** :

- **PASS** → sur un câblage DISJOINT, ablater X est un no-op EXACT pour Y (spécificité fonctionnelle) ; sur
  un câblage PARTAGÉ, Y fuit et le nouveau garde le détecte → SP-2 mesuré dispose d'un contrôle de
  spécificité opposable.
- **FAIL** → même un câblage disjoint laisse fuir l'ablation → l'ablation within-subject n'est pas
  fonctionnellement isolable sur ce moteur, et SP-2 mesuré doit revoir son mécanisme d'ablation.

## 3. Le payload (ce qui rend la calibration non-tautologique)

Le contraste décisif : sur le génome PARTAGÉ (Y fuit réellement), `np.shares_memory` entre les deux sorties
de forward rend **False** (arrays indépendants) → `assert_no_aliasing` **passe** (aveugle), tandis que
`assert_no_functional_aliasing` **tire** (Y a bougé). Un test qui prouve que l'ancien garde rate ce que le
nouveau attrape n'est pas décoratif. Générateur A du pré-vol respecté : la sonde produit **les deux issues**
(SURGICAL sur disjoint, FUNCTIONAL_LEAK sur partagé), et l'ablation change bien la capacité PROPRE de X
(sinon « pas de fuite sur Y » serait vacuux — ablation d'un canal mort).

## 4. Approche : vrai chemin récurrent + câblage imposé

On construit à la main un `Genome` (matrice `W` contrôlée) et on le fait tourner dans le VRAI
`recurrent_forward` (`src/seed_ai/rl_evolution.py`) — comme `partial_oracle`/`GroundTruthCarryWorld`
injectent un étalon dans le vrai banc. On exerce donc le vrai code d'ablation/forward (un bug propre au
moteur de prod ne peut pas passer) tout en gardant une **réponse connue par construction** (c'est moi qui
câble disjoint vs partagé). Déterministe → le no-op est **EXACT**, pas statistique (plus fort que SP-3).

Rejeté : jouet numpy pur (n'exerce pas le moteur réel) ; MambaAgent évolué (câblage appris → pas de réponse
connue → non calibrable, c'est l'étape d'APPLICATION en SP-2, pas la calibration).

## 5. Faits vérifiés du moteur (contraintes de conception)

Cartographie du code (refs à figer au plan) :

- **Layout des nœuds** : `[0:I]` entrées · `[I:N-O]` cachés · `[N-O:N]` sorties. `W[i,j]` = poids source i →
  cible j. Diagonale = **forget-gate** `δ=sigmoid(clip(diag,−10,10))`, retirée de la propagation. Règle LTC :
  `H⁺=(1−δ)·H + δ·tanh(H·W_offdiag)`. Injection d'entrée **destructive** : `H[:,:I]=obs` (écrase). Lecture :
  `preds=H[:,−O:]`.
- **1 micro-tick par appel** pour un génome reflex (`organ_genes=[False,False]` par défaut, MCTS OFF). Un
  chemin entrée→caché→sortie (2 sauts) exige donc **≥2 ticks** : on reboucle `H` en `H_prev` sur K appels.
- **`recurrent_forward(genome, obs, H_prev, Hh, Hp, env_surprise=0.0)` → `preds, H, Hh, Hp, surprise`**.
  `Hh`/`Hp` sont des pass-through (zéros OK). `obs` shape `(B,I)`, `H_prev` `(B,N)`.
- **Halt neuron** = index `N−O−1` ; sans effet en reflex (MCTS OFF) — garder MCTS off, ne pas mettre la
  capacité de contrôle sur ce nœud.
- **L'ablation mono-canal n'existe pas dans le code** : `PerceptionAblatedMamba` dérange TOUTE l'obs
  (permutation cross-agent). Le zéro sur une colonne d'entrée est à implémenter dans la sonde.

## 6. Architecture

### 6.1 Génome-étalon paramétré (dans `tools/ground_truth_worlds.py`)

`make_aliasing_genome(alpha)` — famille à DOSE unique, N=7, I=2, O=2 :

- Nœuds : `0`=X(in), `1`=Y(in), `2`=hA, `3`=hB, `4`=hS (cachés), `5`=out_X, `6`=out_Y.
- Chemin propre de X : `W[0,2]=1` (X→hA), `W[2,5]=1` (hA→out_X).
- Chemin propre de Y : `W[1,3]=1` (Y→hB), `W[3,6]=1` (hB→out_Y).
- **Fuite dosée** : `W[0,4]=1` (X→hS), `W[4,6]=alpha` (hS→out_Y). `alpha` est la DOSE de partage.
- Diagonale = 0 (δ=0.5, demi-fuite) sur tous les nœuds. `mutation_genes`/`organ_genes` par défaut (reflex).
- `alpha=0` → DISJOINT : out_Y ne dépend que de Y ; ablater X est un no-op pour out_Y, mais tue out_X (la
  capacité PROPRE de X répond → ablation non vacuse). `alpha>0` → PARTAGÉ : ablater X déplace out_Y.

### 6.2 Sonde d'aliasing fonctionnel (`tools/functional_aliasing_probe.py`)

- `run_functional_aliasing_probe(genome, x_input=0, x_readout=0, control_readout=1, settle_ticks=4, test_input=(1.0, 1.0))`
  (le nom `run_*probe` trippe le cliquet). **Conventions d'index** : `x_input` = index d'ENTRÉE à ablater
  (`[0:I]`) ; `x_readout` et `control_readout` = index relatifs aux O SORTIES (0-based dans `preds=H[:,-O:]`).
  Pour l'étalon : `x_input=0` (X), `x_readout=0` (out_X, sortie 0 = nœud 5), `control_readout=1` (out_Y,
  sortie 1 = nœud 6). Fait tourner `recurrent_forward` sur `settle_ticks` (reboucle `H` en `H_prev`), entrée
  intacte vs entrée avec la colonne `x_input` mise à 0. Renvoie
  `{"leakage": |Δ preds[control_readout]|, "x_response": |Δ preds[x_readout]|, "verdict": ...}`.
- `functional_aliasing_verdict(leakage, x_response, tol=1e-9)` (`*verdict*` → cliquet) :
  `FUNCTIONAL_LEAK` si `leakage > tol` ; `SURGICAL` si `leakage <= tol` ET `x_response > tol` (ablation
  non vacuse) ; `VACUOUS_ABLATION` si `x_response <= tol` (l'ablation n'a rien fait, générateur A échoué).

### 6.3 Nouveau garde de pré-vol (`tools/experiment_preflight.py`)

- `assert_no_functional_aliasing(control_intact, control_ablated, tol=1e-9, label="capacité de contrôle")` :
  lève `PreflightError` si `|control_intact − control_ablated| > tol`. Docstring citant l'erreur concrète
  qu'il aurait attrapée (le faux positif de demande par aliasing de substrat), format du module. C'est le
  complément COMPORTEMENTAL de `assert_no_aliasing` (structurel) — les deux coexistent, distincts.

## 7. Flux de données

```text
make_aliasing_genome(alpha) ──▶ Genome (W câblée)
                                     │
        recurrent_forward × settle_ticks  (H rebouclé), entrée intacte
        recurrent_forward × settle_ticks  (H rebouclé), colonne X = 0
                                     │
     leakage = |out_Y(intact) − out_Y(ablée)|   x_response = |out_X(intact) − out_X(ablée)|
                                     │
        functional_aliasing_verdict(leakage, x_response)  ──▶ SURGICAL | FUNCTIONAL_LEAK | VACUOUS
                                     │
        assert_no_functional_aliasing(out_Y_intact, out_Y_ablée)  (garde opposable pour SP-2)
```

## 8. Les trois formes canoniques de calibration

Dans `tests/sandbox/test_instrument_calibration.py` + entrée `CALIBRATED` pour les deux instruments détectés :

1. **no-op EXACT (spécificité)** : `alpha=0` → `leakage == 0.0` EXACT (déterministe) → `SURGICAL` ; ET
   `x_response > 0` (l'ablation tue bien la capacité propre de X → non vacuse). `assert_no_functional_aliasing`
   passe.
2. **contrôle positif (fuite)** : `alpha=1.0` → `leakage > 0` → `FUNCTIONAL_LEAK` ; le garde TIRE.
3. **monotonie (direction)** : balayage `alpha ∈ {0, 0.3, 0.6, 1.0}` → `leakage` croît strictement.

**Contraste structurel↔fonctionnel** (le test qui justifie le nouveau garde) : sur `alpha=1.0`,
`np.shares_memory(out_Y_intact, out_Y_ablée)` est False → `assert_no_aliasing` **passe** (aveugle) alors que
`assert_no_functional_aliasing` **lève** → prouve que le fonctionnel n'est pas couvert par le structurel.

## 9. Intégration aux rituels

- **Cliquet** : `run_functional_aliasing_probe` et `functional_aliasing_verdict` détectés → cas de calibration
  écrits dans la même passe (sinon le hook pre-commit bloque). `assert_no_functional_aliasing` et
  `make_aliasing_genome` ne matchent aucun motif d'instrument → pas d'entrée cliquet (comme `assert_no_aliasing`).
- **Pré-vol** : ce sous-projet AJOUTE un garde à `experiment_preflight.py` — auto-amélioration de la suite qui
  a servi à SP-3. Générateur A couvert par la sonde (SURGICAL vs FUNCTIONAL_LEAK), no-op exact, garde de
  vacuité (`x_response`).
- **Record** `docs/EDR/CALIB-ALIAS_...md` : frontmatter `gate:`/`tests:[SDR-Gx]`/`adopts:` ; grave le
  PASS/FAIL. Les issues négatives se gravent au même titre.

## 10. Déterminisme et unité

- **Déterministe** : `recurrent_forward` est une fonction pure du (génome, obs, H_prev) → le no-op est EXACT
  (bit-identique), aucun seed nécessaire pour la claim centrale. Option de robustesse : rejouer sur plusieurs
  `test_input` aléatoires et vérifier que le no-op tient sur toute la distribution (borné, cheap).
- **Coût** : pur numpy via `recurrent_forward`, aucun bail `kuzu`, aucun run long.

## 11. Portée v0 (YAGNI)

Un seul génome-étalon paramétré (I=2, O=2, N=7), balayage de `alpha` sur 4 points. Suffit aux trois formes +
au contraste structurel/fonctionnel. Substrats plus larges, multi-capacités, et surtout **l'APPLICATION au
MambaAgent évolué réel** (le câblage appris, non contrôlable) → SP-2, hors v0.

## 12. Critères de succès

1. Les deux instruments existent, détectés par le cliquet, avec leurs cas dans `CALIBRATED`.
2. `assert_no_functional_aliasing` livré dans `experiment_preflight.py`.
3. Les trois formes passent + le contraste structurel/fonctionnel (l'ancien garde rate, le nouveau attrape).
4. Un record grave le verdict go/no-go, frontmatter conforme.

## 13. Hors scope

L'application de la sonde/garde à un MambaAgent ÉVOLUÉ réel (mesurer si ses capacités aliasent effectivement)
= ouverture de SP-2 mesuré. La correction éventuelle de l'aliasing mémoire-vue par défaut de
`TorchPopulationModel.forward` (le `.clone()` conditionnel) = dette séparée à consigner, pas ce sous-projet.

## 14. Risques et pièges (issus de la cartographie du moteur)

- **2 sauts ⇒ ≥2 ticks** : un chemin entrée→caché→sortie n'atteint pas la sortie en 1 tick reflex. Rebouler
  `H` en `H_prev` sur `settle_ticks` (≥3 pour traverser X→hS→out_Y et laisser le LTC se stabiliser). Un test
  doit vérifier que `out_X` et `out_Y` RÉPONDENT à leurs entrées (sinon `settle_ticks` trop court → tout à 0,
  no-op dégénéré, piège WARM-002).
- **Injection destructive** : `H[:,:I]=obs` réécrit les nœuds d'entrée chaque tick — ne pas s'en servir comme
  accumulateurs.
- **Diagonale = gate, pas un poids** : la mettre à 0 (δ=0.5) ; ne pas l'utiliser pour câbler un signal.
- **Collision halt-neuron** : garder MCTS OFF (reflex) et la capacité de contrôle hors de l'index `N−O−1`.
- **Métrique VIVANTE** : le no-op exact ne vaut que si `out_Y` répond bien à `Y` (amplitude non nulle) — sinon
  « rien ne bouge » est trivial. Asserter `out_Y`(entrée Y) ≠ `out_Y`(sans Y).
