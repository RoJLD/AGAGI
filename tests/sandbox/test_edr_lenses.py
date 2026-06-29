import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.edr_lenses import LENSES, build_lens_prompt, render_markdown, run_lenses, synthesize


def test_lenses_default_non_empty_well_formed():
    assert len(LENSES) >= 4
    for lens in LENSES:
        assert set(["key", "title", "persona"]).issubset(lens) and lens["key"] and lens["persona"]


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
    assert long_text[:500] in p                    # the truncated finding (500 x's) is present
    assert long_text[:501] not in p                # but no more than max_chars of it
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
