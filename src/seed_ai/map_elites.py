"""MAP-Elites (Quality-Diversity) — NAS Axe A-2. Archive de niches comportementales : chaque cellule
garde l'élite de plus haut life_score de sa niche. Reproduire depuis des niches diverses (vs HoF
mono-objectif) pour échapper au plateau de bruit de fitness. Spec : docs/superpowers/specs/2026-06-24-NAS-A2-MapElites-design.md"""
from typing import Dict, Tuple, List
import numpy as np

SIZE_BIN_LO = 150     # num_nodes en dessous -> bin 0
SIZE_BIN_W = 15       # largeur d'un bin de taille
SIZE_BINS = 8         # nb de bins de taille (clamp)


def descriptor(num_nodes: int, stats: dict) -> Tuple[int, int]:
    """(size_bin, tier) — taille réseau × palier moyens→ends (0 survit /1 forage /2 crafte /3 chasse apex)."""
    size_bin = (int(num_nodes) - SIZE_BIN_LO) // SIZE_BIN_W
    size_bin = max(0, min(size_bin, SIZE_BINS - 1))
    if stats.get("mammoth_kills", 0) > 0:
        tier = 3
    elif stats.get("spears_crafted", 0) > 0:
        tier = 2
    elif stats.get("preys_eaten", 0) > 0:
        tier = 1
    else:
        tier = 0
    return (size_bin, tier)


class MapElitesArchive:
    """cells: (size_bin, tier) -> (score, genome, stats). Garde le max par cellule."""

    def __init__(self):
        self.cells: Dict[Tuple[int, int], Tuple[float, object, dict]] = {}

    def upsert(self, score: float, genome, stats: dict) -> bool:
        cell = descriptor(genome.num_nodes, stats)
        cur = self.cells.get(cell)
        if cur is None or score > cur[0]:
            self.cells[cell] = (float(score), genome, dict(stats))
            return True
        return False

    def elites(self) -> List[Tuple[float, object, dict]]:
        return list(self.cells.values())

    def sample(self, n: int) -> List:
        """n génomes tirés (avec remise) uniformément parmi les élites (RNG global np.random, seedé)."""
        elites = self.elites()
        if not elites:
            return []
        idxs = np.random.randint(0, len(elites), size=n)
        return [elites[int(i)][1] for i in idxs]

    def coverage(self) -> int:
        return len(self.cells)

    def best_score(self) -> float:
        return max((c[0] for c in self.cells.values()), default=0.0)
