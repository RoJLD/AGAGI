import kuzu
import json
import numpy as np
import logging
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LibrarianAgent")

class LibrarianState(TypedDict):
    db_path: str
    raw_thoughts: List[Dict[str, Any]]
    intent_chains: List[List[Dict[str, Any]]]
    best_chains: List[List[Dict[str, Any]]]
    memory_vectors: Dict[str, List[float]] # agent_id -> vector[5]
    article_summary: str

def extract_thoughts(state: LibrarianState):
    """Extrait toutes les pensées (AGENT_THOUGHT) de KuzuDB."""
    logger.info("📚 Extraction des pensées de la base...")
    from src.graph_rag.async_logger import logger as async_log
    db = async_log.get_db()
    if db is None:
        db = kuzu.Database(state["db_path"])
    conn = kuzu.Connection(db)
    
    thoughts = []
    try:
        results = conn.execute("MATCH (e:LogEvent) WHERE e.type = 'AGENT_THOUGHT' RETURN e.payload, e.timestamp ORDER BY e.timestamp ASC")
        while results.has_next():
            payload_str, ts = results.get_next()
            try:
                thought = json.loads(payload_str)
                thought["timestamp"] = ts
                thoughts.append(thought)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Impossible d'extraire les pensées: {e}")
        
    return {"raw_thoughts": thoughts}

def synthesize_intents(state: LibrarianState):
    """Groupe les pensées par agent pour former des chaînes (Graphes d'Intents)."""
    logger.info("🧠 Synthèse des chaînes d'intents...")
    chains_by_agent = {}
    
    for thought in state["raw_thoughts"]:
        aid = thought["agent_id"]
        if aid not in chains_by_agent:
            chains_by_agent[aid] = []
        chains_by_agent[aid].append(thought)
        
    # Filtrer les séquences qui terminent par une haute valeur (value_pred > 0.8)
    best_chains = []
    for aid, chain in chains_by_agent.items():
        if any(t.get("value_pred", 0.0) > 0.8 for t in chain):
            best_chains.append(chain)
            
    return {"intent_chains": list(chains_by_agent.values()), "best_chains": best_chains}

def weave_graph(state: LibrarianState):
    """Tisse le graphe sémantique dans KuzuDB (Nodes Intent et Rels THEN)."""
    logger.info(f"🕸️ Tissage de {len(state['best_chains'])} chaînes précieuses dans KuzuDB...")
    from src.graph_rag.async_logger import logger as async_log
    db = async_log.get_db()
    if db is None:
        db = kuzu.Database(state["db_path"])
    conn = kuzu.Connection(db)
    
    try:
        conn.execute("CREATE NODE TABLE IF NOT EXISTS Intent (id STRING, action INT64, value DOUBLE, PRIMARY KEY (id))")
        conn.execute("CREATE REL TABLE IF NOT EXISTS THEN (FROM Intent TO Intent, weight DOUBLE)")
    except Exception:
        pass # Tables existent déjà
        
    import uuid
    for chain in state["best_chains"]:
        prev_id = None
        for thought in chain:
            intent_id = f"intent_{uuid.uuid4().hex[:8]}"
            action = thought.get("action", -1)
            val = thought.get("value_pred", 0.0)
            
            try:
                conn.execute(f"CREATE (i:Intent {{id: '{intent_id}', action: {action}, value: {val}}})")
                if prev_id:
                    try:
                        conn.execute("CREATE REL TABLE IF NOT EXISTS LEADS_TO (FROM Intent TO Intent)")
                    except Exception:
                        pass
                    conn.execute(f"MATCH (a:Intent {{id: '{prev_id}'}}) WITH a MATCH (b:Intent {{id: '{intent_id}'}}) CREATE (a)-[:LEADS_TO]->(b)")
            except Exception as e:
                logger.error(f"Erreur d'insertion de graphe: {e}")
            prev_id = intent_id

    return {}

def generate_memory_vectors(state: LibrarianState):
    """Génère les vecteurs 5D de rappel mémoire (in_mem) pour chaque agent."""
    logger.info("🔮 Génération des vecteurs in_mem (5D) pour demain...")
    mem_vectors = {}
    
    for chain in state["best_chains"]:
        if not chain: continue
        aid = chain[0]["agent_id"]
        
        # Exemple basique: le vecteur encode la signature de l'action qui a rapporté la valeur max
        best_thought = max(chain, key=lambda t: t.get("value_pred", 0.0))
        action = best_thought.get("action", 0)
        
        # Encodage trivial sur 5 dimensions (Mock pour la V16)
        vec = [0.0] * 5
        vec[action % 5] = 1.0
        vec[4] = best_thought.get("value_pred", 0.0)
        
        mem_vectors[aid] = vec
        
    return {"memory_vectors": mem_vectors}

