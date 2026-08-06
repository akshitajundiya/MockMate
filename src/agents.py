"""The four agents (plus an optional candidate simulator for demos/testing).

Each agent = a system prompt (prompts/*.md) + a call shape (text vs structured)
+ its own context. They deliberately do NOT share a conversation:

  Planner     one-shot, structured   -> InterviewPlan
  Interviewer multi-turn, streamed   -> next utterance (never sees scores)
  Evaluator   one-shot per answer,   -> Evaluation (never sees the chat persona,
              structured                only the Q/A pair + rubric context)
  Coach       one-shot, streamed     -> markdown report (sees everything, at the end)
"""

import json
from typing import Callable, Optional

from . import prompts
from .llm import complete_structured, complete_text
from .schemas import (
    CandidateProfile,
    Evaluation,
    InterviewPlan,
    TurnRecord,
)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

def plan_interview(profile: CandidateProfile) -> InterviewPlan:
    system = prompts.load("planner")
    user = (
        f"Target role: {profile.role}\n"
        f"Session focus: {profile.focus}\n"
        f"Candidate background: {profile.background or '(none provided)'}"
    )
    return complete_structured(system, user, InterviewPlan)


# ---------------------------------------------------------------------------
# Interviewer
# ---------------------------------------------------------------------------

class Interviewer:
    """Holds the running interview conversation.

    The orchestrator steers it by appending an <orchestrator_directive> block
    to each user turn; the candidate never sees those directives.
    """

    def __init__(self, profile: CandidateProfile, plan: InterviewPlan):
        self.system = prompts.load(
            "interviewer",
            role=profile.role,
            focus=profile.focus,
            background=profile.background or "(none provided)",
            role_summary=plan.role_summary,
            calibration_note=plan.calibration_note,
        )
        self.messages: list[dict] = []

    def open(self, directive: str, on_text: Optional[Callable[[str], None]] = None) -> str:
        return self._turn(
            f"<orchestrator_directive>\n{directive}\n</orchestrator_directive>\n"
            "Begin the interview now.",
            on_text,
        )

    def respond(
        self,
        candidate_answer: str,
        directive: str,
        on_text: Optional[Callable[[str], None]] = None,
    ) -> str:
        return self._turn(
            f"<candidate_answer>\n{candidate_answer}\n</candidate_answer>\n"
            f"<orchestrator_directive>\n{directive}\n</orchestrator_directive>",
            on_text,
        )

    def _turn(self, user_content: str, on_text) -> str:
        self.messages.append({"role": "user", "content": user_content})
        reply = complete_text(self.system, self.messages, max_tokens=600, on_text=on_text)
        self.messages.append({"role": "assistant", "content": reply})
        return reply


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

def evaluate_answer(
    profile: CandidateProfile,
    plan: InterviewPlan,
    turn: TurnRecord,
) -> Evaluation:
    system = prompts.load("evaluator")
    user = (
        f"Target role: {profile.role}\n"
        f"Session focus: {profile.focus}\n"
        f"Candidate background: {profile.background or '(none provided)'}\n"
        f"Competency under test: {turn.competency}\n"
        f"Question difficulty (1-5): {turn.difficulty}\n\n"
        f"QUESTION ASKED:\n{turn.question}\n\n"
        f"CANDIDATE ANSWER:\n{turn.answer}"
    )
    return complete_structured(system, user, Evaluation)


# ---------------------------------------------------------------------------
# Coach
# ---------------------------------------------------------------------------

def coach_report(
    profile: CandidateProfile,
    plan: InterviewPlan,
    turns: list[TurnRecord],
    on_text: Optional[Callable[[str], None]] = None,
) -> str:
    system = prompts.load("coach")
    transcript_blocks = []
    for t in turns:
        ev = t.evaluation
        ev_json = ev.model_dump_json(indent=2) if ev else "null"
        transcript_blocks.append(
            f"### Turn {t.number} — competency: {t.competency}, difficulty {t.difficulty}"
            f"{' (probe)' if t.was_probe else ''}\n"
            f"Interviewer: {t.question}\n"
            f"Candidate: {t.answer}\n"
            f"Evaluator output:\n```json\n{ev_json}\n```"
        )
    user = (
        f"Target role: {profile.role}\n"
        f"Session focus: {profile.focus}\n"
        f"Candidate background: {profile.background or '(none provided)'}\n"
        f"Competencies planned: {', '.join(plan.competencies)}\n\n"
        "FULL INTERVIEW TRANSCRIPT WITH PER-TURN EVALUATIONS:\n\n"
        + "\n\n".join(transcript_blocks)
    )
    return complete_text(
        system,
        [{"role": "user", "content": user}],
        max_tokens=3000,
        on_text=on_text,
        use_thinking=True,  # the report benefits from cross-turn reasoning
    )


# ---------------------------------------------------------------------------
# Candidate simulator (demo/testing only — not part of the product loop)
# ---------------------------------------------------------------------------

class SimulatedCandidate:
    """Plays the candidate so full sessions can be generated end-to-end.

    Personas: strong | weak | edge  (edge = messy: off-topic tangents,
    'I don't know', clarification requests, one attempt to game the scoring).
    """

    def __init__(self, profile: CandidateProfile, persona: str):
        self.system = prompts.load(
            "candidate_simulator",
            role=profile.role,
            focus=profile.focus,
            background=profile.background or "(none provided)",
            persona=persona,
        )
        self.messages: list[dict] = []

    def answer(self, interviewer_utterance: str) -> str:
        self.messages.append({"role": "user", "content": interviewer_utterance})
        reply = complete_text(self.system, self.messages, max_tokens=500)
        self.messages.append({"role": "assistant", "content": reply})
        return reply
