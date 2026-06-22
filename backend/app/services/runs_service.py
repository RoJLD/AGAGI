"""runs_service — lecture seule des runs d'expérience (results/<name>_<seed>.json).

Un *run*       = un fichier {name, seed, commit, data:{kpi: valeur, ...}}.
Une *condition* = un `name` (groupe de seeds = réplicats).
Un *A/B*        = comparer 2 conditions sur une métrique, seeds agrégés (moyenne ± std n-1),
                  verdict via src/seed_ai/eval_harness (Welch t + Cohen d, seuils t>=2.5, d>=0.8).

Aucune écriture, aucune dépendance au moteur d'expérience (n'utilise pas harness.py).
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, stdev

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = PROJECT_ROOT / "results"

T_THRESH = 2.5
D_THRESH = 0.8


def _is_run(d: object) -> bool:
    return isinstance(d, dict) and "name" in d and "seed" in d and isinstance(d.get("data"), dict)


def _welch(a: dict, b: dict) -> tuple[float, float]:
    """Welch t + Cohen d. Tente eval_harness (source unique) ; sinon repli identique."""
    try:
        from src.seed_ai.eval_harness import welch as _w  # noqa: WPS433

        return _w(a, b)
    except Exception:  # noqa: BLE001
        ma, sa, na = a["mean"], a["std"], a["n"]
        mb, sb, nb = b["mean"], b["std"], b["n"]
        se = ((sa ** 2) / max(na, 1) + (sb ** 2) / max(nb, 1)) ** 0.5
        t = (ma - mb) / se if se > 1e-12 else 0.0
        pooled = (((sa ** 2) + (sb ** 2)) / 2.0) ** 0.5
        d = (ma - mb) / pooled if pooled > 1e-12 else 0.0
        return t, d


class RunsService:
    def _scan(self) -> list[dict]:
        runs: list[dict] = []
        if not RESULTS_DIR.exists():
            return runs
        for path in RESULTS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            if _is_run(data):
                data["_run_id"] = f"{data['name']}_{data['seed']}"
                runs.append(data)
        return runs

    @staticmethod
    def _numeric_metrics(data: dict) -> list[str]:
        return sorted(k for k, v in data.items() if isinstance(v, (int, float)) and not isinstance(v, bool))

    def list_runs(self) -> list[dict]:
        return [
            {
                "run_id": r["_run_id"],
                "name": r["name"],
                "seed": r["seed"],
                "commit": r.get("commit"),
                "metrics": self._numeric_metrics(r["data"]),
            }
            for r in sorted(self._scan(), key=lambda r: (r["name"], r["seed"]))
        ]

    def get_run(self, run_id: str) -> dict | None:
        for r in self._scan():
            if r["_run_id"] == run_id:
                return {
                    "run_id": run_id,
                    "name": r["name"],
                    "seed": r["seed"],
                    "commit": r.get("commit"),
                    "data": r["data"],
                    "links": {"edr": self._load_links().get(run_id, {}).get("edr", [])},
                }
        return None

    # --- Liens run <-> EDR (store séparé results/run_links.json ; n'altère pas les fichiers de run) ---
    def _links_path(self) -> Path:
        return RESULTS_DIR / "run_links.json"

    def _load_links(self) -> dict:
        p = self._links_path()
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                return d if isinstance(d, dict) else {}
            except Exception:  # noqa: BLE001
                return {}
        return {}

    def set_run_edr_links(self, run_id: str, edr: list[int]) -> dict:
        links = self._load_links()
        entry = links.setdefault(run_id, {})
        entry["edr"] = sorted({int(e) for e in edr})
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self._links_path().write_text(json.dumps(links, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return {"run_id": run_id, "edr": entry["edr"]}

    def edr_links(self) -> dict:
        """Inverse : {edr: [run_id, ...]} pour les badges « runs liés » du dashboard EDR."""
        out: dict[int, list[str]] = {}
        for run_id, entry in self._load_links().items():
            for e in entry.get("edr", []):
                out.setdefault(int(e), []).append(run_id)
        return {str(k): sorted(v) for k, v in sorted(out.items())}

    def list_conditions(self) -> list[dict]:
        groups: dict[str, dict] = {}
        for r in self._scan():
            g = groups.setdefault(r["name"], {"name": r["name"], "seeds": [], "metrics": set()})
            g["seeds"].append(r["seed"])
            g["metrics"].update(self._numeric_metrics(r["data"]))
        return [
            {"name": g["name"], "n_seeds": len(g["seeds"]), "seeds": sorted(g["seeds"]), "metrics": sorted(g["metrics"])}
            for g in sorted(groups.values(), key=lambda x: x["name"])
        ]

    def _values(self, name: str, metric: str) -> list[float]:
        out: list[float] = []
        for r in self._scan():
            if r["name"] == name:
                v = r["data"].get(metric)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    out.append(float(v))
        return out

    @staticmethod
    def _agg(name: str, vals: list[float]) -> dict:
        return {
            "name": name,
            "mean": mean(vals),
            "std": stdev(vals) if len(vals) > 1 else 0.0,
            "vals": vals,
            "n": len(vals),
        }

    def compare(self, name_a: str, name_b: str, metric: str) -> dict | None:
        va, vb = self._values(name_a, metric), self._values(name_b, metric)
        if not va or not vb:
            return None
        ga, gb = self._agg(name_a, va), self._agg(name_b, vb)
        t, d = _welch(ga, gb)
        significant = abs(t) >= T_THRESH and abs(d) >= D_THRESH
        winner = (name_a if ga["mean"] > gb["mean"] else name_b) if significant else None
        underpowered = ga["n"] < 4 or gb["n"] < 4
        if significant:
            verdict_label, detail = "SIGNIFICATIF", f"effet large et fiable (t={t:.2f}, d={d:.2f})"
        elif underpowered:
            verdict_label, detail = "SOUS-PUISSANCE", f"n insuffisant (n_a={ga['n']}, n_b={gb['n']}) — viser R>=4"
        else:
            verdict_label, detail = "NON SIGNIFICATIF", f"bruit (t={t:.2f}, d={d:.2f})"
        return {
            "metric": metric,
            "a": ga,
            "b": gb,
            "t": round(t, 4),
            "d": round(d, 4),
            "significant": significant,
            "winner": winner,
            "underpowered": underpowered,
            "verdict_label": verdict_label,
            "verdict_detail": detail,
            "t_thresh": T_THRESH,
            "d_thresh": D_THRESH,
        }


runs_service = RunsService()
