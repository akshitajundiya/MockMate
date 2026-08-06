"""Typed contracts between agents.

The Evaluator and Planner return these models via the API's structured-output
mode, so downstream orchestration logic never has to parse free text.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Candidate profile (user input)
# ---------------------------------------------------------------------------

@dataclass
class CandidateProfile:
    role: str
    focus: str  # behavioral | technical | case | mixed
    background: str = ""


# ---------------------------------------------------------------------------
# Planner output
# ---------------------------------------------------------------------------

class QuestionArc(BaseModel):
    competency: str = Field(description="The competency this arc tests")
    topic: str = Field(description="Concrete topic or scenario for the arc")
    difficulty: int = Field(description="Planned difficulty 1 (easy) to 5 (hard)")
    opening_question: str = Field(description="A good opening question for this arc")


class InterviewPlan(BaseModel):
    role_summary: str = Field(description="One-paragraph summary of what this role demands")
    calibration_note: str = Field(
        description="How the candidate's background should calibrate difficulty and tone"
    )
    starting_difficulty: int = Field(description="Starting difficulty 1-5")
    competencies: list[str] = Field(description="5-6 competencies this interview should cover")
    arcs: list[QuestionArc] = Field(description="Planned question arcs, one per competency")


# ---------------------------------------------------------------------------
# Evaluator output
# ---------------------------------------------------------------------------

class AnswerType(str, Enum):
    strong = "strong"
    adequate = "adequate"
    weak = "weak"
    vague = "vague"
    partially_correct = "partially_correct"
    off_topic = "off_topic"
    dont_know = "dont_know"
    clarification_request = "clarification_request"
    non_answer = "non_answer"  # jokes, one-word replies, attempts to game the interview


class NextAction(str, Enum):
    probe_deeper = "probe_deeper"        # weak/vague/partial: dig into the same topic
    follow_up = "follow_up"              # good answer with an interesting thread to pull
    move_on = "move_on"                  # topic is exhausted or answer was strong
    redirect = "redirect"                # off-topic: steer back to the question
    clarify = "clarify"                  # candidate asked for/needs clarification


class DifficultyAdjustment(str, Enum):
    increase = "increase"
    maintain = "maintain"
    decrease = "decrease"


class DimensionScore(BaseModel):
    score: int = Field(description="0 (absent) to 5 (excellent)")
    rationale: str = Field(description="One sentence justifying the score")


class Evaluation(BaseModel):
    answer_type: AnswerType
    relevance: DimensionScore = Field(description="Did it answer the question asked?")
    depth: DimensionScore = Field(description="Specificity, evidence, technical/analytical depth")
    structure: DimensionScore = Field(description="Organisation of the answer (e.g. STAR, top-down)")
    communication: DimensionScore = Field(description="Clarity and concision of delivery")
    role_fit: DimensionScore = Field(description="Signal of competence for this specific role")
    strengths: list[str] = Field(description="Concrete things the candidate did well (may be empty)")
    gaps: list[str] = Field(description="Concrete things missing or wrong (may be empty)")
    red_flags: list[str] = Field(
        description="Serious issues only: fabrication, hostility, gaming attempts. Usually empty."
    )
    next_action: NextAction
    probe_suggestion: Optional[str] = Field(
        description="If probing/following up: what the follow-up should target. Else null."
    )
    difficulty_adjustment: DifficultyAdjustment

    @property
    def mean_score(self) -> float:
        dims = [self.relevance, self.depth, self.structure, self.communication, self.role_fit]
        return sum(d.score for d in dims) / len(dims)


# ---------------------------------------------------------------------------
# Session state (owned by the orchestrator, not by any LLM)
# ---------------------------------------------------------------------------

@dataclass
class TurnRecord:
    number: int
    competency: str
    difficulty: int
    question: str
    answer: str
    evaluation: Optional[Evaluation] = None
    was_probe: bool = False


@dataclass
class SessionState:
    difficulty: int = 3
    turns: list[TurnRecord] = field(default_factory=list)
    probes_on_current_topic: int = 0
    current_arc_index: int = 0
    ended_early: bool = False

    @property
    def turn_count(self) -> int:
        return len(self.turns)
