"""Consolidation des records de décision (SDR/ADR/EDR) en un graphe statique.

Scanne docs/{SDR,ADR,EDR}/, lit le frontmatter YAML, construit le graphe causal
SDR --MOTIVE--> EDR --DECLENCHE--> ADR (+ EDR --TESTE--> SDR), valide sa cohérence
et génère l'état de la roadmap G0->G4. Pur, sans LLM, sans réseau.
Spec : docs/superpowers/specs/2026-06-29-Roadmap-AGI-Gates-design.md (section 4)."""
import os
import re
import sys
import json
import argparse
from collections import Counter

import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Arêtes causales internes (records de décision) + arêtes-pont vers le SOTA (REF).
# Les ponts émanent des nœuds REF (rediscovered_by/supersedes/adopt_for/grounds) :
# ainsi l'ancrage à la littérature s'ajoute sans toucher les EDR/SDR/ADR existants.
_LIST_KEYS = ("motivates", "triggers", "tests",
              "rediscovered_by", "supersedes", "adopt_for", "grounds")
_EDR_NAME = re.compile(r"^(\d{3})_.+\.md$")


def _empty_record(file: str) -> dict:
    return {"id": None, "type": None, "title": "", "status": "open", "gate": None,
            "motivates": [], "triggers": [], "tests": [],
            "rediscovered_by": [], "supersedes": [], "adopt_for": [], "grounds": [],
            "url": None, "method": None, "lib": None, "maturity": None,
            "requires_ref": False,
            "verdict": None, "file": file, "linked": False}


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


def _prefix_of(rec_id) -> str:
    """Préfixe de territoire d'un id. `EDR-SUB-012` -> 'SUB' ; `EDR-140` -> 'LEGACY' ;
    `SDR-G1` -> 'LEGACY' ; `REF-NEAT-2002` -> 'REF'. Alimente le recensement du cartographe."""
    if not rec_id:
        return "LEGACY"
    parts = str(rec_id).split("-")
    if parts[0] == "REF":
        return "REF"
    if len(parts) >= 3 and parts[1].isalpha():   # EDR-<PREFIX>-<num>
        return parts[1]
    return "LEGACY"


def scan_records(root: str = _ROOT) -> list[dict]:
    """Scanne docs/SDR, docs/ADR, docs/EDR sous root, retourne tous les records
    (triés par id), ignore les fichiers non-record et les dossiers absents."""
    out: list[dict] = []
    for sub in ("docs/SDR", "docs/ADR", "docs/EDR", "docs/REF"):
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


_REL = {"motivates": "MOTIVE", "triggers": "DECLENCHE", "tests": "TESTE",
        "rediscovered_by": "REDECOUVERT_PAR", "supersedes": "DEPASSE",
        "adopt_for": "A_ADOPTER_POUR", "grounds": "FONDE"}
# Clés-pont émanant des nœuds REF (cibles = records ancrés au SOTA).
_BRIDGE_KEYS = ("rediscovered_by", "supersedes", "adopt_for", "grounds")
_NODE_KEYS = ("id", "type", "title", "status", "gate", "verdict", "linked",
              "url", "method", "lib", "maturity")


def build_graph(records: list[dict]) -> dict:
    """Construit le graphe causal à partir des records. Retourne
    {"nodes": [...], "edges": [...]}, où les arêtes sont typées selon
    motivates (MOTIVE), triggers (DECLENCHE), tests (TESTE)."""
    nodes = [{k: r.get(k) for k in _NODE_KEYS} for r in records]
    edges = []
    for r in records:
        for key, rel in _REL.items():
            for target in r.get(key) or []:
                edges.append({"from": r["id"], "to": target, "rel": rel})
    return {"nodes": nodes, "edges": edges}


