# EDR multi-lentilles — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un CLI `tools/edr_lenses.py` qui interprète un doc EDR fini via N lentilles disciplinaires (`llm_fn`) puis synthétise des hypothèses falsifiables nouvelles, écrites dans un fichier séparé `docs/EDR/lenses/<stem>_lenses.md`.

**Architecture:** Fonctions pures (`LENSES`, `build_lens_prompt`, `render_markdown`) + orchestration (`run_lenses`, `synthesize`) prenant un `llm_fn(prompt)->str` INJECTÉ + CLI (`main`) sélectionnant le backend (`scripted_llm_fn` par défaut, `--live`→`anthropic_llm_fn`, `--local`→`local_llm_fn`). Réutilise `src/metaprog/llm_proposer_fn.py`. Spec : `docs/superpowers/specs/2026-06-25-edr-lenses-design.md`.

**Tech Stack:** Python 3.13, stdlib (argparse, pathlib). Aucune nouvelle dépendance. `llm_fn` maison.

## Global Constraints

- **Défaut sûr sans API** : le CLI utilise `scripted_llm_fn` par défaut ; `--live`/`--local` arment les backends gatés. **Les tests injectent leur propre `llm_fn` stub** (zéro appel réseau en CI).
- **Écrit UNIQUEMENT sous le dossier de sortie** (défaut `docs/EDR/lenses/`) ; **ne mute JAMAIS** le doc EDR canonique ni aucun autre fichier. Tests : passer `out_dir=<tmp>` pour ne rien polluer.
- **Sortie étiquetée spéculative** : le markdown commence par un bandeau « ⚠️ interprétations spéculatives générées par LLM — PISTES, pas des findings ».
- `llm_fn` est TOUJOURS un paramètre injecté de `run_lenses`/`synthesize` (jamais appelé en dur).
- Chaque lentille finit par une section « Hypothèses falsifiables : » (consigne dans le prompt).
- Commits **path-scopés** : `git add tools/edr_lenses.py tests/sandbox/test_edr_lenses.py`. Message terminé par `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 1: Fonctions pures — `LENSES`, `build_lens_prompt`, `render_markdown`

**Files:**
- Create: `tools/edr_lenses.py`
- Test: `tests/sandbox/test_edr_lenses.py`

**Interfaces:**
- Produces:
  - `LENSES: list[dict]` — chaque dict `{"key","title","persona"}` ; défaut non vide (≥4 lentilles).
  - `build_lens_prompt(lens: dict, edr_text: str, results_json: str|None = None, max_chars: int = 6000) -> str`.
  - `render_markdown(edr_name: str, interpretations: list[dict], synthesis: str) -> str` — `interpretations[i] = {"key","title","interpretation"}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sandbox/test_edr_lenses.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.edr_lenses import LENSES, build_lens_prompt, render_markdown


def test_lenses_default_non_empty_well_formed():
    assert len(LENSES) >= 4
    for l in LENSES:
        assert set(["key", "title", "persona"]).issubset(l) and l["key"] and l["persona"]


def test_build_lens_prompt_includes_persona_finding_and_hypotheses_instruction():
    lens = {"key": "neuro", "title": "Neuroscientifique", "persona": "un neuroscientifique"}
    p = build_lens_prompt(lens, "FINDING_MARKER le forage casse", results_json=None)
    assert "un neuroscientifique" in p
    assert "FINDING_MARKER" in p
    assert "falsifiable" in p.lower()              # consigne d'hypothèses testables


def test_build_lens_prompt_truncates_and_includes_json():
    long_text = "x" * 10000
    p = build_lens_prompt({"key": "k", "title": "T", "persona": "p"}, long_text,
                          results_json='{"p_reach": 0.18}', max_chars=500)
    assert p.count("x") <= 500                     # finding tronqué
    assert "p_reach" in p                          # JSON inclus


