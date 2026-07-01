"""tools/qd_tier_rescue.py — QD sauve-t-il le tier CRAFT mort ? (P3 audit memoire).

Rebranche l'instrument per-type d'EDR 125 (_measure_profile + _tier_fractions) sur les DEUX bras
evolutifs de map_elites_compare : HoF (mono-objectif life_score) vs QD (archive MAP-Elites, niches
diverses). La selection top-5 par life_score DROPPE un genome craft-pur (spears x300 < forager+apex) ;
l'archive QD garde une elite dans la cellule tier=2. Question gelee : QD leve-t-il frac_craft de >=0.10
(=> selection sauve le craft) ou non (=> mur = substrat/atteignabilite, EDR 111) ?

Tooling pur (pas de src/ modifie ; competence_profile/map_elites_compare/map_elites importes).
Usage : python -m tools.qd_tier_rescue
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
from src.seed_ai.map_elites import MapElitesArchive
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, _seed_genome, _reproduce, run_era_pool
from tools.competence_profile import _evolve_champions, _measure_profile, _tier_fractions


def _tier_coverage(archive):
    """Nb de cellules occupees par tier (readout : le craft/apex existe-t-il dans l'archive ?)."""
    tiers = [cell[1] for cell in archive.cells.keys()]
    return {f"cells_tier{t}": sum(1 for x in tiers if x == t) for t in range(4)}


def _verdict_qd_rescue(fracs_hof, fracs_qd):
    """Primaire = frac_craft. CONFIRME si QD leve le craft de >=0.10 ET le sort du plancher (>=0.10) ;
    QD_NUIT si degrade de >=0.10 ; sinon QD_NEUTRE (mur = substrat/atteignabilite, pas selection)."""
    d = fracs_qd["frac_craft"] - fracs_hof["frac_craft"]
    if d >= 0.10 and fracs_qd["frac_craft"] >= 0.10:
        return "QD_RESCUE_CRAFT CONFIRME"
    if d <= -0.10:
        return "QD_NUIT"
    return "QD_NEUTRE"
