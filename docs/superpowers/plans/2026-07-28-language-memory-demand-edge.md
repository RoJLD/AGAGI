# Troisième arête mesurée (« language demands memory ») Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MESURER et graver la 3ᵉ arête du graphe AGI-Taxonomy — « language demands memory » — par une ablation de SUBSTRAT (reset de l'état récurrent porté) montrée CHIRURGICALE via le garde `functional_aliasing='pass'` de CALIB-ALIAS (son premier usage réel).

**Architecture:** Sonde torch self-contained (delayed-code-application). L'agent apprend DEUX capacités partageant la même tête d'action à 8 logits (mesurées en forwards SÉPARÉS depuis l'état porté `H` partagé — contrainte substrat `_MOVE_LOGITS=8` : impossible d'entraîner 2 readouts dans un même forward) : LANG = `(q+key)%K` (a besoin du `key` retenu + la quête `q`), CONTROL = copier `c` (feedforward, mémoire-indépendant). Ablation mémoire = reset `H` à l'usage. `ablation_verdict` sur LANG (X_DEMANDED) ; `assert_no_functional_aliasing` sur CONTROL (leakage≈0 → SURGICAL → pass). Le garde AUTO-DÉCIDE : chirurgical → arête gravée ; fuite → finding honnête. Calibrée oracle/aléatoire/leaky.

**Tech Stack:** Python 3, torch (CPU), numpy, pytest. Réutilise `MambaAgent`, `make_population(backend="torch")`, `learn_episode`, `tools/demand_marker.ablation_verdict`, `tools/experiment_preflight.assert_no_functional_aliasing`. Le validateur `tools/check_agi_taxonomy.py` accepte DÉJÀ `functional_aliasing="pass"` (livré SP-2). AUCUNE modif validateur.

## Global Constraints