def test_render_markdown_has_banner_all_lenses_and_synthesis():
    interps = [{"key": "a", "title": "Éthologue", "interpretation": "INTERP_A"},
               {"key": "b", "title": "Neuroscientifique", "interpretation": "INTERP_B"}]
    md = render_markdown("105_Foo", interps, "SYNTHESE_X")
    assert "spéculative" in md.lower()             # bandeau d'avertissement
    assert "105_Foo" in md
    assert "Éthologue" in md and "INTERP_A" in md
    assert "Neuroscientifique" in md and "INTERP_B" in md
    assert "SYNTHESE_X" in md and "Synthèse" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_edr_lenses.py -q`
Expected: FAIL (ModuleNotFoundError: tools.edr_lenses).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/edr_lenses.py
"""tools/edr_lenses.py — Interprète multi-lentilles d'un finding EDR (outillage d'analyse).
Lit un doc EDR fini (+ JSON optionnel), le fait interpréter par N lentilles disciplinaires via un
`llm_fn` injecté, puis synthétise des hypothèses falsifiables nouvelles → fichier SÉPARÉ
docs/EDR/lenses/<stem>_lenses.md (ne mute jamais le doc canonique). Spec :
docs/superpowers/specs/2026-06-25-edr-lenses-design.md
Usage : python tools/edr_lenses.py docs/EDR/NNN.md [results/x.json] [--live|--local] [--lenses a,b]"""
import os
import sys
import argparse
from pathlib import Path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

LENSES = [
    {"key": "ethologue", "title": "Éthologue (comportement animal)",
     "persona": "un éthologue spécialiste du comportement animal (forage, navigation, coopération)"},
    {"key": "bio_evo", "title": "Biologiste évolutionniste",
     "persona": "un biologiste de l'évolution (sélection, fitness, adaptation, contraintes du substrat)"},
    {"key": "neuro", "title": "Neuroscientifique",
     "persona": "un neuroscientifique (connectome, plasticité, circuits de navigation et d'apprentissage)"},
    {"key": "anthropo", "title": "Anthropologue",
     "persona": "un anthropologue (culture, usage d'outils, coopération, émergence du langage)"},
]


def build_lens_prompt(lens, edr_text, results_json=None, max_chars=6000):
    """Prompt d'une lentille : persona + finding (tronqué) + JSON optionnel + consigne hypothèses."""
    parts = [
        f"Tu es {lens['persona']}.",
        "Voici le finding d'une expérience (EDR) sur un substrat neuro-évolutif : des agents dont le "
        "cerveau est un 'connectome' évoluent et apprennent dans un monde simulé (survie, forage, chasse).",
        "--- FINDING ---",
        edr_text[:max_chars],
        "--- FIN FINDING ---",
    ]
    if results_json:
        parts += ["Métriques associées (JSON) :", results_json[:2000]]
    parts += [
        "Interprète ce finding À TRAVERS TA DISCIPLINE (2 à 4 paragraphes, concis et spécifique).",
        "Termine IMPÉRATIVEMENT par une section « Hypothèses falsifiables : » listant 1 à 2 hypothèses "
        "testables CONCRÈTES pour ce substrat (dans l'idiome expérimental du projet : une variable, "
        "un effet attendu mesurable).",
    ]
    return "\n".join(parts)


def render_markdown(edr_name, interpretations, synthesis):
    """Assemble le markdown : bandeau spéculatif + 1 section/lentille + synthèse. Déterministe."""
    lines = [
        f"# Interprétations multi-lentilles — {edr_name}",
        "",
        "> ⚠️ **Interprétations spéculatives générées par LLM — ce sont des PISTES, pas des findings.** "
        "Ne pas confondre avec un résultat mesuré ; à confirmer par expérience.",
        "",
    ]
    for it in interpretations:
        lines += [f"## {it['title']}", "", it["interpretation"], ""]
    lines += ["## Synthèse — convergences & nouvelles pistes", "", synthesis, ""]
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_edr_lenses.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add tools/edr_lenses.py tests/sandbox/test_edr_lenses.py
git commit -m "feat(edr-lenses): fonctions pures LENSES + build_lens_prompt + render_markdown"
```

