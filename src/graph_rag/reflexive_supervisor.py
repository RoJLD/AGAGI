"""
src/graph_rag/reflexive_supervisor.py — Supervisor RÉFLEXIF (EDR 036, Vague 2 #9).

Remplace l'`analyze_metrics` myope (if/else sur un snapshot : `std<0.02 and mean<0.95`) par une
décision fondée sur la **tendance multi-ères** lue dans KuzuDB. On regarde la *pente* du score sur
plusieurs ères (amélioration / plateau / déclin), pas l'instantané.

SEAM LLM (#8, différé) : `reflexive_decision` est aujourd'hui un heuristique de tendance ; demain,
un vrai nœud LLM lira `trend` + le contexte KuzuDB (ontologie EDR 032/034) et décidera. La structure
est prête — il suffira de remplacer le corps de `reflexive_decision`.
"""
import numpy as np


def read_recent_scores(db_conn, n: int = 12):
    """Historique multi-ères des scores depuis KuzuDB (Result.mean_score), chronologique."""
    if db_conn is None:
        return []
    try:
        r = db_conn.execute(
            f"MATCH (res:Result) RETURN res.mean_score, res.id ORDER BY res.id DESC LIMIT {int(n)}")
        scores = []
        while r.has_next():
            v = r.get_next()[0]
            if v is not None:
                scores.append(float(v))
        return list(reversed(scores))   # du plus ancien au plus récent
    except Exception:
        return []


def compute_trend(scores):
    """Tendance : direction (improving/plateau/declining) + pente (régression linéaire) + stats."""
    scores = [float(s) for s in scores]
    if len(scores) < 3:
        return {"direction": "unknown", "slope": 0.0,
                "mean": float(np.mean(scores)) if scores else 0.0, "std": 0.0, "n": len(scores)}
    x = np.arange(len(scores), dtype=float)
    y = np.array(scores, dtype=float)
    slope = float(np.polyfit(x, y, 1)[0])
    std, mean = float(np.std(y)), float(np.mean(y))
    if slope > 0.005:
        direction = "improving"
    elif slope < -0.005:
        direction = "declining"
    else:
        direction = "plateau"
    return {"direction": direction, "slope": slope, "mean": mean, "std": std, "n": len(scores)}


def reflexive_decision(trend):
    """Décision réflexive fondée sur la TENDANCE multi-ères (pas un snapshot).

    >>> SEAM LLM (#8) <<< : remplacer ce corps heuristique par un nœud LLM qui lit `trend`
    + le contexte (ontologie KuzuDB) et renvoie le même dict de décision.
    """
    direction, mean, slope = trend["direction"], trend["mean"], trend["slope"]
    decision = {"famine": False, "mutation_boost": False, "reason": ""}
    if direction == "plateau" and mean < 0.95:
        decision["famine"] = True
        decision["reason"] = (f"plateau multi-eres (slope={slope:+.4f}, std={trend['std']:.3f}, "
                              f"mean={mean:.2f}) -> famine cognitive")
    elif direction == "declining":
        decision["mutation_boost"] = True
        decision["reason"] = f"declin (slope={slope:+.4f}) -> ↑ exploration"
    else:
        decision["reason"] = f"{direction} (slope={slope:+.4f}) -> rester le cap"
    return decision
