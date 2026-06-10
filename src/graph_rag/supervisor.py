"""
Phase 3: LangGraph Supervisor for Macro-NAS orchestration.
Adapts simulation parameters based on KuzuDB analysis and real-time metrics.
Commandement 1: Flexible (Hyper-Configurabilité)
Commandement 2: Modulaire (Memory retrieval + orchestration)
Commandement 5: Transparent (audit trail in KuzuDB)
"""
from typing import TypedDict, Optional, Dict, Any, List
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
    db: Optional[Any]
    latest_score: Optional[float]
    score_history: Optional[List[float]]
    latest_metrics: Optional[Dict[str, float]]
    analysis_insight: Optional[str]
    tweaked_parameters: Optional[Dict[str, Any]]
    robustness_score: Optional[float]
    emergence_score: Optional[float]

# 2. Nodes
def read_kuzu_db(state: SupervisorState) -> Dict[str, Any]:
    """Reads the latest CognitiveState or experiment scores from KuzuDB."""
    logger.info("Node: ReadKuzuDB")
    latest_score = 0.5  # default score
    score_history = [0.5]
    
    try:
        # Commandement 5: Transparent & Auditable (using KuzuDB)
        db = state.get("db")
        if db is not None:
            conn = kuzu.Connection(db)
        else:
            db_path = state.get("db_path", "data/kuzu_graph.db")
            db = kuzu.Database(db_path, read_only=True)
            conn = kuzu.Connection(db)
            
        try:
            # Commandement 2: Modulaire (Memory retrieval)
            results = conn.execute("MATCH (c:CognitiveState) RETURN c.score ORDER BY c.timestamp DESC LIMIT 5")
            scores = []
            while results.has_next():
                scores.append(results.get_next()[0])
            if scores:
                latest_score = scores[0]
                score_history = scores
                logger.info(f"Read score history from KuzuDB: {score_history}")
        except RuntimeError as e:
            logger.warning(f"Could not query CognitiveState, using default score: {e}")
    except Exception as e:
        logger.error(f"Failed to connect to KuzuDB: {e}")
        
    return {"latest_score": latest_score, "score_history": score_history}

def analyze_metrics(state: SupervisorState) -> Dict[str, Any]:
    """Analyzes metrics using evaluator and generates parameter tweaks."""
    logger.info("Node: AnalyzeMetrics")
    
    metrics = state.get("latest_metrics", {})
    score = state.get("latest_score", 0.0)
    score_history = state.get("score_history", [score])
    
    evaluator = FitnessEvaluator(EvaluatorConfig())
    robustness = evaluator.score_robustness(metrics)
    emergence = evaluator.score_emergence(metrics)
    
    logger.info(f"Robustness Score: {robustness:.3f} | Emergence Score: {emergence:.3f}")
    
    insight = f"Score={score:.2f}, Robustness={robustness:.2f}, Emergence={emergence:.2f}."

    # 1. Détection réflexive (EDR 036, #9) : décision sur la TENDANCE multi-ères (KuzuDB si
    #    dispo, sinon historique mémoire), pas sur un snapshot. SEAM LLM en place pour le #8.
    from src.graph_rag.reflexive_supervisor import read_recent_scores, compute_trend, reflexive_decision
    db_conn = state.get("db_conn")
    scores = read_recent_scores(db_conn)
    if len(scores) < 3:
        scores = score_history                       # fallback : historique en mémoire
    trend = compute_trend(scores)
    decision = reflexive_decision(trend)
    cognitive_famine = decision["famine"]
    if cognitive_famine:
        insight += f" [FAMINE] {decision['reason']}"
    elif decision["mutation_boost"]:
        insight += f" [DECLIN] {decision['reason']}"
            
    # 2. Trigger active metaprogramming codegen if famine is detected
    codegen_success = False
    if cognitive_famine:
        try:
            from src.metaprog.supervisor_coder import generate_and_test_new_activation
            codegen_success = generate_and_test_new_activation()
            if codegen_success:
                insight += " Métaprogrammation réussie : nouvelle activation 'Swish' installée."
            else:
                insight += " Métaprogrammation échouée : rejetée par la sandbox de sécurité."
        except Exception as e:
            logger.error(f"Failed to run active metaprogramming: {e}")
            insight += f" Métaprogrammation erreur : {e}."
            
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
    print(f"[TUNER] Tweaked Parameters: {params}")
    
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
        
        db = self.adaptive_tuner.db_conn if self.adaptive_tuner else None
        
        initial_state = SupervisorState(
            db_path="data/kuzu_graph.db",
            db=db,
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
