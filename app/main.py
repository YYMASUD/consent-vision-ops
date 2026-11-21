"""FastAPI application entrypoint and lifecycle endpoints."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from app.api.cameras import router as cameras_router
from app.api.events import router as events_router

from app.api.consents import router as consents_router
from app.api.persons import router as persons_router
from app.api.zones import router as zones_router
from app.api.governance import router as governance_router

from app.api.reports import router as reports_router
from app.common.events import stream
from app.config.settings import get_settings
from app.db.session import dispose_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose_engine()

app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
for _router in (cameras_router, consents_router, persons_router, zones_router):
app.include_router(governance_router, prefix="/v1")

    app.include_router(_router, prefix="/v1")
app.include_router(events_router, prefix="/v1")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}

@app.get("/ready", tags=["health"])
async def ready():
    return {"status": "ready"}

@app.get("/metrics", response_class=PlainTextResponse, tags=["health"])
async def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.websocket("/v1/live/events")
async def live_events(websocket: WebSocket):
    await websocket.accept()
    try:
        async for event in stream(websocket.query_params.get("topic", "live")):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass

def run() -> None:
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)

