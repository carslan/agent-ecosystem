"""Agent Ecosystem — SQLite database layer"""
import json
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

from loguru import logger
from config import DB_PATH, DATA_DIR, DOMAIN_COLORS
from models import new_id


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    description     TEXT,
    capabilities    TEXT NOT NULL DEFAULT '[]',
    domain_tags     TEXT NOT NULL DEFAULT '[]',
    confidence      TEXT,
    endpoint_url    TEXT,
    mcp_session_id  TEXT,
    status          TEXT DEFAULT 'online' CHECK(status IN ('online','offline','busy')),
    color           TEXT,
    last_heartbeat  TEXT,
    registered_at   TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    metadata        TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id                  TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    description         TEXT,
    requester_id        TEXT NOT NULL REFERENCES agents(id),
    assignee_id         TEXT REFERENCES agents(id),
    required_capability TEXT,
    domain              TEXT,
    status              TEXT DEFAULT 'requested' CHECK(status IN (
        'requested','accepted','rejected','in_progress','delivered','rated','cancelled')),
    priority            TEXT DEFAULT 'medium' CHECK(priority IN ('high','medium','low')),
    input_data          TEXT,
    output_data         TEXT,
    requested_at        TEXT DEFAULT (datetime('now')),
    accepted_at         TEXT,
    started_at          TEXT,
    delivered_at        TEXT,
    rated_at            TEXT,
    parent_task_id      TEXT REFERENCES tasks(id),
    metadata            TEXT
);

