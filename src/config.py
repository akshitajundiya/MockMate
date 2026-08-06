"""Central configuration. Everything is overridable via environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"

# One model for every agent by default; each agent tunes thinking level and
# token budget per call (see TOKENS_* below).
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# On Gemini 3 models max_output_tokens is a COMBINED budget for thinking tokens
# plus visible output, so these are sized well above the visible text we expect.
# Sized for the thinking, not the visible text: a two-sentence question can still
# burn thousands of thinking tokens on a hard prompt, and running out mid-think
# yields an empty turn rather than a truncated one.
TOKENS_CONVERSATION = 8000   # Interviewer / simulated candidate: a few sentences
TOKENS_STRUCTURED = 8000     # Planner / Evaluator: small JSON, some deliberation
TOKENS_REPORT = 16000        # Coach: a full report plus cross-turn reasoning

# thinking_level defaults to "high" on Gemini 3; only the Coach needs that.
THINKING_FAST = "low"
THINKING_DEEP = "high"

# A full session is ~23 requests; free-tier allowances are per-minute, so rate
# limits are expected rather than exceptional. Retries honour the server's hint.
MAX_RETRIES = int(os.getenv("INTERVIEW_MAX_RETRIES", "5"))

# Interview shape
MIN_TURNS = int(os.getenv("INTERVIEW_MIN_TURNS", "5"))
MAX_TURNS = int(os.getenv("INTERVIEW_MAX_TURNS", "7"))

# Never let the interviewer rabbit-hole: at most N consecutive probes on one topic.
MAX_PROBES_PER_TOPIC = 2

DIFFICULTY_MIN, DIFFICULTY_MAX = 1, 5
