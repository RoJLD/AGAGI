# Banc factoriel 2⁴ — isolation des confounds du binding in-world (throw-gate)

> Territoire BIND/torch. Continue et TRANCHE EDR-176 (« échec sur-déterminé, non isolé »).
> Base de branche : `chantier/throw-gate-factorial` (off `chantier/throw-gate-rp-sweep`, PR #162 amont).

## Objectif

EDR-176 a conclu que l'échec du binding in-world du throw-gate est **multi-causal / sur-déterminé**,
mais **sans isoler** les 4 confounds identifiés (bornage point 4). Ce banc les isole par un **factoriel
complet 2⁴** et répond au test décisif :

> **La cellule tout-propre (les 4 confounds retirés simultanément) produit-elle un binding positif ?**

- **Oui (gap ON−SHUFFLE > 0, sign-test K≥12)** → le substrat EST capable de binder means→ends dans la
  vraie boucle biosphère ; l'échec 172-176 était le **banc**, pas le substrat. Confirme la thèse crédit
  in-world (converge COS Phase B).
- **Non** → verrou in-world **plus profond** que les 4 confounds connus → résultat majeur.
- Les 15 autres cellules donnent la **carte des effets principaux + interactions** : quel confound (seul
  et en paires) re-casse le binding.

## Les 4 facteurs

Chaque facteur est binaire. **Niveau « confound » = comportement ACTUEL = défaut** → strictement
non-régressif. Tous les knobs monde sont gated par `torch_throw_gate` (défaut `False`) ⇒ crans 0-1
inchangés. **Zéro modification de `backend_torch.py`.**

| # | Facteur | Niveau « confound » (défaut) | Niveau « propre » | Mécanisme |
|---|---------|------------------------------|-------------------|-----------|
| **F1** | Consommation | throw retire l'item (`inventory.pop(0)`) | non-consommateur : reseed d'un Spear après un throw de Spear | flag monde `torch_throw_no_consume` |
| **F2** | Poids-portage | Spear pèse 2.0 → −1.0 énergie/tick (détresse) | portage exempté (coût=0), **dégâts conservés** | flag monde `torch_throw_weightless` |
| **F3** | Densité-payoff | proies rares (`r·P` sous plancher) | proies denses (`r·P` élevé) | knob banc existant `prey_count` |
| **F4** | Crédit | marginal (`ret = r − r.mean()`) | conditionnel : baseline par groupe de contexte | flag monde `torch_throw_conditional_credit` |

### F1 — Consommation (`torch_throw_no_consume`)

**Confound (EDR-174)** : throw consomme le Spear ⇒ juste après, l'agent est en contexte ¬spear ; le throw
suivant (bois/roche) gonfle mécaniquement `P(throw|¬spear)` et anti-binde.

**Correctif** : dans le bloc balistique de [world_1_stoneage.py](../../../src/worlds/world_1_stoneage.py)
(après `self.items.append(thrown_item)` ~ligne 1373), si `self.use_torch_inworld and self.torch_throw_gate
and self.torch_throw_no_consume and thrown_item.get("type") == "Spear"`, ré-insérer un Spear en tête
d'inventaire de l'agent : `agent["inventory"].insert(0, {"type": "Spear", "weight": 2.0})`. Le contexte
spear PERSISTE à travers le throw ⇒ `P(throw|¬spear)` n'est plus gonflé par la consommation.

Poids 2.0 (physique) conservé pour rester orthogonal à F2 (F2 gère l'exemption de portage, pas le poids stocké).

### F2 — Poids-portage (`torch_throw_weightless`)

**Confound** : le Spear pèse 2.0 ⇒ coût de portage `carry_weight * 0.5 = 1.0` énergie/tick (ligne 689-690)
⇒ contexte-spear = détresse énergétique ⇒ `logits[8]` de base plus bas, que le gate ne surmonte pas.

**Piège à éviter** : le poids sert AUSSI aux dégâts (`damage = energy_spent * weight`, ligne 1376). Baisser
le poids stocké (comme le ferait un `spear_weight` léger du banc) **couplerait** portage ET payoff — ce
serait re-mélanger F2 et F3. Le correctif doit **découpler** : exempter le portage, garder les dégâts.

**Correctif** : à la ligne 689, quand `self.use_torch_inworld and self.torch_throw_gate and
self.torch_throw_weightless`, exclure le Spear du calcul du coût de portage :
```python
carry_weight = sum(
    i.get("weight", 1.0) if isinstance(i, dict) else 1.0
    for i in agent["inventory"]
    if not (weightless and isinstance(i, dict) and i.get("type") == "Spear")
)
```
(où `weightless` est le flag résolu une fois). Les dégâts (ligne 1376) lisent toujours `thrown_item["weight"]
= 2.0` ⇒ payoff inchangé. Portage du Spear = 0, autres items inchangés.

### F3 — Densité-payoff (`prey_count`, knob banc existant)

**Confound** : `r·P` (récompense fiable × proba de succès) sous le plancher de rétention (loi rétention-167 /
EDR-175). EDR-176 a montré que monter `prey_count` seul ne suffit pas (gap reste négatif) — c'est pourquoi
F3 est UN facteur parmi 4, pas le levier isolé.

**Mécanisme** : déjà présent dans `run_arm` (`prey_count` → `w.config.target_prey_count` + `w.prey_regen_burst`).
Niveaux : `sparse = 15` (proies rares, `r·P` bas) vs `dense = 300` (proies nombreuses, `r·P` haut). Valeurs
cohérentes avec le sweep EDR-176 (15→400, où 400 saturait à ~28 kills ⇒ 300 = régime dense effectif).

**Aucune modification monde** pour F3 — purement piloté par le banc.

### F4 — Crédit conditionnel (`torch_throw_conditional_credit`)

**Confound** : `_learn_throw_gate` calcule `ret = r − r.mean()` (ligne 1051) = baseline MARGINALE (moyenne
population). Le gradient apprend « throw paie en moyenne », pas « throw-SI-spear ». Le contingent n'est pas
crédité.

**Correctif** : baseline **conditionnée au contexte**. `_throw_ctx` (présence spear AVANT le pop) est déjà
stocké par agent (ligne 1224). Quand `self.torch_throw_conditional_credit`, remplacer la baseline globale par
la moyenne intra-groupe :
```python
ctx = np.array([1.0 if a.get("_throw_ctx") else 0.0 for a in self.agents], dtype=np.float32)
if self.torch_throw_conditional_credit:
    adv = r.copy()
    for grp in (0.0, 1.0):
        m = (ctx == grp)
        if m.any():
            adv[m] = r[m] - float(r[m].mean())   # baseline par contexte
    ret = torch.tensor(adv)
else:
    ret = torch.tensor(r - float(r.mean()))       # marginal (actuel)
```
L'avantage reflète « throw a aidé **sachant mon contexte** » (contingent) plutôt que « throw paie en moyenne »
(marginal). Le shuffle permute `r` AVANT ce calcul (ordre inchangé : shuffle puis baseline) ⇒ le témoin
d'artefact reste valide sous les deux régimes de crédit.

**Alternative écartée (YAGNI)** : ajouter un terme contrastif explicite `P(throw|spear) − P(throw|¬spear)`
dans la loss — plus lourd, non nécessaire pour un facteur binaire. Retenu si le factoriel montre F4 dominant
mais insuffisant.

## Architecture (unités isolées)

Trois unités à responsabilité unique, interfaces explicites :

1. **Knobs monde** — [world_1_stoneage.py](../../../src/worlds/world_1_stoneage.py). Trois flags booléens
   (`torch_throw_no_consume`, `torch_throw_weightless`, `torch_throw_conditional_credit`), init défaut `False`
   près des autres flags throw-gate (~ligne 59-67). Trois blocs mécaniques (F1 balistique, F2 portage, F4
   crédit). Chaque bloc gardé par le flag correspondant ET `torch_throw_gate`. **Contrat** : flags OFF ⇒
   comportement identique à l'actuel (testé).

2. **Banc factoriel** — [torch_throw_gate_inworld_ab.py](../../../tools/torch_throw_gate_inworld_ab.py).
   - `run_arm(...)` : +3 params `no_consume=False, weightless=False, conditional_credit=False`, passés aux
     flags monde (`w.torch_throw_no_consume = no_consume`, etc.) après construction du monde, avant la boucle.
   - `compare_factorial(seeds, ticks, warmup, prey_sparse, prey_dense, ...)` : nouvelle fonction. Balaie les
     **16 cellules** = produit `{no_consume∈{F,T}} × {weightless∈{F,T}} × {prey∈{sparse,dense}} ×
     {conditional_credit∈{F,T}}`. Pour chaque cellule : K seeds × 2 bras (ON `shuffle=False`, SHUFFLE
     `shuffle=True`), agrège `binding_gap`, verdict via `compute_ab_verdict`. Réutilise `_seed_spears` /
     `_reseed_spears` (poids seed physique 2.0 conservé — l'exemption de portage vient du flag F2, pas du
     poids seed). **Contrat de sortie** : table 16 lignes (cellule, diff médian ON−SHUFFLE, sign_p, verdict)
     + effets principaux (4) + interactions 2-way + ligne titre cellule-0.

3. **Tests** — [test_torch_throw_gate_world.py](../../../tests/sandbox/test_torch_throw_gate_world.py). Un test
   par knob : (a) défaut OFF ⇒ mécanique inchangée (Spear consommé / porté-coûteux / baseline marginale) ;
   (b) ON ⇒ mécanique ciblée changée (Spear reseedé / portage nul mais dégâts intacts / baseline par contexte).
   Plus un test de fidélité « cellule-0 = les 4 niveaux propres ». Isolation du signal via
   `torch_throw_antisat = 0.0` (Adam sature au 1er pas sinon — pattern établi 173/174).

## Mesure, verdict & analyse

- **Par cellule** : `binding_gap = P(throw|spear) − P(throw|¬spear)` sur la VRAIE présence-spear, fenêtre
  post-warmup, couples (agent,tick). Diff = `gap_ON − gap_SHUFFLE`. Verdict `GRADIENT_GAGNE` (diff>0, binde) /
  `HEBBIEN` (diff<0, anti-binde) via `compute_ab_verdict` (partagé, **ne pas modifier**, cf. garde-fou
  puissance).
- **Effets principaux** : `moyenne(diff | facteur=propre) − moyenne(diff | facteur=confound)`, poolé sur les
  8 cellules de chaque niveau ⇒ bien puissancé même à K modéré.
- **Interactions** : 2-way (6 paires) rapportées ; 3/4-way seulement si non-additivité manifeste.
- **Test-titre (garde-fou `power-evaporation`)** : la cellule-0 binde-t-elle ? sign-test sur K seeds. **Pas de
  verdict POSITIF sous n=12** ⇒ cellule-0 exige K≥12.

## Plan de calcul

16 cellules × K × 2 bras (ON+SHUFFLE).
- **Carte** : K=8 sur les 16 cellules (128 runs ON + 128 SHUFFLE). Effets principaux/interactions poolés
  (n=8×8=64 par niveau) ⇒ bien puissancés.
- **Confirmation** : K=12 focalisé sur la cellule-0 + la meilleure cellule positive (seuls les verdicts
  POSITIFS exigent n≥12).
- K réglable à l'exécution (`TTG_SEEDS`). Warmup/ticks hérités des runs 173-176 (défauts `run_arm`).

## Non-régression

- Les 3 flags monde défaut `False` ; tous gardés par `torch_throw_gate` (défaut `False`). Crans 0-1 et tout
  chemin non-torch strictement inchangés.
- F3 est purement banc (aucune modif monde).
- Le shuffle reste le témoin d'artefact sous tous les régimes (permutation AVANT la baseline).
- `compute_ab_verdict` et `torch_throw_shuffle` non modifiés.

## Fichiers touchés

- Modif : `src/worlds/world_1_stoneage.py` (3 flags init + bloc F1 balistique + bloc F2 portage + bloc F4 crédit)
- Modif : `tools/torch_throw_gate_inworld_ab.py` (+3 params `run_arm` + `compare_factorial`)
- Modif : `tests/sandbox/test_torch_throw_gate_world.py` (tests des 3 knobs + fidélité cellule-0)
- Nouveau (à l'exécution, hors périmètre de ce spec) : `docs/EDR/177_*.md`

## Hygiène de branche

Branche `chantier/throw-gate-factorial` basée sur `chantier/throw-gate-rp-sweep` (PR #162 amont, ouverte).
Commits path-scopés (arbre partagé, sessions parallèles). La PR future mentionnera #162 en dépendance amont
pour éviter un orphelin (cf. incident #160→#162).

## Lignée

Continue et TRANCHE [[torch-inworld-integration-plan]] (arc 172-176). Isole les 4 confounds nommés par
EDR-176. Test décisif de [[warm-start-transversal-law]] in-world (le substrat binde-t-il propre ?) et de la
thèse crédit [[decisive-substrate-thesis-test]] (COS Phase B) dans la VRAIE biosphère.
