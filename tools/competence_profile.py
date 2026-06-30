"""tools/competence_profile.py — Profil de competence par tier (P3a audit memoire).

Mesure la competence stoneage ventilee par tier {forage/craft/apex} sur une COHORTE FIXE (benchmark_mode,
EDR 114b) au lieu d'ecraser sur le scalaire life_score. Tranche le verdict gele « mur du craft » :
l'echelle moyens->ends {survie<forage<craft<apex} s'inverse-t-elle au craft (apex atteint PLUS que la
lance -> pathway outil quasi-mort, poids spears de life_score inerte) ? Indices code (competence.py:66 :
apex 21.7% / lance 1.6%) ; ici on le MESURE proprement et on PRE-ENREGISTRE le verdict.

Tooling pur (pas de src/ modifie ; map_elites_compare/competence importes). Usage : python -m tools.competence_profile
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness, SeedManager
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.curriculum.competence import _frac_reaching
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, _seed_genome, _reproduce, run_era_pool, PRESERVE_DIMS


def _tier_fractions(stats_list):
    """Fractions « a deja atteint » par tier (binaire par agent, _frac_reaching seuil >=1)."""
    return {"frac_forage": _frac_reaching(stats_list, "preys_eaten"),
            "frac_craft": _frac_reaching(stats_list, "spears_crafted"),
            "frac_apex": _frac_reaching(stats_list, "mammoth_kills"),
            "n": len(stats_list)}


def _verdict_craft_wall(fracs):
    """INDETERMINE si forage < 0.10 (cohorte trop incompetente) ; CRAFT_WALL CONFIRME si craft < forage
    ET apex >= craft (echelle inversee) ET craft <= 0.10 (quasi-mort) ; sinon ECHELLE MONOTONE."""
    ff, fc, fa = fracs["frac_forage"], fracs["frac_craft"], fracs["frac_apex"]
    if ff < 0.10:
        return "INDETERMINE"
    if fc < ff and fa >= fc and fc <= 0.10:
        return "CRAFT_WALL CONFIRME"
    return "ECHELLE MONOTONE"


def _report_profile(h, per_seed, R, _return):
    """Table ASCII (1 ligne/seed : forage, craft, apex, n) + moyenne + verdict. Save JSON."""
    keys = ("frac_forage", "frac_craft", "frac_apex")
    fracs = {k: float(np.mean([p[k] for p in per_seed])) for k in keys}
    verdict = _verdict_craft_wall(fracs)
    print("\n=== Profil de competence par tier (cohorte fixe) ===")
    print("  seed | forage  craft   apex  |   n")
    for p in per_seed:
        print(f"  {p['seed']:4d} | {p['frac_forage']:6.3f} {p['frac_craft']:6.3f} {p['frac_apex']:6.3f} | {p['n']:4d}")
    print(f"  MOYEN| {fracs['frac_forage']:6.3f} {fracs['frac_craft']:6.3f} {fracs['frac_apex']:6.3f}")
    print("=== VERDICT (mur du craft) ===")
    print(f"  -> {verdict}")
    h.save({"R": R, "verdict": verdict, "mean_fracs": fracs, "per_seed": per_seed})
    if _return:
        return {"verdict": verdict, "mean_fracs": fracs, "per_seed": per_seed, "R": R}
