"""Agent Ecosystem — Configuration"""
import os
from pathlib import Path

# Paths
APP_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = APP_DIR / "data"
LOG_DIR = APP_DIR / "logs"
DB_PATH = DATA_DIR / "ecosystem.db"

# Server
HOST = os.getenv("AE_HOST", "0.0.0.0")
PORT = int(os.getenv("AE_PORT", "4019"))

# Agent settings
AUTONOMOUS_MODE = os.getenv("AE_AUTONOMOUS", "false").lower() == "true"
HEARTBEAT_TIMEOUT_SECONDS = 300  # 5 min without heartbeat → offline
HEARTBEAT_CHECK_INTERVAL = 60    # check every 60s

# Task settings
TASK_TIMEOUT_HOURS = 24          # auto-cancel unaccepted tasks after 24h

# Rating
RATING_MIN = 1.0
RATING_MAX = 5.0

# Discovery scoring weights
DISCOVERY_RATING_WEIGHT = 0.4
DISCOVERY_CONFIDENCE_WEIGHT = 0.3
DISCOVERY_EXPERIENCE_WEIGHT = 0.3

# SSE
SSE_KEEPALIVE_SECONDS = 15

# Reputation decay
DECAY_RATE = 0.02  # 2% per day — old ratings matter less
DECAY_INTERVAL_HOURS = 6  # run decay every 6 hours

# Specialization evolution
EVOLUTION_THRESHOLD = 5  # complete 5 tasks in a capability to unlock adjacents

# Domain colors (for deterministic assignment)
DOMAIN_COLORS = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8",
    "#4DD0E1", "#AED581", "#FFD54F", "#F06292", "#9575CD",
    "#26C6DA", "#66BB6A", "#FFA726", "#EF5350", "#AB47BC",
]
