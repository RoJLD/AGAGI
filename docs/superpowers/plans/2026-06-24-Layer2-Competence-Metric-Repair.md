# Réparation métrique compétence couche-2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer dans `stoneage_competence` le terme d'autel MORT (pondéré 0.6) par une échelle moyens→ends de signaux VIVANTS (chasse < apex coop < lance), agrégés par fraction de participation (rare-event-aware), pour que la compétence gradue au-delà de la chasse triviale.

**Architecture:** Réparation en place de `src/curriculum/competence.py` : helper pur `_frac_reaching` (fraction d'agents atteignant un barreau) + `stoneage_competence` réécrite en somme pondérée de fractions. `_median_norm` et les autres fonctions inchangés ; registre et signature `List[Dict]->float` intacts.

**Tech Stack:** Python 3.13, numpy (`np.clip`), pytest. Aucune dépendance biosphère (fonctions pures).

## Global Constraints

- **Réparer `stoneage_competence` SEUL** : `industrial`/`gym` (même lavage-médiane sur `altars_solved`) sont PROVISOIRE pour d'autres mondes → HORS périmètre (YAGNI).
- **Agrégateur = fraction de participation, PAS médiane** : les signaux vivants sont des conduites de minorité (apex 21.7%, lance 1.6%) ; la médiane les lave (EDR 094). `_frac_reaching` est binaire par agent → aussi robuste à l'inflation de crédit-groupe (EDR 028).
- **Champs VIVANTS confirmés** (EDR 096, `world_1_stoneage.py`) : `preys_eaten`/`mammoth_kills` (`:717-723`), `spears_crafted` (`:1210`). `altars_solved` est MORT (jamais incrémenté) → retiré de la métrique.
- **Poids** (constantes module) : `W_HUNT=0.4`, `W_APEX=0.45`, `W_TOOL=0.15` (somme = 1.0).
- **Préserver** : `_median_norm`, `soup_competence`, `survival_competence`, `industrial`/`gym`, `ALTAR_REF` (lu par industrial/gym), `COMPETENCE_REGISTRY`, `competence_for`. Signature inchangée.
- **Tree partagé** : commits **pathspec-limités** `git commit <paths> -m "..."` (jamais `git add -A`/`.`/`commit -m` sans pathspec). Branche `feat/d1-prod-pairing`.
- **Fichiers** : `src/curriculum/competence.py` (modif) ; `tests/sandbox/test_competence_repair.py` (nouveau).

---

## File Structure

- **Modify** `src/curriculum/competence.py` — ajout `_frac_reaching` (après `_median_norm` ~ligne 19) ; ajout constantes `W_HUNT/W_APEX/W_TOOL` + réécriture `stoneage_competence` (~lignes 45-58).
- **Create** `tests/sandbox/test_competence_repair.py` — tests purs (`_frac_reaching` + `stoneage_competence`).

---

### Task 1: Helper pur `_frac_reaching`

**Files:**
- Modify: `src/curriculum/competence.py` (après `_median_norm`, ~ligne 19)
- Test: `tests/sandbox/test_competence_repair.py`

**Interfaces:**
- Produces: `_frac_reaching(agent_stats: List[Dict], key: str, threshold: float = 1.0) -> float` (fraction d'agents avec `a.get(key,0) >= threshold` ; liste vide → 0.0).

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_competence_repair.py
from src.curriculum.competence import _frac_reaching


def test_frac_reaching_basic():
    stats = [{"mammoth_kills": 1}, {"mammoth_kills": 0}, {"mammoth_kills": 2},
             {"mammoth_kills": 0}, {"mammoth_kills": 0}]
    assert _frac_reaching(stats, "mammoth_kills") == 0.4   # 2/5


def test_frac_reaching_inflation_robust():
    # crédit-groupe (EDR 028) : un agent crédité 5x compte UNE fois (binaire >=1)
    five = [{"mammoth_kills": 5}, {"mammoth_kills": 0}]
    one = [{"mammoth_kills": 1}, {"mammoth_kills": 0}]
    assert _frac_reaching(five, "mammoth_kills") == _frac_reaching(one, "mammoth_kills") == 0.5


def test_frac_reaching_empty_and_missing():
    assert _frac_reaching([], "mammoth_kills") == 0.0
    assert _frac_reaching([{"age": 3}], "mammoth_kills") == 0.0   # champ absent -> 0


def test_frac_reaching_threshold_default_one():
    assert _frac_reaching([{"x": 1}], "x") == 1.0
    assert _frac_reaching([{"x": 0}], "x") == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_competence_repair.py -q -p no:cacheprovider`
Expected: FAIL (cannot import `_frac_reaching`).

- [ ] **Step 3: Add the helper (après `_median_norm`, ~ligne 19)**

```python
def _frac_reaching(agent_stats: List[Dict], key: str, threshold: float = 1.0) -> float:
    """Fraction des agents dont le champ `key` atteint `threshold` (>=). Rare-event-aware
    (≠ médiane, EDR 094) ; binaire par agent -> robuste à l'inflation de crédit-groupe
    (EDR 028/096 : un agent crédité 1 ou 5 fois compte une seule fois). Liste vide -> 0.0."""
    if not agent_stats:
        return 0.0
    return sum(1 for a in agent_stats if a.get(key, 0) >= threshold) / len(agent_stats)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_competence_repair.py -q -p no:cacheprovider`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git commit src/curriculum/competence.py tests/sandbox/test_competence_repair.py -m "feat(competence): helper pur _frac_reaching (fraction de participation, rare-event-aware)"
```

---

### Task 2: `stoneage_competence` réparée (échelle moyens→ends)

**Files:**
- Modify: `src/curriculum/competence.py` (~lignes 45-58 : la fonction `stoneage_competence` + ajout constantes poids)
- Test: `tests/sandbox/test_competence_repair.py` (append)

**Interfaces:**
- Consumes: `_frac_reaching` (Task 1), `np.clip`.
- Produces: `stoneage_competence(agent_stats: List[Dict]) -> float` (réparée) ; constantes module `W_HUNT=0.4`, `W_APEX=0.45`, `W_TOOL=0.15`.

- [ ] **Step 1: Write the failing test (append à `tests/sandbox/test_competence_repair.py`)**

```python
from src.curriculum.competence import stoneage_competence


def _pop(frac_hunt, frac_apex, frac_tool, n=1000):
    """Construit n agents reproduisant les fractions de participation demandées."""
    return [{"preys_eaten": 1 if i < int(frac_hunt * n) else 0,
             "mammoth_kills": 1 if i < int(frac_apex * n) else 0,
             "spears_crafted": 1 if i < int(frac_tool * n) else 0} for i in range(n)]


def test_stoneage_floor_when_no_behavior():
    stats = [{"preys_eaten": 0, "mammoth_kills": 0, "spears_crafted": 0} for _ in range(10)]
    assert stoneage_competence(stats) == 0.0


def test_stoneage_live_and_graded_edr096():
    # ANTI-THÉÂTRE : fractions réelles EDR 096 (hunt 0.505, apex 0.217, tool 0.016)
    stats = _pop(0.505, 0.217, 0.016)
    comp = stoneage_competence(stats)
    assert comp > 0.15                                   # non-plancher (vs ancienne ~0.07)
    assert comp > stoneage_competence(_pop(0.505, 0.0, 0.016))  # l'apex compte (strictement >)


def test_stoneage_apex_dominates_hunt():
    # franchir l'apex augmente strictement vs chasse seule
    assert stoneage_competence(_pop(0.5, 0.3, 0.0)) > stoneage_competence(_pop(0.5, 0.0, 0.0))


def test_stoneage_bounded_le_one():
    comp = stoneage_competence(_pop(1.0, 1.0, 1.0))
    assert comp <= 1.0 and abs(comp - 1.0) < 1e-9        # 0.4+0.45+0.15 = 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_competence_repair.py -q -p no:cacheprovider`
Expected: FAIL (`test_stoneage_live_and_graded_edr096` : l'ancienne `stoneage_competence` lit `altars_solved` (≡0 absent ici) et `preys_eaten` via médiane → score ≈ plancher, < 0.15).

- [ ] **Step 3: Réécrire `stoneage_competence` + ajouter les poids (remplacer le bloc `PREY_REF`/`ALTAR_REF` + la fonction, ~lignes 41-58)**

Remplacer EXACTEMENT le bloc actuel :

```python
PREY_REF = 5.0    # suggestion de point de départ — ajuste selon tes runs
ALTAR_REF = 3.0


def stoneage_competence(agent_stats: List[Dict]) -> float:
    """
    Monde 1 (Stoneage) — stade causalité/outil. Maîtrise = chasse + usage
    d'outils/puzzles.

    Choix retenus (à ajuster librement) :
      - Normalisation : médiane / réf, clampée — robuste aux génies isolés.
      - Pondération : l'outil/puzzle (`altars_solved`), plus "cognitif", pèse 0.6
        contre 0.4 pour la chasse (`preys_eaten`) — on récompense davantage le
        signe d'intelligence que le signe de survie brute.
    """
    hunt = _median_norm([a.get("preys_eaten", 0) for a in agent_stats], PREY_REF)
    tools = _median_norm([a.get("altars_solved", 0) for a in agent_stats], ALTAR_REF)
    return float(np.clip(0.4 * hunt + 0.6 * tools, 0.0, 1.0))
```

par :

```python
PREY_REF = 5.0    # conservé pour rétro-compat ; stoneage_competence n'en dépend plus (EDR 096)
ALTAR_REF = 3.0   # lu par industrial/gym (PROVISOIRE) ; MORT en stoneage (altars_solved jamais incrémenté)

# Échelle moyens->ends de la compétence stoneage (EDR 096) : poids des barreaux VIVANTS.
W_HUNT = 0.4    # chasse triviale (plancher)
W_APEX = 0.45   # apex-prédation coopérative (mammouth) — barreau dur VIVANT
W_TOOL = 0.15   # craft de lance — pathway outil (froid mais récompensé pour le nudge)


def stoneage_competence(agent_stats: List[Dict]) -> float:
    """Monde 1 (Stoneage) — échelle moyens->ends de comportements VIVANTS (EDR 096).

    L'ancien terme d'autel (`altars_solved`, pondéré 0.6) était du CODE MORT sur stoneage
    (aucune résolution, jamais incrémenté) -> RETIRÉ. Remplacé par la fraction d'agents atteignant
    chaque barreau vivant — chasse < apex-prédation coop < lance — agrégée par PARTICIPATION
    (`_frac_reaching`, pas la médiane : les conduites de minorité apex 21.7% / lance 1.6% sont lavées
    par la médiane, EDR 094 ; la fraction binaire est aussi robuste à l'inflation de crédit-groupe
    d'EDR 028)."""
    frac_hunt = _frac_reaching(agent_stats, "preys_eaten")
    frac_apex = _frac_reaching(agent_stats, "mammoth_kills")
    frac_tool = _frac_reaching(agent_stats, "spears_crafted")
    return float(np.clip(W_HUNT * frac_hunt + W_APEX * frac_apex + W_TOOL * frac_tool, 0.0, 1.0))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_competence_repair.py -q -p no:cacheprovider`
Expected: PASS (8 tests : 4 de Task 1 + 4 de Task 2).

- [ ] **Step 5: Non-régression (consommateurs intacts)**

Run: `python -m pytest tests/sandbox/test_curriculum_transfer.py tests/sandbox/test_retention.py -q -p no:cacheprovider`
Expected: PASS (signature `List[Dict]->float` et `_median_norm`/`survival_competence` inchangés).

- [ ] **Step 6: Commit**

```bash
git commit src/curriculum/competence.py tests/sandbox/test_competence_repair.py -m "feat(competence): stoneage_competence reparee (echelle moyens->ends vivante, EDR 096)"
```

---

## Self-Review

**Spec coverage :** `_frac_reaching` (fraction, rare-event-aware, inflation-robuste, vide→0) → Task 1.
`stoneage_competence` réparée (échelle fractions hunt/apex/tool, poids 0.4/0.45/0.15, docstring réécrite,
ALTAR_REF conservé) → Task 2. Garde-fou anti-théâtre (non-plancher gradué + apex compte) → Task 2 Step 1.
Inflation-robustesse testée → Task 1. Non-régression → Task 2 Step 5. Périmètre (stoneage seul,
industrial/gym/`_median_norm` intacts) respecté. ✓

**Placeholder scan :** aucun TODO/TBD ; tout le code est complet (helper, fonction, 8 tests, bloc à
remplacer cité verbatim). ✓

**Type consistency :** `_frac_reaching(List[Dict], str, float) -> float` (Task 1) consommé par
`stoneage_competence` (Task 2) avec les clés `preys_eaten`/`mammoth_kills`/`spears_crafted`. Constantes
`W_HUNT/W_APEX/W_TOOL` définies et utilisées dans la même fonction. `np` déjà importé (compétence.py:12).
`_pop` (helper de test) produit des agents aux 3 champs, cohérent avec `_frac_reaching`. ✓