def write_article(state: LibrarianState):
    """Commandement 16 : Rédige un Article scientifique et le persiste dans KuzuDB."""
    import datetime
    import uuid
    
    chains = state["intent_chains"]
    best = state["best_chains"]
    mem_vecs = state["memory_vectors"]
    
    if not chains:
        return {"article_summary": "Aucune donnée suffisante pour rédiger un article."}

    # Statistiques brutes
    n_agents = len(chains)
    n_thoughts = sum(len(c) for c in chains)
    n_best = len(best)
    
    # Action la plus mémorisée
    all_actions = [t.get("action", -1) for c in chains for t in c]
    if all_actions:
        from collections import Counter
        dominant_action = Counter(all_actions).most_common(1)[0]
    else:
        dominant_action = (-1, 0)
        
    # Valeur prédite max
    all_vals = [t.get("value_pred", 0.0) for c in chains for t in c]
    max_val = max(all_vals) if all_vals else 0.0
    mean_val = float(np.mean(all_vals)) if all_vals else 0.0
    
    action_names = {0: "Nord", 1: "Sud", 2: "Est", 3: "Ouest", 4: "Haut", 5: "Bas", 6: "Repos", 7: "Attaque"}
    dom_name = action_names.get(dominant_action[0], f"Action#{dominant_action[0]}")
    
    title = f"Ère N — Émergence Comportementale : Dominance de '{dom_name}'"
    content = (
        f"**Observations :** {n_agents} agents ont émis {n_thoughts} pensées conscientes (do_memorize). "
        f"{n_best} chaînes d'intent de haute valeur ont été cristallisées dans le Graphe Sémantique. "
        f"L'action dominante dans la mémoire collective est '{dom_name}' ({dominant_action[1]} occurrences). "
        f"**Valeur Prédite :** Max={max_val:.3f}, Moyenne={mean_val:.3f}. "
        f"**Révélations injectées :** {len(mem_vecs)} vecteurs in_mem transmis aux survivants pour la prochaine ère. "
        f"**Hypothèse :** Si la valeur prédite moyenne augmente entre les ères, "
        f"cela indique que les agents apprennent à calibrer leur World Model interne."
    )
    
    article_id = f"article_{uuid.uuid4().hex[:8]}"
    date_str = datetime.datetime.now().isoformat()
    
    # Persister dans KuzuDB
    try:
        from src.graph_rag.async_logger import logger as async_log
        db = async_log.get_db()
        if db is None:
            db = kuzu.Database(state["db_path"])
        conn = kuzu.Connection(db)
        safe_title = title.replace("'", "`")
        safe_content = content.replace("'", "`")
        conn.execute(
            f"MERGE (a:Article {{id: '{article_id}'}}) "
            f"SET a.title = '{safe_title}', a.content = '{safe_content}', a.date = '{date_str}'"
        )
        logger.info(f"📰 Article publié : '{title}'")
    except Exception as e:
        logger.error(f"Erreur lors de la publication de l'article: {e}")
    
    return {"article_summary": title}

def build_librarian_graph():
    builder = StateGraph(LibrarianState)
    builder.add_node("extract", extract_thoughts)
    builder.add_node("synthesize", synthesize_intents)
    builder.add_node("weave", weave_graph)
    builder.add_node("vectorize", generate_memory_vectors)
    builder.add_node("publish", write_article)
    
    builder.add_edge(START, "extract")
    builder.add_edge("extract", "synthesize")
    builder.add_edge("synthesize", "weave")
    builder.add_edge("weave", "vectorize")
    builder.add_edge("vectorize", "publish")
    builder.add_edge("publish", END)
    
    return builder.compile()

if __name__ == "__main__":
    librarian = build_librarian_graph()
    initial_state = {
        "db_path": "data/kuzu_graph.db",
        "raw_thoughts": [],
        "intent_chains": [],
        "best_chains": [],
        "memory_vectors": {},
        "article_summary": ""
    }
    
    print("\n--- 🌙 Début de la Nuit : Le Bibliothécaire se réveille ---")
    final_state = librarian.invoke(initial_state)
    print("--- ☀️ Fin de la Nuit ---")
    print(f"Vecteurs Mémoire Prêts : {len(final_state['memory_vectors'])}")
    print(f"📰 Article : {final_state['article_summary']}")
