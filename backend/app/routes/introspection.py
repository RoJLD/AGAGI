from fastapi import APIRouter
from typing import Dict, Any, List

from ..services.kuzu_service import kuzu_service

router = APIRouter()

@router.get("/timeline", response_model=Dict[str, Any])
def get_timeline():
    """Retrieve the evolutionary tree from KuzuDB"""
    return kuzu_service.get_timeline()

@router.get("/introspection/{agent_id}", response_model=List[Dict[str, Any]])
def get_cognitive_snapshots(agent_id: str):
    """Retrieve cognitive state timeline for a specific agent"""
    return kuzu_service.get_cognitive_snapshots(agent_id)
