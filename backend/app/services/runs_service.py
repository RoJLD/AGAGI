"""runs_service — lecture seule des runs d'expérience (results/<name>_<seed>.json).

Un *run*       = un fichier {name, seed, commit, data:{kpi: valeur, ...}}.
Une *condition* = un `name` (groupe de seeds = réplicats).
Un *A/B*        = comparer 2 conditions sur une métrique, seeds agrégés (moyenne ± std n-1),
                  verdict via src/seed_ai/eval_harness (Welch t + Cohen d, seuils t>=2.5, d>=0.8).

Aucune écriture, aucune dépendance au moteur d'expérience (n'utilise pas harness.py).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev
from uuid import uuid4

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

    @staticmethod
    def _is_num_list(v: object) -> bool:
        return isinstance(v, list) and len(v) > 0 and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) for x in v
        )

    def list_sweeps(self) -> list[dict]:
        """Runs *sweep* : data.knob (str) + data.levels (liste num) = axe X ;
        chaque autre liste num de même longueur = série Y ; <metric>_std|_spread = y_std."""
        out: list[dict] = []
        for r in self._scan():
            data = r["data"]
            knob, levels = data.get("knob"), data.get("levels")
            if not isinstance(knob, str) or not self._is_num_list(levels):
                continue
            n = len(levels)
            series: dict[str, list[float]] = {}
            y_std: dict[str, list[float]] = {}
            for k, v in data.items():
                if k in ("knob", "levels") or not self._is_num_list(v) or len(v) != n:
                    continue
                if k.endswith("_std") or k.endswith("_spread"):
                    y_std[k.rsplit("_", 1)[0]] = [float(x) for x in v]
                else:
                    series[k] = [float(x) for x in v]
            if not series:
                continue
            out.append({
                "run_id": r["_run_id"], "name": r["name"], "knob": knob,
                "x": [float(x) for x in levels], "series": series,
                "y_std": y_std or None, "seed": r["seed"], "commit": r.get("commit"),
            })
        return out

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
                    "links": {
                        "edr": self._load_links().get(run_id, {}).get("edr", []),
                        "articles": self._articles_for_condition(r["name"]),
                    },
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

    # --- Liens article Sociologue <-> runs (store séparé results/article_links.json) ---
    # Un article compare 2 conditions (baseline/intervention) ; on lie l'article à ces
    # conditions au moment de la publication. Un run est « lié » si son `name` (= condition)
    # fait partie des conditions comparées. N'altère ni les runs ni KuzuDB.
    def _article_links_path(self) -> Path:
        return RESULTS_DIR / "article_links.json"

    def _load_article_links(self) -> dict:
        p = self._article_links_path()
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                return d if isinstance(d, dict) else {}
            except Exception:  # noqa: BLE001
                return {}
        return {}

    def set_article_link(self, article_id: str, conditions: list[str]) -> dict:
        """Associe un article aux conditions comparées (appelé par /sociologist/analyze)."""
        links = self._load_article_links()
        links[article_id] = sorted({c for c in conditions if c})
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self._article_links_path().write_text(
            json.dumps(links, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return {"article_id": article_id, "conditions": links[article_id]}

    def _articles_for_condition(self, name: str) -> list[str]:
        return sorted(aid for aid, conds in self._load_article_links().items() if name in conds)

    def article_links(self) -> dict:
        """Inverse : {run_id: [article_id, ...]} pour afficher les articles liés à chaque run."""
        article_conditions = self._load_article_links()
        cond_articles: dict[str, list[str]] = {}
        for aid, conds in article_conditions.items():
            for c in conds:
                cond_articles.setdefault(c, []).append(aid)
        out: dict[str, list[str]] = {}
        for r in self._scan():
            arts = cond_articles.get(r["name"], [])
            if arts:
                out[r["_run_id"]] = sorted(set(arts))
        return out

    # --- Notes de run (carnet de labo ; store results/run_notes.json) ---
    def _notes_path(self) -> Path:
        return RESULTS_DIR / "run_notes.json"

    def _load_notes(self) -> dict:
        p = self._notes_path()
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                return d if isinstance(d, dict) else {}
            except Exception:  # noqa: BLE001
                return {}
        return {}

    def _save_notes(self, notes: dict) -> None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        self._notes_path().write_text(
            json.dumps(notes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def list_notes(self, run_id: str) -> list[dict]:
        """Notes d'un run, triées par horodatage croissant."""
        return sorted(self._load_notes().get(run_id, []), key=lambda n: n.get("ts", ""))

    def add_note(self, run_id: str, text: str) -> dict | None:
        """Ajoute une note horodatée ; renvoie None si le texte est vide."""
        clean = text.strip()
        if not clean:
            return None
        notes = self._load_notes()
        note = {"id": uuid4().hex[:8], "text": clean, "ts": datetime.now(timezone.utc).isoformat()}
        notes.setdefault(run_id, []).append(note)
        self._save_notes(notes)
        return note

    def delete_note(self, run_id: str, note_id: str) -> bool:
        """Retire une note ; renvoie True si une note a été retirée."""
        notes = self._load_notes()
        items = notes.get(run_id, [])
        kept = [n for n in items if n.get("id") != note_id]
        if len(kept) == len(items):
            return False
        notes[run_id] = kept
        self._save_notes(notes)
        return True

    def all_notes(self) -> list[dict]:
        """Flux agrégé de toutes les notes, run_name résolu, trié par horodatage décroissant."""
        name_by_id = {r["_run_id"]: r["name"] for r in self._scan()}
        out: list[dict] = []
        for run_id, items in self._load_notes().items():
            for n in items:
                out.append(
                    {
                        "run_id": run_id,
                        "run_name": name_by_id.get(run_id, run_id),
                        "id": n.get("id", ""),
                        "text": n.get("text", ""),
                        "ts": n.get("ts", ""),
                    }
                )
        return sorted(out, key=lambda n: n["ts"], reverse=True)

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

    def list_distributions(self, metric: str) -> list[dict]:
        """Valeurs par seed de chaque condition portant `metric` (conditions sans la métrique exclues)."""
        out: list[dict] = []
        for name in sorted({r["name"] for r in self._scan()}):
            vals = self._values(name, metric)
            if vals:
                out.append({"name": name, "vals": vals, "n": len(vals)})
        return out

    _PHASE_KEYS = (
        "brain", "action", "biologie", "mouvement", "net", "n_agents",
        "bio_metab", "bio_terrain", "bio_carry", "bio_autres",
    )

    def list_decompositions(self) -> list[dict]:
        """Runs de decomposition energetique (data.phases avec les 10 cles) — vue Energie."""
        out: list[dict] = []
        for r in self._scan():
            phases = r["data"].get("phases")
            if not isinstance(phases, dict) or any(k not in phases for k in self._PHASE_KEYS):
                continue
            out.append({
                "run_id": r["_run_id"],
                "name": r["name"],
                "seed": r["seed"],
                "commit": r.get("commit"),
                "phases": {k: phases[k] for k in self._PHASE_KEYS},
                "verdict": r["data"].get("verdict", ""),
                "bio_verdict": r["data"].get("bio_verdict", ""),
            })
        return sorted(out, key=lambda d: d["run_id"])

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
