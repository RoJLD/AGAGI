"""
src/seed_ai/eval_harness.py — Harnais d'évaluation PUISSANT (EDR 052).

EDR 051 : un itérateur (#8) ne vaut que ce que vaut sa mesure — un run sous-puissant CLASSE LE BRUIT.
Ce harnais transforme une mesure bruitée en **verdict honnête** :
  - multi-SEEDS : réplicats indépendants (np.random.seed) -> on échantillonne le bruit ;
  - AGRÉGATION : moyenne ± écart-type (n-1) ;
  - SIGNIFICATION : statistique de Welch + taille d'effet de Cohen -> « réel » vs « bruit ».
Sans dépendance externe (pas de scipy). Réutilisable par toute expérience (NAS, langage, #8…).
"""
import numpy as np


def powered_eval(conditions, run_seed_fn, seeds=(0, 1, 2)):
    """Évalue chaque condition sur plusieurs seeds.

    conditions : dict {nom: config}
    run_seed_fn(config, seed) -> float (la métrique d'UN réplicat ; doit poser np.random.seed)
    -> {nom: {"mean":, "std":, "vals":[...], "n":}}
    """
    out = {}
    for name, cfg in conditions.items():
        vals = [float(run_seed_fn(cfg, s)) for s in seeds]
        a = np.array(vals, dtype=float)
        out[name] = {
            "mean": float(a.mean()),
            "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "vals": vals,
            "n": len(a),
        }
    return out


def welch(a, b):
    """Statistique de Welch (t) + taille d'effet de Cohen (d, écart-type poolé). -> (t, d)."""
    ma, sa, na = a["mean"], a["std"], a["n"]
    mb, sb, nb = b["mean"], b["std"], b["n"]
    se = ((sa ** 2) / max(na, 1) + (sb ** 2) / max(nb, 1)) ** 0.5
    t = (ma - mb) / se if se > 1e-12 else 0.0
    pooled = (((sa ** 2) + (sb ** 2)) / 2.0) ** 0.5
    d = (ma - mb) / pooled if pooled > 1e-12 else 0.0
    return t, d


def verdict(name_a, name_b, results, t_thresh=2.5, d_thresh=0.8):
    """Compare deux conditions. Significatif si |t|>=seuil ET |d|>=seuil (effet large ET fiable)."""
    a, b = results[name_a], results[name_b]
    t, d = welch(a, b)
    sig = abs(t) >= t_thresh and abs(d) >= d_thresh
    winner = (name_a if a["mean"] > b["mean"] else name_b) if sig else None
    summary = (f"{name_a}={a['mean']:.4f}±{a['std']:.4f} vs "
               f"{name_b}={b['mean']:.4f}±{b['std']:.4f} | t={t:.2f} d={d:.2f} -> "
               f"{'SIGNIFICATIF: ' + winner if sig else 'NON significatif (bruit)'}")
    return {"t": t, "d": d, "significant": sig, "winner": winner, "summary": summary}


def rank(results):
    """Classe les conditions par moyenne décroissante. -> [(nom, mean, std), ...].
    Le 1er n'est un vrai gagnant que si verdict(1er, 2e) est significatif (à vérifier par le caller)."""
    return sorted(((n, r["mean"], r["std"]) for n, r in results.items()),
                  key=lambda x: x[1], reverse=True)


def is_robust_winner(results, t_thresh=2.5, d_thresh=0.8):
    """Le meilleur bat-il le 2e de façon SIGNIFICATIVE ? -> (nom|None, verdict|None)."""
    r = rank(results)
    if len(r) < 2:
        return (r[0][0] if r else None), None
    v = verdict(r[0][0], r[1][0], results, t_thresh, d_thresh)
    return (v["winner"], v)
