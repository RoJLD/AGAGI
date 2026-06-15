from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .routes.academy import router as academy_router
from .routes.articles import router as articles_router
from .routes.experiments import router as experiments_router
from .routes.sandbox import router as sandbox_router
from .routes.introspection import router as introspection_router
from .routes.strategy import router as strategy_router
from .routes.sociologist import router as sociologist_router
from .routes.edr import router as edr_router
from .routes.observability import router as observability_router
from .routes.flatland import router as flatland_router
from .services.data_service import ExperimentDataService
from .flatland_server import flatland_server

app = FastAPI(title="AGIseed Dashboard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"
service = ExperimentDataService(RESULTS_DIR)

app.include_router(experiments_router, prefix="/api", tags=["experiments"])
app.include_router(academy_router, prefix="/api", tags=["academy"])
app.include_router(articles_router, prefix="/api", tags=["articles"])
app.include_router(sandbox_router, prefix="/api/sandbox", tags=["Sandbox"])
app.include_router(introspection_router, prefix="/api", tags=["introspection"])
app.include_router(strategy_router, prefix="/api/strategy", tags=["Strategy"])
app.include_router(sociologist_router, prefix="/api/sociologist", tags=["Sociologist"])
app.include_router(edr_router, prefix="/api", tags=["EDR"])
app.include_router(observability_router, prefix="/api", tags=["Observability"])
app.include_router(flatland_router, prefix="/api/flatland", tags=["Flatland"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.on_event("startup")
def startup_event():
    flatland_server.start()

@app.websocket("/ws/flatland")
async def websocket_flatland(websocket: WebSocket):
    await websocket.accept()
    if not flatland_server.running:
        flatland_server.start(loop=asyncio.get_running_loop())
    try:
        while True:
            # Wait for a frame from the queue
            frame = await flatland_server.queue.get()
            await websocket.send_json(frame)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/evolution")
async def websocket_evolution(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        events = service.stream_experiment_updates()
        for event in events:
            await websocket.send_json(event)
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
