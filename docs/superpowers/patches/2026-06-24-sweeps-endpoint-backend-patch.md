# Patch backend — endpoint `/api/sweeps` (à appliquer sur `feat/d1-prod-pairing`)

Expose les runs *sweep* (`Harness.save({knob, levels, <metric arrays>, …})`) au frontend. Lecture
seule, aucune dépendance moteur. Contrat aligné sur `frontend/src/types.ts::SweepResult`.

## 1) `backend/app/services/runs_service.py` — ajouter

```python
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
```

## 2) `backend/app/routes/runs.py` — ajouter le modèle + la route

```python
from pydantic import BaseModel

class SweepResult(BaseModel):
    run_id: str
    name: str
    knob: str
    x: list[float]
    series: dict[str, list[float]]
    y_std: dict[str, list[float]] | None = None
    seed: int
    commit: str | None = None

@router.get("/sweeps", response_model=list[SweepResult])
def list_sweeps() -> list[dict]:
    return runs_service.list_sweeps()
```

## 3) `tests/test_backend.py` — ajouter

```python
def test_list_sweeps_extracts_knob_levels_series(tmp_path, monkeypatch) -> None:
    """Un run sweep (knob+levels+series) -> 1 SweepResult ; un run scalaire -> ignoré."""
    import backend.app.services.runs_service as rs_mod
    monkeypatch.setattr(rs_mod, "RESULTS_DIR", tmp_path)
    (tmp_path / "lewis_survival_sweep_42.json").write_text(json.dumps({
        "name": "lewis_survival_sweep", "seed": 42, "commit": "abc1234",
        "data": {"knob": "forage_payoff", "levels": [0.1, 0.2, 0.3],
                 "median_survival": [0.2, 0.5, 0.8], "median_survival_std": [0.05, 0.05, 0.05],
                 "R": 4, "n_eval": 8},
    }), encoding="utf-8")
    (tmp_path / "AND_0.json").write_text(json.dumps({
        "name": "AND", "seed": 0, "data": {"fitness": 0.9},
    }), encoding="utf-8")
    sweeps = rs_mod.runs_service.list_sweeps()
    assert len(sweeps) == 1
    s = sweeps[0]
    assert s["knob"] == "forage_payoff"
    assert s["x"] == [0.1, 0.2, 0.3]
    assert s["series"]["median_survival"] == [0.2, 0.5, 0.8]
    assert s["y_std"]["median_survival"] == [0.05, 0.05, 0.05]
```

## Vérif (sur leur branche)
```
PYTHONPATH=. python -m pytest tests/test_backend.py::test_list_sweeps_extracts_knob_levels_series -q
PYTHONPATH=. python tools/dump_openapi.py && npm --prefix frontend run gen:api   # rafraîchit schema.ts
```
Attendu : test PASS ; le codegen ajoute `SweepResult` à `schema.ts` (la gate de drift CI restera verte une fois committé).

## Note
Le frontend (vue Sweeps) est déjà livré et fonctionne en `Empty` tant que cette route n'existe pas ;
une fois mergée, l'onglet se peuple automatiquement (aucune coordination de timing requise).
