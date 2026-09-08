# Arête « coordination différée exige la rétention » — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer si une tâche de coordination référentielle DIFFÉRÉE exige la rétention d'état, et graver la 3ᵉ arête du graphe AGI-Taxonomy si les deux jambes de la porte durcie passent — après avoir corrigé le caractère unilatéral de `ablation_verdict`.

**Architecture:** Partie A corrige l'instrument partagé `demand_marker.ablation_verdict` (borne bilatérale de `X_DECOY`). Partie B ajoute une sonde Lewis à trois bras (RETAIN testé / PRESENT contrôle de demande / ALIAS contrôle d'aliasing), symétriques par la DATE de présentation de la cible, avec une ablation par **substitution d'état décorrélée** (le H-reset est prouvé faux). Le verdict combine `ablation_verdict` (bras RETAIN), `specificity_control` (bras PRESENT) et `alias_guard_verdict` (bras ALIAS).

**Tech Stack:** Python 3, torch (CPU, `set_num_threads(1)`), numpy, pytest. Réutilise `MambaAgent`, `make_population(backend="torch")`, `learn_episode`, `tools/demand_marker.py`, et les patrons de `tools/perception_coordination_demand_probe.py` et `tools/memory_perception_demand_probe.py`.

**Spec:** `docs/superpowers/specs/2026-09-01-delayed-lewis-retention-edge-design.md`

## Global Constraints

- **Ablation = SUBSTITUTION D'ÉTAT DÉCORRÉLÉE, jamais un H-reset.** Rejouer le préfixe (émission + délai) avec un référent DÉRANGÉ, mêmes poids, même agent, puis présenter le tick de choix. Mesuré : le H-reset AMÉLIORE le contrôle (0.592 → 0.994, 3/3 seeds) parce que δ médian = 0.500 et que 108 des 113 nœuds portés SONT les readouts.
- **Le repli « n'effacer que les nœuds non-readout » est INTERDIT** : seuls 5 nœuds (59..63) ne sont ni entrée ni readout ; mesuré inerte ⇒ `VACUOUS_ABLATION`.
- **Le référent-leurre est tiré UNIFORMÉMENT sur `[0,K)`, indépendamment de la cible.** Jamais « différent de la cible » (biaiserait le plancher).
- **Trois bras distincts.** `leakage <= tol` subsume strictement `ratio <= 1.3` : un bras unique ferait reposer les deux verrous de la porte sur une seule mesure.
- **Plafonnement structurel des contrôles** : bruiter le signal **effectivement porteur dans chaque bras** avec `flip_p=0.3` ⇒ plafond `(1-flip_p)+flip_p/K = 0.75`. Ne JAMAIS laisser un signal propre au tick 1 dans le bras PRESENT (la rétention y redeviendrait payante).
- **E19** : le `lr` est BALAYÉ (≥3 points), sur seeds **disjoints** de ceux du verdict, avec un critère de sélection **scellé avant le run** et défini **uniquement sur RETAIN intact** — jamais sur un contrôle, jamais sur un bras ablé. La grille complète est rapportée dans le record.
- **Bornage** : `torch.set_num_threads(1)` ; run-verdict n=12 **FOREGROUND** ; si > ~10 min, réduire `n_agents` 16→8 (jamais `n`, jamais les épisodes, jamais un plafond en secondes — E13). Aucun bail `kuzu`, aucun monde.
- **Provenance** : le verdict gravé sort de la fonction CALIBRÉE réelle.
- **Commits path-scopés** (arbre PARTAGÉ entre sessions), jamais `git add -A`, jamais `--no-verify`. **Aucun commit sans demande explicite de l'utilisateur** — préparer les fichiers, proposer le commit.
- **L'issue NÉGATIVE est légitime** : si le leakage d'ALIAS ne se referme pas sous `tol=0.05`, l'arête n'est pas gravable et on écrit le négatif.

## File Structure

- `tools/demand_marker.py` (MODIF, Task 1) — borne bilatérale de `X_DECOY`.
- `tools/delayed_coordination_demand_probe.py` (NOUVEAU, Tasks 2-3) — la sonde 3 bras.
- `tests/sandbox/test_instrument_calibration.py` (MODIF, Tasks 1 & 3) — contre-exemples gelés + `CALIBRATED`.
- `tests/test_delayed_coordination_probe.py` (NOUVEAU, Task 2) — smoke de forme.
- `docs/preregistrations/DELAYED-COORD-001.json` (NOUVEAU, Task 4).
- `results/delayed_lewis_edge.json` (NOUVEAU, Task 4).
- `docs/EDR/EDR-DELAYED-COORD_Deferred_Referential_Coordination_Demands_Retention.md` (NOUVEAU, Task 4).
- `data/agi_taxonomy/demands.json` (MODIF, Task 4 — **seulement si les deux jambes passent**).
- `docs/REF/REGISTRE_ERREURS.md` (MODIF, Task 1 — occurrence E3).