def validate_graph(records: list[dict]) -> list[dict]:
    """Valide la cohérence du graphe de décision.

    Retourne une liste de problèmes. Chaque problème est un dict avec :
    - kind: "broken_link" ou "unsupported_gate"
    - record: id du record concerné
    - detail: description textuelle du problème

    Trois types de problèmes :
    1. broken_link : un id cité dans motivates/triggers/tests n'existe pas
    2. unsupported_gate : une SDR validée sans EDR validé qui la teste
    3. missing_ref : un record requires_ref=True qu'aucun nœud REF ne couvre
       (procédure anti-réinvention : un nouvel organe doit citer le SOTA)

    Liste vide = graphe cohérent.
    """
    by_id = {r["id"]: r for r in records}
    problems: list[dict] = []

    # Records ancrés au SOTA = cibles d'au moins une arête-pont d'un nœud REF
    ref_anchored: set = set()
    for r in records:
        if r["type"] == "REF":
            for key in _BRIDGE_KEYS:
                ref_anchored.update(r.get(key) or [])

    # Vérifier les liens cassés
    for r in records:
        for key in _LIST_KEYS:
            for target in r.get(key) or []:
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

    # Vérifier l'ancrage SOTA des records qui l'exigent (requires_ref)
    for r in records:
        if r.get("requires_ref") and r["id"] not in ref_anchored:
            problems.append({"kind": "missing_ref", "record": r["id"],
                             "detail": f"{r['id']} requires_ref mais aucun noeud REF ne le couvre"})
    return problems


_GATES = ("G0", "G1", "G2", "G3", "G4")


def roadmap_state(records: list[dict]) -> dict:
    """Mappe les portes G0..G4 à leurs SDR, EDR testeurs, et ADR déclenchés.

    Retourne {gate: {"sdr": id|None, "status": str, "tested_by": [edr_ids], "triggered_adr": [adr_ids]}}
    - sdr : id du record SDR de la porte, ou None si absent
    - status : statut de la SDR, ou "absent" si pas de SDR
    - tested_by : EDR dont la porte == gate OU qui testent la SDR de la porte
    - triggered_adr : ADR cités dans triggers des EDR testeurs (dédupliqués, triés)
    """
    sdr_by_gate = {r["gate"]: r for r in records if r["type"] == "SDR"}
    state: dict = {}

    for g in _GATES:
        sdr = sdr_by_gate.get(g)
        sdr_id = sdr["id"] if sdr else None

        # EDR testeurs : ceux dont gate == g OU qui testent la SDR de g
        tested_by = sorted(
            r["id"] for r in records
            if r["type"] == "EDR" and (r["gate"] == g or (sdr_id and sdr_id in r["tests"]))
        )

        # ADR déclenchés par les EDR testeurs
        triggered = sorted({adr for r in records if r["id"] in tested_by for adr in r["triggers"]})

        state[g] = {
            "sdr": sdr_id,
            "status": sdr["status"] if sdr else "absent",
            "tested_by": tested_by,
            "triggered_adr": triggered
        }

    return state


def main(argv=None) -> int:
    """Consolide les records, construit le graphe, valide la cohérence.

    Écrit results/records_graph.json avec {"graph", "roadmap", "problems"},
    imprime un résumé, retourne 1 si problèmes sinon 0.
    """
    ap = argparse.ArgumentParser(description="Consolide les records SDR/ADR/EDR.")
    ap.add_argument("--root", default=_ROOT)
    args = ap.parse_args(argv)

    records = scan_records(args.root)
    graph = build_graph(records)
    problems = validate_graph(records)
    roadmap = roadmap_state(records)
    prefix_counts = dict(Counter(_prefix_of(r["id"]) for r in records))

    out_dir = os.path.join(args.root, "results")
    os.makedirs(out_dir, exist_ok=True)
    payload = {"graph": graph, "roadmap": roadmap, "problems": problems,
               "prefix_counts": prefix_counts}

    with open(os.path.join(out_dir, "records_graph.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    print(f"records={len(records)} edges={len(graph['edges'])} problemes={len(problems)}")
    for p in problems:
        print(f"  [{p['kind']}] {p['detail']}")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