- **Deux capacités, tête d'action PARTAGÉE (verbatim)** : le substrat n'a qu'une tête à 8 logits (`out[:, :_MOVE_LOGITS]`, `_MOVE_LOGITS=8`). LANG et CONTROL utilisent la MÊME tête (readout = `argmax(logits[:, :K])`, K=6≤8) mais dans des forwards SÉPARÉS, distingués par les slots d'obs actifs. Ne PAS tenter une action jointe (dépasserait 8).
- **Ablation de SUBSTRAT (verbatim)** : au tick d'USAGE, `agent.H` remis à zéro AVANT le forward (efface le portage `(1-δ)·H` = le `key` retenu ; l'injection d'entrée `_step` réinjecte l'obs courant). À L'ÉVAL uniquement (within-subject). C'est une ÉCRITURE d'état → `functional_aliasing` DOIT valoir `'pass'` (mesuré), JAMAIS `'n/a'`.
- **Layout d'entrée** : `key` aux slots `[0:K]`, `query` aux slots `[K:2K]`, `control` aux slots `[2K:3K]` (disjoints ; I=59 ≥ 3K=18). Encodage : seul `key` actif. Usage-LANG : seul `query`. Usage-CONTROL : seul `control`.
- **État porté** : `H` reset UNE fois par épisode/trajectoire, porté encode→délai→usage (jamais reset entre les ticks SAUF l'ablation).
- **Seam `memory_mode ∈ {learned, oracle, random}`** + **`control_mode ∈ {feedforward, leaky}`** : `oracle` = LANG parfait par fiat (retient `key`) → ablater effondre ; `random` = LANG décorrélé → inerte ; `leaky` = CONTROL forcé de dépendre du `key` retenu → ablater fait FUIR → le garde functional_aliasing DOIT tirer (générateur A du garde). oracle/random/leaky pour la CALIBRATION (n'entraînent pas le substrat, ou peu).
- **Deux gardes** : `ablation_verdict(lang_intact, lang_ablated, floor=1/K)` → X_DEMANDED ; `assert_no_functional_aliasing(control_intact, control_ablated)` + calcul `leakage`/`x_response` → SURGICAL/FUNCTIONAL_LEAK/VACUOUS. `x_response=|lang_intact_med − lang_ablated_med|>0` (générateur A).
- **NO-MEMORY specificity DIFFÉRÉ** (scoping) : le garde functional_aliasing établit déjà que le collapse LANG est mémoire-SPÉCIFIQUE (l'ablation est chirurgicale, pas globale — CONTROL survit ; et la quête est présente fraîche, non ablatée). Le contrôle NO-MEMORY (key re-montré) est une rigueur SECONDAIRE différée à une itération ultérieure. Documenter ce choix dans le record.
- **Nommage cliquet** : `run_language_memory_demand_probe` (motif `run_\w*probe`) → doit figurer dans `CALIBRATED`. Helpers privés (préfixe `_`) ne matchent aucun motif.
- **Bornage du coût** : pur torch CPU, aucun bail `kuzu`, aucun monde. Pré-vol `declare_design`. SMOKE d'abord ; run-verdict n=12 en **FOREGROUND** (jamais background — perdu ~92min SP-2 ; sur MEM-PERCEPTION le contrôleur a dû faire un run de récup, GARDER le run < ~9 min pour tenir sous le cap 590s). Persister accuracies + `_params`. Provenance : fonction CALIBRÉE réelle.
- **Ne modifier AUCUN probe/validateur existant.** Commits path-scoped (JAMAIS `-A`) ; arbre partagé ; stash-contingency fichier étranger ; jamais `--no-verify`. Branche `feat/d1-prod-pairing`.

## File Structure

- `tools/language_memory_demand_probe.py` (NOUVEAU) — la sonde.
- `tests/test_language_memory_probe.py` (NOUVEAU) — smoke unitaire.
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — CALIBRATED + oracle/aléatoire/leaky.
- `data/agi_taxonomy/demands.json` (MODIFIÉ, Task 2, SI gravée) — 3ᵉ arête.
- `docs/EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md` (NOUVEAU, Task 2) — record.
- `results/lang_memory_edge_accuracies.json` (NOUVEAU, Task 2).

---

### Task 1: Sonde + calibration (FUSIONNÉS) + smoke

**Files:**
- Create: `tools/language_memory_demand_probe.py`
- Create: `tests/test_language_memory_probe.py`
- Modify: `tests/sandbox/test_instrument_calibration.py`

**Interfaces:**
- Consumes: `MambaAgent`, `make_population`, `learn_episode`, `ablation_verdict`, `assert_no_functional_aliasing`. **VÉRIFIER contre le code réel** (leçon MEM-PERCEPTION : le brief peut se tromper sur le substrat) : (a) `forward(x)->(logits,_)` met à jour `self.H` en interne (le 2ᵉ retour est un placeholder, NE PAS réassigner `self.H=...`) ; le readout = `logits[:, :K]` (les K premiers des `_MOVE_LOGITS=8`) ; (b) `learn_episode(obs_seq, actions_seq, rewards, gate_last_only=True)` crédite la dernière action, accepte une séquence ; comment gère-t-il `self.H` au début d'un épisode (reset ?) — vérifier pour savoir s'il faut reset manuellement entre trials LANG et CONTROL ; (c) `assert_no_functional_aliasing(control_intact, control_ablated, tol=...)` lève si le contrôle change — l'utiliser pour le verdict OU calculer leakage soi-même et appeler `functional_aliasing_verdict`-style. Adapter si divergence, et le signaler.
- Produces: `run_language_memory_demand_probe(seeds, episodes=1200, n_agents=16, K=6, D=2, lr=0.02, memory_mode="learned", control_mode="feedforward") -> dict` renvoyant `{"lang_demand": <ablation_verdict dict>, "functional_aliasing": "pass"|"fail", "alias_verdict": "SURGICAL"|"FUNCTIONAL_LEAK"|"VACUOUS_ABLATION", "leakage": float, "x_response": float, "n": int, "lang_intact": [...], "lang_ablated": [...], "control_intact": [...], "control_ablated": [...]}`.

- [ ] **Step 1: Écrire le smoke unitaire (qui échoue)**

Create `tests/test_language_memory_probe.py`:

```python
import pytest

pytest.importorskip("torch")


def test_probe_shapes_and_alias_keys_smoke():
    from tools.language_memory_demand_probe import run_language_memory_demand_probe
    # smoke minuscule : FORME + présence des clés du garde, pas les valeurs scientifiques
    r = run_language_memory_demand_probe(seeds=[0, 1], episodes=40, n_agents=8, K=4, D=1)
    assert set(r) >= {"lang_demand", "functional_aliasing", "alias_verdict", "leakage", "x_response"}
    assert r["functional_aliasing"] in ("pass", "fail")
    assert r["n"] == 2 and len(r["lang_intact"]) == 2 and len(r["control_intact"]) == 2
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_language_memory_probe.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter la sonde**

Create `tools/language_memory_demand_probe.py` (VÉRIFIER les interfaces substrat en implémentant ; ce code est un point de départ) :

```python
"""AGI-Taxonomy — MESURE de l'arête « language demands memory » (delayed-code-application).

L'agent apprend DEUX capacités partageant la tête d'action à 8 logits (_MOVE_LOGITS=8), mesurées en forwards
SÉPARÉS depuis l'état porté H partagé : LANG = (q+key)%K (a besoin du key RETENU + la quête q) ; CONTROL =
copier c (feedforward, mémoire-indépendant). Ablation de MÉMOIRE = reset de H à l'usage (efface le portage
(1-δ)·H). ablation_verdict sur LANG (X_DEMANDED) ; assert_no_functional_aliasing sur CONTROL (leakage≈0 ->
SURGICAL -> functional_aliasing='pass', 1er usage réel du jalon CALIB-ALIAS). Le garde AUTO-DÉCIDE la
gravabilité. Calibré oracle/aléatoire/leaky. Pur torch CPU, aucun bail.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.demand_marker import ablation_verdict


def _slot(idx, K, offset, I, n_agents):
    """one-hot de idx dans les slots [offset:offset+K] d'un vecteur d'obs (I,)."""
    m = np.zeros((n_agents, I), dtype=np.float32)
    m[np.arange(n_agents), offset + (idx % K)] = 1.0
    return m


def _zeros(I, n_agents):
    return np.zeros((n_agents, I), dtype=np.float32)


def _reset_H(agent):
    import torch
    agent.H = torch.zeros((agent.W.shape[0], agent.N))


def _carry(agent, key, K, I, n_agents, D, rng):
    """Reset H puis encode(key) + D ticks de délai. H porte le key retenu."""
    _reset_H(agent)
    agent.forward(_slot(key, K, 0, I, n_agents))               # encodage (slots [0:K])
    for _ in range(D):
        agent.forward(_zeros(I, n_agents))                     # délai (H porté, MAJ interne de self.H)


def _lang_move(agent, q, K, I, n_agents):
    """Forward LANG (quête aux slots [K:2K]) -> guess = argmax(logits[:, :K])."""
    logits, _ = agent.forward(_slot(q, K, K, I, n_agents))
    return np.asarray(logits)[:, :K].argmax(axis=1)


def _control_move(agent, c, K, I, n_agents):
    """Forward CONTROL (cible aux slots [2K:3K]) -> guess = argmax(logits[:, :K])."""
    logits, _ = agent.forward(_slot(c, K, 2 * K, I, n_agents))
    return np.asarray(logits)[:, :K].argmax(axis=1)


def _train_and_eval(seed, episodes, n_agents, K, D, lr, memory_mode, control_mode, eval_batches=40):
    """Entraîne l'agent (learned) sur LANG+CONTROL, puis évalue LANG et CONTROL intact vs H-reset.
    Renvoie (lang_i, lang_a, ctrl_i, ctrl_a) = accuracies."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    try:
        agent = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I = agent.I
        rng = np.random.RandomState(seed + 1)
        learned = memory_mode == "learned"
        if learned:
            agent.opt = torch.optim.Adam([agent.W], lr=lr)
            for _ in range(episodes):
                key = rng.randint(0, K, size=n_agents)
                q = rng.randint(0, K, size=n_agents)
                c = rng.randint(0, K, size=n_agents)
                # --- trial LANG : encode(key) + délai + usage(query) -> (q+key)%K ---
                enc = _slot(key, K, 0, I, n_agents)
                seq = [enc] + [_zeros(I, n_agents) for _ in range(D)] + [_slot(q, K, K, I, n_agents)]
                _reset_H(agent)
                logits, _ = None, None
                for x in seq:
                    logits, _ = agent.forward(x)
                guess = np.asarray(logits)[:, :K].argmax(axis=1)
                tgt = (q + key) % K
                adv = (guess == tgt).astype(np.float32); adv = adv - adv.mean()
                acts = [[{"move": 0} for _ in range(n_agents)] for _ in range(len(seq) - 1)]
                acts.append([{"move": int(t)} for t in tgt])     # cible enseignée = bonne réponse
                agent.learn_episode(seq, acts, adv, gate_last_only=True)
                # --- trial CONTROL : usage(control) -> c (feedforward, 1 tick) ---
                _reset_H(agent)
                cseq = [_slot(c, K, 2 * K, I, n_agents)]
                clog, _ = agent.forward(cseq[0])
                cguess = np.asarray(clog)[:, :K].argmax(axis=1)
                cadv = (cguess == c).astype(np.float32); cadv = cadv - cadv.mean()
                agent.learn_episode(cseq, [[{"move": int(t)} for t in c]], cadv, gate_last_only=True)

        def _eval_lang(ablate):
            hits = []
            for _ in range(eval_batches):
                key = rng.randint(0, K, size=n_agents); q = rng.randint(0, K, size=n_agents)
                _carry(agent, key, K, I, n_agents, D, rng)
                if ablate:
                    _reset_H(agent)                              # ABLATION MÉMOIRE : efface le key retenu
                if memory_mode == "oracle":
                    g = ((q + key) % K) if not ablate else rng.randint(0, K, size=n_agents)  # key parfait vs perdu
                elif memory_mode == "random":
                    g = rng.randint(0, K, size=n_agents)
                else:
                    g = _lang_move(agent, q, K, I, n_agents)
                hits.append((g == ((q + key) % K)).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        def _eval_control(ablate):
            hits = []
            for _ in range(eval_batches):
                key = rng.randint(0, K, size=n_agents); c = rng.randint(0, K, size=n_agents)
                _carry(agent, key, K, I, n_agents, D, rng)       # même contexte porté que LANG
                if ablate:
                    _reset_H(agent)
                if control_mode == "leaky":
                    # CONTROL forcé de dépendre du key retenu -> ablater fait FUIR (vérité-terrain du garde)
                    g = c if not ablate else rng.randint(0, K, size=n_agents)
                elif memory_mode in ("oracle", "random"):
                    g = c                                        # contrôle feedforward parfait (bypass)
                else:
                    g = _control_move(agent, c, K, I, n_agents)
                hits.append((g == c).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        return _eval_lang(False), _eval_lang(True), _eval_control(False), _eval_control(True)
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved


def run_language_memory_demand_probe(seeds, episodes=1200, n_agents=16, K=6, D=2, lr=0.02,
                                     memory_mode="learned", control_mode="feedforward"):
    """Mesure « language demands memory ». Par seed : LANG et CONTROL, chacun éval intact/ablé (H-reset).
    LANG -> ablation_verdict (X_DEMANDED) ; CONTROL -> garde functional_aliasing (leakage≈0 -> pass)."""
    li, la, ci, ca = [], [], [], []
    for s in seeds:
        l_i, l_a, c_i, c_a = _train_and_eval(s, episodes, n_agents, K, D, lr, memory_mode, control_mode)
        li.append(l_i); la.append(l_a); ci.append(c_i); ca.append(c_a)

    floor = 1.0 / K
    lang = ablation_verdict(li, la, intervention_verified=True, floor=floor, ceiling=1.0)
    leakage = abs(float(np.median(ci)) - float(np.median(ca)))
    x_response = abs(float(np.median(li)) - float(np.median(la)))
    tol = 0.05                                                  # tolérance de fuite (bruit d'échantillon)
    if x_response <= tol:
        alias = "VACUOUS_ABLATION"
    elif leakage <= tol:
        alias = "SURGICAL"
    else:
        alias = "FUNCTIONAL_LEAK"
    fa = "pass" if alias == "SURGICAL" else "fail"
    return {"lang_demand": lang, "functional_aliasing": fa, "alias_verdict": alias,
            "leakage": leakage, "x_response": x_response, "n": len(seeds),
            "lang_intact": li, "lang_ablated": la, "control_intact": ci, "control_ablated": ca}


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("LM_SEEDS", "12"))))
    r = run_language_memory_demand_probe(seeds, episodes=int(os.environ.get("LM_EPISODES", "1200")),
                                         n_agents=int(os.environ.get("LM_AGENTS", "16")))
    print(json.dumps({k: v for k, v in r.items()
                      if k in ("lang_demand", "functional_aliasing", "alias_verdict", "leakage",
                               "x_response", "n")}, ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Lancer le smoke unitaire**

Run: `python -m pytest tests/test_language_memory_probe.py -v`
Expected: PASS (forme + clés du garde présentes, n=2). Si échec d'interface (H, learn_episode, readout), corriger d'après le code réel et re-signaler. VÉRIFIER surtout que LANG s'apprend (`lang_intact` > 1/K après entraînement) au smoke ; sinon le mécanisme est cassé.

- [ ] **Step 5: Déclarer calibré + écrire la calibration (oracle/aléatoire/leaky)**

In `tests/sandbox/test_instrument_calibration.py`, add to `CALIBRATED`:

```python
    # « language demands memory » (delayed-code-application). Contrôle positif DEMANDE = memory ORACLE
    # (rétention parfaite -> ablater effondre LANG) ; négatif = ALÉATOIRE (inerte) ; le garde
    # functional_aliasing est prouvé SENSIBLE par control LEAKY (contrôle forcé de dépendre du key -> FUITE
    # détectée). Générateur A dans les DEUX dimensions (demande + aliasing).
    "run_language_memory_demand_probe": ["*"],
```

Append:

```python
def test_lm_oracle_memory_makes_language_demanded():
    """CONTRÔLE POSITIF (demande) : mémoire ORACLE -> ablater l'état effondre LANG -> X_DEMANDED."""
    from tools.language_memory_demand_probe import run_language_memory_demand_probe
    r = run_language_memory_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6, D=2,
                                         memory_mode="oracle")
    assert r["lang_demand"]["verdict"] == "X_DEMANDED", r["lang_demand"]


def test_lm_random_memory_is_inert():
    """CONTRÔLE NÉGATIF (demande) : mémoire ALÉATOIRE -> ablater inerte -> PAS X_DEMANDED."""
    from tools.language_memory_demand_probe import run_language_memory_demand_probe
    r = run_language_memory_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6, D=2,
                                         memory_mode="random")
    assert r["lang_demand"]["verdict"] != "X_DEMANDED", r["lang_demand"]


def test_lm_leaky_control_fires_the_aliasing_guard():
    """VÉRITÉ-TERRAIN DU GARDE : un control LEAKY (forcé de dépendre du key retenu) -> ablater fait FUIR le
    contrôle -> functional_aliasing='fail' (FUNCTIONAL_LEAK). Prouve que le garde SAIT détecter une fuite
    (sinon un 'pass' serait vacux). oracle+leaky : LANG effondre (X_DEMANDED) ET le garde tire."""
    from tools.language_memory_demand_probe import run_language_memory_demand_probe
    r = run_language_memory_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6, D=2,
                                         memory_mode="oracle", control_mode="leaky")
    assert r["functional_aliasing"] == "fail" and r["alias_verdict"] == "FUNCTIONAL_LEAK", r
```

Note : oracle/random/leaky avec `episodes=0` (bypassent l'agent) → rapides. Vérifier qu'aucune division par `episodes`.

- [ ] **Step 6: Lancer calibration + cliquet**

Run: `python -m pytest tests/sandbox/test_instrument_calibration.py -k "lm_oracle or lm_random or lm_leaky" -v`
Expected: PASS (3 cas : oracle→X_DEMANDED, random→pas X_DEMANDED, leaky→garde tire).

Run: `python tools/check_instrument_calibration.py`
Expected: `OK : aucun nouvel instrument non calibré.`

- [ ] **Step 7: Commit (FUSIONNÉ)**

```bash
git add tools/language_memory_demand_probe.py tests/test_language_memory_probe.py tests/sandbox/test_instrument_calibration.py
git status --short   # UNIQUEMENT ces trois chemins
git commit -m "feat(LANG-MEMORY): sonde language-demande-memoire (ablation substrat) + calibration oracle/aleatoire/leaky (cliquet)"
```

Si le hook bloque sur un instrument étranger : stash path-scoped, commit, pop, vérifier — jamais `--no-verify`.

---

### Task 2: Run-verdict (n=12, FOREGROUND) + arête (SI chirurgicale) + record

**Files:**
- Create: `results/lang_memory_edge_accuracies.json`
- Modify: `data/agi_taxonomy/demands.json` (si gravée)
- Create: `docs/EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md`

**Interfaces:**
- Consumes: `run_language_memory_demand_probe` (Task 1), `check_agi_taxonomy` (livré).
- Produces: la 3ᵉ arête (si `functional_aliasing='pass'`) OU un finding négatif honnête + record + accuracies.

- [ ] **Step 1: Pré-vol + SMOKE (mécanisme + débit)**

Run: `python -c "import time,json; from tools.language_memory_demand_probe import run_language_memory_demand_probe as R; t=time.time(); r=R(seeds=[0,1,2], episodes=400, n_agents=16, K=6, D=2); print('dt_s=%.1f' % (time.time()-t)); print('lang', r['lang_demand']['verdict'], round(r['lang_demand']['ratio'],2), 'lang_intact_med', sorted(r['lang_intact'])[1]); print('alias', r['alias_verdict'], 'fa', r['functional_aliasing'], 'leakage', round(r['leakage'],3), 'x_response', round(r['x_response'],3))"`

Attendu (smoke, 3 seeds) : `dt_s` (débit — noter), `lang` tend X_DEMANDED, `lang_intact_med` > `1/K+0.15`≈0.32, `alias` SURGICAL ou FUNCTIONAL_LEAK (les DEUX sont un résultat). ⚠️ n<12 ne tranche pas.

**Décision de bornage** : si le run n=12 projette > ~9 min, RÉDUIRE `episodes`/`n_agents`/`D` (viser LANG émergent + CONTROL appris : `lang_intact` et `control_intact` médians > `1/K+0.15`). Garder le run FOREGROUND court (sous le cap 590s). Si LANG n'émerge pas → augmenter episodes/réduire D (précédent MEM-PERCEPTION : la rétention S'APPREND). Si CONTROL n'émerge pas (control_intact ≈ hasard), l'agent n'a pas appris la copie → augmenter episodes.

- [ ] **Step 2: Run-verdict n=12 (FOREGROUND, borné) + persister**

⚠️ FOREGROUND, JAMAIS background. Si le harness promeut en bg, BLOQUER dessus (poll le results), ne pas dupliquer.

Run (ajuster d'après le smoke) :
`python -c "import json; from tools.language_memory_demand_probe import run_language_memory_demand_probe as R; r=R(seeds=list(range(12)), episodes=1200, n_agents=16, K=6, D=2); r['_params']={'K':6,'D':2,'lr':0.02,'episodes':1200,'n_agents':16,'seeds':12}; json.dump(r, open('results/lang_memory_edge_accuracies.json','w'), indent=2); print('lang', r['lang_demand']['verdict'], round(r['lang_demand']['ratio'],3)); print('alias', r['alias_verdict'], 'fa', r['functional_aliasing'], 'leakage', round(r['leakage'],3), 'x_response', round(r['x_response'],3)); print('lang_intact_med', sorted(r['lang_intact'])[6], 'control_intact_med', sorted(r['control_intact'])[6], 'control_ablated_med', sorted(r['control_ablated'])[6])"`

Attendu : `lang X_DEMANDED` (intacte vivante > 0.32), `alias SURGICAL`/`fa pass` (contrôle survit) → arête GRAVABLE. OU `alias FUNCTIONAL_LEAK`/`fa fail` → finding honnête.

**Si CONTROL ne survit pas intact** (control_intact ≈ hasard) : l'agent n'a pas appris la copie feedforward → pas de capacité de contrôle valide → augmenter episodes/re-smoke. Ce n'est PAS un leak, c'est un contrôle non-appris (à distinguer : leak = control_intact HAUT mais control_ablated bas).

- [ ] **Step 3: Écrire l'arête (SSI functional_aliasing='pass')**

SSI `lang_demand X_DEMANDED` ET `functional_aliasing == 'pass'` ET `lang_intact` médian > `1/K+0.15`, LIRE `data/agi_taxonomy/demands.json` (2 arêtes existantes) et AJOUTER (liste de 3) :

```json
{
  "capability": "language",
  "prerequisite": "memory",
  "strength": "hard",
  "evidence": {
    "ablation_verdict": "X_DEMANDED",
    "ratio": 0.0,
    "n": 12,
    "functional_aliasing": "pass",
    "record": "docs/EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md"
  }
}
```

Remplacer `ratio` par le mesuré. Ne PAS écraser les 2 arêtes existantes. (Avec `functional_aliasing='pass'`, `specificity_control` n'est PAS requis par le validateur.)

- [ ] **Step 4: Écrire le record** (avant validation)

Create `docs/EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md` (valeurs réelles) :

```markdown
---
id: EDR-LANG-MEMORY
type: EDR
title: "Troisième arête MESURÉE du graphe AGI-Taxonomy : le langage/code appris DEMANDE la mémoire (ablation de SUBSTRAT chirurgicale — premier usage réel du garde functional_aliasing de CALIB-ALIAS)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER, REF-AGI-TAXONOMY]
---

## Question
3ᵉ arête MESURÉE : « language demands memory » ? Premier cas d'ablation de SUBSTRAT (pas d'entrée) —
exige de prouver l'ablation CHIRURGICALE via le garde `functional_aliasing='pass'` de CALIB-ALIAS.

## Méthode
Proxy torch delayed-code-application (MambaAgent). Deux capacités partageant la tête d'action à 8 logits,
mesurées en forwards séparés depuis l'état porté H partagé : LANG=(q+key)%K (a besoin du key RETENU),
CONTROL=copier c (feedforward). Ablation de MÉMOIRE = reset de H à l'usage (efface le portage (1-δ)·H).
`ablation_verdict` sur LANG ; `assert_no_functional_aliasing` sur CONTROL. n=12 seeds. Sonde calibrée :
oracle→effondre, aléatoire→inerte, LEAKY-control→le garde TIRE (générateur A des deux gardes).

## Résultat
LANG : X_DEMANDED (ratio R_REEL ; intacte VIVANTE médiane M_INTACT > 1/K+0.15, ablée ~hasard). CONTROL :
leakage L_REEL ≈ 0 → **SURGICAL** → `functional_aliasing='pass'`. Donc l'ablation de l'état retenu effondre
la capacité de code APPRISE de façon CHIRURGICALE (le contrôle feedforward survit) → la capacité route
causalement par la RÉTENTION. Arête `language → memory` gravée. **Premier usage réel du garde
functional_aliasing='pass'** — les 2 arêtes précédentes contournaient via l'ablation d'entrée ('n/a').

## Portée (bornée)
Proxy hors-monde (code-application), pas la biosphère. Single-agent (pas sender/receiver). Ablation
= reset TOTAL de H à l'usage (chirurgicalité PROUVÉE empiriquement par le contrôle, pas une ablation
ciblée par-dim). Contrôle NO-MEMORY (key re-montré) DIFFÉRÉ : le garde functional_aliasing fournit déjà
la spécificité (collapse chirurgical). Coût borné (smoke + n=12 FOREGROUND, accuracies persistées).

## Ce que ça débloque
3ᵉ arête ; **le garde `functional_aliasing='pass'` de CALIB-ALIAS enfin exercé sur un vrai substrat appris**
(sa raison d'être). Le pipeline gère maintenant les ablations de SUBSTRAT, pas seulement d'entrée.
Cf. `docs/superpowers/specs/2026-07-28-language-memory-demand-edge-design.md`.
```

Remplacer `R_REEL`/`M_INTACT`/`L_REEL`. **Si le run est FUNCTIONAL_LEAK** : record NÉGATIF honnête (l'ablation d'état FUIT dans le substrat appris ; le garde a bloqué une ablation non-chirurgicale — exactement son rôle ; arête NON écrite ; une ablation ciblée par-dim serait le suivant).

- [ ] **Step 5: Valider**

Run: `python tools/check_agi_taxonomy.py` (attendu `3 arêtes, 0 violations` si gravée, sinon `2 arêtes`)
Run: `python tools/check_record_links.py` (EDR-LANG-MEMORY non-orphelin)
Run: `python -m pytest tests/test_agi_taxonomy.py -q` (tous PASS ; `test_demands_shipped_graph_validates` sur 3 arêtes)
Run: `python tools/check_instrument_calibration.py` (OK)

- [ ] **Step 6: Commit**

```bash
git add data/agi_taxonomy/demands.json docs/EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md results/lang_memory_edge_accuracies.json
git status --short   # UNIQUEMENT ces trois chemins (omettre demands.json si finding négatif)
git commit -m "feat(LANG-MEMORY): 3e arete MESUREE language->memory (X_DEMANDED, ablation substrat SURGICAL, functional_aliasing=pass, n=12)"
```

Si `results/` gitignored : `git add -f`. Si finding négatif : ne pas stager demands.json. Stash-contingency fichier étranger si besoin.

---

## Self-Review

**Spec coverage :**
- §3 proxy delayed-code-application 2 readouts → Task 1 sonde (`_carry`/`_lang_move`/`_control_move`). ✓ (raffiné forwards séparés à H partagé, contrainte `_MOVE_LOGITS=8` — validée avec l'utilisateur.)
- §4 ablation de substrat (reset H à l'usage) → `_reset_H` dans `_eval_*(ablate=True)`. ✓
- §5.1 demande (ablation_verdict sur LANG) → `run_..._probe` lang_demand. ✓
- §5.2 functional_aliasing (leakage sur CONTROL) → `leakage`/`x_response`/`alias_verdict`/`fa`. ✓
- §6 calibration oracle/aléatoire/**leaky** (générateur A des 2 gardes) → Task 1 Step 5 (3 cas + CALIBRATED). ✓
- §7 bornage (smoke, run FOREGROUND borné, persister _params, provenance) → Task 2 Steps 1-2. ✓
- §8 arête SSI functional_aliasing='pass' + finding honnête sinon → Task 2 Steps 3-4. ✓
- §5.1 NO-MEMORY specificity → DIFFÉRÉ (documenté, functional_aliasing fournit la spécificité). Déviation notée. ✓

**Placeholder scan :** valeurs à mesurer (R_REEL/M_INTACT/L_REEL, `ratio:0.0`) marquées explicitement, remplies au run. Aucun TODO code.

**Type consistency :** `run_language_memory_demand_probe(seeds, episodes, n_agents, K, D, lr, memory_mode, control_mode)` renvoie `{lang_demand, functional_aliasing, alias_verdict, leakage, x_response, n, lang_intact, lang_ablated, control_intact, control_ablated}` — identique en Task 1 (tests) et Task 2 (run). L'arête (§8) porte `functional_aliasing:'pass'`, exactement ce que le validateur (livré SP-2) exige (sans specificity_control requis). Helpers privés `_slot`/`_zeros`/`_reset_H`/`_carry`/`_lang_move`/`_control_move`/`_train_and_eval` — aucun ne matche un motif de cliquet. ✓
