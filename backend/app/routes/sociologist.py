from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import kuzu
import os

router = APIRouter()

class ArticleResponse(BaseModel):
    id: str
    title: str
    content: str
    timestamp: int

class AnalyzeRequest(BaseModel):
    baseline: str
    intervention: str

@router.post("/analyze")
def trigger_analysis(request: AnalyzeRequest):
    from backend.app.services.kuzu_service import kuzu_service
    from src.graph_rag.sociologist import Sociologist
    
    # Use a local Sociologist DB connection
    soc = Sociologist(db_path=kuzu_service.db_path)
    
    try:
        res = soc.publish_article(request.baseline, request.intervention)
        if res:
            article_id = res[0]
            # Lie l'article aux conditions comparées (traçabilité article <-> runs).
            try:
                from backend.app.services.runs_service import runs_service
                runs_service.set_article_link(article_id, [request.baseline, request.intervention])
            except Exception:  # noqa: BLE001 — le lien ne doit jamais faire échouer la publication
                pass
            return {"status": "success", "article_id": article_id}
        return {"status": "error", "message": "Données insuffisantes ou erreur"}
    finally:
        if hasattr(soc, 'conn'): del soc.conn
        if hasattr(soc, 'db'): del soc.db

@router.get("/articles", response_model=List[ArticleResponse])
def get_articles():
    from backend.app.services.kuzu_service import kuzu_service
    from src.graph_rag.experiment_tracker import ExperimentGraph
    
    tracker = None
    try:
        tracker = ExperimentGraph(kuzu_service.db_path, read_only=True)
        query = "MATCH (a:Article) RETURN a.id, a.title, a.content, a.timestamp ORDER BY a.timestamp DESC"
        res = tracker.conn.execute(query)
        
        articles = []
        while res.has_next():
            row = res.get_next()
            articles.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "timestamp": row[3]
            })
            
        return articles
    except Exception as e:
        print(f"Error fetching articles: {e}")
        return []
    finally:
        if tracker:
            if hasattr(tracker, 'conn'): del tracker.conn
            if hasattr(tracker, 'db'): del tracker.db
            del tracker