---

### Task 1 : Borner `X_DECOY` des deux côtés (Partie A, préalable)

**Files:**
- Modify: `tools/demand_marker.py` (fonction `ablation_verdict`)
- Modify: `tests/sandbox/test_instrument_calibration.py`
- Modify: `docs/REF/REGISTRE_ERREURS.md` (occurrence E3)

**Interfaces:**
- Consumes: `ablation_verdict(intact, ablated, intervention_verified, floor, ceiling)` existant.
- Produces: même signature ; le dict renvoyé gagne la possibilité du verdict `INCONCLUSIVE_INVERTED`. Les clés existantes (`verdict`, `ratio`, …) sont PRÉSERVÉES — Task 3 en dépend.

- [ ] **Step 1 : Lire l'existant avant de toucher quoi que ce soit**

Lire `tools/demand_marker.py` en entier, en particulier `_degeneracy` et le bloc de décision (`collapse := ratio >= collapse_factor` ; `decoy := ratio <= decoy_ceiling`). Noter les valeurs réelles de `collapse_factor` et `decoy_ceiling` et les noms EXACTS des clés du dict renvoyé. **Ne rien supposer depuis ce plan** : les chiffres ci-dessous (1.5 / 1.3) viennent d'une lecture antérieure et doivent être re-vérifiés.

- [ ] **Step 2 : Écrire les tests qui échouent**

Ajouter dans `tests/sandbox/test_instrument_calibration.py` :

```python
def test_ablation_verdict_REFUSES_an_inverted_effect_as_decoy():
    """CONTRE-EXEMPLE GELÉ (classe E3) — mesuré le 2026-09-01 sur le bras de contrôle Lewis
    sous H-reset : l'ablation MULTIPLIE le contrôle par 1.68 (0.592 -> 0.994), donc ratio 0.596.
    L'ancienne règle `decoy := ratio <= 1.3` classait ça `X_DECOY`, lu « ablation inerte », donc
    `specificity_control='pass'`. Un effet massif de SIGNE INVERSE n'est pas une inertie."""
    from tools.demand_marker import ablation_verdict
    ci = [0.510, 0.658, 0.592]
    ca = [0.988, 0.994, 0.994]
    r = ablation_verdict(ci, ca, intervention_verified=True, floor=1 / 6, ceiling=1.0)
    assert r["verdict"] != "X_DECOY", r
    assert r["ratio"] < 1.0, r


def test_ablation_verdict_STILL_accepts_a_genuine_decoy():
    """CONTRÔLE POSITIF — sans lui, une garde qui refuse TOUT serait aussi inutile qu'une garde
    qui accepte tout. Un vrai decoy (ablation réellement inerte, ratio ~1.0) doit RESTER X_DECOY."""
    from tools.demand_marker import ablation_verdict
    ci = [0.592, 0.658, 0.610]
    ca = [0.590, 0.652, 0.615]
    r = ablation_verdict(ci, ca, intervention_verified=True, floor=1 / 6, ceiling=1.0)
    assert r["verdict"] == "X_DECOY", r


def test_ablation_verdict_still_collapses_a_real_demand():
    """NON-RÉGRESSION du sens principal : une vraie demande reste X_DEMANDED."""
    from tools.demand_marker import ablation_verdict
    r = ablation_verdict([0.633, 0.654, 0.621], [0.194, 0.175, 0.177],
                         intervention_verified=True, floor=1 / 6, ceiling=1.0)
    assert r["verdict"] == "X_DEMANDED", r
```

- [ ] **Step 3 : Lancer, vérifier que le premier échoue**

Run: `python -m pytest tests/sandbox/test_instrument_calibration.py -q -k "ablation_verdict_REFUSES or ablation_verdict_STILL or still_collapses"`
Expected: `test_ablation_verdict_REFUSES_an_inverted_effect_as_decoy` ÉCHOUE (le verdict rendu est `X_DECOY`) ; les deux autres PASSENT déjà.

