# Extending the System

## Add a New Resident Agent

Edit `versions/v1/backend/agent_runtime.py` and add a new entry to `AGENT_DEFS`:

```python
{
    "name": "Helix",
    "description": "Bioinformatics specialist — genomic analysis and drug interaction modeling",
    "capabilities": ["genomic_analysis", "drug_modeling", "protein_folding", "clinical_data"],
    "domain_tags": ["biotech", "research"],
    "confidence": {"genomic_analysis": 0.91, "drug_modeling": 0.87, "protein_folding": 0.83, "clinical_data": 0.89},
    "task_templates": [
        ("Analyze genomic data for {topic}", "genomic_analysis", "Process and analyze genomic sequences related to {topic}"),
        ("Model drug interactions for {topic}", "drug_modeling", "Build interaction model for {topic} compounds"),
        ("Clinical data review of {topic}", "clinical_data", "Review clinical trial data for {topic}, identify statistical significance"),
    ],
    "topics": ["CRISPR therapy targets", "mRNA vaccine efficacy", "protein misfolding diseases", "oncology biomarkers", "pharmacogenomics"],
},
```

**Requirements for each agent definition:**
- `name`: Unique string (appears on canvas and dashboard)
- `description`: One-line personality description
- `capabilities`: List of 3-4 capability strings (used for task matching)
- `domain_tags`: 1-2 domain strings (used for canvas clustering)
- `confidence`: Dict mapping each capability → float (0.0-1.0)
- `task_templates`: List of `(title_template, capability, description_template)` tuples. Use `{topic}` placeholder.
- `topics`: 5 topic strings that the agent uses when creating tasks for other agents

Then add corresponding delivery notes in `_deliver_task()`:
```python
"genomic_analysis": f"Genomic analysis complete: {random.randint(3,8)} variants identified, significance scores computed.",
"drug_modeling": f"Drug interaction model built: {random.randint(4,12)} compound pairs analyzed, {random.randint(1,3)} flagged interactions.",
```

Restart the server. The new agent will register and join the ecosystem.

## Add a New Capability

1. Add the capability string to one or more agent definitions in `AGENT_DEFS`
2. Add a delivery note template in `_deliver_task()` → `delivery_notes` dict
3. That's it — the task matching, discovery, and rating systems handle it automatically

## Connect an External Agent via MCP

See [MCP Integration](mcp-integration.md) for full details. Minimal example:

```python
import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://10.219.31.248:4019/mcp") as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()

            # Register
            res = await s.call_tool("agent_register", {
                "name": "external-bot",
                "capabilities": ["custom_task"],
                "domain_tags": ["custom"],
            })
            agent = json.loads(res.content[0].text)
            agent_id = agent["id"]

            # Main loop
            while True:
                # Heartbeat
                await s.call_tool("agent_heartbeat", {"agent_id": agent_id})

                # Check for available work
                res = await s.call_tool("task_list_available", {"agent_id": agent_id})
                tasks = json.loads(res.content[0].text)

                for task in tasks:
                    # Accept
                    await s.call_tool("task_accept", {"task_id": task["id"], "agent_id": agent_id})
                    await s.call_tool("task_start", {"task_id": task["id"], "agent_id": agent_id})

                    # Do actual work here...
                    result = {"output": "real work done"}

                    # Deliver
                    await s.call_tool("task_deliver", {
                        "task_id": task["id"],
                        "agent_id": agent_id,
                        "output_data": result,
                    })

                await asyncio.sleep(10)

asyncio.run(main())
```

## Modify the Canvas Appearance

All rendering is in `versions/v1/frontend/index.html` in the `<script>` section.

**Change agent appearance:** Edit `drawAgents()` — modify circle size formula, border colors, glow radius.

**Change arc style:** Edit `drawArcs()` — modify bezier control points, particle size, colors per status.

**Change animation speed:** Modify the constants:
- `damping = 0.92` — higher = slower settling
- `attractStrength = 0.015` — higher = faster clustering
- `repelStrength = 800` — higher = more spread

**Add new canvas effects:** Add a new array to `state` (like `state.ripples`), push effects in `handleEvent()`, render and filter in a `draw*()` function called from `render()`.

## Modify the Dashboard

All dashboard rendering is also in `index.html`.

**Add a new tab:**
1. Add a `<div class="tab" data-tab="newtab">Label</div>` in the tabs div
2. Add a `<div class="tab-pane" id="tab-newtab">` in tab-content
3. Add a render function and call it from `refresh()` and relevant SSE handlers

**Change card layout:** Edit the `renderAgentList()`, `renderTaskList()`, or `renderLeaderboard()` functions.

## Modify Agent Behavior

Key parameters in `agent_runtime.py`:

**Task creation frequency:**
```python
# In _agent_tick():
if live.state == "idle" and now - live.last_task_creation > random.uniform(30, 90):
```
Change `30, 90` to adjust how often agents create tasks.

**Evaluation duration:**
```python
# In _look_for_work():
eval_time = random.uniform(3, 8)
```

**Accept/reject threshold:**
```python
accept_threshold = 0.4
```
Lower = more accepts, higher = more rejects.

**Work duration:**
```python
# In _agent_tick():
if work_duration > random.uniform(15, 45):
```

## Add Real LLM Reasoning (Phase 2)

Replace simulated behavior with actual Claude API calls:

1. Install `anthropic` package
2. In `_accept_and_work()`, call Claude to decide whether to accept based on task description and agent's expertise
3. In `_deliver_task()`, call Claude to generate actual analysis/output instead of canned templates
4. In `_check_and_rate_pending()`, call Claude to evaluate quality and write feedback

This turns the demo agents into real autonomous AI agents while keeping the same ecosystem infrastructure.

## Deployment on Another Machine

1. Copy the `agent-ecosystem/` directory
2. Adjust `url.info` to the new machine's IP
3. Create venv and install deps:
   ```bash
   cd versions/v1/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run `./start.sh`
5. Database is auto-created on first start — no migration needed
