"""Agent Ecosystem — MCP Tool definitions for agent-to-agent communication"""
import json
from mcp.server.fastmcp import FastMCP

import database as db

mcp = FastMCP("agent-ecosystem")


# ─── Registration & Identity ───

@mcp.tool()
def agent_register(name: str, capabilities: list[str], domain_tags: list[str],
                   description: str = "", confidence: dict = None,
                   endpoint_url: str = None) -> str:
    """Register an agent in the ecosystem. Returns the agent profile with assigned ID and color."""
    agent = db.agent_create(name=name, description=description, capabilities=capabilities,
                            domain_tags=domain_tags, confidence=confidence,
                            endpoint_url=endpoint_url)
    return json.dumps(agent, default=str)


@mcp.tool()
def agent_update(agent_id: str, capabilities: list[str] = None, domain_tags: list[str] = None,
                 confidence: dict = None, status: str = None, description: str = None) -> str:
    """Update an agent's profile (capabilities, status, etc.)."""
    kwargs = {}
    if capabilities is not None: kwargs["capabilities"] = capabilities
    if domain_tags is not None: kwargs["domain_tags"] = domain_tags
    if confidence is not None: kwargs["confidence"] = confidence
    if status is not None: kwargs["status"] = status
    if description is not None: kwargs["description"] = description
    agent = db.agent_update(agent_id, **kwargs)
    if not agent:
        return json.dumps({"error": "Agent not found"})
    return json.dumps(agent, default=str)


@mcp.tool()
def agent_heartbeat(agent_id: str) -> str:
    """Send a keep-alive heartbeat. Call periodically to stay 'online'."""
    ok = db.agent_heartbeat(agent_id)
    return json.dumps({"success": ok})


@mcp.tool()
def agent_deregister(agent_id: str) -> str:
    """Remove an agent from the ecosystem."""
    ok = db.agent_delete(agent_id)
    return json.dumps({"success": ok})


# ─── Discovery ───

@mcp.tool()
def agent_discover(capability: str = None, domain: str = None,
                   query: str = None, min_rating: float = 0.0, limit: int = 10) -> str:
    """Find agents by capability, domain, or free-text search. Returns ranked list."""
    results = []
    if query:
        results = db.agent_search_fts(query, limit=limit)
    else:
        results = db.agent_list(domain=domain, capability=capability)
    # Filter by min_rating
    if min_rating > 0:
        results = [a for a in results if a.get("rating_avg", 0) >= min_rating]
    # Sort by rating desc, then total_tasks desc
    results.sort(key=lambda a: (a.get("rating_avg", 0), a.get("total_tasks", 0)), reverse=True)
    return json.dumps(results[:limit], default=str)


@mcp.tool()
def agent_profile(agent_id: str) -> str:
    """Get full profile of a specific agent including stats and recent ratings."""
    agent = db.agent_get(agent_id)
    if not agent:
        return json.dumps({"error": "Agent not found"})
    ratings = db.rating_list(ratee_id=agent_id, limit=10)
    agent["recent_ratings"] = ratings
    return json.dumps(agent, default=str)


# ─── Task Delegation ───

@mcp.tool()
def task_create(requester_id: str, title: str, description: str = "",
                required_capability: str = None, domain: str = None,
                priority: str = "medium", input_data: dict = None,
                target_agent_id: str = None) -> str:
    """Create a task delegation request. Optionally target a specific agent."""
    task = db.task_create(requester_id=requester_id, title=title, description=description,
                          required_capability=required_capability, domain=domain,
                          priority=priority, input_data=input_data,
                          target_agent_id=target_agent_id)
    return json.dumps(task, default=str)


@mcp.tool()
def task_offer(task_id: str, agent_id: str, confidence: float = None,
               message: str = None) -> str:
    """Offer to take on a task. The requester will choose among offers."""
    offer = db.offer_create(task_id=task_id, agent_id=agent_id,
                            confidence=confidence, message=message)
    return json.dumps(offer, default=str)


@mcp.tool()
def task_accept_offer(task_id: str, offer_id: str) -> str:
    """Accept a specific offer for a task, assigning it to the offering agent."""
    offer = db.offer_accept(offer_id)
    if not offer:
        return json.dumps({"error": "Offer not found"})
    return json.dumps(offer, default=str)


@mcp.tool()
def task_accept(task_id: str, agent_id: str) -> str:
    """Directly accept a task (when targeted or self-assigning)."""
    task = db.task_update_status(task_id, "accepted", agent_id=agent_id)
    if not task:
        return json.dumps({"error": "Task not found"})
    return json.dumps(task, default=str)


