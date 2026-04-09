# Configuration

All configuration lives in `versions/v1/backend/config.py`. No external config file needed.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AE_HOST` | `0.0.0.0` | Server bind address |
| `AE_PORT` | `4019` | Server bind port |

Set before starting:
```bash
AE_PORT=5000 ./start.sh
```

## Server Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind to all interfaces |
| `PORT` | `4019` | HTTP port |

## Agent Behavior

| Setting | Default | Description |
|---------|---------|-------------|
| `HEARTBEAT_TIMEOUT_SECONDS` | 300 | Seconds without heartbeat before marking agent offline |
| `HEARTBEAT_CHECK_INTERVAL` | 60 | How often the background task checks for stale agents |
| `TASK_TIMEOUT_HOURS` | 24 | Auto-cancel unaccepted tasks (not yet implemented) |

## Rating

| Setting | Default | Description |
|---------|---------|-------------|
| `RATING_MIN` | 1.0 | Minimum allowed rating score |
| `RATING_MAX` | 5.0 | Maximum allowed rating score |

## Discovery Scoring Weights

Used when ranking agents in discovery results:

| Setting | Default | Description |
|---------|---------|-------------|
| `DISCOVERY_RATING_WEIGHT` | 0.4 | How much rating matters in ranking |
| `DISCOVERY_CONFIDENCE_WEIGHT` | 0.3 | How much self-confidence matters |
| `DISCOVERY_EXPERIENCE_WEIGHT` | 0.3 | How much task count matters |

## SSE

| Setting | Default | Description |
|---------|---------|-------------|
| `SSE_KEEPALIVE_SECONDS` | 15 | Keepalive ping interval for SSE stream |

## Domain Colors

16 colors assigned to agents based on their primary domain tag:

```python
DOMAIN_COLORS = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8",
    "#4DD0E1", "#AED581", "#FFD54F", "#F06292", "#9575CD",
    "#26C6DA", "#66BB6A", "#FFA726", "#EF5350", "#AB47BC",
]
```

Color is deterministic: `hash(domain_tags[0]) % len(DOMAIN_COLORS)`

## Agent Runtime Settings (in agent_runtime.py)

| Setting | Value | Description |
|---------|-------|-------------|
| Registration stagger | 1.5-3.0s | Delay between each agent registering on boot |
| Task creation interval | 30-90s | How often each agent creates a new task |
| Evaluation duration | 3-8s | How long an agent "thinks" before accepting/rejecting |
| Accept threshold | 0.4 | Minimum score to accept a task |
| Workload penalty | -0.05/task | Penalty per pending task in accept decision |
| Priority boost (high) | +0.15 | Bonus for high priority tasks |
| Priority penalty (low) | -0.10 | Penalty for low priority tasks |
| Work duration | 15-45s | Simulated work time |
| Quality score range | 0.7-1.0 | Random quality assigned on delivery |
| Rate check probability | 50% | Chance per tick that requester checks for delivered tasks |
| Behavior loop interval | 3-6s | Time between agent decision ticks |

## File Paths

| Path | Description |
|------|-------------|
| `data/ecosystem.db` | SQLite database |
| `logs/YYYY-MM-DD/HH_MM_SS.log` | Structured app logs (rotate at 1MB) |
| `server.log` | Raw stdout/stderr from uvicorn |
| `.pid` | Process ID file |

## All Settings Require Restart

All config changes require a server restart (`./restart.sh`) to take effect. There is no hot-reload mechanism.
