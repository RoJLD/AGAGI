# src/seed_ai/harness.py
"""
src/seed_ai/harness.py — Socle de validité D1 (scan global, item Dev D1).

SeedManager : pose le déterminisme aux FRONTIÈRES (boot/ère/répétition) via le RNG global numpy.
Garantit l'APPARIEMENT (deux conditions au même seed partent du même monde initial) sans réécrire
les 168 sites np.random.X. Expose aussi un Generator default_rng pour le code NEUF qui veut
l'isolation par tirage. Détail : docs/superpowers/specs/2026-06-13-D1-RNG-Harness-design.md.
"""
import numpy as np


class SeedManager:
    def __init__(self, base_seed):
        self.base_seed = int(base_seed)
        self.rng = np.random.default_rng(self.base_seed)

    def seed_boundary(self, i=0):
        """Pose np.random.seed(base_seed + i) (déterministe). Renvoie la graine effective."""
        s = self.base_seed + int(i)
        np.random.seed(s)
        return s

    @staticmethod
    def resolve(seed=None):
        """seed fourni -> int(seed) ; None -> graine d'entropie (run rejouable a posteriori)."""
        if seed is not None:
            return int(seed)
        return int(np.random.SeedSequence().entropy % (2 ** 32))
