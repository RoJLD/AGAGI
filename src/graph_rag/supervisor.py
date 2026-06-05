"""
Phase 3: LangGraph Supervisor for Macro-NAS orchestration.
Adapts simulation parameters based on KuzuDB analysis and real-time metrics.
Commandement 1: Flexible (Hyper-Configurabilité)
Commandement 2: Modulaire (Memory retrieval + orchestration)
Commandement 5: Transparent (audit trail in KuzuDB)
"""
from typing import TypedDict, Optional, Dict, Any
import json
import logging
import os
from langgraph.graph import StateGraph, END
import kuzu
import numpy as np

from src.graph_rag.adaptive_tuner import AdaptiveTuner, AdaptiveConfig
from src.graph_rag.evaluator import FitnessEvaluator, EvaluatorConfig

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# 1. Typed State (Commandement 2 & 5)
class SupervisorState(TypedDict):
    db_path: str
    latest_score: Optional[float]
    latest_metrics: Optional[Dict[str, float]]
    analysis_insight: Optional[str]
    tweaked_parameters: Optional[Dict[str, Any]]
    robustness_score: Optional[float]
    emergence_score: Optional[float]

# 2. Nodes
def read_kuzu_db(state: SupervisorState) -> Dict[str, Any]:
    """Reads the latest CognitiveState or experiment scores from KuzuDB."""
    logger.info("Node: ReadKuzuDB")
    db_path = state.get("db_path", "data/experiment_graph.db")
    latest_score = 0.5  # default score
    
    try:
        # Commandement 5: Transparent & Auditable (using KuzuDB)
        db = kuzu.Database(db_path, read_only=True)
        conn = kuzu.Connection(db)
        try:
            # Commandement 2: Modulaire (Memory retrieval)
            results = conn.execute("MATCH (c:CognitiveState) RETURN c.score ORDER BY c.timestamp DESC LIMIT 1")
            if results.has_next():
                latest_score = results.get_next()[0]
                logger.info(f"Read latest score from KuzuDB: {latest_score}")
        except RuntimeError as e:
            logger.warning(f"Could not query CognitiveState, using default score: {e}")
    except Exception as e:
        logger.error(f"Failed to connect to KuzuDB at {db_path}: {e}")
        
    return {"latest_score": latest_score}

def analyze_metrics(state: SupervisorState) -> Dict[str, Any]:
    """Analyzes metrics using evaluator and generates parameter tweaks."""
    logger.info("Node: AnalyzeMetrics")
    
    metrics = state.get("latest_metrics", {})
    score = state.get("latest_score", 0.0)
    
    evaluator = FitnessEvaluator(EvaluatorConfig())
    robustness = evaluator.score_robustness(metrics)
    emergence = evaluator.score_emergence(metrics)
    
    logger.info(f"Robustness Score: {robustness:.3f} | Emergence Score: {emergence:.3f}")
    
    # Mock LLM Call / Decision Logic
    insight = f"Score={score:.2f}, Robustness={robustness:.2f}, Emergence={emergence:.2f}."
    
    # Generate parameter tweak based on scores
    tweaked_params = {}
    
    # If robustness is low, increase mutation to explore new solutions
    if robustness < 0.5:
        tweaked_params["mutation_rate"] = 0.05
        insight += " Robustness faible → ↑ mutation."
    else:
        tweaked_params["mutation_rate"] = 0.01
        insight += " Robustness bonne → ↓ mutation."
    
    # If emergence is low, boost social bonuses
    if emergence < 0.5:
        tweaked_params["social_bonus_scale"] = 1.5
        insight += " Émergeance faible → ↑ bonus social."
    else:
        tweaked_params["social_bonus_scale"] = 1.0
        insight += " Émergeance bonne → social normal."
    
    # If energy is unstable, adjust energy rewards
    if metrics.get("energy_stability", 1.0) < 0.5:
        tweaked_params["energy_reward_scale"] = 1.2
        insight += " Énergie instable → ↑ récompenses."
    
    logger.info(f"LLM Insight: {insight}")
    
    return {
        "analysis_insight": insight,
        "tweaked_parameters": tweaked_params,
        "robustness_score": robustness,
        "emergence_score": emergence,
    }

def tweak_environment(state: SupervisorState) -> Dict[str, Any]:
    """Writes the new parameter to a JSON config file and adaptive tuner."""
    logger.info("Node: TweakEnvironment")
    params = state.get("tweaked_parameters", {})
    
    config_path = "config.json"
    
    # Commandement 1: Flexible (Hyper-Configurabilité)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=4)
        
    logger.info(f"Tweaked parameters saved to {config_path}: {params}")
    print(f"✓ Tweaked Parameters: {params}")
    
    return {"tweaked_parameters": params}

