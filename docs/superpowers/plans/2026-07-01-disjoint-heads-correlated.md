# EDR 155 (V2) — profs corrélés / interférence induite : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un banc de profs corrélés (sous-espace partagé signé, sweep ρ) qui induit une vraie interférence inter-têtes, et re-teste si le crédit-équilibrage plat (FLAT_NORM, 153) recouvre encore l'avantage DISJOINT quand le cosinus devient négatif — ou si l'architecture se met enfin à compter.

**Architecture:** Nouveau fichier `tools/disjoint_heads_correlated.py`. Seul code neuf = un constructeur de profs corrélés (`_make_correlated_teachers`) au même format que `_make_teachers` (152), un verdict combiné 2-axes, un report et un driver de sweep. TOUT le reste (entraînement FLAT/DISJOINT/FLAT_NORM, cosinus, recovery) est réutilisé par import depuis `disjoint_heads_ab` (152) et `disjoint_heads_confound` (153).

**Tech Stack:** Python, PyTorch (proxy supervisé teacher-student auto-contenu, CPU, déterministe), NumPy.

## Global Constraints

- **TOOLING ADDITIF** : créer SEULEMENT `tools/disjoint_heads_correlated.py` et `tests/sandbox/test_disjoint_heads_correlated.py`. NE modifier AUCUN autre fichier — ni `tools/disjoint_heads_ab.py`, ni `tools/disjoint_heads_confound.py`, ni `src/`, ni `torch_batch_model.py`/`backend_torch.py`/`substrate_*` (fil // torch).
- **Prints exécutés = ASCII-only** (cp1252 Windows) : toute chaîne passée à `print()` strictement ASCII (`->` en tirets OK, pas d'accent ni flèche unicode). Accents seulement dans les docstrings.
- **Déterminisme** : `main_correlated_check` appelle `torch.set_num_threads(1)` et `torch.use_deterministic_algorithms(True)` (try/except). Le run réel = 2 passes byte-identiques.
- **Imports minimaux (pas d'import mort)** : n'importer QUE ce qui est utilisé.
- **Format profs** : `_make_correlated_teachers` DOIT renvoyer `{"action":(w1,w2), "value":(w1,w2), "pred":(w1,w2)}` avec `w1` de forme `(D,16)` et `w2` de forme `(16,out)` (out = K_A/1/P_PRED), pour que `_teacher_forward`/`_targets`/`_make_data` (152) marchent inchangés.
- **Reproductibilité du sweep** : `_make_correlated_teachers(rho)` utilise `np.random.default_rng(TEACHER_SEED)` (même seed pour tout ρ → seule la mixture change à travers ρ). Appelé UNE fois par ρ, AVANT la boucle de seeds d'entraînement (pas de contamination d'état RNG global par `_train_arm`).
- **Verdict gelé** : Axe A `INDUCED` si `cos ≤ −0.05` majorité ; Axe B `CREDIT_ROBUST` recovery≥0.50 / `ARCH_MATTERS` ≤0.20 / `CREDIT_PARTIAL`. Ne PAS ajuster après le run.

---

## Fichiers

- Créer : `tools/disjoint_heads_correlated.py`.
- Créer : `tests/sandbox/test_disjoint_heads_correlated.py`.

Imports disponibles (déjà exportés, vérifiés dans le code des deux fichiers) :
- de `tools.disjoint_heads_ab` : `torch, _train_arm, _seed_improv, D, K_A, P_PRED, TEACHER_SEED, STEPS`.
- de `tools.disjoint_heads_confound` : `_train_flat_norm, _recovery`.
- `numpy` importé directement (`import numpy as np`).

Rappels de types (152/153, ne PAS redéfinir) :
- `_train_arm(arm, seed, teachers, steps=STEPS) -> (eval_dict, interf_or_None)`. `arm="flat"` renvoie `(eval, cos)` (cosinus du trunc partagé) ; `arm="disjoint"` renvoie `(eval, None)`. `eval_dict = {"action","value","pred"}` (floats).
- `_train_flat_norm(seed, teachers, steps=STEPS) -> eval_dict`.
- `_seed_improv(flat_eval, disj_eval) -> float` (amélioration relative moyenne 3 têtes).
- `_recovery(flat_eval, mid_eval, disj_eval) -> float` (recouvrement value+pred du gain FLAT→DISJOINT par `mid`).
- Constantes : `D==32`, `K_A==4`, `P_PRED==8`, `TEACHER_SEED==777`, `STEPS==2000`.

---

## Task 1 : constructeur de profs corrélés + verdict gelé

**Files:**
- Create: `tools/disjoint_heads_correlated.py`
- Test: `tests/sandbox/test_disjoint_heads_correlated.py`

**Interfaces:**
- Consumes : `torch, _train_arm, _seed_improv, D, K_A, P_PRED, TEACHER_SEED, STEPS` (de `disjoint_heads_ab`) ; `_train_flat_norm, _recovery` (de `disjoint_heads_confound`) ; `numpy as np`.
- Produces : `_make_correlated_teachers(rho, seed=TEACHER_SEED) -> dict` ; `_verdict_correlated(cos_list, recovery_list) -> str`.

- [ ] **Step 1 : écrire les tests qui échouent**

Créer `tests/sandbox/test_disjoint_heads_correlated.py` :

```python
import numpy as np

from tools.disjoint_heads_ab import D, K_A, P_PRED
from tools.disjoint_heads_correlated import _make_correlated_teachers, _verdict_correlated


def test_teacher_format():
    t = _make_correlated_teachers(0.5)
    assert set(t.keys()) == {"action", "value", "pred"}
    assert t["action"][0].shape == (D, 16) and t["action"][1].shape == (16, K_A)
    assert t["value"][0].shape == (D, 16) and t["value"][1].shape == (16, 1)
    assert t["pred"][0].shape == (D, 16) and t["pred"][1].shape == (16, P_PRED)


def test_rho_changes_w1():
    # rho=0 (independant) vs rho=0.95 (sous-espace commun signe) -> w1 differe pour value
    t0 = _make_correlated_teachers(0.0)
    t95 = _make_correlated_teachers(0.95)
    assert not np.allclose(t0["value"][0], t95["value"][0])
    # meme seed -> reproductible
    assert np.allclose(t95["value"][0], _make_correlated_teachers(0.95)["value"][0])


def test_verdict_induced_credit_robust():
    assert _verdict_correlated([-0.1, -0.1, -0.2, 0.0, -0.3], [0.8, 0.7, 0.9, 0.6, 0.85]) == "INDUCED+CREDIT_ROBUST"


def test_verdict_not_induced():
    assert _verdict_correlated([0.0, 0.01, -0.02, 0.03, 0.0], [0.9, 0.8, 0.85, 0.7, 0.9]) == "NOT_INDUCED+CREDIT_ROBUST"


def test_verdict_induced_arch_matters():
    assert _verdict_correlated([-0.2, -0.15, -0.3, -0.1, -0.25], [0.1, 0.15, 0.05, 0.2, 0.1]) == "INDUCED+ARCH_MATTERS"


def test_verdict_induced_partial():
    assert _verdict_correlated([-0.2, -0.15, -0.3, -0.1, -0.25], [0.35, 0.4, 0.3, 0.45, 0.38]) == "INDUCED+CREDIT_PARTIAL"
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-correlated" && python -m pytest tests/sandbox/test_disjoint_heads_correlated.py -v`
Expected : FAIL (ImportError sur `tools.disjoint_heads_correlated`).

- [ ] **Step 3 : implémenter (créer le fichier, EXACTEMENT ce code)**

Créer `tools/disjoint_heads_correlated.py` :

```python
"""tools/disjoint_heads_correlated.py — Profs correles, interference induite (EDR 155, V2).

EDR 152 : les tetes disjointes battent le plat mais cos-conflit~0 -> interference REFUTEE, MAIS les profs etaient
INDEPENDANTS (quasi-orthogonaux) -> pas d'interference a trouver (caveat I2). V2 induit une vraie interference
(profs correles par sous-espace partage signe, sweep rho) et re-teste : quand le cosinus du trunc devient negatif,
le credit-equilibrage PLAT (FLAT_NORM, 153) recouvre-t-il encore l'avantage DISJOINT, ou l'architecture compte-t-elle
enfin ? Reutilise 152 (_train_arm, cosinus) + 153 (FLAT_NORM, recovery). Auto-contenu PyTorch, ne modifie rien.

Usage : python -m tools.disjoint_heads_correlated
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.disjoint_heads_ab import (
    torch, _train_arm, _seed_improv, D, K_A, P_PRED, TEACHER_SEED, STEPS,
)
from tools.disjoint_heads_confound import _train_flat_norm, _recovery

# Signes par tete sur la composante commune : action/value alignees, pred opposee -> au moins une paire contestee.
SIGMA = {"action": 1.0, "value": 1.0, "pred": -1.0}
COS_INDUCED = -0.05   # seuil axe A (gele)


def _make_correlated_teachers(rho, seed=TEACHER_SEED):
    """3 profs correles par sous-espace partage signe. Meme format que _make_teachers (152) : {"action":(w1,w2),...},
    w1 (D,16), w2 (16,out). w1_k(rho) = colnorm(sqrt(1-rho)*indep_k + sqrt(rho)*SIGMA[k]*common). rho=0 -> independants
    (baseline ~orthogonale de CE mecanisme) ; rho->1 -> meme sous-espace, signes opposes -> conflit vise. Meme seed
    pour tout rho -> seule la mixture change a travers le sweep. Deterministe (numpy default_rng)."""
    rng = np.random.default_rng(seed)
    outs = {"action": K_A, "value": 1, "pred": P_PRED}
    common = (rng.standard_normal((D, 16)) / np.sqrt(D)).astype(np.float32)
    teachers = {}
    for name, out in outs.items():
        indep = (rng.standard_normal((D, 16)) / np.sqrt(D)).astype(np.float32)
        w1 = np.sqrt(1.0 - rho) * indep + np.sqrt(rho) * SIGMA[name] * common
        # colnorm : rescale chaque colonne a la norme de la colonne independante d'origine (echelle feature ~rho-invariante)
        for c in range(w1.shape[1]):
            src = float(np.linalg.norm(indep[:, c]))
            cur = float(np.linalg.norm(w1[:, c]))
            if cur > 1e-8:
                w1[:, c] *= src / cur
        w1 = w1.astype(np.float32)
        w2 = (rng.standard_normal((16, out)) / np.sqrt(16)).astype(np.float32)
        teachers[name] = (w1, w2)
    return teachers


def _verdict_correlated(cos_list, recovery_list):
    """Verdict combine 2 axes a rho_max. GELE.
    Axe A : INDUCED si cos<=COS_INDUCED majorite, sinon NOT_INDUCED.
    Axe B : CREDIT_ROBUST recovery>=0.50 majorite / ARCH_MATTERS <=0.20 majorite / sinon CREDIT_PARTIAL."""
    n = len(cos_list)
    maj = n // 2 + 1
    axis_a = "INDUCED" if sum(1 for c in cos_list if c <= COS_INDUCED) >= maj else "NOT_INDUCED"
    robust = sum(1 for r in recovery_list if r >= 0.50)
    arch = sum(1 for r in recovery_list if r <= 0.20)
    if robust >= maj:
        axis_b = "CREDIT_ROBUST"
    elif arch >= maj:
        axis_b = "ARCH_MATTERS"
    else:
        axis_b = "CREDIT_PARTIAL"
    return axis_a + "+" + axis_b
```

- [ ] **Step 4 : lancer les tests, vérifier PASS**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-correlated" && python -m pytest tests/sandbox/test_disjoint_heads_correlated.py -v`
Expected : PASS (6 tests — format, rho-change, 4 verdict).

- [ ] **Step 5 : vérifier zéro modif fichiers existants**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-correlated" && git status --short`
Expected : seuls `tools/disjoint_heads_correlated.py` et `tests/sandbox/test_disjoint_heads_correlated.py` apparaissent.

- [ ] **Step 6 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-correlated"
git add tools/disjoint_heads_correlated.py tests/sandbox/test_disjoint_heads_correlated.py
git commit -m "feat(correlated): profs correles sous-espace signe + verdict 2-axes gele

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2 : report par ρ + main_correlated_check (sweep) + smoke

**Files:**
- Modify: `tools/disjoint_heads_correlated.py` (AJOUTER après `_verdict_correlated`)
- Test: `tests/sandbox/test_disjoint_heads_correlated.py` (AJOUTER à la fin)

**Interfaces:**
- Consumes : `_make_correlated_teachers, _verdict_correlated` (Task 1) ; `torch, _train_arm, _seed_improv, STEPS, _train_flat_norm, _recovery, np` (déjà importés en tête).
- Produces : `_report_correlated(rho_rows) -> None` ; `main_correlated_check(K=5, base=2200, rhos=(0.0, 0.6, 0.95), steps=STEPS, _return=False) -> dict|None` retournant `{verdict, per_rho, rho_max}` (ou `{verdict:"SKIPPED_NO_TORCH", per_rho:[]}` si torch absent).

- [ ] **Step 1 : ajouter le test smoke qui échoue**

Ajouter à la fin de `tests/sandbox/test_disjoint_heads_correlated.py` :

```python
from tools.disjoint_heads_correlated import main_correlated_check


def test_smoke_correlated_returns_verdict():
    res = main_correlated_check(K=1, base=99000, rhos=(0.0, 0.95), steps=25, _return=True)
    assert res["verdict"] == "SKIPPED_NO_TORCH" or "+" in res["verdict"]
    assert "per_rho" in res
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-correlated" && python -m pytest tests/sandbox/test_disjoint_heads_correlated.py -k smoke -v`
Expected : FAIL (ImportError sur `main_correlated_check`).

- [ ] **Step 3 : implémenter (AJOUTER après `_verdict_correlated`, EXACTEMENT ce code)**

```python
def _report_correlated(rho_rows):
    print("\n=== Profs correles : interference induite (FLAT vs DISJOINT vs FLAT_NORM par rho) ===")
    for rr in rho_rows:
        print("  rho=%.2f | cos=%+.3f | improv=%+.3f | recovery=%+.3f"
              % (rr["rho"], rr["mean_cos"], rr["mean_improv"], rr["mean_recovery"]))
        for r in rr["seeds"]:
            print("    seed %4d | cos %+.3f | improv %+.3f | recovery %+.3f | gain(FLAT-DISJ) v/p %.3f %.3f"
                  % (r["seed"], r["cos"], r["improv"], r["recovery"],
                     r["flat"]["value"] - r["disj"]["value"], r["flat"]["pred"] - r["disj"]["pred"]))
    print("=== VERDICT (mesure a rho_max) ===")


def main_correlated_check(K=5, base=2200, rhos=(0.0, 0.6, 0.95), steps=STEPS, _return=False):
    if torch is None:
        print("PyTorch indisponible -> banc saute.")
        res = {"verdict": "SKIPPED_NO_TORCH", "per_rho": []}
        return res if _return else None
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass
    torch.set_num_threads(1)
    rho_rows = []
    for rho in rhos:
        teachers = _make_correlated_teachers(rho)
        seeds = []
        for i in range(K):
            s = base + i
            flat, cos = _train_arm("flat", s, teachers, steps=steps)
            disj, _ = _train_arm("disjoint", s, teachers, steps=steps)
            flatnorm = _train_flat_norm(s, teachers, steps=steps)
            seeds.append({"seed": s, "flat": flat, "disj": disj, "flatnorm": flatnorm,
                          "cos": cos, "improv": _seed_improv(flat, disj),
                          "recovery": _recovery(flat, flatnorm, disj)})
        rho_rows.append({"rho": rho, "seeds": seeds,
                         "mean_cos": float(np.mean([r["cos"] for r in seeds])),
                         "mean_improv": float(np.mean([r["improv"] for r in seeds])),
                         "mean_recovery": float(np.mean([r["recovery"] for r in seeds]))})
    rho_max = max(rhos)
    top = [rr for rr in rho_rows if rr["rho"] == rho_max][0]
    verdict = _verdict_correlated([r["cos"] for r in top["seeds"]], [r["recovery"] for r in top["seeds"]])
    _report_correlated(rho_rows)
    print("  -> %s (A: cos<=-0.05 majorite=INDUCED ; B: recovery>=0.50=CREDIT_ROBUST, <=0.20=ARCH_MATTERS)" % verdict)
    res = {"verdict": verdict, "per_rho": rho_rows, "rho_max": rho_max}
    return res if _return else None


if __name__ == "__main__":
    main_correlated_check()
```

- [ ] **Step 4 : lancer TOUS les tests**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-correlated" && python -m pytest tests/sandbox/test_disjoint_heads_correlated.py -v`
Expected : PASS (7 tests). Le smoke lance 2 ρ × 1 seed × 3 bras × 25 pas → quelques secondes, laisse finir.

- [ ] **Step 5 : vérifier zéro modif fichiers existants + ASCII des prints**

Run : `cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-correlated" && git status --short`
Expected : seuls les 2 fichiers du chantier touchés. Vérifier que les `print` de `_report_correlated`/`main_correlated_check` sont strictement ASCII.

- [ ] **Step 6 : commit**

```bash
cd "c:/Users/robla/VScode_Project/AGAGI/.claude/worktrees/disjoint-correlated"
git add tools/disjoint_heads_correlated.py tests/sandbox/test_disjoint_heads_correlated.py
git commit -m "feat(correlated): report par rho + main_correlated_check (sweep) + smoke

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (rempli)

**1. Spec coverage :** §2 mécanisme (`_make_correlated_teachers`, ρ+SIGMA+colnorm) → Task 1. §3 sweep 3 bras/ρ → `main_correlated_check` Task 2. §4 verdict 2-axes gelé → `_verdict_correlated` Task 1. §8 interfaces → T1 (`_make_correlated_teachers`/`_verdict_correlated`) + T2 (`_report_correlated`/`main_correlated_check`). §7 additif + ASCII + déterminisme → Global Constraints + steps de vérif. Couverture complète.

**2. Placeholder scan :** aucun TBD/TODO ; tout le code complet et exécutable.

**3. Type consistency :** `_make_correlated_teachers` renvoie le format `{name:(w1,w2)}` consommé par `_train_arm`/`_train_flat_norm` (via `teachers` param, inchangé). `_verdict_correlated(cos_list, recovery_list)` seuils (−0.05 / 0.50 / 0.20) cohérents spec §4. Clés de row (`flat/disj/flatnorm/cos/improv/recovery`) cohérentes entre `main_correlated_check` et `_report_correlated` (`r["flat"]["value"]` etc.). `rho_rows` clés (`rho/seeds/mean_cos/mean_improv/mean_recovery`) cohérentes main↔report.
