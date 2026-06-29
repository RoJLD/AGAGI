"""Pré-check de calibration du tool-gate de l'apex (EDR 111).

Vérifie ANALYTIQUEMENT, à partir des constantes de combat RÉELLES, qu'un hp de Mammouth donné
« gate » l'apex : un pack mains-nues meurt de la riposte cumulée avant le kill, mais un pack-lance
(5x plus efficace) survit. C'est un garde-fou anti-théâtre : sans lui, l'A/B serait ininterprétable.

Mécanique modélisée (world_1_stoneage.py:592-700) : un attaquant sur la case du Mammouth livre
`weapon_damage`/tick et absorbe `riposte`/tick ; il survit `floor(agent_hp / riposte)` ticks. Un pack
de P livre au plus `survivable_ticks * P * weapon_damage` avant de mourir, et TUE ssi >= mammoth_hp.

NB : le verdict empirique reste l'A/B (le bras contrôle hp=100 doit reproduire l'apex 108/109).
Ce module choisit/valide le hp de gate AVANT de lancer.
"""
import math
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.environments.config import WorldConfig
from src.environments.stone_economy import BASE_DAMAGE, SPEAR_DAMAGE


def gate_diagnostic(mammoth_hp, pack_size, *, config=None):
    """Le hp donné gate-t-il l'apex pour un pack de `pack_size` ? Renvoie un dict de diagnostic."""
    config = config or WorldConfig()
    agent_hp = float(config.agent.energy_max)            # 100.0
    riposte = float(config.preys["Mammouth"].damage)     # 50.0
    survivable_ticks = math.floor(agent_hp / riposte) if riposte > 0 else 10 ** 9

    def kills(weapon_damage):
        delivered = survivable_ticks * pack_size * weapon_damage
        return delivered >= mammoth_hp

    bare_kills = kills(BASE_DAMAGE)
    spear_kills = kills(SPEAR_DAMAGE)
    # Plus petite taille de pack mains-nues qui re-casse le gate : survivable*P*BASE >= hp.
    per_agent_bare = survivable_ticks * BASE_DAMAGE
    break_pack_size = math.ceil(mammoth_hp / per_agent_bare) if per_agent_bare > 0 else 10 ** 9
    return {
        "mammoth_hp": float(mammoth_hp),
        "pack_size": int(pack_size),
        "survivable_ticks": int(survivable_ticks),
        "bare_kills": bool(bare_kills),
        "spear_kills": bool(spear_kills),
        "gate_valid": bool((not bare_kills) and spear_kills),
        "break_pack_size": int(break_pack_size),
    }


if __name__ == "__main__":
    hp = float(os.environ.get("GATE_HP", "250"))
    for p in (3, 5, 8, 12, 20):
        print(gate_diagnostic(hp, p))
