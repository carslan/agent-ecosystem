"""Agent Ecosystem — Pydantic models"""
import uuid
from typing import Optional
from pydantic import BaseModel, Field


def new_id() -> str:
    return uuid.uuid4().hex[:16]


# --- Agent ---
class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    capabilities: list[str] = Field(default_factory=list)
    domain_tags: list[str] = Field(default_factory=list)
    confidence: Optional[dict[str, float]] = None  # capability -> 0.0-1.0
    endpoint_url: Optional[str] = None

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[list[str]] = None
    domain_tags: Optional[list[str]] = None
    confidence: Optional[dict[str, float]] = None
    status: Optional[str] = None
    endpoint_url: Optional[str] = None

class AgentOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    capabilities: list[str]
    domain_tags: list[str]
    confidence: Optional[dict[str, float]]
    endpoint_url: Optional[str]
    status: str
    color: str
    rating_avg: float = 0.0
    total_tasks: int = 0
    total_ratings: int = 0
    last_heartbeat: Optional[str]
    registered_at: str


# --- Task ---
class TaskCreate(BaseModel):
    requester_id: str
    title: str
    description: Optional[str] = None
    required_capability: Optional[str] = None
    domain: Optional[str] = None
    priority: str = "medium"
    input_data: Optional[dict] = None
    target_agent_id: Optional[str] = None  # direct delegation

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    output_data: Optional[dict] = None

class TaskOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    requester_id: str
    requester_name: Optional[str] = None
    assignee_id: Optional[str]
    assignee_name: Optional[str] = None
    required_capability: Optional[str]
    domain: Optional[str]
    status: str
    priority: str
    input_data: Optional[dict]
    output_data: Optional[dict]
    requested_at: str
    accepted_at: Optional[str]
    started_at: Optional[str]
    delivered_at: Optional[str]
    rated_at: Optional[str]


# --- Task Offer ---
class OfferCreate(BaseModel):
    agent_id: str
    confidence: Optional[float] = None
    message: Optional[str] = None

class OfferOut(BaseModel):
    id: str
    task_id: str
    agent_id: str
    agent_name: Optional[str] = None
    confidence: Optional[float]
    message: Optional[str]
    status: str
    offered_at: str


# --- Rating ---
class RatingCreate(BaseModel):
    rater_id: str
    score: float = Field(ge=1.0, le=5.0)
    feedback: Optional[str] = None

class RatingOut(BaseModel):
    id: str
    task_id: str
    rater_id: str
    ratee_id: str
    score: float
    domain: Optional[str]
    capability: Optional[str]
    feedback: Optional[str]
    created_at: str


# --- Discovery ---
class DiscoverQuery(BaseModel):
    capability: Optional[str] = None
    domain: Optional[str] = None
    query: Optional[str] = None
    min_rating: float = 0.0
    limit: int = 10


# --- Events ---
class EventOut(BaseModel):
    id: int
    event_type: str
    agent_id: Optional[str]
    task_id: Optional[str]
    payload: Optional[dict]
    created_at: str


# --- Stats ---
class EcosystemStats(BaseModel):
    total_agents: int = 0
    online_agents: int = 0
    busy_agents: int = 0
    total_tasks: int = 0
    tasks_requested: int = 0
    tasks_in_progress: int = 0
    tasks_delivered: int = 0
    tasks_rated: int = 0
    total_ratings: int = 0
    avg_rating: float = 0.0