- [ ] **Step 4 : Implémenter la borne bilatérale**

Dans `ablation_verdict`, remplacer la condition unilatérale `decoy := ratio <= decoy_ceiling` par une condition **bilatérale** :

```python
    # E3 — un effet massif de SIGNE INVERSE n'est pas une inertie. Borne des DEUX côtés :
    # une ablation qui AMÉLIORE le bras autant qu'une vraie demande l'effondre ne peut pas
    # être lue « inerte ». Contre-exemple gelé : ratio 0.596 (le contrôle passe de 0.592 à 0.994).
    decoy = (1.0 / decoy_ceiling) <= ratio <= decoy_ceiling
    inverted = ratio < (1.0 / decoy_ceiling)
```

et faire précéder la branche `X_DECOY` d'une branche qui rend `INCONCLUSIVE_INVERTED` quand `inverted` est vrai. **Préserver toutes les clés existantes du dict** et l'ordre des autres branches.

- [ ] **Step 5 : Vérifier les tests et la non-régression du graphe**

Run: `python -m pytest tests/sandbox/test_instrument_calibration.py -q -k "ablation_verdict_REFUSES or ablation_verdict_STILL or still_collapses"`
Expected: 3 passed.

Run: `python tools/check_agi_taxonomy.py`
Expected: `4 capacités, 2 arêtes | 0 violations` — **les deux arêtes gravées doivent rester valides**. Si l'une tombe, c'est l'implémentation qui est fausse : corriger, ne pas relâcher la règle.

Run: `python -m pytest tests/sandbox/ -q -k "demand_marker or calib_sp3"` (les tests existants du marqueur)
Expected: aucun échec nouveau. Rapporter la sortie réelle.

- [ ] **Step 6 : Inscrire l'occurrence au registre**

Dans `docs/REF/REGISTRE_ERREURS.md`, ajouter à la cellule Occurrences de **E3** une occurrence datée 2026-09-01 : `ablation_verdict` était UNILATÉRAL (`decoy := ratio <= 1.3` se déclenchait pour ratio 0.596, soit une ablation multipliant le contrôle par 1.68) ; `_degeneracy` ne l'attrapait pas (elle ne teste que « intact au plancher » et « les DEUX au plafond », or ici l'intact est vivant et seul l'ABLÉ sature). Garde : borne bilatérale + contre-exemple gelé + contrôle positif. **Vérifier que la ligne du tableau garde 5 colonnes** (échapper toute barre verticale littérale).

- [ ] **Step 7 : Préparer le commit (ne pas committer sans demande)**

```bash
git add tools/demand_marker.py tests/sandbox/test_instrument_calibration.py docs/REF/REGISTRE_ERREURS.md
git status --short   # UNIQUEMENT ces trois chemins
```

Message proposé : `fix(E3): ablation_verdict borné des DEUX côtés -- un effet de signe inverse n'est pas une inertie`

---

### Task 2 : La sonde différée, deux bras symétriques, ablation par substitution

**Files:**
- Create: `tools/delayed_coordination_demand_probe.py`
- Create: `tests/test_delayed_coordination_probe.py`

**Interfaces:**
- Consumes: `MambaAgent`, `make_population`, `learn_episode`, et les patrons de `tools/perception_coordination_demand_probe.py` (sender/receiver, `_onehot`, `_noisy_onehot`, `_sample`) et `tools/memory_perception_demand_probe.py` (`_forward_seq`, construction des `acts` multi-ticks).
- Produces:
  - `_train_and_eval_arm(seed, arm, D, episodes, n_agents, K, V, lr, flip_p) -> (intact, ablated)` — deux floats.
  - `run_delayed_coordination_demand_probe(seeds, D=2, episodes=800, n_agents=16, K=6, V=8, lr=0.05, flip_p=0.3, arms=("RETAIN","PRESENT")) -> dict` avec au minimum `{"<ARM>_intact": [...], "<ARM>_ablated": [...], "n": int, "_params": {...}}`. Task 3 ajoutera le bras ALIAS et le verdict.

- [ ] **Step 1 : Lire les deux sondes de référence**