---

### Task 2: Orchestration — `run_lenses`, `synthesize` (llm_fn injecté)

**Files:**
- Modify: `tools/edr_lenses.py`
- Test: `tests/sandbox/test_edr_lenses.py`

**Interfaces:**
- Consumes: `LENSES`, `build_lens_prompt` (Task 1).
- Produces:
  - `run_lenses(edr_text: str, results_json: str|None, llm_fn, lenses: list[dict]|None = None) -> list[dict]` — renvoie `[{"key","title","interpretation"}]` ; une lentille dont `llm_fn` lève → interprétation = message d'échec capturé (n'avorte pas).
  - `synthesize(interpretations: list[dict], edr_text: str, llm_fn) -> str` — passe finale (convergences + tensions + hypothèses nouvelles) ; capture les exceptions.

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_edr_lenses.py
from tools.edr_lenses import run_lenses, synthesize


def _fake_llm(prompt):
    # déterministe + identifiable : renvoie une marque dérivée du prompt
    return "REP::" + prompt[:40]


def test_run_lenses_one_per_lens_with_content():
    lenses = [{"key": "a", "title": "A", "persona": "persona_A"},
              {"key": "b", "title": "B", "persona": "persona_B"}]
    out = run_lenses("finding", None, _fake_llm, lenses=lenses)
    assert [o["key"] for o in out] == ["a", "b"]
    assert all(o["interpretation"].startswith("REP::") for o in out)
    # chaque interprétation reflète SA lentille (persona dans le prompt échoé)
    assert "persona_A" in out[0]["interpretation"] or "persona_A" in build_lens_prompt(lenses[0], "finding")


def test_run_lenses_captures_lens_failure():
    def boom(prompt):
        raise RuntimeError("api down")
    out = run_lenses("finding", None, boom, lenses=[{"key": "a", "title": "A", "persona": "p"}])
    assert len(out) == 1
    assert "échec" in out[0]["interpretation"].lower() and "api down" in out[0]["interpretation"]


def test_synthesize_receives_all_interps_and_returns_text():
    interps = [{"key": "a", "title": "A", "interpretation": "INT_A"},
               {"key": "b", "title": "B", "interpretation": "INT_B"}]
    captured = {}
    def capture_llm(prompt):
        captured["prompt"] = prompt
        return "SYNTH_OUT"
    out = synthesize(interps, "finding", capture_llm)
    assert out == "SYNTH_OUT"
    assert "INT_A" in captured["prompt"] and "INT_B" in captured["prompt"]   # synthèse voit tout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_edr_lenses.py -q`
Expected: FAIL (ImportError: cannot import name 'run_lenses').

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à tools/edr_lenses.py
def run_lenses(edr_text, results_json, llm_fn, lenses=None):
    """Boucle les lentilles → llm_fn(build_lens_prompt). Une lentille en échec est capturée (n'avorte pas)."""
    lenses = lenses if lenses is not None else LENSES
    out = []
    for lens in lenses:
        try:
            interp = llm_fn(build_lens_prompt(lens, edr_text, results_json))
        except Exception as e:                       # noqa: BLE001 — on isole une lentille défaillante
            interp = f"_(lentille « {lens.get('title', lens.get('key'))} » en échec : {e})_"
        out.append({"key": lens["key"], "title": lens["title"], "interpretation": interp})
    return out


def synthesize(interpretations, edr_text, llm_fn):
    """Passe finale : convergences + tensions + 2-3 hypothèses/expériences EDR nouvelles priorisées."""
    joined = "\n\n".join(f"### {it['title']}\n{it['interpretation']}" for it in interpretations)
    prompt = "\n".join([
        "Voici plusieurs interprétations disciplinaires d'un même finding EDR (substrat neuro-évolutif) :",
        joined,
        "",
        "Synthétise de façon ACTIONNABLE : (a) les CONVERGENCES inter-disciplines ; (b) les TENSIONS ou "
        "désaccords ; (c) 2 à 3 HYPOTHÈSES ou EXPÉRIENCES EDR NOUVELLES, priorisées et FALSIFIABLES, pour "
        "« chercher plus loin » (chacune : une variable, un effet mesurable attendu).",
    ])
    try:
        return llm_fn(prompt)
    except Exception as e:                           # noqa: BLE001
        return f"_(synthèse en échec : {e})_"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_edr_lenses.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add tools/edr_lenses.py tests/sandbox/test_edr_lenses.py
