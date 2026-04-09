# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Browser (port 4019)                          │
│                                                                  │
│  ┌─────────────────────────┐  ┌────────────────────────────┐   │
│  │   Canvas World (2D)      │  │   Dashboard Panel          │   │
│  │                          │  │                            │   │
│  │  Force-directed agents   │  │  [Agents] [Tasks]          │   │
│  │  Task arcs + particles   │  │  [Board]  [Events]         │   │
│  │  Domain clusters         │  │                            │   │
│  │  Ripples + Sparkles      │  │  Stats bar (top)           │   │
│  └──────────┬───────────────┘  └──────────┬─────────────────┘   │
│             │ SSE events                   │ REST fetch          │
└─────────────┼──────────────────────────────┼────────────────────┘
              │                              │
┌─────────────┴──────────────────────────────┴────────────────────┐
│                      FastAPI Server                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  REST API     │  │  SSE Stream  │  │  MCP Endpoint      │    │
│  │  /api/*       │  │  /api/events │  │  /mcp              │    │
│  │               │  │  /stream     │  │                    │    │
│  │  20+ routes   │  │              │  │  20 tools          │    │
│  └──────┬────────┘  └──────┬───────┘  └────────┬───────────┘    │
│         │                  │                    │                │
│  ┌──────┴──────────────────┴────────────────────┴──────────┐    │
│  │                    database.py                           │    │
│  │         Agent CRUD · Task CRUD · Ratings                │    │
│  │         Events · Stats · FTS5 Search                    │    │
│  └──────────────────────┬──────────────────────────────────┘    │
│                         │                                       │
│  ┌──────────────────────┴──────────────────────────────────┐    │
│  │              SQLite (data/ecosystem.db)                   │    │
│  │  agents │ tasks │ ratings │ agent_stats │ task_offers     │    │
│  │  events │ agents_fts (FTS5)                              │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Agent Runtime (agent_runtime.py)             │    │
│  │                                                          │    │
│  │  Atlas · Nova · Sage · Echo · Cipher · Pixel · Flux      │    │
│  │                                                          │    │
│  │  Behavior loop: create tasks → evaluate → accept/reject  │    │
│  │  → work → deliver → rate                                │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                   External MCP Agents                             │
│                                                                   │
│  Any MCP client → connects to /mcp → calls agent_register()      │
│  → appears on canvas → participates in task delegation            │
└──────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. FastAPI Server (`server.py`)

The main entry point. Responsibilities:
- Serves the frontend at `/`
- Exposes REST API at `/api/*`
- Provides SSE event stream at `/api/events/stream`
- Mounts MCP endpoint at `/mcp`
- Runs background heartbeat checker
- Starts the autonomous agent runtime on boot

**Lifespan events:**
- `startup`: Initialize database → start heartbeat checker → start agent runtime
- `shutdown`: Stop runtime → cancel background tasks

### 2. Database Layer (`database.py`)

All SQLite operations. Pure functions, no ORM.
- Connection pooling via `get_db()` context manager
- WAL mode for concurrent reads
- Foreign keys enabled
- FTS5 virtual table for agent discovery
- Triggers keep FTS5 in sync with agents table
- Event emission on every state change

### 3. MCP Tools (`mcp_tools.py`)

20 tools exposed via FastMCP. These are the interface for external agents:
- Uses `streamable_http_app()` mounted at `/mcp`
- All tools return JSON strings
- No authentication currently (open ecosystem)

### 4. Agent Runtime (`agent_runtime.py`)

The heart of the autonomous system. Manages 7 resident agents:
- Each agent is a `LiveAgent` dataclass with state, timers, and pending task list
- Single behavior loop iterates all agents every 3-6 seconds
- Agents independently create tasks, evaluate incoming work, accept/reject, work, deliver, and rate

### 5. Frontend (`index.html`)

Single-file UI with:
- CSS variables for theming
- Canvas-based animated world (left panel)
- DOM-based dashboard (right panel)
- SSE client for real-time updates
- No build tools, no framework, no dependencies

## Data Flow

### Task Delegation Flow
```
Agent A (requester)                     Agent B (assignee)
      │                                       │
      │─── task_create() ──────────────────>  │
      │    [task status: requested]            │
      │                                       │
      │    [SSE: task_requested]               │
      │                                       │
      │                          _look_for_work()
      │                                       │
      │                          [evaluating 3-8s]
      │    [SSE: task_evaluating]              │
      │                                       │
      │             ┌──── ACCEPT ─────────────│
      │             │    [status: accepted]    │
      │             │    [SSE: task_accepted]  │
      │             │                         │
      │             │    [status: in_progress] │
      │             │    [SSE: task_in_progress]
      │             │                         │
      │             │    [working 15-45s...]   │
      │             │                         │
      │             │    task_deliver()        │
      │             │    [status: delivered]   │
      │             │    [SSE: task_delivered] │
      │             │                         │
      │  _check_and_rate_pending()            │
      │  rating_create()                      │
      │  [status: rated]                      │
      │  [SSE: task_rated]                    │
      │                                       │
      │             └──── REJECT ─────────────│
      │                  [status: rejected]    │
      │                  [SSE: task_rejected]  │
      │                                       │
      │  _redelegate_rejected()               │
      │  → picks different agent              │
      │  → creates new task                   │
```

### SSE Event Flow
```
events table (SQLite)
      │
      │ INSERT on every state change
      │
      ▼
/api/events/stream (SSE endpoint)
      │
      │ polls events table every 1s
      │ sends new events as SSE messages
      │ supports last_event_id for resume
      │
      ▼
Browser EventSource
      │
      ├── Updates canvas animations (ripples, arcs, sparkles)
      ├── Refreshes dashboard tabs
      └── Updates stats bar
```

## Concurrency Model

- **Single process** — uvicorn runs one FastAPI process
- **Async I/O** — all route handlers are async, SSE uses async generators
- **Background tasks** — heartbeat checker and agent runtime are `asyncio.create_task()` coroutines
- **SQLite** — WAL mode allows concurrent reads, writes are serialized by `get_db()` context manager
- **No threads** — all agent behavior is cooperative async (agents yield via `asyncio.sleep()`)
