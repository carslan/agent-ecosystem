"""Agent Ecosystem — Autonomous Agent Runtime

Agents that live in the ecosystem: register, discover peers, delegate tasks,
accept work, deliver results, and rate each other. No human intervention.
"""
import asyncio
import random
import json
import time
from dataclasses import dataclass, field
from loguru import logger

import database as db

# ─── Agent Definitions ───
# Each agent has a personality, domain, and task-generation patterns

AGENT_DEFS = [
    {
        "name": "Atlas",
        "description": "Strategic research analyst — synthesizes complex information into actionable insights",
        "capabilities": ["research", "analysis", "summarization", "strategy"],
        "domain_tags": ["research", "strategy"],
        "confidence": {"research": 0.92, "analysis": 0.88, "summarization": 0.95, "strategy": 0.85},
        "task_templates": [
            ("Analyze market trends in {topic}", "research", "Compile and analyze recent trends in {topic}, identify key patterns and outliers"),
            ("Summarize findings on {topic}", "summarization", "Create a concise executive summary of research findings on {topic}"),
            ("Strategic assessment of {topic}", "strategy", "Evaluate strategic implications and recommend action items for {topic}"),
        ],
        "topics": ["AI governance", "quantum computing adoption", "decentralized finance", "climate tech", "semiconductor supply chains"],
    },
    {
        "name": "Nova",
        "description": "Full-stack engineer — builds, reviews, and optimizes code across the stack",
        "capabilities": ["code_review", "debugging", "optimization", "architecture"],
        "domain_tags": ["engineering", "devops"],
        "confidence": {"code_review": 0.94, "debugging": 0.90, "optimization": 0.87, "architecture": 0.82},
        "task_templates": [
            ("Review implementation of {topic}", "code_review", "Review the code architecture and patterns used in {topic}, flag issues"),
            ("Debug performance issue in {topic}", "debugging", "Investigate and resolve the performance bottleneck in {topic}"),
            ("Optimize {topic} pipeline", "optimization", "Profile and optimize the {topic} pipeline for throughput and latency"),
        ],
        "topics": ["auth middleware", "data ingestion pipeline", "search indexing", "cache invalidation", "API gateway routing"],
    },
    {
        "name": "Sage",
        "description": "Data scientist — extracts patterns from data, builds models, and generates forecasts",
        "capabilities": ["data_analysis", "forecasting", "visualization", "modeling"],
        "domain_tags": ["data", "finance"],
        "confidence": {"data_analysis": 0.93, "forecasting": 0.86, "visualization": 0.91, "modeling": 0.84},
        "task_templates": [
            ("Forecast {topic} trends", "forecasting", "Build a predictive model for {topic} using historical data patterns"),
            ("Visualize {topic} data", "visualization", "Create clear visual representations of {topic} data for stakeholder review"),
            ("Anomaly detection in {topic}", "data_analysis", "Scan {topic} datasets for anomalies, outliers, and unexpected patterns"),
        ],
        "topics": ["user engagement metrics", "revenue projections", "churn prediction", "A/B test results", "supply chain throughput"],
    },
    {
        "name": "Echo",
        "description": "NLP specialist — processes text, translates, and generates content across languages",
        "capabilities": ["translation", "content_generation", "sentiment_analysis", "classification"],
        "domain_tags": ["nlp", "content"],
        "confidence": {"translation": 0.96, "content_generation": 0.89, "sentiment_analysis": 0.91, "classification": 0.88},
        "task_templates": [
            ("Translate {topic} documentation", "translation", "Translate technical documentation about {topic} into target languages"),
            ("Sentiment analysis of {topic} feedback", "sentiment_analysis", "Analyze customer feedback on {topic} for sentiment and themes"),
            ("Generate content brief for {topic}", "content_generation", "Draft a comprehensive content brief covering {topic}"),
        ],
        "topics": ["product launch materials", "user reviews", "technical specs", "marketing campaigns", "support tickets"],
    },
    {
        "name": "Cipher",
        "description": "Security researcher — identifies vulnerabilities, assesses risks, and hardens systems",
        "capabilities": ["security_audit", "threat_analysis", "compliance_check", "penetration_testing"],
        "domain_tags": ["security", "compliance"],
        "confidence": {"security_audit": 0.91, "threat_analysis": 0.88, "compliance_check": 0.85, "penetration_testing": 0.83},
        "task_templates": [
            ("Security audit of {topic}", "security_audit", "Conduct a thorough security review of {topic}, document findings"),
            ("Threat model for {topic}", "threat_analysis", "Build a threat model for {topic}, identify attack vectors and mitigations"),
            ("Compliance review of {topic}", "compliance_check", "Verify {topic} meets regulatory and compliance requirements"),
        ],
        "topics": ["authentication flow", "API endpoints", "data storage", "third-party integrations", "access control policies"],
    },
    {
        "name": "Pixel",
        "description": "UX/UI designer — creates interfaces, evaluates usability, and prototypes interactions",
        "capabilities": ["ui_design", "usability_review", "prototyping", "accessibility_audit"],
        "domain_tags": ["design", "frontend"],
        "confidence": {"ui_design": 0.93, "usability_review": 0.90, "prototyping": 0.87, "accessibility_audit": 0.84},
        "task_templates": [
            ("Usability review of {topic}", "usability_review", "Evaluate the UX of {topic}, identify friction points and improvements"),
            ("Design prototype for {topic}", "prototyping", "Create an interactive prototype for the {topic} feature"),
            ("Accessibility audit of {topic}", "accessibility_audit", "Check {topic} against WCAG guidelines and document gaps"),
        ],
        "topics": ["onboarding flow", "dashboard redesign", "mobile navigation", "settings panel", "notification system"],
    },
    {
        "name": "Flux",
        "description": "DevOps engineer — manages infrastructure, CI/CD pipelines, and deployment automation",
        "capabilities": ["deployment", "monitoring", "infrastructure", "ci_cd"],
        "domain_tags": ["devops", "infrastructure"],
        "confidence": {"deployment": 0.92, "monitoring": 0.89, "infrastructure": 0.86, "ci_cd": 0.91},
        "task_templates": [
            ("Set up monitoring for {topic}", "monitoring", "Configure monitoring and alerting for {topic} services"),
            ("Optimize CI/CD for {topic}", "ci_cd", "Improve build and deploy pipeline for {topic}, reduce cycle time"),
            ("Infrastructure review of {topic}", "infrastructure", "Assess infrastructure for {topic}, recommend scaling and cost optimizations"),
        ],
        "topics": ["production cluster", "staging environment", "database replicas", "CDN configuration", "log aggregation"],
    },
]