git commit -m "feat(edr-lenses): orchestration run_lenses + synthesize (llm_fn injecte, robuste)"
```

---

### Task 3: CLI `main` — sélection backend + écriture fichier séparé

**Files:**
- Modify: `tools/edr_lenses.py`
- Test: `tests/sandbox/test_edr_lenses.py`

**Interfaces:**
- Consumes: tout ce qui précède + `src/metaprog/llm_proposer_fn.py` (`scripted_llm_fn`, `anthropic_llm_fn`, `local_llm_fn`).
- Produces:
  - `select_llm_fn(live: bool, local: bool) -> callable` — `scripted_llm_fn` par défaut ; `live`→`anthropic_llm_fn()` ; `local`→`local_llm_fn()`.
  - `generate(edr_path: str, results_json_path: str|None, llm_fn, lenses=None, out_dir="docs/EDR/lenses") -> str` — lit, génère, écrit `<out_dir>/<stem>_lenses.md`, renvoie le chemin écrit.
  - `main(argv: list[str]|None = None) -> int`.

- [ ] **Step 1: Write the failing test**

```python
# Ajouter à tests/sandbox/test_edr_lenses.py
import tempfile
from pathlib import Path
from tools.edr_lenses import select_llm_fn, generate, main
from src.metaprog.llm_proposer_fn import scripted_llm_fn


def test_select_llm_fn_default_is_scripted():
    assert select_llm_fn(live=False, local=False) is scripted_llm_fn


def test_generate_writes_separate_file_without_touching_source(tmp_path):
    edr = tmp_path / "077_Demo_Finding.md"
    edr.write_text("# EDR 077\nLe forage casse à l'approche.", encoding="utf-8")
    before = edr.read_text(encoding="utf-8")
    out_dir = tmp_path / "lenses"
    lenses = [{"key": "a", "title": "Éthologue", "persona": "p"}]
    path = generate(str(edr), None, _fake_llm, lenses=lenses, out_dir=str(out_dir))
    assert Path(path).exists()
    assert Path(path).parent == out_dir and path.endswith("077_Demo_Finding_lenses.md")
    md = Path(path).read_text(encoding="utf-8")
    assert "spéculative" in md.lower() and "Éthologue" in md and "Synthèse" in md
    assert edr.read_text(encoding="utf-8") == before     # NE mute PAS la source