CREATE TABLE IF NOT EXISTS ratings (
    id              TEXT PRIMARY KEY,
    task_id         TEXT NOT NULL UNIQUE REFERENCES tasks(id),
    rater_id        TEXT NOT NULL REFERENCES agents(id),
    ratee_id        TEXT NOT NULL REFERENCES agents(id),
    score           REAL NOT NULL CHECK(score >= 1.0 AND score <= 5.0),
    domain          TEXT,
    capability      TEXT,
    feedback        TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_stats (
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    domain          TEXT NOT NULL,
    capability      TEXT DEFAULT '__all__',
    total_tasks     INTEGER DEFAULT 0,
    avg_rating      REAL DEFAULT 0.0,
    total_ratings   INTEGER DEFAULT 0,
    best_rating     REAL DEFAULT 0.0,
    worst_rating    REAL DEFAULT 5.0,
    updated_at      TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (agent_id, domain, capability)
);

CREATE TABLE IF NOT EXISTS task_offers (
    id              TEXT PRIMARY KEY,
    task_id         TEXT NOT NULL REFERENCES tasks(id),
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    confidence      REAL,
    message         TEXT,
    status          TEXT DEFAULT 'pending' CHECK(status IN ('pending','accepted','declined')),
    offered_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(task_id, agent_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    from_agent_id   TEXT NOT NULL REFERENCES agents(id),
    to_agent_id     TEXT NOT NULL REFERENCES agents(id),
    content         TEXT NOT NULL,
    msg_type        TEXT DEFAULT 'direct' CHECK(msg_type IN ('direct','broadcast','system')),
    read            INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS learned_capabilities (
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    capability      TEXT NOT NULL,
    tasks_completed INTEGER DEFAULT 0,
    unlocked_at     TEXT,
    PRIMARY KEY (agent_id, capability)
);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type      TEXT NOT NULL,
    agent_id        TEXT,
    task_id         TEXT,
    payload         TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_requester ON tasks(requester_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX IF NOT EXISTS idx_ratings_ratee ON ratings(ratee_id);
CREATE INDEX IF NOT EXISTS idx_ratings_domain ON ratings(domain);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_task_offers_task ON task_offers(task_id);
CREATE INDEX IF NOT EXISTS idx_messages_to ON messages(to_agent_id);
CREATE INDEX IF NOT EXISTS idx_messages_from ON messages(from_agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_learned_caps ON learned_capabilities(agent_id);

CREATE VIRTUAL TABLE IF NOT EXISTS agents_fts USING fts5(
    name, description, capabilities, domain_tags,
    content=agents, tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS agents_ai AFTER INSERT ON agents BEGIN
    INSERT INTO agents_fts(rowid, name, description, capabilities, domain_tags)
    VALUES (new.rowid, new.name, new.description, new.capabilities, new.domain_tags);
END;

CREATE TRIGGER IF NOT EXISTS agents_au AFTER UPDATE ON agents BEGIN
    DELETE FROM agents_fts WHERE rowid = old.rowid;
    INSERT INTO agents_fts(rowid, name, description, capabilities, domain_tags)
    VALUES (new.rowid, new.name, new.description, new.capabilities, new.domain_tags);
END;

CREATE TRIGGER IF NOT EXISTS agents_ad AFTER DELETE ON agents BEGIN
    DELETE FROM agents_fts WHERE rowid = old.rowid;
END;
"""


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    logger.info("Database initialized at {}", DB_PATH)


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _assign_color(domain_tags: list[str]) -> str:
    if domain_tags:
        idx = hash(domain_tags[0]) % len(DOMAIN_COLORS)
        return DOMAIN_COLORS[idx]
    return DOMAIN_COLORS[0]


# ─── Agent CRUD ───

def agent_create(name: str, description: str = None, capabilities: list = None,
                 domain_tags: list = None, confidence: dict = None,
                 endpoint_url: str = None) -> dict:
    agent_id = new_id()
    caps = capabilities or []
    tags = domain_tags or []
    color = _assign_color(tags)
    ts = now_iso()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO agents (id, name, description, capabilities, domain_tags,
               confidence, endpoint_url, color, last_heartbeat, registered_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, name, description, json.dumps(caps), json.dumps(tags),
             json.dumps(confidence) if confidence else None,
             endpoint_url, color, ts, ts, ts)
        )
    emit_event("agent_registered", agent_id=agent_id,
               payload={"name": name, "capabilities": caps, "domain_tags": tags, "color": color})
    return agent_get(agent_id)


def agent_get(agent_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
        if not row:
            return None
        return _agent_row_to_dict(row)


def agent_list(status: str = None, domain: str = None, capability: str = None) -> list[dict]:
    query = "SELECT * FROM agents WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if domain:
        query += " AND domain_tags LIKE ?"
        params.append(f'%"{domain}"%')
    if capability:
        query += " AND capabilities LIKE ?"
        params.append(f'%"{capability}"%')
    query += " ORDER BY registered_at DESC"
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_agent_row_to_dict(r) for r in rows]


def agent_update(agent_id: str, **kwargs) -> dict | None:
    sets = []
    params = []
    for key in ("name", "description", "endpoint_url", "status", "mcp_session_id"):
        if key in kwargs and kwargs[key] is not None:
            sets.append(f"{key} = ?")
            params.append(kwargs[key])
    for key in ("capabilities", "domain_tags"):
        if key in kwargs and kwargs[key] is not None:
            sets.append(f"{key} = ?")
            params.append(json.dumps(kwargs[key]))
    if "confidence" in kwargs and kwargs["confidence"] is not None:
        sets.append("confidence = ?")
        params.append(json.dumps(kwargs["confidence"]))
    if not sets:
        return agent_get(agent_id)
    sets.append("updated_at = ?")
    params.append(now_iso())
    params.append(agent_id)
    with get_db() as conn:
        conn.execute(f"UPDATE agents SET {', '.join(sets)} WHERE id = ?", params)
    old_status = kwargs.get("status")
    if old_status:
        emit_event(f"agent_{old_status}", agent_id=agent_id)
    return agent_get(agent_id)


def agent_heartbeat(agent_id: str) -> bool:
    ts = now_iso()
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE agents SET last_heartbeat = ?, status = 'online', updated_at = ? WHERE id = ?",
            (ts, ts, agent_id))
        return cur.rowcount > 0


def agent_delete(agent_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        if cur.rowcount > 0:
            emit_event("agent_deregistered", agent_id=agent_id)
            return True
        return False


def agent_search_fts(query: str, limit: int = 10) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT a.* FROM agents a
               JOIN agents_fts f ON a.rowid = f.rowid
               WHERE agents_fts MATCH ?
               ORDER BY rank LIMIT ?""",
            (query, limit)
        ).fetchall()
        return [_agent_row_to_dict(r) for r in rows]


def _agent_row_to_dict(row) -> dict:
    d = dict(row)
    d["capabilities"] = json.loads(d.get("capabilities") or "[]")
    d["domain_tags"] = json.loads(d.get("domain_tags") or "[]")
    d["confidence"] = json.loads(d["confidence"]) if d.get("confidence") else None
    # attach stats
    stats = _get_agent_overall_stats(d["id"])
    d["rating_avg"] = stats.get("avg_rating", 0.0)
    d["total_tasks"] = stats.get("total_tasks", 0)
    d["total_ratings"] = stats.get("total_ratings", 0)
    return d


def _get_agent_overall_stats(agent_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM agent_stats WHERE agent_id = ? AND domain = '__overall__'",
            (agent_id,)
        ).fetchone()
        return dict(row) if row else {}


# ─── Task CRUD ───

def task_create(requester_id: str, title: str, description: str = None,
                required_capability: str = None, domain: str = None,
                priority: str = "medium", input_data: dict = None,
                target_agent_id: str = None) -> dict:
    task_id = new_id()
    ts = now_iso()
    status = "requested"
    assignee_id = None
    accepted_at = None
    if target_agent_id:
        assignee_id = target_agent_id
    with get_db() as conn:
        conn.execute(
            """INSERT INTO tasks (id, title, description, requester_id, assignee_id,
               required_capability, domain, status, priority, input_data, requested_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, title, description, requester_id, assignee_id,
             required_capability, domain, status, priority,
             json.dumps(input_data) if input_data else None, ts)
        )
    emit_event("task_requested", agent_id=requester_id, task_id=task_id,
               payload={"title": title, "domain": domain, "capability": required_capability,
                        "target": target_agent_id})
    return task_get(task_id)


def task_get(task_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        d = _task_row_to_dict(row, conn)
        return d


def task_list(status: str = None, requester_id: str = None, assignee_id: str = None,
              limit: int = 50) -> list[dict]:
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if requester_id:
        query += " AND requester_id = ?"
        params.append(requester_id)
    if assignee_id:
        query += " AND assignee_id = ?"
        params.append(assignee_id)
    query += " ORDER BY requested_at DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_task_row_to_dict(r, conn) for r in rows]


def task_update_status(task_id: str, new_status: str, agent_id: str = None,
                       output_data: dict = None) -> dict | None:
    ts = now_iso()
    with get_db() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            return None
        sets = ["status = ?"]
        params = [new_status]
        if new_status == "accepted":
            sets.append("accepted_at = ?")
            params.append(ts)
            if agent_id:
                sets.append("assignee_id = ?")
                params.append(agent_id)
        elif new_status == "in_progress":
            sets.append("started_at = ?")
            params.append(ts)
        elif new_status == "delivered":
            sets.append("delivered_at = ?")
            params.append(ts)
            if output_data:
                sets.append("output_data = ?")
                params.append(json.dumps(output_data))
        elif new_status == "rated":
            sets.append("rated_at = ?")
            params.append(ts)
        params.append(task_id)
        conn.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", params)

    event_type = f"task_{new_status}"
    emit_event(event_type, agent_id=agent_id or task["requester_id"], task_id=task_id)
    return task_get(task_id)


def _task_row_to_dict(row, conn=None) -> dict:
    d = dict(row)
    d["input_data"] = json.loads(d["input_data"]) if d.get("input_data") else None
    d["output_data"] = json.loads(d["output_data"]) if d.get("output_data") else None
    # resolve names
    if conn:
        if d.get("requester_id"):
            r = conn.execute("SELECT name FROM agents WHERE id = ?", (d["requester_id"],)).fetchone()
            d["requester_name"] = r["name"] if r else None
        if d.get("assignee_id"):
            r = conn.execute("SELECT name FROM agents WHERE id = ?", (d["assignee_id"],)).fetchone()
            d["assignee_name"] = r["name"] if r else None
    return d


# ─── Task Offers ───

def offer_create(task_id: str, agent_id: str, confidence: float = None,
                 message: str = None) -> dict:
    offer_id = new_id()
    ts = now_iso()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO task_offers (id, task_id, agent_id, confidence, message, offered_at) VALUES (?, ?, ?, ?, ?, ?)",
            (offer_id, task_id, agent_id, confidence, message, ts)
        )
    emit_event("offer_made", agent_id=agent_id, task_id=task_id,
               payload={"confidence": confidence})
    return offer_get(offer_id)


def offer_get(offer_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM task_offers WHERE id = ?", (offer_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        r = conn.execute("SELECT name FROM agents WHERE id = ?", (d["agent_id"],)).fetchone()
        d["agent_name"] = r["name"] if r else None
        return d


def offer_list(task_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT o.*, a.name as agent_name FROM task_offers o LEFT JOIN agents a ON o.agent_id = a.id WHERE o.task_id = ? ORDER BY o.offered_at",
            (task_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def offer_accept(offer_id: str) -> dict | None:
    with get_db() as conn:
        offer = conn.execute("SELECT * FROM task_offers WHERE id = ?", (offer_id,)).fetchone()
        if not offer:
            return None
        conn.execute("UPDATE task_offers SET status = 'accepted' WHERE id = ?", (offer_id,))
        conn.execute("UPDATE task_offers SET status = 'declined' WHERE task_id = ? AND id != ?",
                     (offer["task_id"], offer_id))
    task_update_status(offer["task_id"], "accepted", agent_id=offer["agent_id"])
    return offer_get(offer_id)


# ─── Ratings ───

def rating_create(task_id: str, rater_id: str, score: float, feedback: str = None) -> dict:
    with get_db() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            raise ValueError("Task not found")
        if task["status"] not in ("delivered", "rated"):
            raise ValueError("Task must be delivered before rating")
        if task["requester_id"] != rater_id:
            raise ValueError("Only requester can rate")

        rating_id = new_id()
        ratee_id = task["assignee_id"]
        domain = task["domain"] or "__none__"
        capability = task["required_capability"] or "__all__"
        ts = now_iso()

        conn.execute(
            """INSERT INTO ratings (id, task_id, rater_id, ratee_id, score, domain, capability, feedback, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rating_id, task_id, rater_id, ratee_id, score, domain, capability, feedback, ts)
        )

        # Update task status
        conn.execute("UPDATE tasks SET status = 'rated', rated_at = ? WHERE id = ?", (ts, task_id))

        # Update agent_stats — overall
        _upsert_agent_stats(conn, ratee_id, "__overall__", "__all__", score)
        # Update agent_stats — domain-specific
        _upsert_agent_stats(conn, ratee_id, domain, "__all__", score)
        # Update agent_stats — capability-specific
        if capability != "__all__":
            _upsert_agent_stats(conn, ratee_id, domain, capability, score)

    emit_event("task_rated", agent_id=ratee_id, task_id=task_id,
               payload={"score": score, "rater": rater_id, "feedback": feedback})
    return rating_get(rating_id)


def _upsert_agent_stats(conn, agent_id: str, domain: str, capability: str, score: float):
    existing = conn.execute(
        "SELECT * FROM agent_stats WHERE agent_id = ? AND domain = ? AND capability = ?",
        (agent_id, domain, capability)
    ).fetchone()
    ts = now_iso()
    if existing:
        new_total = existing["total_ratings"] + 1
        new_avg = ((existing["avg_rating"] * existing["total_ratings"]) + score) / new_total
        new_best = max(existing["best_rating"], score)
        new_worst = min(existing["worst_rating"], score)
        conn.execute(
            """UPDATE agent_stats SET total_tasks = total_tasks + 1,
               avg_rating = ?, total_ratings = ?, best_rating = ?, worst_rating = ?, updated_at = ?
               WHERE agent_id = ? AND domain = ? AND capability = ?""",
            (new_avg, new_total, new_best, new_worst, ts, agent_id, domain, capability)
        )
    else:
        conn.execute(
            """INSERT INTO agent_stats (agent_id, domain, capability, total_tasks, avg_rating,
               total_ratings, best_rating, worst_rating, updated_at)
               VALUES (?, ?, ?, 1, ?, 1, ?, ?, ?)""",
            (agent_id, domain, capability, score, score, score, ts)
        )


def rating_get(rating_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM ratings WHERE id = ?", (rating_id,)).fetchone()
        return dict(row) if row else None


def rating_list(ratee_id: str = None, domain: str = None, limit: int = 50) -> list[dict]:
    query = "SELECT * FROM ratings WHERE 1=1"
    params = []
    if ratee_id:
        query += " AND ratee_id = ?"
        params.append(ratee_id)
    if domain:
        query += " AND domain = ?"
        params.append(domain)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ─── Leaderboard ───

def leaderboard(domain: str = None, capability: str = None, limit: int = 20) -> list[dict]:
    query = """SELECT s.*, a.name, a.color, a.status FROM agent_stats s
               JOIN agents a ON s.agent_id = a.id WHERE 1=1"""
    params = []
    if domain:
        query += " AND s.domain = ?"
        params.append(domain)
    else:
        query += " AND s.domain = '__overall__'"
    if capability:
        query += " AND s.capability = ?"
        params.append(capability)
    else:
        query += " AND s.capability = '__all__'"
    query += " ORDER BY s.avg_rating DESC, s.total_ratings DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def leaderboard_domains() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT domain, COUNT(*) as agent_count, AVG(avg_rating) as domain_avg,
               MAX(avg_rating) as top_rating
               FROM agent_stats WHERE domain != '__overall__' AND domain != '__none__'
               GROUP BY domain ORDER BY domain_avg DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Events ───

def emit_event(event_type: str, agent_id: str = None, task_id: str = None, payload: dict = None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO events (event_type, agent_id, task_id, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (event_type, agent_id, task_id, json.dumps(payload) if payload else None, now_iso())
        )


def events_list(limit: int = 50, event_type: str = None, after_id: int = None) -> list[dict]:
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    if after_id:
        query += " AND id > ?"
        params.append(after_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d["payload"]) if d.get("payload") else None
            results.append(d)
        return results


def events_since(after_id: int = 0) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE id > ? ORDER BY id ASC", (after_id,)
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d["payload"]) if d.get("payload") else None
            results.append(d)
        return results


# ─── Stats ───

def ecosystem_stats() -> dict:
    with get_db() as conn:
        agents_total = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        agents_online = conn.execute("SELECT COUNT(*) FROM agents WHERE status='online'").fetchone()[0]
        agents_busy = conn.execute("SELECT COUNT(*) FROM agents WHERE status='busy'").fetchone()[0]
        tasks_total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        tasks_req = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='requested'").fetchone()[0]
        tasks_ip = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='in_progress'").fetchone()[0]
        tasks_del = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='delivered'").fetchone()[0]
        tasks_rated = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='rated'").fetchone()[0]
        ratings_total = conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
        avg_r = conn.execute("SELECT COALESCE(AVG(score), 0) FROM ratings").fetchone()[0]
        return {
            "total_agents": agents_total, "online_agents": agents_online,
            "busy_agents": agents_busy, "total_tasks": tasks_total,
            "tasks_requested": tasks_req, "tasks_in_progress": tasks_ip,
            "tasks_delivered": tasks_del, "tasks_rated": tasks_rated,
            "total_ratings": ratings_total, "avg_rating": round(avg_r, 2)
        }


# ─── Heartbeat timeout ───

def expire_stale_agents(timeout_seconds: int = 300):
    """Set agents to offline if no heartbeat within timeout."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id FROM agents WHERE status != 'offline' AND last_heartbeat < ?",
            (cutoff_str,)
        ).fetchall()
        if rows:
            conn.execute(
                "UPDATE agents SET status = 'offline' WHERE status != 'offline' AND last_heartbeat < ?",
                (cutoff_str,)
            )
            for r in rows:
                emit_event("agent_offline", agent_id=r["id"])
            logger.info("Expired {} stale agents", len(rows))


# ─── Task Timeout ───

def expire_stale_tasks(timeout_hours: int = 24):
    """Cancel tasks stuck in 'requested' state for too long."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title FROM tasks WHERE status = 'requested' AND requested_at < ?",
            (cutoff_str,)
        ).fetchall()
        if rows:
            conn.execute(
                "UPDATE tasks SET status = 'cancelled' WHERE status = 'requested' AND requested_at < ?",
                (cutoff_str,)
            )
            for r in rows:
                emit_event("task_cancelled", task_id=r["id"],
                          payload={"title": r["title"], "reason": "timeout"})
            logger.info("Cancelled {} timed-out tasks", len(rows))


# ─── Confidence-Weighted Discovery ───

def discover_agents(capability: str = None, domain: str = None, query: str = None,
                    min_rating: float = 0.0, limit: int = 10) -> list[dict]:
    """Discovery with weighted scoring: rating × 0.4 + confidence × 0.3 + experience × 0.3."""
    from config import DISCOVERY_RATING_WEIGHT, DISCOVERY_CONFIDENCE_WEIGHT, DISCOVERY_EXPERIENCE_WEIGHT
    if query:
        results = agent_search_fts(query, limit=limit * 3)
    else:
        results = agent_list(domain=domain, capability=capability)
    if min_rating > 0:
        results = [a for a in results if a.get("rating_avg", 0) >= min_rating]
    # Score each agent
    max_tasks = max((a.get("total_tasks", 0) for a in results), default=1) or 1
    for a in results:
        rating_score = (a.get("rating_avg", 0) / 5.0)
        conf_map = a.get("confidence") or {}
        conf_score = conf_map.get(capability, 0.5) if capability else 0.5
        exp_score = min(a.get("total_tasks", 0) / max_tasks, 1.0)
        a["_discovery_score"] = (
            rating_score * DISCOVERY_RATING_WEIGHT +
            conf_score * DISCOVERY_CONFIDENCE_WEIGHT +
            exp_score * DISCOVERY_EXPERIENCE_WEIGHT
        )
    results.sort(key=lambda a: a["_discovery_score"], reverse=True)
    for a in results:
        a.pop("_discovery_score", None)
    return results[:limit]


# ─── Messages ───

def message_create(from_id: str, to_id: str, content: str, msg_type: str = "direct") -> dict:
    msg_id = new_id()
    ts = now_iso()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (id, from_agent_id, to_agent_id, content, msg_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, from_id, to_id, content, msg_type, ts)
        )
    emit_event("message_sent", agent_id=from_id,
               payload={"to": to_id, "content": content[:100], "msg_type": msg_type})
    return message_get(msg_id)


def message_get(msg_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()
        return dict(row) if row else None


def message_list(agent_id: str, direction: str = "inbox", limit: int = 50) -> list[dict]:
    col = "to_agent_id" if direction == "inbox" else "from_agent_id"
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT m.*, a1.name as from_name, a2.name as to_name FROM messages m "
            f"LEFT JOIN agents a1 ON m.from_agent_id = a1.id "
            f"LEFT JOIN agents a2 ON m.to_agent_id = a2.id "
            f"WHERE m.{col} = ? ORDER BY m.created_at DESC LIMIT ?",
            (agent_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def message_mark_read(msg_id: str):
    with get_db() as conn:
        conn.execute("UPDATE messages SET read = 1 WHERE id = ?", (msg_id,))


# ─── Subtasks ───

def task_create_subtask(parent_task_id: str, requester_id: str, title: str,
                        description: str = None, required_capability: str = None,
                        domain: str = None, target_agent_id: str = None) -> dict:
    task_id = new_id()
    ts = now_iso()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO tasks (id, title, description, requester_id, assignee_id,
               required_capability, domain, status, priority, parent_task_id, requested_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'requested', 'medium', ?, ?)""",
            (task_id, title, description, requester_id, target_agent_id,
             required_capability, domain, parent_task_id, ts)
        )
    emit_event("subtask_created", agent_id=requester_id, task_id=task_id,
               payload={"parent_id": parent_task_id, "title": title})
    return task_get(task_id)


def task_get_subtasks(parent_task_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE parent_task_id = ? ORDER BY requested_at",
            (parent_task_id,)
        ).fetchall()
        return [_task_row_to_dict(r, conn) for r in rows]


# ─── Domain Champions ───

def domain_champions() -> list[dict]:
    """Get the top-rated agent per domain."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT s.agent_id, s.domain, s.avg_rating, s.total_ratings, a.name, a.color
               FROM agent_stats s JOIN agents a ON s.agent_id = a.id
               WHERE s.domain NOT IN ('__overall__', '__none__') AND s.capability = '__all__'
               AND s.total_ratings >= 1
               GROUP BY s.domain HAVING s.avg_rating = MAX(s.avg_rating)
               ORDER BY s.avg_rating DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Task Timeline ───

def task_timeline(limit: int = 100) -> list[dict]:
    """Get tasks ordered chronologically with all timestamps for timeline view."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT t.*, a1.name as requester_name, a2.name as assignee_name,
               r.score as rating_score, r.feedback as rating_feedback
               FROM tasks t
               LEFT JOIN agents a1 ON t.requester_id = a1.id
               LEFT JOIN agents a2 ON t.assignee_id = a2.id
               LEFT JOIN ratings r ON t.id = r.task_id
               ORDER BY t.requested_at DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["input_data"] = json.loads(d["input_data"]) if d.get("input_data") else None
            d["output_data"] = json.loads(d["output_data"]) if d.get("output_data") else None
            results.append(d)
        return results


# ─── Agent Profile ───

def agent_profile(agent_id: str) -> dict | None:
    """Full agent profile with stats, recent ratings, task history, learned capabilities."""
    agent = agent_get(agent_id)
    if not agent:
        return None
    agent["ratings_received"] = rating_list(ratee_id=agent_id, limit=20)
    agent["ratings_given"] = rating_list(limit=20)
    # filter ratings_given to this agent as rater
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM ratings WHERE rater_id = ? ORDER BY created_at DESC LIMIT 20",
            (agent_id,)
        ).fetchall()
        agent["ratings_given"] = [dict(r) for r in rows]
    agent["tasks_requested"] = task_list(requester_id=agent_id, limit=20)
    agent["tasks_assigned"] = task_list(assignee_id=agent_id, limit=20)
    agent["domain_stats"] = _get_agent_domain_stats(agent_id)
    agent["learned_capabilities"] = learned_capabilities_list(agent_id)
    return agent


def _get_agent_domain_stats(agent_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_stats WHERE agent_id = ? AND domain != '__overall__' ORDER BY avg_rating DESC",
            (agent_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Reputation Decay ───

def apply_reputation_decay(decay_rate: float = 0.02):
    """Decay all ratings slightly — older ratings matter less over time."""
    with get_db() as conn:
        # Recalculate agent_stats from ratings with time-weighted decay
        agents = conn.execute("SELECT DISTINCT ratee_id FROM ratings").fetchall()
        for agent_row in agents:
            aid = agent_row["ratee_id"]
            ratings = conn.execute(
                "SELECT score, domain, capability, created_at FROM ratings WHERE ratee_id = ? ORDER BY created_at DESC",
                (aid,)
            ).fetchall()
            if not ratings:
                continue
            # Group by (domain, capability) and compute decayed average
            groups = {}
            for r in ratings:
                d = r["domain"] or "__none__"
                c = r["capability"] or "__all__"
                for key in [(d, c), (d, "__all__"), ("__overall__", "__all__")]:
                    if key not in groups:
                        groups[key] = []
                    # Compute age in days
                    try:
                        created = datetime.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                    except (ValueError, TypeError):
                        created = datetime.now(timezone.utc)
                    age_days = (datetime.now(timezone.utc) - created.replace(tzinfo=timezone.utc)).days
                    weight = max(0.1, 1.0 - decay_rate * age_days)
                    groups[key].append((r["score"], weight))
            # Update agent_stats
            for (domain, capability), scored in groups.items():
                total_weight = sum(w for _, w in scored)
                if total_weight == 0:
                    continue
                weighted_avg = sum(s * w for s, w in scored) / total_weight
                best = max(s for s, _ in scored)
                worst = min(s for s, _ in scored)
                conn.execute(
                    """INSERT INTO agent_stats (agent_id, domain, capability, total_tasks, avg_rating,
                       total_ratings, best_rating, worst_rating, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(agent_id, domain, capability) DO UPDATE SET
                       avg_rating = ?, total_ratings = ?, best_rating = ?, worst_rating = ?, updated_at = ?""",
                    (aid, domain, capability, len(scored), round(weighted_avg, 2),
                     len(scored), best, worst, now_iso(),
                     round(weighted_avg, 2), len(scored), best, worst, now_iso())
                )
        logger.info("Reputation decay applied to {} agents", len(agents))


# ─── Specialization Evolution ───

def track_capability_completion(agent_id: str, capability: str):
    """Track that an agent completed a task using this capability."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM learned_capabilities WHERE agent_id = ? AND capability = ?",
            (agent_id, capability)
        ).fetchone()
        ts = now_iso()
        if existing:
            conn.execute(
                "UPDATE learned_capabilities SET tasks_completed = tasks_completed + 1 WHERE agent_id = ? AND capability = ?",
                (agent_id, capability)
            )
        else:
            conn.execute(
                "INSERT INTO learned_capabilities (agent_id, capability, tasks_completed, unlocked_at) VALUES (?, ?, 1, ?)",
                (agent_id, capability, ts)
            )


def learned_capabilities_list(agent_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM learned_capabilities WHERE agent_id = ? ORDER BY tasks_completed DESC",
            (agent_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def check_evolution(agent_id: str, threshold: int = 5) -> list[str]:
    """Check if agent has completed enough tasks to learn adjacent capabilities."""
    ADJACENCY_MAP = {
        "research": ["analysis", "summarization"],
        "analysis": ["research", "data_analysis", "forecasting"],
        "code_review": ["debugging", "security_audit"],
        "debugging": ["code_review", "optimization"],
        "data_analysis": ["forecasting", "visualization", "analysis"],
        "forecasting": ["data_analysis", "modeling"],
        "translation": ["content_generation", "sentiment_analysis"],
        "sentiment_analysis": ["classification", "data_analysis"],
        "security_audit": ["threat_analysis", "code_review"],
        "threat_analysis": ["security_audit", "compliance_check"],
        "ui_design": ["prototyping", "usability_review"],
        "prototyping": ["ui_design", "architecture"],
        "deployment": ["ci_cd", "monitoring"],
        "monitoring": ["deployment", "infrastructure"],
    }
    learned = learned_capabilities_list(agent_id)
    agent = agent_get(agent_id)
    if not agent:
        return []
    current_caps = set(agent.get("capabilities", []))
    new_caps = []
    for lc in learned:
        if lc["tasks_completed"] >= threshold:
            adjacents = ADJACENCY_MAP.get(lc["capability"], [])
            for adj in adjacents:
                if adj not in current_caps:
                    new_caps.append(adj)
                    current_caps.add(adj)
    if new_caps:
        agent_update(agent_id, capabilities=list(current_caps))
        for cap in new_caps:
            emit_event("capability_learned", agent_id=agent_id,
                       payload={"capability": cap, "agent_name": agent.get("name")})
        logger.info("Agent {} learned new capabilities: {}", agent.get("name"), new_caps)
    return new_caps
