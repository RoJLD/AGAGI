# Substrat bilinéaire : débloquer la composition (le verrou dominant)

**Date** : 2026-08-03
**Statut** : design validé, prêt pour plan d'implémentation
**Vision parente** : AGI-Taxonomy (backlog P4.3) + thèse SOTA-gap. Le finding LANG-MEMORY (2026-07-28) a établi
que la capacité LANGAGE (composition `(q+key)%K`) N'ÉMERGE PAS sur le substrat contractif — mur de
composition/binding, le verrou DOMINANT. Ce sous-projet ATTAQUE ce verrou. Cf. [[sota-gap-substrate]],
[[planner-depth1-refuted]] (précédent : compo affine échouait jusqu'à un terme bilinéaire), [[agi-taxonomy-os-taxonomy-bridge]].

---

## 1. Objectif

Ajouter un terme d'interaction **BILINÉAIRE** flag-gated au substrat (`TorchPopulationModel._step`) et
**PROUVER par calibration** qu'il débloque la composition : la tâche `(q+key)%K` — nulle sur le substrat
PLAIN (mesuré : 0.15-0.33 sous REINFORCE/BPTT/imitation) — devient APPRENABLE avec le terme bilinéaire.
Livrable = le substrat bilinéaire + la preuve calibrée. Re-tenter `language→memory` et la généralisation
AVEC ce substrat = sous-projets SUIVANTS (hors scope ici).

## 2. Pourquoi bilinéaire, et pourquoi représentationnel (pas crédit)

Le `_step` actuel est **affine en H** : `H_new = (1-δ)·H + δ·tanh(H·W_off)` (δ=σ(diag W)). L'excitation
`H·W_off` est une combinaison LINÉAIRE des unités — aucun produit `H_i·H_j` possible. Or `(q+key)%K` exige
une INTERACTION entre la représentation de `q` et celle de `key` (modulo = non-linéaire dans le produit). Le
finding LANG-MEMORY a isolé le blocage au REPRÉSENTATIONNEL (l'imitation SUPERVISÉE échoue aussi → pas le
crédit ; le pur-rappel apprend → machinerie OK). Un terme bilinéaire donne au substrat la classe de fonctions
manquante (produits d'unités), précisément ce qu'ajoutait le terme bilinéaire de PLAN-001/003 pour le planning.

## 3. La modification substrat (flag-gated, backward-compatible)

`src/agents/backend_torch.py`, `TorchPopulationModel` :

- **Flag de classe** : `BILINEAR = False` (défaut). Quand `False`, le modèle est **BIT-IDENTIQUE** à
  l'actuel (aucun paramètre ni calcul ajouté) — condition non-négociable (fichier CORE, nombreux dépendants).
- **Paramètres (créés SEULEMENT si `BILINEAR`)** : forme **LOW-RANK** (un bilinéaire plein (B,N,N,N)=172³/agent
  est prohibitif). Rang `r` petit (défaut `BILINEAR_RANK=16`). Par agent (B copies, comme `W`) :
  `U`,`V` de forme `(B, N, r)`, `W_bl` de forme `(B, r, N)`. ~`3·N·r` params/agent (~8000 à N=172,r=16).
- **Terme dans `_step`** : l'excitation devient
  `excitation = H·W_off + bilinear(H)` avec `bilinear(H) = ((H·U) ⊙ (H·V)) · W_bl` (⊙ = produit de Hadamard
  élément-par-élément dans l'espace de rang r) — chaque nœud reçoit une somme de PRODUITS de projections de
  H. Puis `H_new = (1-δ)·H + δ·tanh(excitation)` inchangé sinon. (Insertion DANS le tanh : le bilinéaire
  contribue au même canal d'excitation que le linéaire.)
- **Optimisation** : quand `BILINEAR`, les params `U,V,W_bl` sont différentiables et inclus dans l'optimiseur
  par l'appelant (le banc : `Adam([W, U, V, W_bl])`). `learn_episode` calcule la perte via `_step` (qui utilise
  les nouveaux params si `BILINEAR`) → le gradient circule sans changer `learn_episode`. Vérifier que
  `learn_episode`/`forward` restent différentiables via les nouveaux params.
- **Init** : `U,V` init petit (p.ex. `randn*0.1`), `W_bl` init 0 → au démarrage le terme bilinéaire vaut 0 →
  l'agent bilinéaire DÉMARRE comme le plain puis apprend l'interaction (init douce, pas de choc).

## 4. La calibration (le cœur — générateur A dans les deux sens)

La modif produit une AFFIRMATION scientifique (« le bilinéaire débloque la composition ») → doit être
CALIBRÉE. La calibration EST la comparaison plain-vs-bilinéaire, sur vérité-terrain connue :

- **Contrôle POSITIF (le levier débloque)** : la tâche composition `(q+key)%K`. `BILINEAR=False` → NUL
  (`lang_intact` médian ≤ 1/K+0.15 ≈ 0.32, reproduit le finding). `BILINEAR=True` → APPREND (`lang_intact`
  médian nettement > 0.32, idéalement fort avec séparation par-seed). Le levier produit les DEUX issues.
- **Contrôle NO-OP (spécificité)** : le PUR-RAPPEL (que le plain apprend DÉJÀ, ~0.88-0.90). `BILINEAR=True`
  doit **ENCORE** l'apprendre (pas de régression). Le terme bilinéaire n'abîme pas ce qui marchait.
- **Contrôle de RÉGRESSION (backward-compat)** : `BILINEAR=False` sur la tâche composition = BIT-IDENTIQUE au
  substrat actuel (même null, mêmes nombres par-seed déterministes) — prouve que le flag off ne change RIEN.

La sonde `run_bilinear_composition_probe(...)` (nom `run_*probe` → trippe le cliquet) entraîne la tâche
`(q+key)%K` avec `BILINEAR` on/off et renvoie `{plain_intact_median, bilinear_intact_median, unlocked: bool,
noop_ok: bool, per_seed: {...}}`. Cas dans `tests/sandbox/test_instrument_calibration.py` + `CALIBRATED`.

## 5. Backward-compatibilité (non-négociable)

- `BILINEAR=False` par défaut → aucun test existant ne change de comportement. **Faire tourner la suite
  substrat existante** (`tests/` touchant `backend_torch`/`MambaAgent`) et vérifier VERTE avant/après.
- Aucun paramètre créé quand off (pas de surcoût mémoire/calcul pour les milliers d'appels existants).
- Le flag est de classe (comme `CONDITION_GATE`/`GATE_TARGET`) → activable par un banc, off partout ailleurs.

## 6. Verdict

- `unlocked = (plain_intact_median ≤ 0.32) ET (bilinear_intact_median > 0.32 avec marge + séparation)` →
  le substrat bilinéaire DÉBLOQUE la composition. + `noop_ok` (pur-rappel non régressé) + régression
  bit-identique off. n ≥ 12 seeds pour le verdict.
- **Si le bilinéaire ne débloque PAS** (`bilinear_intact` reste ≤ 0.32) : finding honnête — le terme
  bilinéaire low-rank de ce design ne suffit pas ; l'ablation du levier est un VRAI nul (le mur est plus
  profond qu'un simple produit d'unités, ou le rang/budget insuffisant — à documenter). Ne pas forcer.

## 7. Bornage du coût

Pur torch CPU, aucun bail `kuzu`, aucun monde. Pré-vol `declare_design`. SMOKE d'abord (le bilinéaire
apprend-il la compo à petit budget ? débit). Run-verdict n=12 en **FOREGROUND** borné (< ~9 min ; leçons
SP-2/MEM-PERCEPTION : bg perdu). Le bilinéaire ajoute des params → un peu plus lent ; tuner `r`/episodes au
smoke. Persister accuracies + `_params`.

## 8. Livrable final

Le substrat bilinéaire (flag-gated dans `backend_torch.py`) + la sonde de calibration + le record
`docs/EDR/EDR-BILINEAR_Bilinear_Substrate_Unlocks_Composition.md` (positif si débloqué, négatif sinon). PAS
d'arête ajoutée à `demands.json` (ce sous-projet est un changement de SUBSTRAT, pas une arête ; les arêtes
débloquées sont des sous-projets suivants). Frontmatter EDR `gate:`/`tests:`/`adopts:`.

## 9. Fichiers

- `src/agents/backend_torch.py` (MODIFIÉ) — flag `BILINEAR` + params low-rank + terme dans `_step`. CORE.
- `tools/bilinear_composition_probe.py` (NOUVEAU) — la sonde de calibration (plain vs bilinéaire sur `(q+key)%K`).
- `tests/test_bilinear_composition_probe.py` (NOUVEAU) — smoke unitaire + régression bit-identique off.
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — CALIBRATED + cas positif/no-op/régression.
- `results/bilinear_composition.json` (NOUVEAU) — accuracies + `_params`.
- `docs/EDR/EDR-BILINEAR_Bilinear_Substrate_Unlocks_Composition.md` (NOUVEAU) — le record.

## 10. Critères de succès

1. `BILINEAR=False` bit-identique à l'actuel (régression) ; suite substrat existante VERTE.
2. Sonde calibrée : positif (bilinéaire débloque `(q+key)%K`), no-op (pur-rappel non régressé), sous cliquet.
3. Run-verdict n=12 : `unlocked=True` (plain nul, bilinéaire apprend, marge+séparation) OU finding négatif honnête.
4. Record EDR gravé ; `check_record_links` non-orphelin.

## 11. Hors scope

- Re-tenter `language→memory` avec le substrat bilinéaire = sous-projet SUIVANT (si débloqué).
- La généralisation (application de règle) avec le bilinéaire = sous-projet suivant.
- Un bilinéaire PLEIN (non low-rank) ou d'autres formes (attention, produit externe complet) = itérations si
  le low-rank ne suffit pas.
- Évolution in-world du bilinéaire (le NAS l'active-t-il ?) = hors scope (ici on teste la CAPACITÉ, pas
  l'émergence évolutive).

## 12. Risques et pièges

- **Casser le substrat CORE** : le flag off DOIT être bit-identique ; suite existante verte avant/après ;
  params créés seulement si on. Le plus gros risque du sous-projet.
- **Le low-rank ne suffit pas** : `r=16` peut être trop petit pour `(q+key)%K` ; tuner `r` au smoke ; si
  échec robuste, finding négatif honnête (pas forcer un `r` géant non borné).
- **Régression sur le pur-rappel** : le terme bilinéaire pourrait déstabiliser ce qui marchait → le contrôle
  NO-OP l'attrape.
- **Coût/instabilité** : produits → gradients plus raides ; init `W_bl=0` + `r` petit + lr modéré ; smoke.
- **Sonde non calibrée = résultat fabriqué** : la calibration (positif/no-op/régression) est un livrable.
- **Confondre capacité et émergence** : ce sous-projet montre que le substrat PEUT composer avec le
  bilinéaire (calibration, entraînement direct). Il ne prétend PAS que l'évolution l'active in-world.
