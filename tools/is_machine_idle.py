"""Probe : la machine est-elle LIBRE pour un run biosphère AGAGI (KuzuDB) ?

SAFE si (a) aucun process python exécutant un pilote biosphère AGAGI (détecté par LIGNE DE
COMMANDE, pas juste le nom — ignore Claude Code, VS Code, daemons d'autres projets), ET
(b) le wal KuzuDB est quiescent depuis > IDLE_S (aucune écriture récente = pas de writer actif).

Exit 0 = SAFE (lancer la Tâche B), 1 = BUSY. Usage : python tools/is_machine_idle.py
Env : IDLE_S (défaut 120s).
"""
import os
import sys
import time
import subprocess

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WAL = os.path.join(_ROOT, "data", "kuzu_graph.db.wal")
_IDLE_S = int(os.environ.get("IDLE_S", "120"))

# Marqueurs de pilotes biosphère AGAGI (contention KuzuDB / CPU). Un process python dont la
# ligne de commande contient l'un de ces marqueurs = run projet en cours.
_MARKERS = ("main_biosphere", "main_curriculum", "cross_world_transfer", "curriculum_transfer",
            "run_evolution", "s2_demand", "substrate_world_ab", "substrate_ab_compositional",
            "transfer_ratio", "lewis_survival_sweep", "famine_harshness_probe", "qd_tier_rescue")


def verdict(biosphere_procs, wal_age, idle_s: int = _IDLE_S) -> dict:
    """Décision PURE (testable sans IO). biosphere_procs: list[str] cmdlines ; wal_age: float|None sec."""
    reasons = []
    if biosphere_procs:
        reasons.append(f"{len(biosphere_procs)} pilote(s) biosphère actif(s)")
    if wal_age is not None and wal_age < idle_s:
        reasons.append(f"KuzuDB wal écrit il y a {int(wal_age)}s (< {idle_s}s seuil)")
    return {"safe": not reasons, "reasons": reasons}


def _biosphere_procs():
    """Lignes de commande des process python exécutant un pilote biosphère AGAGI."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | "
             "Select-Object -ExpandProperty CommandLine"],
            capture_output=True, text=True, timeout=25).stdout or ""
    except Exception as e:  # noqa: BLE001 — probe best-effort
        return [f"(vérif process indisponible: {e.__class__.__name__})"]
    hits = []
    for line in out.splitlines():
        low = line.lower()
        if "agagi" in low and any(m in low for m in _MARKERS):
            hits.append(line.strip()[:110])
        elif any(m in low for m in _MARKERS):  # marqueur sans chemin AGAGI explicite : signaler quand même
            hits.append(line.strip()[:110])
    return hits


def _wal_age():
    return (time.time() - os.path.getmtime(_WAL)) if os.path.exists(_WAL) else None


def main():
    procs = _biosphere_procs()
    age = _wal_age()
    v = verdict(procs, age)
    print("SAFE" if v["safe"] else "BUSY")
    for r in v["reasons"]:
        print("  -", r)
    for p in procs:
        print("    ·", p)
    print(f"  (wal âge={'n/a' if age is None else str(int(age)) + 's'}, seuil idle={_IDLE_S}s)")
    return 0 if v["safe"] else 1


if __name__ == "__main__":
    sys.exit(main())
