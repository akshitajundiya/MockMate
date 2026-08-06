"""Deterministic orchestration layer.

This is intentionally plain Python, not another LLM call: the Evaluator makes
per-answer judgements, and this module turns those judgements into session-level
policy — when to probe vs move on, how difficulty drifts, when to stop, and
what directive the Interviewer receives next. Keeping the policy in code makes
the adaptive behaviour inspectable, testable and impossible for a candidate to
talk their way around.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from .agents import Interviewer, coach_report, evaluate_answer, plan_interview
from .config import (
    DIFFICULTY_MAX,
    DIFFICULTY_MIN,
    MAX_PROBES_PER_TOPIC,
    MAX_TURNS,
    MIN_TURNS,
)
from .schemas import (
    CandidateProfile,
    Evaluation,
    InterviewPlan,
    NextAction,
    SessionState,
    TurnRecord,
)

# The candidate is any callable that maps interviewer text -> answer text.
# The CLI passes human input; --simulate passes a SimulatedCandidate.
CandidateFn = Callable[[str], str]

END_SENTINELS = {"quit", "exit", "/quit", "/exit"}


@dataclass
class SessionCallbacks:
    """Hooks so the CLI can render progress without the orchestrator knowing about rich/stdout."""
    on_interviewer_text: Optional[Callable[[str], None]] = None
    on_coach_text: Optional[Callable[[str], None]] = None
    on_turn_evaluated: Optional[Callable[[TurnRecord], None]] = None
    on_phase: Optional[Callable[[str], None]] = None


class InterviewSession:
    def __init__(self, profile: CandidateProfile, callbacks: SessionCallbacks | None = None,
                 max_turns: int = MAX_TURNS):
        self.profile = profile
        self.cb = callbacks or SessionCallbacks()
        self.max_turns = max(MIN_TURNS, min(max_turns, MAX_TURNS))
        self.plan: InterviewPlan | None = None
        self.state = SessionState()
        self.report: str = ""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, candidate: CandidateFn) -> None:
        self._phase("Planning the interview…")
        self.plan = plan_interview(self.profile)
        self.state.difficulty = _clamp(self.plan.starting_difficulty)

        interviewer = Interviewer(self.profile, self.plan)

        question = interviewer.open(self._directive(first=True), self.cb.on_interviewer_text)

        while True:
            answer = candidate(question)
            if answer.strip().lower() in END_SENTINELS:
                self.state.ended_early = True
                break

            turn = TurnRecord(
                number=self.state.turn_count + 1,
                competency=self._current_competency(),
                difficulty=self.state.difficulty,
                question=question,
                answer=answer,
                was_probe=self.state.probes_on_current_topic > 0,
            )
            self._phase("Evaluating answer…")
            turn.evaluation = evaluate_answer(self.profile, self.plan, turn)
            self.state.turns.append(turn)
            if self.cb.on_turn_evaluated:
                self.cb.on_turn_evaluated(turn)

            self._apply_adaptation(turn.evaluation)

            if self._should_end():
                interviewer.respond(
                    answer,
                    "The interview is over. Thank the candidate warmly in 1-2 sentences, "
                    "tell them their feedback report is being prepared, and ask NO further questions.",
                    self.cb.on_interviewer_text,
                )
                break

            question = interviewer.respond(
                answer, self._directive(), self.cb.on_interviewer_text
            )

        self._phase("Preparing your coaching report…")
        self.report = coach_report(
            self.profile, self.plan, self.state.turns, self.cb.on_coach_text
        )

    # ------------------------------------------------------------------
    # Adaptation policy
    # ------------------------------------------------------------------

    def _apply_adaptation(self, ev: Evaluation) -> None:
        """Convert an evaluation into state changes for the next turn."""
        # Difficulty drifts on the evaluator's recommendation, but only moves
        # one step at a time and only when recent evidence agrees.
        if ev.difficulty_adjustment.value == "increase" and self._recent_mean() >= 3.5:
            self.state.difficulty = _clamp(self.state.difficulty + 1)
        elif ev.difficulty_adjustment.value == "decrease":
            self.state.difficulty = _clamp(self.state.difficulty - 1)

        wants_probe = ev.next_action in (NextAction.probe_deeper, NextAction.follow_up,
                                         NextAction.redirect, NextAction.clarify)
        if wants_probe and self.state.probes_on_current_topic < MAX_PROBES_PER_TOPIC:
            self.state.probes_on_current_topic += 1
        else:
            # Move to the next planned arc (probe budget spent, or evaluator said move on).
            self.state.probes_on_current_topic = 0
            self.state.current_arc_index += 1

    def _should_end(self) -> bool:
        n = self.state.turn_count
        if n >= self.max_turns:
            return True
        # End early only once the minimum is met AND every planned arc is covered.
        arcs_exhausted = self.state.current_arc_index >= len(self.plan.arcs)
        return n >= MIN_TURNS and arcs_exhausted

    # ------------------------------------------------------------------
    # Directives for the interviewer
    # ------------------------------------------------------------------

    def _directive(self, first: bool = False) -> str:
        arc = self._current_arc()
        base = (
            f"Turn {self.state.turn_count + 1} of at most {self.max_turns}. "
            f"Current difficulty target: {self.state.difficulty}/5.\n"
        )
        if first:
            return base + (
                "Briefly introduce yourself and the session in 1-2 sentences, then ask the "
                f"opening question for this arc — competency: {arc.competency}; topic: {arc.topic}. "
                f"You may use or adapt: \"{arc.opening_question}\""
            )

        last = self.state.turns[-1].evaluation
        action = last.next_action
        if action == NextAction.redirect:
            return base + (
                "The previous answer drifted off-topic. Politely but firmly bring the candidate "
                "back to the original question and ask them to answer it directly. Do not change topic."
            )
        if action == NextAction.clarify:
            return base + (
                "The candidate needs clarification. Restate or scope the question more concretely, "
                "then let them answer. Do not reveal what a good answer looks like."
            )
        if action in (NextAction.probe_deeper, NextAction.follow_up) \
                and self.state.probes_on_current_topic > 0:
            hint = last.probe_suggestion or "the weakest or most interesting part of their answer"
            return base + (
                f"Stay on the current topic and probe deeper. Target: {hint}. "
                "Ask exactly one focused follow-up question."
            )
        # Fresh arc
        return base + (
            "Acknowledge their previous answer in a short, natural sentence (no scores, no verdicts), "
            f"then transition to a new topic — competency: {arc.competency}; topic: {arc.topic}. "
            f"Calibrate to difficulty {self.state.difficulty}/5. "
            f"You may use or adapt: \"{arc.opening_question}\""
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current_arc(self):
        idx = min(self.state.current_arc_index, len(self.plan.arcs) - 1)
        return self.plan.arcs[idx]

    def _current_competency(self) -> str:
        return self._current_arc().competency

    def _recent_mean(self) -> float:
        recent = [t.evaluation.mean_score for t in self.state.turns[-2:] if t.evaluation]
        return sum(recent) / len(recent) if recent else 3.0

    def _phase(self, message: str) -> None:
        if self.cb.on_phase:
            self.cb.on_phase(message)


def _clamp(d: int) -> int:
    return max(DIFFICULTY_MIN, min(DIFFICULTY_MAX, d))