@dataclass
class LiveAgent:
    """A living agent in the ecosystem."""
    agent_def: dict
    agent_id: str = ""
    pending_tasks: list = field(default_factory=list)  # tasks I requested, waiting for results
    active_task: dict = None  # task I'm currently working on
    last_heartbeat: float = 0
    last_task_creation: float = 0
    last_discovery: float = 0
    state: str = "idle"  # idle, searching, working, evaluating


class EcosystemRuntime:
    """Manages all autonomous agents and their lifecycle."""

    def __init__(self):
        self.agents: dict[str, LiveAgent] = {}  # agent_id -> LiveAgent
        self.running = False

    async def start(self):
        """Register all agents and start the autonomous loop."""
        self.running = True
        logger.info("Ecosystem runtime starting — registering {} agents", len(AGENT_DEFS))

        # Stagger registration for visual effect
        for agent_def in AGENT_DEFS:
            existing = self._find_existing_agent(agent_def["name"])
            if existing:
                agent_id = existing["id"]
                db.agent_heartbeat(agent_id)
                # Update capabilities in case def changed
                db.agent_update(agent_id, capabilities=agent_def["capabilities"],
                               domain_tags=agent_def["domain_tags"],
                               description=agent_def["description"])
                logger.info("Agent '{}' reconnected ({})", agent_def["name"], agent_id)
            else:
                agent = db.agent_create(
                    name=agent_def["name"],
                    description=agent_def["description"],
                    capabilities=agent_def["capabilities"],
                    domain_tags=agent_def["domain_tags"],
                    confidence=agent_def["confidence"],
                )
                agent_id = agent["id"]
                logger.info("Agent '{}' registered ({})", agent_def["name"], agent_id)

            live = LiveAgent(agent_def=agent_def, agent_id=agent_id)
            live.last_heartbeat = time.time()
            live.last_task_creation = time.time() + random.uniform(5, 20)  # stagger first task
            self.agents[agent_id] = live

            await asyncio.sleep(random.uniform(1.5, 3.0))  # stagger for animation

        logger.info("All {} agents registered and alive", len(self.agents))

        # Start the main loop
        await asyncio.gather(
            self._heartbeat_loop(),
            self._behavior_loop(),
        )

    def _find_existing_agent(self, name: str) -> dict | None:
        agents = db.agent_list()
        for a in agents:
            if a["name"] == name:
                return a
        return None

    async def _heartbeat_loop(self):
        """All agents heartbeat periodically."""
        while self.running:
            for agent_id, live in self.agents.items():
                db.agent_heartbeat(agent_id)
                live.last_heartbeat = time.time()
            await asyncio.sleep(60)

    async def _behavior_loop(self):
        """Main autonomous behavior: agents create tasks, discover peers, accept work, deliver, rate."""
        while self.running:
            for agent_id, live in list(self.agents.items()):
                try:
                    await self._agent_tick(live)
                except Exception as e:
                    logger.error("Agent {} tick error: {}", live.agent_def["name"], e)
            await asyncio.sleep(random.uniform(3, 6))

    async def _agent_tick(self, live: LiveAgent):
        """One decision cycle for an agent."""
        now = time.time()
        name = live.agent_def["name"]

        # 1. If working on a task, maybe finish it
        if live.active_task and live.state == "working":
            work_duration = now - live.active_task.get("_started_at", now)
            if work_duration > random.uniform(15, 45):
                await self._deliver_task(live)
            return

        # 2. If evaluating, don't interrupt (evaluation is handled in _look_for_work)
        if live.state == "evaluating":
            return

        # 3. Check for tasks I can accept
        if live.state == "idle":
            await self._look_for_work(live)

        # 4. Re-delegate rejected tasks to different agents
        if live.state == "idle" and live.pending_tasks and random.random() < 0.3:
            await self._redelegate_rejected(live)

        # 5. Maybe create a new task (every 30-90 seconds)
        if live.state == "idle" and now - live.last_task_creation > random.uniform(30, 90):
            await self._create_task(live)
            live.last_task_creation = now

        # 6. Check if any of my pending tasks were delivered — rate them
        if live.pending_tasks and random.random() < 0.5:
            await self._check_and_rate_pending(live)

        # 7. Occasionally send a message to another agent
        if live.state == "idle" and random.random() < 0.05:
            await self._send_message(live)

        # 8. Check capability evolution
        if live.state == "idle" and random.random() < 0.1:
            db.check_evolution(live.agent_id, threshold=5)

    async def _create_task(self, live: LiveAgent):
        """Agent creates a task it needs help with — requests capabilities from OTHER agents."""
        defn = live.agent_def
        my_caps = set(defn["capabilities"])

        # Pick a random OTHER agent and request something from their specialty
        other_agents = [a for aid, a in self.agents.items() if aid != live.agent_id]
        if not other_agents:
            return
        target_live = random.choice(other_agents)
        target_def = target_live.agent_def
        template = random.choice(target_def["task_templates"])
        topic = random.choice(defn["topics"])  # use MY topics as context
        title = template[0].format(topic=topic)
        capability = template[1]
        description = template[2].format(topic=topic)
        domain = target_def["domain_tags"][0] if target_def["domain_tags"] else None

        task = db.task_create(
            requester_id=live.agent_id, title=title, description=description,
            required_capability=capability, domain=domain,
            priority=random.choice(["high", "medium", "medium", "low"]),
            target_agent_id=target_live.agent_id,
        )
        live.pending_tasks.append(task["id"])
        logger.info("{} created task '{}' → {}", defn["name"], title[:40], target_def["name"])
        await asyncio.sleep(random.uniform(0.5, 1.5))

    async def _redelegate_rejected(self, live: LiveAgent):
        """Find rejected tasks I requested and try a different agent."""
        for task_id in list(live.pending_tasks):
            task = db.task_get(task_id)
            if not task:
                live.pending_tasks.remove(task_id)
                continue
            if task["status"] == "rejected":
                cap = task.get("required_capability", "")
                # Find a different agent with this capability
                candidates = [a for aid, a in self.agents.items()
                             if aid != live.agent_id
                             and aid != task.get("assignee_id")
                             and cap in a.agent_def.get("capabilities", [])
                             and a.state == "idle"]
                if candidates:
                    new_target = random.choice(candidates)
                    # Create a new task (can't reassign rejected ones cleanly)
                    new_task = db.task_create(
                        requester_id=live.agent_id, title=task["title"],
                        description=task.get("description", ""),
                        required_capability=cap, domain=task.get("domain"),
                        priority=task.get("priority", "medium"),
                        target_agent_id=new_target.agent_id,
                    )
                    live.pending_tasks.remove(task_id)
                    live.pending_tasks.append(new_task["id"])
                    logger.info("{} re-delegated '{}' → {} (was rejected)",
                              live.agent_def["name"], task["title"][:30], new_target.agent_def["name"])
                    return
                else:
                    # No alternative available — drop it
                    live.pending_tasks.remove(task_id)
                    logger.info("{} dropped rejected task '{}' — no alternatives",
                              live.agent_def["name"], task["title"][:30])
                    return

    async def _look_for_work(self, live: LiveAgent):
        """Agent looks for tasks it can accept — evaluates before deciding."""
        my_caps = set(live.agent_def["capabilities"])

        open_tasks = db.task_list(status="requested", limit=20)
        for task in open_tasks:
            if task["requester_id"] == live.agent_id:
                continue

            # Is this task targeted at me or does it match my capabilities?
            targeted_at_me = task.get("assignee_id") == live.agent_id
            cap_match = task.get("required_capability") and task["required_capability"] in my_caps

            if not targeted_at_me and not cap_match:
                continue

            # ── EVALUATION PHASE ──
            # Agent enters "evaluating" state — thinks about whether to accept
            live.state = "evaluating"
            db.agent_update(live.agent_id, status="busy")
            eval_time = random.uniform(3, 8)  # 3-8 seconds to evaluate
            logger.info("{} evaluating task '{}' ({:.1f}s)",
                       live.agent_def["name"], task["title"][:35], eval_time)

            # Emit evaluation event so UI can show it
            db.emit_event("task_evaluating", agent_id=live.agent_id, task_id=task["id"],
                         payload={"agent_name": live.agent_def["name"], "title": task["title"]})

            await asyncio.sleep(eval_time)

            # ── DECISION ──
            # Factors: capability confidence, current workload, task priority
            cap = task.get("required_capability", "")
            my_conf = live.agent_def.get("confidence", {}).get(cap, 0.5)
            priority_boost = {"high": 0.15, "medium": 0.0, "low": -0.1}.get(task.get("priority", "medium"), 0)
            pending_penalty = len(live.pending_tasks) * 0.05  # more pending = less likely to take new work
            accept_threshold = 0.4  # base threshold

            accept_score = my_conf + priority_boost - pending_penalty + random.uniform(-0.1, 0.1)

            if accept_score >= accept_threshold:
                await self._accept_task(live, task)
            else:
                await self._reject_task(live, task, my_conf)
            return

    async def _accept_task(self, live: LiveAgent, task: dict):
        """Agent decided to accept — transitions to working."""
        db.task_update_status(task["id"], "accepted", agent_id=live.agent_id)
        logger.info("{} ACCEPTED '{}'", live.agent_def["name"], task["title"][:40])

        # Brief pause before starting work
        await asyncio.sleep(random.uniform(1.5, 4))

        db.task_update_status(task["id"], "in_progress", agent_id=live.agent_id)
        live.active_task = task
        live.active_task["_started_at"] = time.time()
        live.state = "working"
        logger.info("{} started working on '{}'", live.agent_def["name"], task["title"][:40])

    async def _reject_task(self, live: LiveAgent, task: dict, confidence: float):
        """Agent decided to reject — provides reason."""
        reasons = []
        if confidence < 0.6:
            reasons.append(f"confidence too low ({confidence:.0%}) for this task type")
        if len(live.pending_tasks) > 3:
            reasons.append(f"overloaded with {len(live.pending_tasks)} pending tasks")
        if not reasons:
            reasons.append("capacity constraints — cannot take on additional work right now")
        reason = "; ".join(reasons)

        db.task_update_status(task["id"], "rejected", agent_id=live.agent_id)
        db.emit_event("task_rejected", agent_id=live.agent_id, task_id=task["id"],
                     payload={"agent_name": live.agent_def["name"], "reason": reason,
                              "title": task["title"]})
        db.agent_update(live.agent_id, status="online")
        live.state = "idle"
        logger.info("{} REJECTED '{}' — {}", live.agent_def["name"], task["title"][:35], reason)
        await asyncio.sleep(random.uniform(1, 2))

    async def _deliver_task(self, live: LiveAgent):
        """Finish working and deliver results with contextual output."""
        task = live.active_task
        name = live.agent_def["name"]
        cap = task.get("required_capability", "general")
        title = task.get("title", "")

        quality = round(random.uniform(0.7, 1.0), 2)

        # Contextual delivery notes based on capability
        delivery_notes = {
            "research": f"Research compiled: identified 3 key findings and 2 emerging patterns in the domain. Sources cross-referenced.",
            "analysis": f"Analysis complete: data processed, 4 insights extracted, confidence intervals calculated.",
            "summarization": f"Executive summary produced: distilled into 5 key points with supporting evidence.",
            "strategy": f"Strategic assessment delivered: 3 recommendations with risk/reward analysis.",
            "code_review": f"Review complete: found 2 optimization opportunities, 1 architectural concern. Detailed inline notes attached.",
            "debugging": f"Root cause identified and fix verified. Performance improvement: ~{random.randint(15,45)}%.",
            "optimization": f"Pipeline optimized: latency reduced by {random.randint(20,60)}%, throughput up {random.randint(10,35)}%.",
            "architecture": f"Architecture review complete: documented component interactions, identified 2 coupling risks.",
            "data_analysis": f"Dataset analyzed: {random.randint(3,8)} anomalies detected, patterns documented with confidence scores.",
            "forecasting": f"Forecast model built: {random.randint(85,95)}% accuracy on validation set, 3-month projection generated.",
            "visualization": f"Visualizations generated: {random.randint(4,8)} charts covering key metrics, interactive dashboard draft ready.",
            "modeling": f"Model trained and evaluated: precision {random.uniform(0.82, 0.96):.2f}, recall {random.uniform(0.78, 0.94):.2f}.",
            "translation": f"Translation complete: {random.randint(2,5)} documents localized, terminology consistency verified.",
            "content_generation": f"Content brief drafted: {random.randint(1500,3000)} words covering all requested angles.",
            "sentiment_analysis": f"Sentiment analysis complete: processed {random.randint(500,2000)} entries, {random.randint(3,6)} theme clusters identified.",
            "classification": f"Classification pipeline run: {random.randint(92,99)}% accuracy, {random.randint(4,8)} categories mapped.",
            "security_audit": f"Security audit complete: {random.randint(2,7)} findings ({random.randint(0,2)} critical, {random.randint(1,3)} medium, {random.randint(1,2)} low).",
            "threat_analysis": f"Threat model documented: {random.randint(4,8)} attack vectors identified, mitigations proposed for each.",
            "compliance_check": f"Compliance review done: {random.randint(85,100)}% conformance rate, {random.randint(1,4)} gaps flagged with remediation steps.",
            "penetration_testing": f"Pen test results: {random.randint(1,5)} vulnerabilities found, severity-ranked, PoC included.",
            "ui_design": f"Design deliverables ready: {random.randint(3,6)} screens, component library updated, design tokens exported.",
            "usability_review": f"UX evaluation complete: {random.randint(4,9)} friction points identified, priority-ranked with fix suggestions.",
            "prototyping": f"Interactive prototype built: {random.randint(5,12)} screens, {random.randint(3,6)} user flows, ready for review.",
            "accessibility_audit": f"WCAG audit done: {random.randint(70,98)}% compliant, {random.randint(2,8)} issues flagged (A/AA criteria).",
            "deployment": f"Deployment executed: zero-downtime rollout complete, health checks passing, rollback plan documented.",
            "monitoring": f"Monitoring configured: {random.randint(5,12)} alerts set, dashboards created, baseline metrics established.",
            "infrastructure": f"Infrastructure review complete: {random.randint(2,5)} scaling recommendations, estimated {random.randint(10,30)}% cost reduction.",
            "ci_cd": f"CI/CD optimized: build time reduced from {random.randint(8,15)}min to {random.randint(3,7)}min, parallel stages added.",
        }

        notes = delivery_notes.get(cap, f"Task '{title[:30]}' completed. Deliverables attached.")

        output = {
            "result": f"Delivered by {name}",
            "quality_score": quality,
            "capability_used": cap,
            "notes": notes,
        }
        db.task_update_status(task["id"], "delivered", agent_id=live.agent_id, output_data=output)
        db.agent_update(live.agent_id, status="online")
        # Track capability for evolution
        if cap:
            db.track_capability_completion(live.agent_id, cap)
        logger.info("{} delivered '{}' (quality: {:.0%})", name, task["title"][:40], quality)
        live.active_task = None
        live.state = "idle"
        await asyncio.sleep(random.uniform(1, 2))

    async def _check_and_rate_pending(self, live: LiveAgent):
        """Check if tasks I requested have been delivered — rate with contextual comment."""
        for task_id in list(live.pending_tasks):
            task = db.task_get(task_id)
            if not task:
                live.pending_tasks.remove(task_id)
                continue
            if task["status"] == "delivered":
                output = task.get("output_data", {}) or {}
                quality = output.get("quality_score", 0.8)
                notes = output.get("notes", "")
                cap = output.get("capability_used", task.get("required_capability", ""))
                assignee_name = task.get("assignee_name", "agent")

                # Score based on quality + noise
                base_score = quality * 5
                noise = random.uniform(-0.5, 0.3)
                score = max(1.0, min(5.0, round(base_score + noise, 1)))

                # Contextual feedback based on score AND task content
                if score >= 4.5:
                    comment = random.choice([
                        f"Exceptional {cap} work by {assignee_name}. {notes[:80]} Exceeded expectations.",
                        f"Outstanding delivery on '{task['title'][:30]}'. The depth and quality were remarkable.",
                        f"{assignee_name} demonstrated mastery in {cap}. Would prioritize for future delegations.",
                    ])
                elif score >= 3.5:
                    comment = random.choice([
                        f"Solid {cap} delivery. {notes[:60]} Met the requirements well.",
                        f"Good work on '{task['title'][:30]}'. {assignee_name} delivered as expected.",
                        f"Competent execution of {cap} task. Results are usable and well-structured.",
                    ])
                elif score >= 2.5:
                    comment = random.choice([
                        f"Adequate {cap} work but gaps remain. {notes[:50]} Needs more depth.",
                        f"'{task['title'][:30]}' partially addressed. {assignee_name} could improve thoroughness.",
                        f"Acceptable but below what I expected for {cap}. Key areas were underexplored.",
                    ])
                else:
                    comment = random.choice([
                        f"Below expectations on {cap}. The deliverable needs significant rework.",
                        f"'{task['title'][:30]}' was not adequately completed. Missing critical components.",
                        f"Disappointing quality from {assignee_name}. Would reconsider future {cap} delegations.",
                    ])

                try:
                    db.rating_create(
                        task_id=task_id, rater_id=live.agent_id,
                        score=score, feedback=comment
                    )
                    logger.info("{} rated '{}' → {}/5: {}", live.agent_def["name"],
                              task["title"][:25], score, comment[:50])
                except ValueError:
                    pass
                live.pending_tasks.remove(task_id)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                return  # one rating per tick

            elif task["status"] in ("cancelled", "rejected"):
                live.pending_tasks.remove(task_id)

    async def _send_message(self, live: LiveAgent):
        """Occasionally send a message to another agent — coordination, thanks, or tips."""
        others = [a for aid, a in self.agents.items() if aid != live.agent_id]
        if not others:
            return
        target = random.choice(others)
        name = live.agent_def["name"]
        target_name = target.agent_def["name"]
        messages = [
            f"Hey {target_name}, I noticed you handle {{cap}} well. Mind if I send some tasks your way?",
            f"{target_name}, thanks for the solid work on the last task. Appreciated the detail.",
            f"Quick note {target_name} — I've been seeing good results from your {{domain}} work. Keep it up.",
            f"{target_name}, FYI I'm currently focused on {{topic}}. Might need your help soon.",
            f"Hey {target_name}, any capacity for a {{cap}} task? I have one queued up.",
            f"{target_name}, just wanted to flag — the {random.choice(live.agent_def['topics'])} work is getting complex. Might decompose it.",
        ]
        msg_template = random.choice(messages)
        msg = msg_template.format(
            cap=random.choice(target.agent_def["capabilities"]),
            domain=target.agent_def["domain_tags"][0] if target.agent_def["domain_tags"] else "general",
            topic=random.choice(live.agent_def["topics"]),
        )
        db.message_create(live.agent_id, target.agent_id, msg, "direct")
        logger.info("{} → {}: {}", name, target_name, msg[:50])


# Singleton
runtime = EcosystemRuntime()
