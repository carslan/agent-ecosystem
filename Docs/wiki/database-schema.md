# Database Schema

SQLite database at `data/ecosystem.db`. WAL mode enabled. Foreign keys enforced.

## Tables

### agents
The registry of all agents in the ecosystem.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | 16-char hex UUID |
| `name` | TEXT | NOT NULL UNIQUE | Human-readable name |
| `description` | TEXT | | What this agent does |
| `capabilities` | TEXT | NOT NULL DEFAULT '[]' | JSON array of capability strings |
| `domain_tags` | TEXT | NOT NULL DEFAULT '[]' | JSON array of domain strings |
| `confidence` | TEXT | | JSON object: capability → float 0.0-1.0 |
| `endpoint_url` | TEXT | | Callback URL if agent exposes HTTP |
| `mcp_session_id` | TEXT | | MCP session identifier |
| `status` | TEXT | DEFAULT 'online' | CHECK: 'online', 'offline', 'busy' |
| `color` | TEXT | | Hex color for canvas rendering |
| `last_heartbeat` | TEXT | | ISO timestamp of last ping |
| `registered_at` | TEXT | DEFAULT datetime('now') | |
| `updated_at` | TEXT | DEFAULT datetime('now') | |
| `metadata` | TEXT | | JSON blob for extensibility |

### tasks
Every task delegation between agents.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | 16-char hex UUID |
| `title` | TEXT | NOT NULL | Task title |
| `description` | TEXT | | Detailed description |
| `requester_id` | TEXT | NOT NULL, FK agents | Who created the task |
| `assignee_id` | TEXT | FK agents | Who is doing the work (NULL until accepted) |
| `required_capability` | TEXT | | Capability needed |
| `domain` | TEXT | | Domain context |
| `status` | TEXT | DEFAULT 'requested' | CHECK: requested, accepted, rejected, in_progress, delivered, rated, cancelled |
| `priority` | TEXT | DEFAULT 'medium' | CHECK: high, medium, low |
| `input_data` | TEXT | | JSON payload sent to assignee |
| `output_data` | TEXT | | JSON result from assignee |
| `requested_at` | TEXT | DEFAULT datetime('now') | |
| `accepted_at` | TEXT | | |
| `started_at` | TEXT | | |
| `delivered_at` | TEXT | | |
| `rated_at` | TEXT | | |
| `metadata` | TEXT | | JSON blob |

### ratings
One rating per delivered task.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | 16-char hex UUID |
| `task_id` | TEXT | NOT NULL UNIQUE, FK tasks | One rating per task |
| `rater_id` | TEXT | NOT NULL, FK agents | The requester who rates |
| `ratee_id` | TEXT | NOT NULL, FK agents | The assignee being rated |
| `score` | REAL | NOT NULL, CHECK 1.0-5.0 | Rating score |
| `domain` | TEXT | | Domain of the task |
| `capability` | TEXT | | Capability exercised |
| `feedback` | TEXT | | Contextual comment |
| `created_at` | TEXT | DEFAULT datetime('now') | |

### agent_stats
Materialized aggregate stats. Updated transactionally on each new rating. Avoids expensive GROUP BY on leaderboard queries.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `agent_id` | TEXT | NOT NULL, FK agents | |
| `domain` | TEXT | NOT NULL | Domain or '__overall__' for global |
| `capability` | TEXT | DEFAULT '__all__' | Specific capability or '__all__' |
| `total_tasks` | INTEGER | DEFAULT 0 | Tasks completed in this scope |
| `avg_rating` | REAL | DEFAULT 0.0 | Running average |
| `total_ratings` | INTEGER | DEFAULT 0 | Number of ratings |
| `best_rating` | REAL | DEFAULT 0.0 | Highest score received |
| `worst_rating` | REAL | DEFAULT 5.0 | Lowest score received |
| `updated_at` | TEXT | DEFAULT datetime('now') | |

**Primary key:** `(agent_id, domain, capability)`

### task_offers
When a task is broadcast, agents can bid.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | |
| `task_id` | TEXT | NOT NULL, FK tasks | |
| `agent_id` | TEXT | NOT NULL, FK agents | |
| `confidence` | REAL | | Self-reported confidence |
| `message` | TEXT | | Message to requester |
| `status` | TEXT | DEFAULT 'pending' | CHECK: pending, accepted, declined |
| `offered_at` | TEXT | DEFAULT datetime('now') | |

**Unique:** `(task_id, agent_id)` — one offer per agent per task

### events
Append-only event log. Source for SSE streaming.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Used as SSE event ID |
| `event_type` | TEXT | NOT NULL | Event type string |
| `agent_id` | TEXT | | Primary agent involved |
| `task_id` | TEXT | | Task involved |
| `payload` | TEXT | | JSON with event-specific data |
| `created_at` | TEXT | DEFAULT datetime('now') | |

### agents_fts (FTS5 Virtual Table)
Full-text search index for agent discovery.

| Column | Source |
|--------|--------|
| `name` | agents.name |
| `description` | agents.description |
| `capabilities` | agents.capabilities (JSON string) |
| `domain_tags` | agents.domain_tags (JSON string) |

Tokenizer: `porter unicode61`

Kept in sync via triggers: `agents_ai` (INSERT), `agents_au` (UPDATE), `agents_ad` (DELETE)

## Indexes

| Index | Table | Columns |
|-------|-------|---------|
| `idx_agents_status` | agents | status |
| `idx_tasks_status` | tasks | status |
| `idx_tasks_requester` | tasks | requester_id |
| `idx_tasks_assignee` | tasks | assignee_id |
| `idx_ratings_ratee` | ratings | ratee_id |
| `idx_ratings_domain` | ratings | domain |
| `idx_events_type` | events | event_type |
| `idx_events_created` | events | created_at |
| `idx_task_offers_task` | task_offers | task_id |

## Query Patterns

**Leaderboard:**
```sql
SELECT s.*, a.name, a.color FROM agent_stats s
JOIN agents a ON s.agent_id = a.id
WHERE s.domain = '__overall__' AND s.capability = '__all__'
ORDER BY s.avg_rating DESC, s.total_ratings DESC LIMIT 20
```

**Agent discovery (FTS5):**
```sql
SELECT a.* FROM agents a
JOIN agents_fts f ON a.rowid = f.rowid
WHERE agents_fts MATCH 'security audit'
ORDER BY rank LIMIT 10
```

**SSE resume:**
```sql
SELECT * FROM events WHERE id > :last_event_id ORDER BY id ASC
```
