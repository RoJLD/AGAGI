# Design — Gate de conditionnement sur action BINAIRE (cran 2, Brique A)

> Session 2026-07-10 (suite EDR-163/165/166). Cran 2 = gate de binding in-world sur l'action offensive
> (craft → throw l'outil). Décomposé en Brique A (mécanisme binaire, isolation, CE SPEC) + Brique B
> (câblage biosphère, suivi). Backlog : `../../BACKLOG.md` §Axe 1. Méthode : Commandement 15.

## Problème

Le gate de conditionnement livré (EDR-159/165, `backend_torch.py`) biaise une politique CATÉGORIELLE
sur les 8 logits de déplacement (`out[:, :_MOVE_LOGITS]`, `log_softmax` sur 8). Or l'action « ends » du
means→ends biosphère — utiliser l'outil crafté — est `do_throw = logits[8] > 0`, une action BINAIRE
hors de cette politique. Gater throw exige donc un mécanisme de gate + crédit sur une **décision
binaire**, absent du substrat. **Question : un readout de H peut-il apprendre à conditionner une action
binaire (throw) sur un contexte (did_craft), sous crédit épisodique — comme le gate catégoriel le fait
pour les moves (161/165) ?** On le teste en ISOLATION avant tout câblage biosphère invasif.

## Architecture — harnais autonome (fichier neuf)

`tools/torch_binary_gate_probe.py` : ne touche NI `backend_torch.py` (activement modifié par sessions //)
NI la biosphère. Réutilise le pop torch pour l'état H ; le mécanisme de gate binaire vit dans le harnais.

### Monde 2-pas binaire
- **S1** (obs_a) : l'agent choisit un move ; `did_craft = (argmax(move_logits) == CRAFT)`.
- **S2** (obs_b, n'encode PAS did_craft — doit être décodé de H via la récurrence) : décision BINAIRE
  `throw ~ Bernoulli(σ(logit_throw))`.
- Énergie/épisode : `+1` si `throw & did_craft` (composition réussie) ; coût de faim constant `−0.3`
  sinon (throw-sans-craft ou abstention) → l'abstention coûte, force l'engagement (patron EDR-161).

### Tête throw (le mécanisme nouveau)
- Params harnais : `w_throw` (N,) + `b_throw` (1,), séparés de W et du gate move.
- **ON** : `logit_throw = H·w_throw + b_throw` → conditionne sur H (peut décoder did_craft).
- **OFF** (contrôle) : `logit_throw = b_throw` (marginal, aucune lecture de H → ne peut pas conditionner).
- Échantillonnage : `throw_i ~ Bernoulli(σ(logit_throw_i))`.

### Crédit épisodique binaire + anti-saturation
- REINFORCE sur la log-vraisemblance de la décision throw prise :
  `logp_throw = throw*log σ(z) + (1−throw)*log(1−σ(z))`, pondéré par le retour épisodique baseliné.
- Anti-saturation : pénalité homéostatique sur la marginale `mean(σ(z))` (garde P(throw) loin de 0/1,
  préserve le gradient différentiel — patron EDR-136).
- Optimiseur Adam sur `[w_throw, b_throw]` (+ W via le pop si on veut ; MVP : W gelé, on isole la tête).

## Data flow
1. Init : pop torch (pour H), tête throw (`w_throw`/`b_throw`), Adam.
2. Par épisode : `pop.H=0` → forward S1 → move → `did_craft` ; forward S2 → `z=logit_throw(H_S2)` →
   `throw~Bernoulli(σ(z))` → énergie.
3. Fin d'épisode : REINFORCE binaire (retour baseliné) + anti-sat → step.
4. Mesure (dernier quart) : `binding_gap = P(throw|did_craft) − P(throw|¬did_craft)` + `comp_rate`.

## KPI et verdict
`binding_gap` (instrument direct d'EDR-126) = le gate binaire route-t-il throw sur le craft ? A/B
apparié ON vs OFF via `compute_ab_verdict` (diff = gap_ON − gap_OFF). Attendu si le mécanisme marche :
ON binde (gap > 0), OFF plat (gap ≈ 0, throw marginal ⊥ did_craft).

## Error handling
- Tête OFF : `w_throw` non utilisé (logit = b_throw) — pas de lecture de H, contrôle propre.
- `σ` clampé (`z` borné) pour éviter log(0) dans REINFORCE.
- Cohorte fixe, N stable (pas de rebuild ici — Brique A isole le mécanisme, pas la persistance).

## Testing
- La tête throw se construit (dims N) et un pas d'entraînement ne crashe pas.
- ON vs OFF : `run_arm` renvoie `binding_gap` + `comp_rate` ; ON produit un gap ≥ OFF sur un smoke seedé.
- `binding_gap` calculé correctement (P conditionnelles séparées did_craft vs ¬did_craft).
- `compare` produit un verdict apparié.

## Bornes (caveats)
- Monde synthétique 2-pas (proxy biosphère, comme 161/165) — indicatif, pas conclusif in-world.
- Mécanisme dans le harnais (pas backend_torch) : sera porté en Brique B (câblage biosphère). MVP isole
  la tête throw (W gelé possible) pour attribuer l'effet au gate binaire, pas au substrat.
- N stable ; pas de rebuild (la persistance = EDR-166, orthogonale ici).
- did_craft doit être décodable de H_S2 (récurrence within-épisode) ; si non, gap≈0 même ON (résultat
  informatif : le binding binaire échoue → borne pour la Brique B).

## Contraintes projet
- Fichiers NEUFS uniquement (`tools/torch_binary_gate_probe.py`, `tests/sandbox/test_torch_binary_gate_probe.py`).
  NE PAS toucher `backend_torch.py` (sessions // actives). Commits PATH-SCOPED.
- Réutilise `make_population`, `compute_ab_verdict`, et le patron monde/énergie d'EDR-161 (DRY si possible).

## Hors scope (Brique B, suivi)
Câblage du gate binaire dans `world_1_stoneage.py` (biais sur `logits[8]` avant `do_throw`, crédit throw
in-world) ; KPI biosphère (kills-avec-outil, rétention craft EDR-127) ; persistance du gate au rebuild
(EDR-166) ; promotion du mécanisme binaire dans `backend_torch.py`.
