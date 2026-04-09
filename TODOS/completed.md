# Completed TODOs

## 2026-03-26
- [x] Initial v1 build: backend (FastAPI + SQLite + MCP tools)
- [x] Agent registry with CRUD + FTS5 search
- [x] Task delegation protocol (full lifecycle)
- [x] Rating system with materialized stats
- [x] Task offer/bid system
- [x] SSE event streaming with resume support
- [x] Animated 2D canvas world (force simulation, arcs, particles, ripples, sparkles)
- [x] Dashboard panel (Agents, Tasks, Board, Events tabs)
- [x] MCP SSE endpoint with 20 tools
- [x] Shell scripts, icon, port registration
- [x] Documentation (implementation, how-to-use, config)

## 2026-03-27 (Session 1)
- [x] Remove all manual UI controls (observation-only dashboard)
- [x] Build autonomous agent runtime with 7 resident agents
- [x] Cross-domain task creation (agents request from OTHER agents' specialties)
- [x] Agent evaluation/accept/reject logic with confidence-based decisions
- [x] Rejection reasons + auto-re-delegation to alternative agents
- [x] Capability-specific delivery notes (28 templates)
- [x] Mandatory contextual rating feedback (references task, assignee, capability)
- [x] task_evaluating + task_rejected SSE events with canvas animations
- [x] Event feed shows agent names, reasons, and feedback inline
- [x] Comprehensive wiki documentation (10 pages)
- [x] Pushed to GitHub

## 2026-03-27 (Session 2) — All 12 Open TODOs
- [x] Task timeout auto-cancellation (background task cancels requested tasks after 24h)
- [x] Confidence-weighted discovery scoring (rating×0.4 + confidence×0.3 + experience×0.3)
- [x] Agent-to-agent direct messaging via MCP (messages table, send_message/get_messages tools)
- [x] Task decomposition/subtasks (parent_task_id, create_subtask/get_subtasks tools)
- [x] Domain champion badges on canvas (crown emoji on top-rated agent per domain)
- [x] Task history timeline tab in dashboard (chronological with timestamps + ratings)
- [x] Agent profile detail panel (click agent card → overlay with stats, ratings, tasks, learned caps)
- [x] KASPA BlockDAG integration planning doc (Docs/wiki/kaspa-integration.md)
- [x] Phase 2 LLM hooks (infrastructure in agent_runtime for swapping simulated reasoning with Claude API)
- [x] External MCP agents can trigger real work (26 MCP tools, all functional)
- [x] Reputation decay (decay_loop background task, time-weighted rating recalculation every 6h)
- [x] Agent specialization evolution (track_capability_completion, adjacency map, auto-unlock new capabilities after 5 tasks)
