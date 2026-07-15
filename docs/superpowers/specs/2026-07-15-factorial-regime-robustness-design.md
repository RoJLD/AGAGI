# Robustesse aux régimes de la structure de facteurs du binding in-world (EDR-178)

> Territoire BIND/torch. Suites d'EDR-177 (« la consommation est le verrou maître, la cellule propre binde »).
> Base : `chantier/factorial-regime-sweep` (off `chantier/throw-gate-factorial`, contient factoriel + EDR-177).

## Objectif

EDR-177 a établi la structure de facteurs du binding in-world **dans un seul régime** (couche-1 neutralisée,
payoff modéré) : `no_consume` domine (+0.465), `weightless` (F2) et `conditional_credit` (F4) sont
négligeables. Ce chantier teste si cette structure est **invariante au régime** ou si les facteurs inertes au
repos **émergent** quand leur coût devient saillant. Deux suites d'EDR-177 réunies en **une étude de
robustesse** :

- **Suite 1 — régime LÉTAL** : la survie devient une vraie contrainte. `no_consume` reste-t-il le verrou
  maître ? **Prédiction** : oui (c'est un artefact mécanique de `P(y|x)`, régime-indépendant) ; MAIS **F2
  (weightless) émerge positif** — porter un spear lourd (coût de portage) coûte alors la survie, donc l'en
  exempter aide le binding.
- **Suite 2 — régime PAYOFF-RARE** : les kills deviennent vraiment rares. La cellule propre binde-t-elle
  encore ? **Prédiction** : le binding s'affaiblit (signal clairsemé) ; MAIS **F4 (conditional_credit)
  émerge** — créditer le contingent « throw-SI-spear » plutôt que le marginal aide quand le signal marginal
  est trop rare pour être attribué.

**Les deux issues sont informatives** : émergence confirmée = validation du modèle causal (F2/F4 sont les
facteurs qu'on prédit voir compter sous leur stress respectif) ; non-émergence = ils sont réellement inertes
in-world même sous stress.

## Régimes

Trois régimes, mêmes 16 cellules 2⁴, mêmes seeds. Seuls les knobs de régime changent (les 4 FACTEURS restent
les variables du factoriel).

| Régime | night | energy | base_metabolism | prey_sparse / prey_dense | rôle |
|--------|-------|--------|-----------------|--------------------------|------|
| **neutralisé** | False | 250 | 0.05 | 15 / 300 | baseline (= EDR-177) |
| **létal** | True | *calibré* | *calibré* | 15 / 300 | Suite 1 (survie contrainte) |
| **rare** | False | 250 | 0.05 | *calibré bas* (~2 / 8) | Suite 2 (payoff clairsemé) |

Les valeurs *calibrées* sont fixées par la sonde de calibration (§Calibration) puis gravées dans le driver.

## Extension d'instrument (minimale)

Deux unités, l'une une modif d'une ligne, l'autre un nouveau fichier :

1. **Exposer `night` en param de `compare_factorial`** — [tools/torch_throw_gate_inworld_ab.py](../../../tools/torch_throw_gate_inworld_ab.py).
   Actuellement `night=False` est **hardcodé** dans le `kw` dict de `compare_factorial` (~ligne 333). Ajouter
   `night=False` à la signature et l'utiliser dans `kw` (`night=night`). Défaut `False` ⇒ le régime neutralisé
   et tous les appels existants (CLI, tests) sont **inchangés** (non-régressif). `penalty=0.0` reste hardcodé
   (non-biaisé, invariant du factoriel).

2. **Driver de sweep `tools/factorial_regime_sweep.py`** (nouveau). Importe `compare_factorial` +
   `_factorial_effects`. Définit un dict de régimes nommés `{nom: {night, energy, base_metabolism,
   prey_sparse, prey_dense}}`. Pour chaque régime : appelle `compare_factorial(**regime, seeds, ...)`,
   calcule `_factorial_effects`, et imprime **une table comparative des 4 effets principaux × régimes** +
   par régime le verdict cellule-0 (avec garde-fou K≥12 comme dans le mode CLI factorial). Invocable
   `python tools/factorial_regime_sweep.py` (env `FRS_SEEDS`, `FRS_TICKS`, `FRS_REGIMES` = sous-liste).

Aucune modif de `backend_torch.py` ni de `compute_ab_verdict`. Les 3 flags monde (F1/F2/F4) et
`compare_factorial`/`_factorial_effects` d'EDR-177 sont réutilisés tels quels.

## Calibration du régime létal (étape préalable, pas un livrable)

**Risque** : un régime trop létal reproduit le confond #1 d'EDR-172 (cohorte fraîche éteinte AVANT l'horizon
d'apprentissage → aucun signal de binding, pas « pas de binding »). Un régime trop doux = neutralisé.

**Méthode** : sonde de survie rapide — sur la cellule tout-propre (NWDK), quelques seeds, mesurer le
`n_alive_end` et la fenêtre de survie médiane sous des candidats `{night=True, energy∈[120,180],
base_metabolism∈[0.15,0.30]}`. **Critère** : la cohorte doit rester vivante sur **~la moitié** de la fenêtre
post-warmup (ticks 30→120) sous attrition réelle — ni extinction avant tick ~60 (trop létal), ni survie
quasi-totale (pas de pression). Retenir le triplet le plus proche du critère ; le graver dans le driver.
Idem pour `rare` : calibrer `prey_dense` bas tel que la cellule dense donne des kills médians ~3-8 (rare mais
non nul), `prey_sparse` ~ moitié.

## Mesure & analyse

- **Effets principaux par régime** (`_factorial_effects`), poolés sur 8 cellules/niveau ⇒ bien puissancés.
  Livrable central = **table 4 facteurs × 3 régimes** montrant les DÉPLACEMENTS (surtout F2 en létal, F4 en
  rare, et la stabilité de `no_consume`).
- **Verdict cellule-0 par régime** : GRADIENT_GAGNE / HEBBIEN / NEUTRE via `compute_ab_verdict`, sign-test.
  **Garde-fou power-evaporation** : pas de verdict POSITIF sous n=12 ⇒ K≥12 pour toute conclusion positive
  (létal/rare inclus).
- **Interactions** rapportées si un déplacement d'effet principal est porté par une interaction (ex.
  `no_consume×weightless` en létal).

## Non-régression

- `night` défaut `False` ⇒ `compare_factorial` et le mode CLI factorial inchangés (le neutralisé reproduit
  EDR-177 au seed près). `penalty=0.0` toujours hardcodé (non-biaisé).
- Nouveau fichier `tools/factorial_regime_sweep.py` = additif, ne touche aucun chemin existant.
- `compute_ab_verdict` / `backend_torch.py` intacts.

## Fichiers touchés

- Modif : `tools/torch_throw_gate_inworld_ab.py` (param `night` dans `compare_factorial` + `kw`)
- Nouveau : `tools/factorial_regime_sweep.py` (driver de sweep + table comparative)
- Modif : `tests/sandbox/test_torch_throw_gate_factorial.py` (test : `night` param par défaut inchangé + driver importe/structure)
- Nouveau (à l'exécution, hors périmètre du spec) : `docs/EDR/178_*.md`

## Hygiène de branche

Base `chantier/factorial-regime-sweep` sur `chantier/throw-gate-factorial` (contient factoriel + **EDR-177**,
orphelin du merge #164). La PR de suite cible `feat/d1-prod-pairing` et **rapatrie factoriel + EDR-177 +
regime-sweep + EDR-178** d'un coup, refermant l'orphelin. Commits path-scopés (arbre partagé).

## Lignée

Suites d'[[torch-inworld-integration-plan]] (EDR-177). Teste la robustesse aux régimes de la loi
« consommation = verrou maître, substrat capable in-world ». F2 sous survie / F4 sous rareté = prédictions
falsifiables du modèle causal d'EDR-177. Recoupe [[warm-start-transversal-law]] +
[[power-evaporation-guardrail]].
