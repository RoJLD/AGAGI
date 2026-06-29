"""Consolidation des records de décision (SDR/ADR/EDR) en un graphe statique.

Scanne docs/{SDR,ADR,EDR}/, lit le frontmatter YAML, construit le graphe causal
SDR --MOTIVE--> EDR --DECLENCHE--> ADR (+ EDR --TESTE--> SDR), valide sa cohérence
et génère l'état de la roadmap G0->G4. Pur, sans LLM, sans réseau.
Spec : docs/superpowers/specs/2026-06-29-Roadmap-AGI-Gates-design.md (section 4)."""
import os
import re
import sys
import json

import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_LIST_KEYS = ("motivates", "triggers", "tests")
_EDR_NAME = re.compile(r"^(\d{3})_.+\.md$")


def _empty_record(file: str) -> dict:
    return {"id": None, "type": None, "title": "", "status": "open", "gate": None,
            "motivates": [], "triggers": [], "tests": [], "verdict": None,
            "file": file, "linked": False}


def parse_record(path: str) -> dict | None:
    """Lit un record .md. Frontmatter YAML -> record lié. EDR nommé NNN_*.md sans
    frontmatter -> record toléré non lié. Sinon None (fichier non-record)."""
    name = os.path.basename(path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    rec = _empty_record(os.path.relpath(path, _ROOT).replace(os.sep, "/"))

    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            meta = yaml.safe_load(text[3:end]) or {}
            for k, v in meta.items():
                if k in _LIST_KEYS:
                    rec[k] = list(v) if v else []
                elif k in rec:
                    rec[k] = v
            if rec["id"]:
                rec["linked"] = True
                return rec

    m = _EDR_NAME.match(name)
    if m:
        rec["id"] = f"EDR-{int(m.group(1)):03d}"
        rec["type"] = "EDR"
        rec["title"] = name[4:-3].replace("_", " ")
        return rec
    return None


def scan_records(root: str = _ROOT) -> list[dict]:
    """Scanne docs/SDR, docs/ADR, docs/EDR sous root, retourne tous les records
    (triés par id), ignore les fichiers non-record et les dossiers absents."""
    out: list[dict] = []
    for sub in ("docs/SDR", "docs/ADR", "docs/EDR"):
        d = os.path.join(root, sub)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if not name.endswith(".md"):
                continue
            rec = parse_record(os.path.join(d, name))
            if rec is not None:
                out.append(rec)
    out.sort(key=lambda r: r["id"])
    return out


_REL = {"motivates": "MOTIVE", "triggers": "DECLENCHE", "tests": "TESTE"}
_NODE_KEYS = ("id", "type", "title", "status", "gate", "verdict", "linked")


def build_graph(records: list[dict]) -> dict:
    """Construit le graphe causal à partir des records. Retourne
    {"nodes": [...], "edges": [...]}, où les arêtes sont typées selon
    motivates (MOTIVE), triggers (DECLENCHE), tests (TESTE)."""
    nodes = [{k: r[k] for k in _NODE_KEYS} for r in records]
    edges = []
    for r in records:
        for key, rel in _REL.items():
            for target in r[key]:
                edges.append({"from": r["id"], "to": target, "rel": rel})
    return {"nodes": nodes, "edges": edges}


def validate_graph(records: list[dict]) -> list[dict]:
    """Valide la cohérence du graphe de décision.

    Retourne une liste de problèmes. Chaque problème est un dict avec :
    - kind: "broken_link" ou "unsupported_gate"
    - record: id du record concerné
    - detail: description textuelle du problème

    Deux types de problèmes :
    1. broken_link : un id cité dans motivates/triggers/tests n'existe pas
    2. unsupported_gate : une SDR validée sans EDR validé qui la teste

    Liste vide = graphe cohérent.
    """
    by_id = {r["id"]: r for r in records}
    problems: list[dict] = []

    # Vérifier les liens cassés
    for r in records:
        for key in _LIST_KEYS:
            for target in r[key]:
                if target not in by_id:
                    problems.append({"kind": "broken_link", "record": r["id"],
                                     "detail": f"{r['id']}.{key} -> {target} inexistant"})

    # Vérifier les portes validées sans EDR validé qui les teste
    for r in records:
        if r["type"] == "SDR" and r["status"] == "validated":
            supporters = [s for s in records
                          if s["type"] == "EDR" and s["status"] == "validated"
                          and r["id"] in s["tests"]]
            if not supporters:
                problems.append({"kind": "unsupported_gate", "record": r["id"],
                                 "detail": f"{r['id']} validee sans EDR valide qui la teste"})
    return problems


def roadmap_state(graph: dict) -> dict:
    """Stub pour roadmap_state."""
    pass


def main():
    """Stub pour main."""
    pass
