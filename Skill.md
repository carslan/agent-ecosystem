## Memory

This app uses the **MCP Memory Server** for all persistent memory, context, and task state.

**Session ID:** `agent-ecosystem`
**On start:** `session_boot(session_id="agent-ecosystem")`
**Learn a tool:** `tool_guide(tool_name="memory_store")` — returns request/response payload and example

### Available Tools

| Tool | Purpose |
|------|---------|
| `session_boot` | Load all context on startup |
| `session_create` | Create new session |
| `session_list` | List sessions |
| `memory_store` | Store a new memory |
| `memory_search` | Search with confidence scoring |
| `memory_recall` | Get memory by ID (expand L2) |
| `memory_update` | Update memory fields |
| `memory_list` | List memories with filters |
| `context_compress` | Compress conversation to summary + ref |
| `context_expand` | Expand compressed reference |
| `context_list` | List compressed contexts |
| `activity_log` | Record last action |
| `activity_get` | Get last action |
| `session_note_add` | Add journal entry |
| `session_notes_list` | List journal entries |
| `todo_add` | Create todo |
| `todo_update` | Update todo status |
| `todo_list` | List todos |
| `app_create` | Create app scope |
| `chat_create` | Create chat scope |
| `web_store` | Store URL as memory |
| `decay_run` | Trigger decay/promotion cycle |
| `decay_stats` | Tier distribution stats |
| `system_stats` | Overall system stats |
| `import_markdown` | Import .md file as memories |
| `export_markdown` | Export memories as markdown |
| `tool_guide` | Learn how to use any tool |

### Tiers
- **L1**: Critical — always loaded on boot
- **L2**: Important — summary on boot, expand on demand
- **L3**: Archive — only found via search

### Memory Types
| Type | Use for |
|------|---------|
| `primary` | Core facts, active constraints, key decisions |
| `secondary` | Supporting context, less critical but useful |
| `skill` | Learned patterns, techniques, how-to knowledge |
| `tool` | Tool/library-specific knowledge, configs |
| `feature` | App feature documentation |
| `boot_strategy` | What to load or check on startup |
| `web` | Web page references, URL bookmarks |
| `implementation_note` | Technical decisions, design rationale |
| `reference` | Pointers to external resources, docs, configs |
