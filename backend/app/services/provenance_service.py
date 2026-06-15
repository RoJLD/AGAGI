# backend/app/services/provenance_service.py
"""Ledger de provenance + observabilité (C1).

Lit results/*.json (format Harness.save : seed/commit/config_hash/git_dirty/data) et expose la santé
KuzuDB (lecture seule, via la connexion PARTAGÉE de l'AsyncLogger -> pas de lock concurrent) + les
métriques du logger. Tout dégrade gracieusement sans KuzuDB (jamais de 500). Spec §4-§6.
"""
import json
from pathlib import Path
from typing import Optional


class ProvenanceService:
    def __init__(self, results_dir: Path):
        self.results_dir = Path(results_dir)

    def list_runs(self) -> list[dict]:
        """Tous les runs (results/*.json), triés par mtime décroissant. Ignore les fichiers corrompus."""
        runs = []
        if not self.results_dir.exists():
            return runs
        for p in sorted(self.results_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(d, dict) or "seed" not in d:
                continue
            runs.append({
                "file": p.stem,
                "name": d.get("name"), "seed": d.get("seed"),
                "commit": d.get("commit"), "config_hash": d.get("config_hash"),
                "git_dirty": d.get("git_dirty"),
                "kpis": d.get("data"), "mtime": p.stat().st_mtime,
            })
        return runs

    def get_run(self, file_stem: str) -> Optional[dict]:
        """Détail d'un run (provenance + KPIs) + cross-link KuzuDB best-effort. None si introuvable."""
        p = self.results_dir / f"{file_stem}.json"
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
        d["kuzu"] = self._run_db_link(d.get("seed"), d.get("commit"))
        return d

    def _run_db_link(self, seed, commit) -> dict:
        """Nœud Run + Result liés (best-effort). {linked:false} si DB absente/sans correspondance."""
        db = self._get_db()
        if db is None or seed is None or commit is None:
            return {"linked": False}
        try:
            import kuzu
            conn = kuzu.Connection(db)
            rid = f"run_{seed}_{commit}"
            res = conn.execute(f"MATCH (r:Run {{id: '{rid}'}})<-[:BELONGS_TO_RUN]-(x:Result) RETURN count(x)")
            n = res.get_next()[0] if res.has_next() else 0
            return {"linked": True, "run_id": rid, "result_count": int(n)}
        except Exception:
            return {"linked": False}

    def kuzu_health(self) -> dict:
        """Santé KuzuDB (lecture seule, connexion partagée). reachable/writable/schema/counts."""
        from src.graph_rag.async_logger import logger as async_logger
        db = self._get_db()
        if db is None:
            return {"reachable": False, "writable": False, "schema_present": False, "counts_by_label": {}}
        out = {"reachable": True, "writable": bool(getattr(async_logger, "_running", False)),
               "schema_present": False, "counts_by_label": {}}
        try:
            import kuzu
            conn = kuzu.Connection(db)
            for label in ("Run", "Result", "Article", "LogEvent"):
                try:
                    res = conn.execute(f"MATCH (n:{label}) RETURN count(n)")
                    out["counts_by_label"][label] = int(res.get_next()[0]) if res.has_next() else 0
                except Exception:
                    pass
            out["schema_present"] = len(out["counts_by_label"]) > 0
        except Exception:
            out["reachable"] = False
        return out

    def logger_metrics(self) -> dict:
        from src.graph_rag.async_logger import logger as async_logger
        return async_logger.metrics()

    def _get_db(self):
        try:
            from src.graph_rag.async_logger import logger as async_logger
            return async_logger.get_db()
        except Exception:
            return None
