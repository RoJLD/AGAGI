"""
Carte de rétention — mesure de l'oubli catastrophique (cf. docs/EDR/009 §2).

Après qu'un cerveau a gradué le monde N puis poussé jusqu'au monde N+k, on le
re-teste sur le monde N : combien de compétence reste-t-il ? La carte est une
matrice triangulaire R[i][j] :

    R[i][j] = compétence d'un cerveau ayant atteint le stade j (champions[j]),
              re-testé sur le monde i   (défini pour i <= j).

  - Diagonale  R[i][i] : maîtrise du monde i au moment de sa graduation.
  - Sous-diag. R[i][j>i] : ce qu'il reste du monde i après être allé plus loin.
  - forgetting_i = R[i][i] - R[i][dernier stade]  (>0 oubli ; <0 transfert rétrograde).

Découplage (comme le runner) : la rétention ne connaît ni les worlds ni KuzuDB.
Elle appelle le `run_era_fn` injecté, SANS promouvoir le résultat (c'est une
sonde, pas une progression).
"""
from typing import Callable, List, Dict, Optional

import numpy as np

from src.curriculum.runner import EraResult

RunEraFn = Callable[[str, Optional[str], int], EraResult]


def retention_probe(run_era_fn: RunEraFn, world_type: str,
                    agent_id: Optional[str], keep_memory: bool = False) -> float:
    """Re-teste un cerveau (agent_id) sur un monde et renvoie sa compétence.

    On réutilise run_era_fn tel quel : il instancie le monde, importe le cerveau,
    joue une ère et renvoie la compétence. On ignore simplement le champion
    renvoyé — une sonde ne fait pas progresser le curriculum.
    """
    result = run_era_fn(world_type, agent_id, 1 if keep_memory else 0)
    return result.competence


def build_retention_map(run_era_fn: RunEraFn, ladder: List[str],
                        champions: List[Optional[str]], keep_memory: bool = False) -> np.ndarray:
    """Construit la matrice triangulaire R[i][j] (NaN au-dessus de la diagonale).

    Coût : K(K+1)/2 sondes (une ère chacune). À budgéter pour de vrais runs.
    """
    if len(champions) != len(ladder):
        raise ValueError("champions et ladder doivent avoir la même longueur.")
    K = len(ladder)
    R = np.full((K, K), np.nan, dtype=float)
    for j in range(K):                 # stade développemental atteint
        if champions[j] is None:
            continue
        for i in range(j + 1):         # re-test des mondes 0..j
            R[i, j] = retention_probe(run_era_fn, ladder[i], champions[j], keep_memory)
    return R


def forgetting_from_matrix(R: np.ndarray, ladder: List[str]) -> Dict[str, Dict[str, float]]:
    """Pour chaque monde i : maîtrise, compétence finale, oubli, ratio de rétention.

    forgetting > 0  : oubli (la compétence a baissé en poussant plus loin).
    forgetting ~ 0  : rétention parfaite.
    forgetting < 0  : transfert rétrograde (apprendre plus loin a amélioré ce monde).
    """
    K = len(ladder)
    out: Dict[str, Dict[str, float]] = {}
    for i in range(K):
        mastery = R[i, i]
        if np.isnan(mastery):
            continue
        # Dernière colonne non-NaN de la ligne i (= stade le plus avancé testé).
        valid = [R[i, j] for j in range(i, K) if not np.isnan(R[i, j])]
        final = valid[-1] if valid else mastery
        out[ladder[i]] = {
            "mastery": float(mastery),
            "final": float(final),
            "forgetting": float(mastery - final),
            "retention_ratio": float(final / mastery) if mastery else float("nan"),
        }
    return out


def matrix_to_json(R: np.ndarray) -> List[List[Optional[float]]]:
    """Sérialise la matrice (NaN -> None pour un JSON valide)."""
    return [[None if np.isnan(v) else float(v) for v in row] for row in R]


def summarize_retention(run_era_fn: RunEraFn, ladder: List[str],
                        champions: List[Optional[str]], keep_memory: bool = False) -> Dict:
    """Bout-en-bout : construit la carte et la résume en dict JSON-sérialisable."""
    R = build_retention_map(run_era_fn, ladder, champions, keep_memory)
    forgetting = forgetting_from_matrix(R, ladder)
    valid_forgets = [v["forgetting"] for v in forgetting.values()]
    return {
        "ladder": list(ladder),
        "champions": list(champions),
        "matrix": matrix_to_json(R),
        "forgetting": forgetting,
        "mean_forgetting": float(np.mean(valid_forgets)) if valid_forgets else float("nan"),
    }
