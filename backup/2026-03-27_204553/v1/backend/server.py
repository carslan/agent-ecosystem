"""Agent Ecosystem — FastAPI server with MCP SSE, REST API, and animated dashboard"""
import sys
import asyncio
import json
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Add backend dir to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from config import HOST, PORT, LOG_DIR, APP_DIR
import database as db
from models import (AgentCreate, AgentUpdate, TaskCreate as TaskCreateModel,
                    OfferCreate, RatingCreate)
from mcp_tools import mcp
from agent_runtime import runtime

# ─── Logging ───
LOG_DIR.mkdir(parents=True, exist_ok=True)
today = datetime.now().strftime("%Y-%m-%d")
log_dir = LOG_DIR / today
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"{datetime.now().strftime('%H_%M_%S')}.log"
logger.add(str(log_file), rotation="1 MB", level="INFO")


# ─── Background tasks ───
async def heartbeat_checker():
    while True:
        await asyncio.sleep(config.HEARTBEAT_CHECK_INTERVAL)
        try:
            db.expire_stale_agents(config.HEARTBEAT_TIMEOUT_SECONDS)
        except Exception as e:
            logger.error("Heartbeat checker error: {}", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    logger.info("Agent Ecosystem starting on {}:{}", HOST, PORT)
    hb_task = asyncio.create_task(heartbeat_checker())
    runtime_task = asyncio.create_task(runtime.start())
    yield
    runtime.running = False
    hb_task.cancel()
    runtime_task.cancel()
    logger.info("Agent Ecosystem stopped")


# ─── App ───
app = FastAPI(title="Agent Ecosystem", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Mount MCP SSE
mcp_app = mcp.streamable_http_app()
app.mount("/mcp", mcp_app)


# ─── Dashboard ───
FRONTEND_DIR = APP_DIR / "source_code" / "frontend"

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    return HTMLResponse("<h1>Agent Ecosystem</h1><p>Frontend not found</p>")

@app.get("/favicon.svg")
async def favicon():
    icon = APP_DIR / "public" / "icon.svg"
    if icon.exists():
        return HTMLResponse(icon.read_text(), media_type="image/svg+xml")
    return HTMLResponse("", status_code=404)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-ecosystem"}


# ─── SSE Events Stream ───
@app.get("/api/events/stream")
async def events_stream(request: Request, last_event_id: int = Query(default=0)):
    async def generate():
        last_id = last_event_id
        while True:
            if await request.is_disconnected():
                break
            events = db.events_since(last_id)
            for evt in events:
                data = json.dumps(evt, default=str)
                yield f"id: {evt['id']}\nevent: {evt['event_type']}\ndata: {data}\n\n"
                last_id = evt["id"]
            if not events:
                yield f": keepalive\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ─── Agent REST API ───

@app.post("/api/agents")
async def api_agent_create(body: AgentCreate):
    agent = db.agent_create(name=body.name, description=body.description,
                            capabilities=body.capabilities, domain_tags=body.domain_tags,
                            confidence=body.confidence, endpoint_url=body.endpoint_url)
    return agent

@app.get("/api/agents")
async def api_agent_list(status: str = None, domain: str = None, capability: str = None):
    return db.agent_list(status=status, domain=domain, capability=capability)

@app.get("/api/agents/{agent_id}")
async def api_agent_get(agent_id: str):
    agent = db.agent_get(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent

@app.patch("/api/agents/{agent_id}")
async def api_agent_update(agent_id: str, body: AgentUpdate):
    kwargs = body.model_dump(exclude_none=True)
    agent = db.agent_update(agent_id, **kwargs)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent

@app.delete("/api/agents/{agent_id}")
async def api_agent_delete(agent_id: str):
    ok = db.agent_delete(agent_id)
    if not ok:
        raise HTTPException(404, "Agent not found")
    return {"success": True}

@app.post("/api/agents/{agent_id}/heartbeat")
async def api_agent_heartbeat(agent_id: str):
    ok = db.agent_heartbeat(agent_id)
    if not ok:
        raise HTTPException(404, "Agent not found")
    return {"success": True}


# ─── Discovery ───

@app.get("/api/discover")
async def api_discover(q: str = None, domain: str = None, capability: str = None,
                       min_rating: float = 0.0, limit: int = 10):
    results = []
    if q:
        results = db.agent_search_fts(q, limit=limit)
    else:
        results = db.agent_list(domain=domain, capability=capability)
    if min_rating > 0:
        results = [a for a in results if a.get("rating_avg", 0) >= min_rating]
    results.sort(key=lambda a: (a.get("rating_avg", 0), a.get("total_tasks", 0)), reverse=True)
    return results[:limit]


# ─── Task REST API ───

@app.post("/api/tasks")
async def api_task_create(body: TaskCreateModel):
    task = db.task_create(requester_id=body.requester_id, title=body.title,
                          description=body.description, required_capability=body.required_capability,
                          domain=body.domain, priority=body.priority, input_data=body.input_data,
                          target_agent_id=body.target_agent_id)
    return task

@app.get("/api/tasks")
async def api_task_list(status: str = None, requester_id: str = None,
                        assignee_id: str = None, limit: int = 50):
    return db.task_list(status=status, requester_id=requester_id,
                        assignee_id=assignee_id, limit=limit)

@app.get("/api/tasks/{task_id}")
async def api_task_get(task_id: str):
    task = db.task_get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task

@app.patch("/api/tasks/{task_id}")
async def api_task_update(task_id: str, status: str = None, agent_id: str = None,
                          output_data: dict = None):
    if not status:
        raise HTTPException(400, "Status required")
    task = db.task_update_status(task_id, status, agent_id=agent_id, output_data=output_data)
    if not task:
        raise HTTPException(404, "Task not found")
    return task

@app.get("/api/tasks/{task_id}/offers")
async def api_task_offers(task_id: str):
    return db.offer_list(task_id)

@app.post("/api/tasks/{task_id}/offers")
async def api_task_offer_create(task_id: str, body: OfferCreate):
    return db.offer_create(task_id=task_id, agent_id=body.agent_id,
                           confidence=body.confidence, message=body.message)

@app.patch("/api/tasks/{task_id}/offers/{offer_id}")
async def api_task_offer_accept(task_id: str, offer_id: str):
    offer = db.offer_accept(offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    return offer


# ─── Rating REST API ───

@app.post("/api/tasks/{task_id}/rate")
async def api_task_rate(task_id: str, body: RatingCreate):
    try:
        return db.rating_create(task_id=task_id, rater_id=body.rater_id,
                                score=body.score, feedback=body.feedback)
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.get("/api/ratings")
async def api_ratings(ratee_id: str = None, domain: str = None, limit: int = 50):
    return db.rating_list(ratee_id=ratee_id, domain=domain, limit=limit)


# ─── Leaderboard ───

@app.get("/api/leaderboard")
async def api_leaderboard(domain: str = None, capability: str = None, limit: int = 20):
    return db.leaderboard(domain=domain, capability=capability, limit=limit)

@app.get("/api/leaderboard/domains")
async def api_leaderboard_domains():
    return db.leaderboard_domains()


# ─── Events REST ───

@app.get("/api/events")
async def api_events(limit: int = 50, event_type: str = None):
    return db.events_list(limit=limit, event_type=event_type)


# ─── Stats ───

@app.get("/api/stats")
async def api_stats():
    return db.ecosystem_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=HOST, port=PORT, log_level="info")
