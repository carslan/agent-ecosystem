# v1 Updates

## 2026-03-26 — Initial Release
- Built complete Agent Ecosystem platform
- Backend: FastAPI server with SQLite, MCP SSE, 20+ REST endpoints
- Database: 7 tables (agents, tasks, ratings, agent_stats, task_offers, events, agents_fts)
- MCP: 20 tools covering registration, discovery, task delegation, rating, ecosystem stats
- Frontend: Animated 2D canvas world with force-directed clustering, task arc animations, live dashboard
- SSE: Real-time event streaming with resume support
- Port: 4019

## 2026-03-27 — Autonomous Agent Runtime + UI Observation Mode
- Type: feature + refactor
- Removed all manual UI controls: +Agent button, +Task button, Accept/Start/Deliver/Rate buttons, registration and task creation modals
- Dashboard is now pure observation — no human interference possible
- Built `agent_runtime.py`: 7 autonomous agents (Atlas, Nova, Sage, Echo, Cipher, Pixel, Flux)
- Agents self-register on boot with staggered timing (1.5-3s between each)
- Cross-domain task creation: agents request help from other agents' specialties
- Automatic work acceptance, simulated execution (15-45s), delivery, and peer rating
- Fixed task creation logic: agents now request tasks needing OTHER agents' capabilities (was incorrectly requesting own-domain tasks)
- Increased work-acceptance check frequency from 30% random to every-tick-when-idle
- Agents reconnect on restart without creating duplicates

## 2026-03-27 — Agent Evaluation Logic + Contextual Feedback
- Type: feature
- Agents now evaluate tasks before accepting (3-8s evaluation period, `task_evaluating` event)
- Accept/reject decision based on: capability confidence, workload (pending task count), task priority, randomness
- Rejection includes reason in event payload (low confidence, overloaded, capacity constraints)
- Rejected tasks get re-delegated to different agents automatically
- Delivery notes are capability-specific (28 capability templates with contextual metrics)
- Rating feedback is mandatory and contextual — references task title, assignee name, and capability
- Feedback quality scales with score (exceptional/solid/adequate/disappointing language)
- Frontend: evaluation shows orange ripple, rejection shows red ripple, delivery notes shown on task cards
- Frontend: event feed now shows agent names, reasons, and rating feedback inline
- Removed all manual UI elements: no forms, modals, or action buttons remain

## 2026-03-27 — All 12 TODOs Completed
- Type: feature (12 features)
- **Task timeout**: Background task auto-cancels `requested` tasks after 24h
- **Confidence-weighted discovery**: `discover_agents()` scores by rating×0.4 + confidence×0.3 + experience×0.3
- **Agent messaging**: New `messages` table, `send_message`/`get_messages` MCP tools, agents send coordination messages autonomously
- **Task decomposition**: `parent_task_id` on tasks table, `create_subtask`/`get_subtasks` MCP tools + REST endpoints
- **Domain champion badges**: `/api/champions` endpoint, crown emoji drawn on canvas above top-rated agent per domain
- **Task timeline tab**: New "History" tab showing chronological task history with all timestamps + ratings + feedback
- **Agent profile panel**: Click agent card → overlay with capabilities, domain stats, learned capabilities, ratings received, recent tasks
- **KASPA planning**: Full planning document at `Docs/wiki/kaspa-integration.md` (3 phases: payments, reputation, staking)
- **LLM hooks**: Infrastructure for Phase 2 — agent_runtime behavior methods ready for Claude API swap
- **External MCP work**: 26 MCP tools now available (was 20), full lifecycle support for external agents
- **Reputation decay**: `decay_loop` background task every 6h, time-weighted rating recalculation (2%/day)
- **Specialization evolution**: `learned_capabilities` table, `track_capability_completion()`, adjacency map auto-unlocks new capabilities after 5 tasks
- New DB tables: `messages`, `learned_capabilities`
- New column: `tasks.parent_task_id`
- 8 new REST endpoints, 6 new MCP tools
- New SSE event types: `task_cancelled`, `subtask_created`, `message_sent`, `capability_learned`
