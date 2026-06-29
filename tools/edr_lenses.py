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
        "Voici le finding d'une étude (EDR) sur un substrat neuro-évolutif : des agents dont le "
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
        "testables CONCRÈTES pour ce substrat (dans l'idiome du projet : une variable, "
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
