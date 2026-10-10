"""
tools/register_arc10_roadmap.py — Enregistre l'Arc 10 (The Foundation Bridge) dans KuzuDB.
Conforme au Commandement 5 (Auditabilité & Lattice Memory).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import datetime
from src.graph_rag.database import KuzuDatabase, DatabaseConfig


def main():
    db_path = str(Path(__file__).resolve().parents[1] / "data" / "kuzudb" / "kuzu.db")
    db = KuzuDatabase(DatabaseConfig(db_path=db_path))

    event_id = f"evt_arc10_roadmap_{int(datetime.datetime.now().timestamp())}"
    msg = (
        "Feuille de route Arc 10 (The Foundation Bridge) enregistrée : "
        "M16 (LLMLatentExtractor), M17 (LLMThoughtBridge Procruste/CKA), "
        "M18 (Continuous Steering & Soft-Prompting Démiurgique), M19 (Lattice KuzuDB & Preuves de Hoare)."
    )
    ts_now = int(datetime.datetime.now().timestamp() * 1000)

    info = db.execute_cypher("CALL table_info('LogEvent') RETURN *")
    cols = [row[1] for row in info]

    props = []
    if "id" in cols: props.append(f"id: '{event_id}'")
    if "event_type" in cols: props.append("event_type: 'ROADMAP_ARC10'")
    if "message" in cols: props.append(f"message: '{msg}'")
    if "timestamp" in cols: props.append(f"timestamp: {ts_now}")
    if "level" in cols: props.append("level: 'INFO'")

    props_str = ", ".join(props)
    try:
        db.execute_cypher(f"CREATE (e:LogEvent {{{props_str}}})")
        print(f"✅ Événement Roadmap Arc 10 '{event_id}' enregistré avec succès dans KuzuDB.")
    except Exception as e:
        print(f"⚠️ Insertion LogEvent: {e}")


if __name__ == "__main__":
    main()
