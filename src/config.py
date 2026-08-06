"""Central configuration. Everything is overridable via environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"

# One model for every agent by default; each agent tunes thinking/effort per call.
MODEL = os.getenv("INTERVIEW_COACH_MODEL", "claude-opus-4-8")

# Interview shape
MIN_TURNS = int(os.getenv("INTERVIEW_MIN_TURNS", "5"))
MAX_TURNS = int(os.getenv("INTERVIEW_MAX_TURNS", "7"))

# Never let the interviewer rabbit-hole: at most N consecutive probes on one topic.
MAX_PROBES_PER_TOPIC = 2

DIFFICULTY_MIN, DIFFICULTY_MAX = 1, 5