def update_adaptive_tuner(state: SupervisorState, tuner: Optional[AdaptiveTuner] = None) -> Dict[str, Any]:
    """Updates the adaptive tuner with new parameters."""
    if tuner is None:
        return {}
    
    logger.info("Node: UpdateAdaptiveTuner")
    params = state.get("tweaked_parameters", {})
    
    tuner.apply_supervisor_recommendation(params)
    logger.info(f"Adaptive tuner updated with: {params}")
    
    return {}

def publish_article(state: SupervisorState) -> Dict[str, Any]:
    """Uses Ollama locally to generate a scientific article based on current insight."""
    logger.info("Node: PublishArticle (Ollama)")
    insight = state.get("analysis_insight", "")
    metrics = state.get("latest_metrics", {})
    db_path = state.get("db_path", "data/experiment_graph.db")
    
    prompt = f"""Tu es le Chercheur IA du projet AGIseed.
Rédige un très court article scientifique (2 paragraphes max) sur l'état de la biosphère.
Voici les données de l'ère actuelle :
{insight}
Métriques : {metrics}
Analyse ce qui se passe et donne une interprétation évolutionniste.
"""

    article_content = "Impossible de générer l'article (Ollama non joignable)."
    try:
        import requests
        response = requests.post("http://127.0.0.1:11434/api/generate", json={
            "model": "mistral", # ou "llama3", selon ce qui est installé
            "prompt": prompt,
            "stream": False
        }, timeout=10)
        if response.status_code == 200:
            article_content = response.json().get("response", article_content)
    except Exception as e:
        logger.warning(f"Ollama error: {e}")

    # Enregistrer dans KuzuDB de manière asynchrone (pour éviter le lock SQLite/Kuzu)
    try:
        import time
        timestamp = int(time.time())
        title = f"Rapport d'Observation #{timestamp}"
        
        article_data = {
            "title": title,
            "content": article_content,
            "timestamp": timestamp
        }
        
        pending_path = "data/pending_article.json"
        with open(pending_path, "w", encoding="utf-8") as f:
            json.dump(article_data, f, ensure_ascii=False)
            
        logger.info(f"Article écrit dans {pending_path} en attente d'insertion par le superviseur principal.")
    except Exception as e:
        logger.error(f"Erreur d'écriture de l'article en attente: {e}")

    return {}

# 3. Build Graph
def build_supervisor_graph(adaptive_tuner: Optional[AdaptiveTuner] = None) -> StateGraph:
    """Constructs the LangGraph StateGraph."""
    workflow = StateGraph(SupervisorState)
    
    workflow.add_node("ReadKuzuDB", read_kuzu_db)
    workflow.add_node("AnalyzeMetrics", analyze_metrics)
    workflow.add_node("TweakEnvironment", tweak_environment)
    workflow.add_node("PublishArticle", publish_article)
    
    if adaptive_tuner:
        workflow.add_node("UpdateAdaptiveTuner", 
                         lambda state: update_adaptive_tuner(state, adaptive_tuner))
    
    workflow.set_entry_point("ReadKuzuDB")
    workflow.add_edge("ReadKuzuDB", "AnalyzeMetrics")
    workflow.add_edge("AnalyzeMetrics", "TweakEnvironment")
    workflow.add_edge("TweakEnvironment", "PublishArticle")
    
    if adaptive_tuner:
        workflow.add_edge("PublishArticle", "UpdateAdaptiveTuner")
        workflow.add_edge("UpdateAdaptiveTuner", END)
    else:
        workflow.add_edge("PublishArticle", END)
    
    return workflow.compile()

# 4. Supervisor Loop Runner
class SupervisorLoop:
    """Orchestre le supervisor en boucle avec les métriques de simulation."""
    
    def __init__(self, adaptive_tuner: Optional[AdaptiveTuner] = None, 
                 interval_seconds: float = 30.0):
        self.app = build_supervisor_graph(adaptive_tuner)
        self.adaptive_tuner = adaptive_tuner
        self.interval = interval_seconds
        self._running = False
        self._iteration = 0
        
    def run_once(self, latest_metrics: Optional[Dict[str, float]] = None):
        """Run a single pass of the supervisor."""
        self._iteration += 1
        logger.info(f"[Supervisor Iteration #{self._iteration}]")
        
        initial_state = SupervisorState(
            db_path="data/experiment_graph.db",
            latest_metrics=latest_metrics or {},
        )
        
        for output in self.app.stream(initial_state):
            for key, value in output.items():
                logger.debug(f"Output from node '{key}': {value}")

if __name__ == "__main__":
    # Test standalone
    app = build_supervisor_graph()
    initial_state = SupervisorState(
        db_path="data/experiment_graph.db",
        latest_metrics={
            "energy_stability": 0.7,
            "genome_diversity": 0.6,
            "social_density": 0.4,
            "avg_energy": 60.0,
        }
    )
    
    for output in app.stream(initial_state):
        for key, value in output.items():
            print(f"Output from node '{key}':")
            print("---")
            print(value)
        print("\n")
