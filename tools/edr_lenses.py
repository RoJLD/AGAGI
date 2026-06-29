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
