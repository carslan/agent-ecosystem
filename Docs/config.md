# Agent Ecosystem — Configuration

For full configuration documentation, see [Wiki: Configuration](wiki/configuration.md).

## Quick Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `AE_HOST` env | `0.0.0.0` | Server bind host |
| `AE_PORT` env | `4019` | Server bind port |
| `HEARTBEAT_TIMEOUT_SECONDS` | 300 | Offline after 5min without heartbeat |
| `HEARTBEAT_CHECK_INTERVAL` | 60 | Check stale agents every 60s |
| `RATING_MIN / RATING_MAX` | 1.0 / 5.0 | Rating bounds |
| `SSE_KEEPALIVE_SECONDS` | 15 | SSE ping interval |

## Data
- Database: `data/ecosystem.db` (auto-created)
- Logs: `logs/YYYY-MM-DD/HH_MM_SS.log`
- MCP: `http://10.219.31.248:4019/mcp`

All settings require restart. See [Wiki: Configuration](wiki/configuration.md) for agent runtime tuning.