Lire `tools/perception_coordination_demand_probe.py` EN ENTIER (protocole sender/receiver, slots, `derange_rows`, la boucle d'entraînement, l'optimiseur, l'éval) et `tools/memory_perception_demand_probe.py` (la boucle `_forward_seq` multi-ticks et la construction des `acts` avec des actions neutres aux ticks intermédiaires). **Copier ces patrons**, ne pas les réinventer : l'identité de construction est ce qui rend la mesure comparable aux arêtes gravées.

- [ ] **Step 2 : Écrire le smoke de forme (qui échoue)**

Create `tests/test_delayed_coordination_probe.py` :

```python
import pytest

pytest.importorskip("torch")


def test_probe_returns_both_arms_smoke():
    from tools.delayed_coordination_demand_probe import run_delayed_coordination_demand_probe
    r = run_delayed_coordination_demand_probe(seeds=[0, 1], D=1, episodes=30, n_agents=4, K=6, V=8)
    for arm in ("RETAIN", "PRESENT"):
        assert len(r[arm + "_intact"]) == 2, r
        assert len(r[arm + "_ablated"]) == 2, r
        for v in r[arm + "_intact"] + r[arm + "_ablated"]:
            assert 0.0 <= v <= 1.0, r
    assert r["n"] == 2
    assert r["_params"]["D"] == 1
```

- [ ] **Step 3 : Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_delayed_coordination_probe.py -q`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4 : Implémenter les deux bras, symétriques par la DATE**

Créer `tools/delayed_coordination_demand_probe.py`. Structure imposée :

- **Deux populations séparées** (`sender`, `receiver`), comme la sonde de référence ; jamais de poids partagés. `torch.set_num_threads(1)` en tête du module d'exécution.
- **Un essai** : le sender voit un référent au tick 1 et émet un symbole `sig ∈ [0,V)` ; le receiver reçoit `onehot(sig)` au tick 1, puis `D` ticks de **vecteur nul**, puis le tick de choix. Les slots d'entrée étant écrasés à chaque tick, les ticks de délai sont nécessairement nuls.
- **La différence entre les bras est UNIQUEMENT la date de présentation de la cible au sender** :

```python
# RETAIN  : la CIBLE est montrée au sender au tick 1 ; un LEURRE au tick de choix.
# PRESENT : un LEURRE au tick 1 ; la CIBLE au tick de choix.
# Canal, sender, longueur de sequence et nombre de forwards IDENTIQUES entre les bras.
target = rng.randint(0, K, size=n_agents)
decoy  = rng.randint(0, K, size=n_agents)          # UNIFORME et INDEPENDANT de target
first  = target if arm == "RETAIN" else decoy
last   = decoy  if arm == "RETAIN" else target
```

- **Plafonnement structurel** : le signal **effectivement porteur** de chaque bras passe par le bruitage `flip_p=0.3` (patron `_noisy_onehot` de la sonde de référence). Dans RETAIN c'est le signal du tick 1 ; dans PRESENT c'est celui du tick de choix. **Ne jamais laisser un signal propre au tick 1 dans PRESENT.**
- **Ablation (`ablated=True`) : substitution d'état décorrélée.** Rejouer le préfixe avec un référent **dérangé** au lieu du vrai, sur le MÊME agent et les MÊMES poids, puis présenter le tick de choix inchangé :

```python
def _prefix_state(receiver, sig_first, K, V, I, n, D, deranged=False, rng=None):
    """Rejoue emission + delai et laisse receiver.H dans l'etat porte correspondant.
    deranged=True : le symbole du prefixe est remplace par un tirage UNIFORME independant
    -> la distribution marginale de H, sa norme et ses correlations sont PRESERVEES ;
    seule l'information sur la cible de CE trial est detruite. Analogue-etat de derange_rows."""
    s = rng.randint(0, V, size=n) if deranged else sig_first
    receiver.H = torch.zeros((n, receiver.N))
    receiver.forward(_onehot(s, V, I, n))
    for _ in range(D):
        receiver.forward(_zeros(I, n))
```

  puis le tick de choix, et lecture de `argmax(logits[:, :K])`. **Ne PAS remettre H à zéro entre le préfixe et le choix** — c'est précisément l'erreur écartée.
- **Entraînement** : REINFORCE via `learn_episode` sur la séquence complète, avec des actions neutres aux ticks intermédiaires et le guess échantillonné au dernier tick (patron `memory_perception_demand_probe.py`). Optimiseurs `Adam` sur les `W` des deux populations, `lr` passé en argument.
- **Éval** : `eval_batches=40`, `argmax` déterministe, mêmes tirages pour intact et ablé **dans le même appel** (rejouer le même essai deux fois, une fois intact une fois substitué) — l'appariement par essai renforce la mesure et ne coûte rien.
- Sauvegarder/restaurer les flags de classe manipulés dans un `try/finally` (patron des sondes existantes) ; forcer `CONDITION_GATE=False`, `GATE_TARGET=None`, `GATE_TARGETS=None`.

- [ ] **Step 5 : Lancer le smoke**

Run: `python -m pytest tests/test_delayed_coordination_probe.py -q`
Expected: PASS.

- [ ] **Step 6 : Crible fail-fast T1 (peut tuer le sous-projet — le lancer AVANT d'aller plus loin)**

Run:
```bash
python -c "
import torch, time; torch.set_num_threads(1)
from tools.delayed_coordination_demand_probe import run_delayed_coordination_demand_probe as R
t=time.time(); r=R(seeds=[0,1,2], D=2, episodes=800, n_agents=16, K=6, V=8, lr=0.05, flip_p=0.3)
print('dt_s=%.0f' % (time.time()-t))
for a in ('RETAIN','PRESENT'):
    print(a, 'intact', [round(x,3) for x in r[a+'_intact']], 'able', [round(x,3) for x in r[a+'_ablated']])
"
```

Attendu, et à TRANCHER explicitement avant de continuer :
1. **RETAIN intact APPREND** (nettement au-dessus de `1/K = 0.167`). Sinon il n'y a pas de capacité, donc pas d'arête : s'arrêter et rapporter.
2. **RETAIN s'effondre sous substitution** (vers ~0.17).
3. **PRESENT intact est VIVANT mais NON SATURÉ** — le plafond visé est `0.75` ; s'il sature à 1.000, le plafonnement `flip_p` n'a pas été appliqué au bon signal (relire la contrainte globale).
4. **PRESENT est INERTE sous substitution** (écart sous `tol=0.05`).
Si (3) ou (4) échoue, c'est le design du bras PRESENT qu'il faut corriger — **pas** le seuil.

Reporter `dt_s` : il fixe la projection de coût du run-verdict.

- [ ] **Step 7 : Préparer le commit**

```bash
git add tools/delayed_coordination_demand_probe.py tests/test_delayed_coordination_probe.py
git status --short   # UNIQUEMENT ces deux chemins
```

Message proposé : `feat(DELAYED-COORD): sonde Lewis différée 2 bras + ablation par substitution d'état décorrélée`

---

### Task 3 : Le bras ALIAS, l'assemblage du verdict, et la calibration

**Files:**
- Modify: `tools/delayed_coordination_demand_probe.py`
- Modify: `tests/sandbox/test_instrument_calibration.py`

**Interfaces:**
- Consumes: `_train_and_eval_arm`, `run_delayed_coordination_demand_probe` (Task 2) ; `ablation_verdict` (Task 1) ; `alias_guard_verdict` de `tools/language_memory_demand_probe.py` (import read-only).
- Produces: `run_delayed_coordination_demand_probe(...)` renvoie en plus `{"ablation_verdict": dict, "specificity_control": "pass"|"fail", "functional_aliasing": "pass"|"fail", "alias_verdict": str, "leak_seeds": int, "ablation_target": "substrate"}`.

- [ ] **Step 1 : Résoudre le point ouvert de la tête d'action unique — par la mesure**

Le substrat n'a qu'une tête d'action (`_MOVE_LOGITS=8`) et LANG-MEMORY a buté dessus (« 2 capacités entraînées dans un même forward impossible → forwards séparés à H partagé »). Le bras ALIAS est une **troisième** capacité.

Vérifier MÉCANIQUEMENT, avant d'écrire le verdict : entraîner ALIAS et RETAIN et mesurer qu'ils ne s'écrasent pas — c'est-à-dire que `RETAIN_intact` avec ALIAS co-entraîné reste dans le même régime que `RETAIN_intact` seul (Task 2, Step 6). Si les deux capacités s'écrasent, adopter des **forwards séparés à H partagé** (patron `language_memory_demand_probe.py`) et le re-mesurer. Rapporter les deux chiffres.

- [ ] **Step 2 : Implémenter le bras ALIAS**

Le bras ALIAS est une **discrimination perceptive immédiate BRUITÉE**, sur des **slots d'entrée dédiés** (disjoints de ceux du canal et du référent), évaluée sous la MÊME substitution d'état.

Deux exigences non négociables :
- **Son plafond vient de BAYES**, jamais d'un sous-entraînement : le bruit de la tâche fixe le plafond, de sorte que la garde de non-saturation ne dépende pas du réglage (sinon E19 mord sur la garde elle-même).
- **Il est entraîné sur le MÊME contexte porté** que le bras principal (piège corrigé dans `language_memory_demand_probe.py:267-273`) : sinon l'éval intacte est hors-distribution et le signe de la fuite peut s'inverser.

- [ ] **Step 3 : Assembler le verdict**

```python
    # Bras RETAIN -> la demande (arithmetiquement FORCEE : ce n'est pas le resultat).
    dem = ablation_verdict(retain_i, retain_a, intervention_verified=True, floor=1.0 / K, ceiling=1.0)
    # Bras PRESENT -> le controle de DEMANDE. C'est LUI qui porte le contenu empirique :
    # il doit etre VIVANT et INERTE. 'pass' SSI X_DECOY non degenere.
    spec = ablation_verdict(present_i, present_a, intervention_verified=True, floor=1.0 / K, ceiling=1.0)
    specificity_control = "pass" if spec["verdict"] == "X_DECOY" else "fail"
    # Bras ALIAS -> la chirurgie. Garde de degenerescence armee le 2026-09-01.
    alias = alias_guard_verdict(alias_i, alias_a, floor=1.0 / K, ceiling=1.0, tol=0.05)
```

`functional_aliasing` vaut `'pass'` **uniquement** si `alias` rend `SURGICAL` (donc jamais si `DEGENERATE_CONTROL` ni `FUNCTIONAL_LEAK`). Exposer `leak_seeds` (nombre de seeds où `|intact − ablé| > tol` sur ALIAS) et `ablation_target = "substrate"`.

- [ ] **Step 4 : Écrire les cas de calibration, dont le GÉNÉRATEUR NÉGATIF**

Dans `tests/sandbox/test_instrument_calibration.py` :

```python
@pytest.mark.slow
@pytest.mark.timeout(900)
def test_delayed_coord_specificity_FAILS_on_a_redundant_design():
    """GÉNÉRATEUR NÉGATIF (le cas central) — un design où le préfixe PORTE la réponse est
    l'erreur exacte de MEM-PERCEPTION itération 1. Le contrôle de demande DOIT alors échouer :
    la mémoire redevient payante dans le bras censé ne pas la demander. Sans ce cas, l'arête
    se graverait sur un contrôle qui valide n'importe quoi. Mesuré 2026-09-01 : ratio ≈ 1.856."""
    from tools.delayed_coordination_demand_probe import run_delayed_coordination_demand_probe
    r = run_delayed_coordination_demand_probe(seeds=[0, 1, 2], D=2, episodes=800, n_agents=16,
                                              K=6, V=8, lr=0.05, flip_p=0.3, redundant_control=True)
    assert r["specificity_control"] == "fail", r


@pytest.mark.slow
@pytest.mark.timeout(900)
def test_delayed_coord_specificity_PASSES_on_the_correct_design():
    """CONTRÔLE POSITIF apparié — le MÊME instrument, le design CORRECT (préfixe-leurre
    décorrélé) : le contrôle doit être vivant ET inerte. Le couple des deux tests prouve que
    le contrôle DISCRIMINE, ce que le H-reset ne permettait pas (les deux rendaient 'pass')."""
    from tools.delayed_coordination_demand_probe import run_delayed_coordination_demand_probe
    r = run_delayed_coordination_demand_probe(seeds=[0, 1, 2], D=2, episodes=800, n_agents=16,
                                              K=6, V=8, lr=0.05, flip_p=0.3)
    assert r["specificity_control"] == "pass", r
```

Le paramètre `redundant_control=True` (défaut `False`) doit être ajouté à la sonde : il fait porter la réponse par le préfixe dans le bras PRESENT. C'est un levier de calibration, pas une option de mesure.

- [ ] **Step 5 : Déclarer au cliquet**

Ajouter `run_delayed_coordination_demand_probe` au dict `CALIBRATED` avec des **branches nommées par régime** (la règle du fichier : ajouter une branche EXIGE d'ajouter le cas de test). Ne PAS déclarer `["*"]`.

- [ ] **Step 6 : Vérifier**

Run: `python -m pytest tests/sandbox/test_instrument_calibration.py -q -k "delayed_coord"`
Expected: 2 passed. Rapporter la durée réelle.

Run: `python tools/check_instrument_calibration.py`
Expected: `OK : aucun nouvel instrument non calibré`. **INTERDIT** : `--update-baseline`.

- [ ] **Step 7 : Préparer le commit**

```bash
git add tools/delayed_coordination_demand_probe.py tests/sandbox/test_instrument_calibration.py
git status --short   # UNIQUEMENT ces deux chemins
```

Message proposé : `feat(DELAYED-COORD): bras ALIAS + verdict 3 bras + calibration (générateur NÉGATIF : design redondant -> fail)`

---

### Task 4 : Balayage `lr` scellé, run-verdict n=12, record, arête

**Files:**
- Create: `docs/preregistrations/DELAYED-COORD-001.json`
- Create: `results/delayed_lewis_edge.json`
- Create: `docs/EDR/EDR-DELAYED-COORD_Deferred_Referential_Coordination_Demands_Retention.md`
- Modify: `data/agi_taxonomy/demands.json` (**seulement si les deux jambes passent**)

**Interfaces:**
- Consumes: `run_delayed_coordination_demand_probe` (Tasks 2-3).
- Produces: le verdict persisté, le record, et l'arête éventuelle.

- [ ] **Step 1 : Sceller la règle AVANT tout balayage**

Écrire `docs/preregistrations/DELAYED-COORD-001.json` via `tools/preregister.py` (lire un fichier récent de `docs/preregistrations/` pour le format exact). La règle scellée doit contenir :
- le critère de sélection du `lr` : **la valeur qui maximise `RETAIN_intact` médian sur les seeds de balayage** — jamais un contrôle, jamais un bras ablé ;
- les seeds de balayage, **disjoints** de ceux du verdict (ex. balayage `100-102`, verdict `0-11`) ;
- la grille : au moins 3 valeurs de `lr` ;
- les conditions de gravure : `X_DEMANDED` ET `n>=12` ET `specificity_control=='pass'` ET `functional_aliasing=='pass'` ET `ablation_target=='substrate'` ;
- les grandeurs que le record citera (`RETAIN_intact`, `PRESENT_intact`, `ALIAS_intact`, `ablation_verdict`, `specificity_control`, `functional_aliasing`, `ablation_target`, la grille de `lr`) — sinon `check_preregistration_applied` échoue.

- [ ] **Step 2 : Balayer le `lr` sur les seeds disjoints**

Lancer les ≥3 points de `lr` sur les seeds de balayage, FOREGROUND, `set_num_threads(1)`. **Rapporter la grille COMPLÈTE**, pas seulement le point retenu (un rung rapporté seul est un max sur une recherche non rapportée — E9/E11).

Appliquer le critère scellé. Si aucun `lr` ne garde à la fois RETAIN vivant et les contrôles non saturés malgré le plafonnement `flip_p`, **ne pas bricoler le seuil** : c'est le plafonnement qu'il faut re-concevoir (retour Task 2), ou le round rend un négatif.

- [ ] **Step 3 : Run-verdict n=12, FOREGROUND**

⚠️ FOREGROUND. Si le harnais le promeut en arrière-plan, **bloquer dessus, ne pas le dupliquer**.

Lancer les 3 bras × 12 seeds au `lr` retenu, persister dans `results/delayed_lewis_edge.json` : les accuracies **par seed** des 6 séries (3 bras × intact/ablé), `_params` complet (dont `D`, `episodes`, `n_agents`, `K`, `V`, `flip_p`, `lr`, `threads`), la grille de `lr`, `leak_seeds`, et les trois verdicts.

Projection : ~22 s par cellule ⇒ 36 cellules ≈ 13 min. Si > ~10 min, réduire `n_agents` 16→8 — **jamais** `n`, **jamais** les épisodes.

- [ ] **Step 4 : Écrire le record**

Créer le record avec frontmatter `id` / `type: EDR` / `title` / `status: active` / `verdict:` / `gate: G0` / `tests: [SDR-G0]`. Le corps doit contenir :
- **Le cadrage honnête, en premier** : le bras RETAIN est arithmétiquement FORCÉ (privé de l'information, le receiver est au hasard) — ce n'est PAS le résultat ; tout le contenu vient des contrôles.
- Le titre et la formulation en termes de TÂCHE : « une tâche de coordination référentielle DIFFÉRÉE exige la rétention d'état ; la même tâche NON différée ne l'exige pas ». Jamais « le langage exige la mémoire ».
- Les valeurs par seed **INLINÉES** (`results/` est gitignoré — sans inline la preuve disparaît au premier clone), la **séparation par seed** (les deux arêtes gravées tiennent 12/12 sans chevauchement : la troisième ne doit pas passer sous un standard plus faible), `leak_seeds`, et la grille de `lr` complète.
- La méthode d'ablation et **pourquoi le H-reset a été écarté** (chiffres : contrôle 0.592 → 0.994, l'ablation AMÉLIORE ; 108 des 113 nœuds portés sont les readouts), ainsi que l'inertie mesurée du repli non-readout (5 nœuds).
- Portée bornée : un seul substrat, un seul proxy, capacité et non émergence.

- [ ] **Step 5 : Graver l'arête — SEULEMENT si les deux jambes passent**

Si `X_DEMANDED` ET `specificity_control=='pass'` ET `functional_aliasing=='pass'` : ajouter l'arête à `data/agi_taxonomy/demands.json` avec `evidence.ablation_target = "substrate"` et le chemin du record.

**Sinon : NE PAS graver.** Écrire le négatif dans le record — notamment si le leakage d'ALIAS ne se referme pas sous `tol=0.05` (issue prévue au design). Un négatif honnête est un livrable, pas un échec.

- [ ] **Step 6 : Valider**

```bash
python tools/check_agi_taxonomy.py          # 3 arêtes si gravée, sinon 2 ; 0 violation
python tools/check_record_links.py          # le nouveau record non-orphelin
python tools/check_instrument_calibration.py
python -m pytest tests/test_delayed_coordination_probe.py -q
```

- [ ] **Step 7 : Préparer le commit**

```bash
git add docs/preregistrations/DELAYED-COORD-001.json \
        docs/EDR/EDR-DELAYED-COORD_Deferred_Referential_Coordination_Demands_Retention.md \
        data/agi_taxonomy/demands.json
git add -f results/delayed_lewis_edge.json
git status --short
```

Message proposé : `feat(DELAYED-COORD): verdict n=12 -- la coordination différée exige-t-elle la rétention ? + record`

---

## Self-Review

**Spec coverage :**
- §2 Partie A (borne bilatérale, contre-exemple 0.596, contrôle positif, non-régression, E3) → Task 1. ✓
- §3 protocole différé, deux bras symétriques par la DATE, leurre uniforme → Task 2 Step 4. ✓
- §3.1 substitution d'état décorrélée ; H-reset et repli non-readout écartés → contrainte globale + Task 2 Step 4 + record Task 4 Step 4. ✓
- §3.2 trois bras distincts, ALIAS plafonné par Bayes et entraîné sur le contexte porté → Task 3 Steps 2-3. ✓
- §3.3 plafonnement `flip_p=0.3` sur le signal porteur de chaque bras → contrainte globale + Task 2 Step 4 + crible Step 6. ✓
- §4 verdict, porte durcie, séparation par seed, issue négative → Task 3 Step 3 + Task 4 Steps 4-5. ✓
- §5 calibration, générateur NÉGATIF (design redondant), vacuous → Task 3 Step 4 ; le cas « vacuous non-readout » n'a PAS de test dédié (il est interdit par contrainte globale plutôt que testé) — assumé : le tester exigerait d'implémenter une ablation qu'on s'interdit d'écrire.
- §6 bornage, E19, pré-inscription, fail-fast → Task 2 Step 6 + Task 4 Steps 1-3. ✓
- §3.2 point ouvert tête d'action unique → Task 3 Step 1, résolu PAR LA MESURE. ✓

**Placeholder scan :** aucun TODO/TBD. Les chiffres à mesurer (grille `lr`, valeurs n=12) sont explicitement marqués « à mesurer », jamais inventés. Task 1 Step 1 demande de re-vérifier `collapse_factor`/`decoy_ceiling` dans le code plutôt que de les tenir de ce plan.

**Type consistency :** `run_delayed_coordination_demand_probe(seeds, D, episodes, n_agents, K, V, lr, flip_p, arms, redundant_control)` — signature étendue en Task 3 (ajout de `redundant_control`, du bras ALIAS et des clés de verdict) ; les clés de Task 2 (`<ARM>_intact`, `<ARM>_ablated`, `n`, `_params`) sont PRÉSERVÉES et réutilisées telles quelles en Tasks 3-4. `ablation_verdict` garde sa signature et ses clés (Task 1 Step 4 l'exige explicitement), donc Task 3 peut lire `spec["verdict"]`. `alias_guard_verdict` est importé read-only. ✓
