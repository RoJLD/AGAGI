#!/usr/bin/env python3
"""Parity check — détecteur de drift entre les expériences (EDR) et leur narration frontend.

ETAPE 1 : checks NARRATION uniquement.
  Chaine de vérité :
    docs/EDR/NNN_*.md  ->  backend/app/edr_findings.json (onglet EDR)  ->  docs/FIL_CONDUCTEUR.md (récit)

Le but n'est PAS de bloquer le travail : par défaut on RAPPORTE le drift (exit 0).
Seuls les INVARIANTS DURS (JSON cassé / findings vide / schéma) peuvent faire échouer, et
uniquement en mode --strict (destiné à la CI).

Modes :
  (défaut)    rapport de parité complet, exit 0
  --staged    classe le diff stagé (dev/experience/doc) ; checks narration seulement si EXPERIENCE
  --strict    exit 1 si un invariant dur est violé (pour la CI)
  --repo PATH racine du repo (défaut : auto-détection)
  --recent N  fenêtre des EDR "récents" dont on exige la couverture (défaut 10)

Sans dépendance externe (stdlib seulement). Sortie ASCII (compatible console Windows).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

WARN = "WARN"
FAIL = "FAIL"

REQUIRED_FINDING_KEYS = {"edr", "title", "subtitle", "type", "series", "insight"}
VALID_TYPES = {"multiline", "bar", "bar_err"}


# --------------------------------------------------------------------------- #
# Localisation du repo
# --------------------------------------------------------------------------- #
def find_repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    here = Path(__file__).resolve().parent
    for d in [Path.cwd().resolve(), here, *here.parents]:
        if (d / "docs" / "EDR").is_dir() or (d / ".git").exists():
            return d
    return Path.cwd().resolve()


# --------------------------------------------------------------------------- #
# Lecture des 3 sources
# --------------------------------------------------------------------------- #
def _edr_num(name: str) -> int | None:
    m = re.match(r"^(\d{3})_", name)
    return int(m.group(1)) if m else None


def scan_edr_docs(repo: Path) -> list[int]:
    d = repo / "docs" / "EDR"
    nums: list[int] = []
    if d.is_dir():
        for p in d.glob("[0-9][0-9][0-9]_*.md"):
            n = _edr_num(p.name)
            if n is not None:
                nums.append(n)
    return sorted(set(nums))


def load_findings(repo: Path):
    """Retourne (data | None, error | None, path)."""
    candidates = [
        repo / "backend" / "app" / "edr_findings.json",
        repo / "results" / "edr_findings.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8")), None, p
            except Exception as exc:  # noqa: BLE001
                return None, f"JSON invalide ({exc})", p
    return None, "fichier introuvable", candidates[0]


def findings_edrs(data: dict) -> list[int]:
    out: list[int] = []
    for f in data.get("findings") or []:
        try:
            out.append(int(f.get("edr")))
        except (TypeError, ValueError):
            pass
    return sorted(set(out))


def validate_findings_schema(data: dict) -> list[str]:
    errs: list[str] = []
    findings = data.get("findings")
    if not isinstance(findings, list) or not findings:
        return ["`findings` absent ou vide"]
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            errs.append(f"finding #{i}: n'est pas un objet")
            continue
        missing = REQUIRED_FINDING_KEYS - set(f)
        if missing:
            errs.append(f"finding #{i} (edr {f.get('edr', '?')}): clés manquantes {sorted(missing)}")
        if f.get("type") not in VALID_TYPES:
            errs.append(f"finding #{i} (edr {f.get('edr', '?')}): type invalide {f.get('type')!r}")
        if f.get("type") == "multiline" and "x" not in f:
            errs.append(f"finding #{i} (edr {f.get('edr', '?')}): type multiline sans champ `x`")
    return errs


def scan_fil_conducteur(repo: Path):
    """Retourne (existe: bool, nums: list[int], h1: str | None)."""
    p = repo / "docs" / "FIL_CONDUCTEUR.md"
    if not p.exists():
        return False, [], None
    text = p.read_text(encoding="utf-8")
    nums = sorted({int(m) for m in re.findall(r"EDR\s+0?(\d{2,3})", text)})
    h1 = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), None)
    return True, nums, h1


def _title_nums(title: str | None) -> list[int]:
    return [int(x) for x in re.findall(r"0?(\d{2,3})", title)] if title else []


# --------------------------------------------------------------------------- #
# Rapport de parité narration
# --------------------------------------------------------------------------- #
def build_report(repo: Path, recent_window: int):
    docs = scan_edr_docs(repo)
    data, ferr, _fpath = load_findings(repo)
    fil_exists, fil_nums, fil_h1 = scan_fil_conducteur(repo)

    lines: list[str] = []
    issues: list[tuple[str, str]] = []

    max_doc = max(docs) if docs else None
    lines.append(f"docs/EDR            : {len(docs)} fichiers, dernier = {max_doc}")

    f_nums: list[int] = []
    if ferr:
        issues.append((FAIL, f"edr_findings.json : {ferr}"))
        lines.append("edr_findings.json   : ILLISIBLE")
    else:
        for e in validate_findings_schema(data):
            issues.append((FAIL, f"edr_findings.json schéma : {e}"))
        f_nums = findings_edrs(data)
        f_title = data.get("title")
        max_f = max(f_nums) if f_nums else None
        lines.append(f"edr_findings.json   : {len(f_nums)} findings, max = {max_f}, EDR = {f_nums}")
        if max_doc is not None and (max_f is None or max_f < max_doc):
            issues.append((WARN, f"dernier EDR documenté ({max_doc}) absent des findings (max findings = {max_f})"))
        tnums = _title_nums(f_title)
        if tnums and f_nums and max(tnums) < max(f_nums):
            issues.append((WARN, f"titre edr_findings annonce {max(tnums)} mais contient {max(f_nums)} -> titre obsolète"))

    if not fil_exists:
        issues.append((WARN, "docs/FIL_CONDUCTEUR.md introuvable"))
        lines.append("FIL_CONDUCTEUR      : ABSENT")
    else:
        max_fil = max(fil_nums) if fil_nums else None
        lines.append(f"FIL_CONDUCTEUR      : corps va jusqu'à EDR {max_fil}, H1 = {fil_h1!r}")
        if max_doc is not None and (max_fil is None or max_fil < max_doc):
            issues.append((WARN, f"récit en retard : corps va à {max_fil}, dernier EDR = {max_doc}"))
        hnums = _title_nums(fil_h1)
        if hnums and max_fil is not None and max(hnums) < max_fil:
            issues.append((WARN, f"titre H1 annonce {max(hnums)} mais le corps va à {max_fil} -> titre obsolète"))

    # Couverture des EDR récents : carte OU mention dans le récit
    if max_doc is not None:
        recent = [n for n in docs if n > max_doc - recent_window]
        covered = set(f_nums) | set(fil_nums)
        uncovered = [n for n in recent if n not in covered]
        if uncovered:
            issues.append((WARN, f"EDR récents sans carte ni mention récit : {uncovered}"))

    return lines, issues


# --------------------------------------------------------------------------- #
# Parité DEV : endpoint backend <-> consommateur frontend (étape 3, heuristique, WARN)
# --------------------------------------------------------------------------- #
_HTTP_DECO = re.compile(r'@router\.(?:get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']')
_WS_DECO = re.compile(r'@app\.websocket\(\s*["\']([^"\']+)["\']')
_INCLUDE = re.compile(r'include_router\(\s*(\w+)\s*,\s*prefix\s*=\s*["\']([^"\']+)["\']')
_IMPORT_ROUTER = re.compile(r'from\s+\.routes\.(\w+)\s+import\s+router\s+as\s+(\w+)')
_FE_CALL = re.compile(r'(?:apiFetch|wsUrl|useWebSocket|fetch)\s*(?:<[^>]*>)?\s*\(\s*[`"\']([^`"\']+)')


def _norm_path(path: str) -> str:
    path = path.split("?")[0]
    path = re.sub(r"\$\{[^}]*\}", "*", path)  # template literal frontend
    path = re.sub(r"\{[^}]*\}", "*", path)  # path param backend
    return path.rstrip("/") or "/"


def scan_backend_routes(repo: Path) -> list[str]:
    """Reconstruit les chemins complets (prefix d'include_router + route du décorateur) + WS."""
    backend = repo / "backend" / "app"
    if not backend.is_dir():
        return []
    main_text = (backend / "main.py").read_text(encoding="utf-8") if (backend / "main.py").exists() else ""
    alias_mod = {alias: mod for mod, alias in _IMPORT_ROUTER.findall(main_text)}
    alias_prefix = dict(_INCLUDE.findall(main_text))
    mod_prefix = {mod: alias_prefix.get(alias, "") for alias, mod in alias_mod.items()}
    paths: list[str] = []
    routes_dir = backend / "routes"
    if routes_dir.is_dir():
        for p in routes_dir.glob("*.py"):
            prefix = mod_prefix.get(p.stem, "")
            for route in _HTTP_DECO.findall(p.read_text(encoding="utf-8")):
                paths.append(prefix + route if route != "/" else (prefix or "/"))
    paths.extend(_WS_DECO.findall(main_text))
    return sorted(set(paths))


def scan_frontend_consumers(repo: Path) -> set[str]:
    """Chemins passés à apiFetch/wsUrl/useWebSocket/fetch dans frontend/src (hors tests)."""
    src = repo / "frontend" / "src"
    out: set[str] = set()
    if not src.is_dir():
        return out
    for p in src.rglob("*.ts*"):
        if p.name.endswith((".test.ts", ".test.tsx", ".d.ts")):
            continue
        for m in _FE_CALL.findall(p.read_text(encoding="utf-8")):
            if m.startswith("/"):
                out.add(_norm_path(m))
    return out


def dev_parity_report(repo: Path):
    """Heuristique : signale les endpoints backend sans consommateur frontend. WARN only."""
    backend = scan_backend_routes(repo)
    frontend = scan_frontend_consumers(repo)
    lines = [f"endpoints backend : {len(backend)} ; chemins consommés (frontend) : {len(frontend)}"]
    issues: list[tuple[str, str]] = []
    uncovered = [b for b in backend if _norm_path(b) not in frontend]
    if uncovered:
        issues.append((WARN, f"endpoints backend sans consommateur frontend (heuristique) : {uncovered}"))
    else:
        lines.append("tous les endpoints backend ont un consommateur frontend (heuristique).")
    return lines, issues


def report_dict(repo: Path, recent_window: int = 10) -> dict:
    """Rapport de parité structuré (JSON) — consommé par l'onglet Santé du frontend."""
    narr_lines, narr_issues = build_report(repo, recent_window)
    dev_lines, dev_issues = dev_parity_report(repo)

    def split(issues: list[tuple[str, str]]) -> dict:
        return {
            "fail": [m for lvl, m in issues if lvl == FAIL],
            "warn": [m for lvl, m in issues if lvl == WARN],
        }

    docs = scan_edr_docs(repo)
    data, _ferr, _ = load_findings(repo)
    f_nums = findings_edrs(data) if isinstance(data, dict) else []
    all_issues = narr_issues + dev_issues
    return {
        "narration": {"lines": narr_lines, **split(narr_issues)},
        "dev_parity": {"lines": dev_lines, **split(dev_issues)},
        "edr_coverage": {
            "docs_total": len(docs),
            "curated": len(f_nums),
            "max_doc": max(docs) if docs else None,
            "max_finding": max(f_nums) if f_nums else None,
        },
        "ok": not any(lvl == FAIL for lvl, _ in all_issues),
        "warn_count": sum(1 for lvl, _ in all_issues if lvl == WARN),
    }


# --------------------------------------------------------------------------- #
# Classification du commit (taxonomie de la cartographie)
# --------------------------------------------------------------------------- #
def changed_files(repo: Path, staged: bool) -> list[tuple[str, str]]:
    cmd = ["git", "-C", str(repo), "diff", "--name-status"] + (["--cached"] if staged else ["HEAD"])
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except Exception:  # noqa: BLE001
        return []
    files: list[tuple[str, str]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append((parts[0], parts[-1]))
    return files


def classify(files: list[tuple[str, str]], commit_msg: str = "") -> str:
    paths = [p for _, p in files]
    added = [p for s, p in files if s.startswith("A")]
    new_edr = any(re.match(r"^docs/EDR/\d{3}_.*\.md$", p) for p in added)
    if new_edr or re.match(r"^EDR\s+\d+", commit_msg.strip()):
        return "EXPERIENCE"
    if paths and all(p.endswith(".md") for p in paths):
        return "DOC"
    return "DEV"


# --------------------------------------------------------------------------- #
# Scaffolder (--fix) : pose un stub de carte pour chaque EDR documenté non curé
# --------------------------------------------------------------------------- #
def _doc_summary(path: Path) -> str:
    """Première ligne de contenu significative d'un doc EDR (pour l'insight du stub)."""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and not s.startswith("---") and not s.startswith(">"):
                return (s[:197] + "...") if len(s) > 200 else s
    except Exception:  # noqa: BLE001
        pass
    return "Résumé à curer."


def scaffold_edr_stubs(repo: Path) -> list[int]:
    """Ajoute un stub de finding pour chaque EDR documenté absent de edr_findings.json. -> EDR ajoutés.

    Le stub (`stub: true`, `series: []`) est valide au schéma et apparaît en section « non curés »
    du frontend (pas comme carte vide) ; le chercheur n'a plus qu'à remplir les séries du graphique.
    """
    data, ferr, fpath = load_findings(repo)
    if ferr or not isinstance(data, dict):
        data = {"title": "Découvertes EDR", "findings": []}
        fpath = repo / "backend" / "app" / "edr_findings.json"
    findings = list(data.get("findings") or [])
    existing = set(findings_edrs(data))
    docs_dir = repo / "docs" / "EDR"
    added: list[int] = []
    if docs_dir.is_dir():
        for p in sorted(docs_dir.glob("[0-9][0-9][0-9]_*.md")):
            m = re.match(r"^(\d{3})_(.+)\.md$", p.name)
            if not m or int(m.group(1)) in existing:
                continue
            num = int(m.group(1))
            findings.append({
                "edr": num,
                "title": m.group(2).replace("_", " "),
                "subtitle": "Carte à curer (stub auto-généré)",
                "type": "bar",
                "series": [],
                "insight": _doc_summary(p),
                "stub": True,
            })
            added.append(num)
    if added:
        data["findings"] = sorted(findings, key=lambda f: f.get("edr", 0))
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Parity check narration EDR <-> frontend (étape 1)")
    ap.add_argument("--repo", default=None, help="racine du repo (défaut : auto)")
    ap.add_argument("--staged", action="store_true", help="classer le diff stagé et n'agir que si EXPERIENCE")
    ap.add_argument("--warn", action="store_true", help="mode non bloquant (défaut) — explicite pour le hook")
    ap.add_argument("--strict", action="store_true", help="exit 1 si invariant dur violé (CI)")
    ap.add_argument("--recent", type=int, default=10, help="fenêtre des EDR récents à couvrir")
    ap.add_argument("--fix", action="store_true", help="scaffolde un stub de carte EDR pour chaque EDR documenté non curé (écrit edr_findings.json)")
    args = ap.parse_args(argv)

    repo = find_repo_root(args.repo)
    print(f"[repo] {repo}")

    if args.fix:
        added = scaffold_edr_stubs(repo)
        if added:
            print(f"[fix] {len(added)} stub(s) de carte EDR ajouté(s) : {added}")
            print("[fix] -> curez les `series` dans edr_findings.json (les stubs s'affichent en section « non curés »).")
        else:
            print("[fix] aucun EDR non curé — rien à scaffolder.")
        return 0

    NARRATION = "Parité narration (docs/EDR -> edr_findings.json -> FIL_CONDUCTEUR)"
    DEVPAR = "Parité dev (route backend <-> fetch frontend, heuristique)"
    reports: list[tuple[str, list[str], list[tuple[str, str]]]] = []

    if args.staged:
        cls = classify(changed_files(repo, staged=True))
        print(f"[classe] diff stagé = {cls}")
        if cls == "EXPERIENCE":
            reports.append((NARRATION, *build_report(repo, args.recent)))
        elif cls == "DEV":
            reports.append((DEVPAR, *dev_parity_report(repo)))
        else:
            print("[parity] commit DOC -> rien à vérifier (OK).")
            return 0
    else:
        reports.append((NARRATION, *build_report(repo, args.recent)))
        reports.append((DEVPAR, *dev_parity_report(repo)))

    all_fails: list[str] = []
    all_warns: list[str] = []
    for title, lines, issues in reports:
        print(f"=== {title} ===")
        for ln in lines:
            print("  " + ln)
        fails = [m for lvl, m in issues if lvl == FAIL]
        warns = [m for lvl, m in issues if lvl == WARN]
        if fails:
            print("  INVARIANTS DURS (FAIL) :")
            for m in fails:
                print("    [FAIL] " + m)
        if warns:
            print("  DRIFT (WARN) :")
            for m in warns:
                print("    [WARN] " + m)
        if not fails and not warns:
            print("  [OK] aucune désynchronisation détectée.")
        all_fails += fails
        all_warns += warns
        print()

    if args.strict and all_fails:
        print(f"[strict] {len(all_fails)} invariant(s) dur(s) violé(s) -> exit 1")
        return 1
    print("[ok] rapport terminé (non bloquant)" if not args.strict else "[ok] aucun invariant dur violé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
