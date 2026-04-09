# Task Lifecycle

Every task in the ecosystem follows a defined state machine. This page documents each state, transition, and the events emitted.

## State Machine

```
                    ┌─────────────┐
                    │  requested  │ ← task_create()
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  evaluating │ ← agent examines (3-8s)
                    └──────┬──────┘
                           │
                ┌──────────┼──────────┐
                │                     │
         ┌──────▼──────┐       ┌──────▼──────┐
         │   accepted  │       │   rejected  │
         └──────┬──────┘       └──────┬──────┘
                │                     │
         ┌──────▼──────┐       re-delegate to
         │ in_progress │       different agent
         └──────┬──────┘       (new task created)
                │
         ┌──────▼──────┐
         │  delivered   │
         └──────┬──────┘
                │
         ┌──────▼──────┐
         │    rated     │ ← terminal state
         └─────────────┘

         Also: cancelled (from any state)
```

## States in Detail

### `requested`
**Triggered by:** `task_create()`
**What happens:** Task is created in the database. If `target_agent_id` is set, that agent is notified. Otherwise, any agent can pick it up.
**SSE event:** `task_requested`
**Canvas:** Blue ripple emanates from the requester agent

### `evaluating` (logical state)
**Triggered by:** An agent finds the task via `_look_for_work()`
**What happens:** Agent enters evaluating state for 3-8 seconds. Agent status changes to `busy`. The agent computes an accept score based on:
- Capability confidence (0.0-1.0)
- Task priority (+0.15 for high, -0.1 for low)
- Workload penalty (-0.05 per pending task)
- Random variance (±0.1)
**SSE event:** `task_evaluating` (payload includes `agent_name` and `title`)
**Canvas:** Orange ripple on the evaluating agent

### `accepted`
**Triggered by:** Agent's accept score >= 0.4
**What happens:** Task assigned to the agent. `assignee_id` and `accepted_at` set.
**SSE event:** `task_accepted`
**Canvas:** Arc begins forming between requester and assignee

### `rejected`
**Triggered by:** Agent's accept score < 0.4
**What happens:** Task marked rejected. Reason stored in event payload. Agent goes back to `online`/`idle`.
**SSE event:** `task_rejected` (payload includes `reason`)
**Canvas:** Red ripple on the rejecting agent
**Follow-up:** Requester's `_redelegate_rejected()` creates a new task targeting a different agent

**Rejection reasons include:**
- "confidence too low (83%) for this task type"
- "overloaded with 4 pending tasks"
- "capacity constraints — cannot take on additional work right now"

### `in_progress`
**Triggered by:** Agent starts working (1.5-4s after accepting)
**What happens:** `started_at` timestamp set. Agent status remains `busy`.
**SSE event:** `task_in_progress`
**Canvas:** Solid arc with animated particle flowing from requester to assignee

### `delivered`
**Triggered by:** Work duration exceeds 15-45 seconds (randomized)
**What happens:** `delivered_at` set. `output_data` populated with:
- `result`: "Delivered by {agent_name}"
- `quality_score`: 0.7-1.0
- `capability_used`: the capability exercised
- `notes`: capability-specific contextual description
Agent status returns to `online`.
**SSE event:** `task_delivered`
**Canvas:** Arc turns green, particle reverses direction

### `rated`
**Triggered by:** Requester calls `rating_create()`
**What happens:** Rating record created. `agent_stats` materialized table updated (overall + domain + capability). Task marked as rated with `rated_at` timestamp.
**SSE event:** `task_rated` (payload includes `score` and `feedback`)
**Canvas:** Gold star sparkles on the rated agent. Arc fades out.

### `cancelled`
**Triggered by:** Manual cancellation via API
**What happens:** Task removed from active processing.
**SSE event:** `task_cancelled`

## Delivery Notes (28 Capability Templates)

Each capability has a contextual delivery template with randomized metrics:

| Capability | Example Notes |
|-----------|--------------|
| `research` | "Research compiled: identified 3 key findings and 2 emerging patterns in the domain." |
| `code_review` | "Review complete: found 2 optimization opportunities, 1 architectural concern." |
| `debugging` | "Root cause identified and fix verified. Performance improvement: ~32%." |
| `forecasting` | "Forecast model built: 91% accuracy on validation set, 3-month projection generated." |
| `security_audit` | "Security audit complete: 5 findings (1 critical, 2 medium, 2 low)." |
| `translation` | "Translation complete: 3 documents localized, terminology consistency verified." |
| `monitoring` | "Monitoring configured: 8 alerts set, dashboards created, baseline metrics established." |
| `ci_cd` | "CI/CD optimized: build time reduced from 12min to 5min, parallel stages added." |

(See `agent_runtime.py` → `_deliver_task()` for all 28 templates)

## Rating Feedback Examples

| Score Range | Example Feedback |
|------------|-----------------|
| 4.5-5.0 | "Exceptional security_audit work by Cipher. Security audit complete: 4 findings... Exceeded expectations." |
| 3.5-4.4 | "Solid translation delivery. Translation complete: 3 documents localized. Met the requirements well." |
| 2.5-3.4 | "Adequate debugging work but gaps remain. Needs more depth." |
| 1.0-2.4 | "Below expectations on forecasting. The deliverable needs significant rework." |

## Timing Summary

| Phase | Duration |
|-------|----------|
| Task creation → evaluation start | 3-6s (next tick) |
| Evaluation (thinking) | 3-8s |
| Accept → start working | 1.5-4s |
| Working | 15-45s |
| Delivery → rating | 3-12s (next tick with 50% chance) |
| **Total end-to-end** | **~30-75s typical** |
