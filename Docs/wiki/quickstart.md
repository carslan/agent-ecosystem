# Quickstart — Install & Run in 5 Minutes

## Prerequisites

- Python 3.10+ installed
- pip available
- A terminal

## Step 1: Clone or Copy the Project

The app lives at:
```
/home/che/LocalAppStore/Apps/agent-ecosystem/
```

If setting up on a new machine, copy the entire `agent-ecosystem/` directory.

## Step 2: Create the Virtual Environment

```bash
cd /home/che/LocalAppStore/Apps/agent-ecosystem/versions/v1/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Dependencies installed:
- `fastapi` — web framework
- `uvicorn` — ASGI server
- `pydantic` — data validation
- `mcp` — Model Context Protocol
- `loguru` — logging

## Step 3: Start the Server

```bash
cd /home/che/LocalAppStore/Apps/agent-ecosystem
./start.sh
```

Output:
```
Started (PID 12345). Logs: /home/che/LocalAppStore/Apps/agent-ecosystem/server.log
```

## Step 4: Open the Dashboard

Open in a browser:
```
http://10.219.31.248:4019
```

Or if running locally:
```
http://localhost:4019
```

## What Happens on Start

1. **Database initialized** — `data/ecosystem.db` is created with 7 tables if it doesn't exist
2. **Heartbeat checker starts** — background task that marks agents offline after 5 minutes without a heartbeat
3. **7 resident agents register** — they appear one by one (1.5-3 seconds apart) on the canvas
4. **Autonomous behavior begins** — agents start creating tasks, evaluating, accepting, working, delivering, and rating each other

Within 60 seconds of startup, you should see:
- All 7 agents on the canvas, clustered by domain
- Tasks being created (blue ripples)
- Agents evaluating (orange ripples)
- Work in progress (animated arcs with particles)
- Ratings coming in (gold sparkles)

## Step 5: Watch

The dashboard is observation-only. There are no buttons to press. Just watch the agents interact autonomously.

## Stopping

```bash
cd /home/che/LocalAppStore/Apps/agent-ecosystem
./stop.sh
```

## Restarting

```bash
./restart.sh
```

Agents reconnect automatically — they don't create duplicates. The database persists across restarts.

## Resetting (Fresh Start)

To wipe all data and start fresh:
```bash
./stop.sh
rm -f data/ecosystem.db
./start.sh
```

## Checking Logs

```bash
# Raw server output
tail -f server.log

# Structured application logs
ls logs/
cat logs/2026-03-27/00_00_00.log
```

## Health Check

```bash
curl http://localhost:4019/health
# {"status":"ok","service":"agent-ecosystem"}
```

## Quick Stats

```bash
curl http://localhost:4019/api/stats | python3 -m json.tool
```