def test_main_smoke_scripted_default(tmp_path):
    edr = tmp_path / "099_X.md"
    edr.write_text("# EDR 099\nDrain = biologie.", encoding="utf-8")
    out_dir = tmp_path / "out"
    rc = main([str(edr), "--out-dir", str(out_dir)])     # défaut scripted → zéro API
    assert rc == 0
    assert (out_dir / "099_X_lenses.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_edr_lenses.py -q`
Expected: FAIL (ImportError: cannot import name 'select_llm_fn').

- [ ] **Step 3: Write minimal implementation**

```python
# Ajouter à tools/edr_lenses.py
def select_llm_fn(live=False, local=False):
    """scripted (défaut, sûr) | anthropic (--live, gaté clé) | local (--local). Imports paresseux."""
    from src.metaprog.llm_proposer_fn import scripted_llm_fn
    if live:
        from src.metaprog.llm_proposer_fn import anthropic_llm_fn
        return anthropic_llm_fn()
    if local:
        from src.metaprog.llm_proposer_fn import local_llm_fn
        return local_llm_fn()
    return scripted_llm_fn


def generate(edr_path, results_json_path, llm_fn, lenses=None, out_dir="docs/EDR/lenses"):
    """Lit le doc EDR (+ JSON optionnel), génère interprétations + synthèse, écrit <out_dir>/<stem>_lenses.md."""
    edr_text = Path(edr_path).read_text(encoding="utf-8")
    results_json = Path(results_json_path).read_text(encoding="utf-8") if results_json_path else None
    interps = run_lenses(edr_text, results_json, llm_fn, lenses=lenses)
    synthesis = synthesize(interps, edr_text, llm_fn)
    stem = Path(edr_path).stem
    md = render_markdown(stem, interps, synthesis)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    out_path = out / f"{stem}_lenses.md"
    out_path.write_text(md, encoding="utf-8")
    return str(out_path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Interprétations multi-lentilles d'un finding EDR.")
    ap.add_argument("edr_path", help="chemin du doc EDR (docs/EDR/NNN_*.md)")
    ap.add_argument("results_json", nargs="?", default=None, help="JSON de résultats optionnel")
    ap.add_argument("--live", action="store_true", help="LLM Anthropic réel (gaté ANTHROPIC_API_KEY)")
    ap.add_argument("--local", action="store_true", help="LLM local (LM Studio/Ollama)")
    ap.add_argument("--lenses", default=None, help="clés de lentilles séparées par virgule (sous-ensemble)")
    ap.add_argument("--out-dir", default="docs/EDR/lenses", help="dossier de sortie")
    args = ap.parse_args(argv)
    lenses = None
    if args.lenses:
        keys = {k.strip() for k in args.lenses.split(",") if k.strip()}
        lenses = [l for l in LENSES if l["key"] in keys] or None
    llm_fn = select_llm_fn(live=args.live, local=args.local)
    path = generate(args.edr_path, args.results_json, llm_fn, lenses=lenses, out_dir=args.out_dir)
    print(f"écrit -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/sandbox/test_edr_lenses.py -q`
Expected: PASS (10 passed).

- [ ] **Step 5: Démo réelle (optionnelle, non-CI) — scripted sur un vrai EDR**

Run: `python tools/edr_lenses.py docs/EDR/105_Forage_Bottleneck_Is_Approach_Not_Capture_Champions_Dont_Reach_Prey.md --out-dir /tmp/edr_lenses_demo`
Expected: `écrit -> /tmp/edr_lenses_demo/105_..._lenses.md` (contenu scripted factice — valide le pipeline de bout en bout sans API). Ne pas committer la sortie.

- [ ] **Step 6: Commit**

```bash
git add tools/edr_lenses.py tests/sandbox/test_edr_lenses.py
git commit -m "feat(edr-lenses): CLI main + select_llm_fn + generate (fichier separe, scripted defaut)"
```

---

## Self-Review (auteur)

**Couverture spec :** A `build_lens_prompt`→T1 ; B `LENSES`→T1 ; C `run_lenses`→T2 ; D `synthesize`→T2 ; E `render_markdown`→T1 ; F CLI/`select_llm_fn`/`generate`→T3. Backend scripted défaut + `--live`/`--local`→T3. Sortie fichier séparé + ne mute pas la source→T3 (test dédié). Bandeau spéculatif→T1/T3. Robustesse lentille en échec→T2. **Tout couvert.**

**Types cohérents :** `interpretations[i]={key,title,interpretation}` partout (run_lenses produit, render_markdown/synthesize consomment) ; `llm_fn(prompt)->str` injecté ; `lenses` = `list[{key,title,persona}]`. `generate(...)->str` (chemin). `select_llm_fn(live,local)->callable`.

**Placeholders :** code complet + tests complets, stub `_fake_llm` déterministe, `out_dir=tmp` en test (zéro pollution repo, zéro API). Aucun « TODO ».

**Risque :** `select_llm_fn` importe `src/metaprog/llm_proposer_fn.py` — présent dans `main` (vérifié). `scripted_llm_fn` renvoie du JSON catalogue (factice pour les lentilles) — acceptable : les tests vérifient la STRUCTURE, le fond n'a de sens qu'en `--live`.
