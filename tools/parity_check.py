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
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Parity check narration EDR <-> frontend (étape 1)")
    ap.add_argument("--repo", default=None, help="racine du repo (défaut : auto)")
    ap.add_argument("--staged", action="store_true", help="classer le diff stagé et n'agir que si EXPERIENCE")
    ap.add_argument("--warn", action="store_true", help="mode non bloquant (défaut) — explicite pour le hook")
    ap.add_argument("--strict", action="store_true", help="exit 1 si invariant dur violé (CI)")
    ap.add_argument("--recent", type=int, default=10, help="fenêtre des EDR récents à couvrir")
    args = ap.parse_args(argv)

    repo = find_repo_root(args.repo)
    print(f"[repo] {repo}")

    if args.staged:
        cls = classify(changed_files(repo, staged=True))
        print(f"[classe] diff stagé = {cls}")
        if cls != "EXPERIENCE":
            print("[parity] non-EXPERIENCE -> checks narration ignorés (OK).")
            return 0

    lines, issues = build_report(repo, args.recent)
    print("=== Parité narration (docs/EDR -> edr_findings.json -> FIL_CONDUCTEUR) ===")
    for ln in lines:
        print("  " + ln)

    fails = [m for lvl, m in issues if lvl == FAIL]
    warns = [m for lvl, m in issues if lvl == WARN]
    print()
    if fails:
        print("INVARIANTS DURS (FAIL) :")
        for m in fails:
            print("  [FAIL] " + m)
    if warns:
        print("DRIFT (WARN) :")
        for m in warns:
            print("  [WARN] " + m)
    if not fails and not warns:
        print("  [OK] aucune désynchronisation détectée.")

    print()
    if args.strict and fails:
        print(f"[strict] {len(fails)} invariant(s) dur(s) violé(s) -> exit 1")
        return 1
    print("[ok] rapport terminé (non bloquant)" if not args.strict else "[ok] aucun invariant dur violé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