@mcp.tool()
def task_reject(task_id: str, agent_id: str, reason: str = "") -> str:
    """Reject a task assignment."""
    task = db.task_update_status(task_id, "rejected", agent_id=agent_id)
    if not task:
        return json.dumps({"error": "Task not found"})
    return json.dumps(task, default=str)


@mcp.tool()
def task_start(task_id: str, agent_id: str) -> str:
    """Mark a task as in_progress (work has begun)."""
    task = db.task_update_status(task_id, "in_progress", agent_id=agent_id)
    if not task:
        return json.dumps({"error": "Task not found"})
    return json.dumps(task, default=str)


@mcp.tool()
def task_deliver(task_id: str, agent_id: str, output_data: dict = None) -> str:
    """Deliver task results."""
    task = db.task_update_status(task_id, "delivered", agent_id=agent_id, output_data=output_data)
    if not task:
        return json.dumps({"error": "Task not found"})
    return json.dumps(task, default=str)


@mcp.tool()
def task_list_available(agent_id: str, limit: int = 20) -> str:
    """List open tasks that match an agent's capabilities."""
    agent = db.agent_get(agent_id)
    if not agent:
        return json.dumps({"error": "Agent not found"})
    all_open = db.task_list(status="requested", limit=100)
    # Filter to tasks matching agent capabilities
    caps = set(agent.get("capabilities", []))
    matched = []
    for t in all_open:
        if t.get("required_capability") and t["required_capability"] in caps:
            matched.append(t)
        elif not t.get("required_capability"):
            matched.append(t)
    return json.dumps(matched[:limit], default=str)


@mcp.tool()
def task_get(task_id: str) -> str:
    """Get task details."""
    task = db.task_get(task_id)
    if not task:
        return json.dumps({"error": "Task not found"})
    return json.dumps(task, default=str)


# ─── Rating ───

@mcp.tool()
def task_rate(task_id: str, rater_id: str, score: float, feedback: str = "") -> str:
    """Rate a delivered task (1.0-5.0). Only the requester can rate."""
    try:
        rating = db.rating_create(task_id=task_id, rater_id=rater_id,
                                  score=score, feedback=feedback)
        return json.dumps(rating, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def rating_leaderboard(domain: str = None, capability: str = None, limit: int = 20) -> str:
    """Get the leaderboard — top-rated agents by domain/capability."""
    lb = db.leaderboard(domain=domain, capability=capability, limit=limit)
    return json.dumps(lb, default=str)


# ─── Ecosystem ───

@mcp.tool()
def ecosystem_stats() -> str:
    """Get platform-wide stats (agents, tasks, ratings)."""
    stats = db.ecosystem_stats()
    return json.dumps(stats, default=str)


@mcp.tool()
def ecosystem_events(limit: int = 50, event_type: str = None) -> str:
    """Get recent ecosystem events."""
    events = db.events_list(limit=limit, event_type=event_type)
    return json.dumps(events, default=str)


# ─── Messaging ───

@mcp.tool()
def send_message(from_agent_id: str, to_agent_id: str, content: str) -> str:
    """Send a direct message to another agent."""
    msg = db.message_create(from_agent_id, to_agent_id, content, "direct")
    return json.dumps(msg, default=str)


@mcp.tool()
def get_messages(agent_id: str, direction: str = "inbox", limit: int = 20) -> str:
    """Get messages for an agent. Direction: 'inbox' or 'outbox'."""
    msgs = db.message_list(agent_id, direction=direction, limit=limit)
    return json.dumps(msgs, default=str)


# ─── Subtasks ───

@mcp.tool()
def create_subtask(parent_task_id: str, requester_id: str, title: str,
                   description: str = "", required_capability: str = None,
                   domain: str = None, target_agent_id: str = None) -> str:
    """Break a task into subtasks. Creates a child task linked to the parent."""
    sub = db.task_create_subtask(parent_task_id, requester_id, title, description,
                                 required_capability, domain, target_agent_id)
    return json.dumps(sub, default=str)


@mcp.tool()
def get_subtasks(parent_task_id: str) -> str:
    """Get all subtasks of a parent task."""
    subs = db.task_get_subtasks(parent_task_id)
    return json.dumps(subs, default=str)


# ─── Champions & Timeline ───

@mcp.tool()
def domain_champions() -> str:
    """Get the top-rated agent (champion) for each domain."""
    champs = db.domain_champions()
    return json.dumps(champs, default=str)


@mcp.tool()
def task_timeline(limit: int = 50) -> str:
    """Get chronological task history with all timestamps and ratings."""
    tl = db.task_timeline(limit=limit)
    return json.dumps(tl, default=str)
