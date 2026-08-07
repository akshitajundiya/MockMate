"""Offline smoke test — runs the full system with a fake model.

    python smoke_test.py

Exercises the real Planner, Interviewer, Evaluator, Coach, orchestration policy
and transcript writer. Only the network layer is replaced, so this proves the
wiring works without an API key, an internet connection, or any quota.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import agents, cli, orchestrator
from src.orchestrator import InterviewSession, SessionCallbacks
from src.schemas import (
    AnswerType,
    CandidateProfile,
    DifficultyAdjustment,
    DimensionScore,
    Evaluation,
    InterviewPlan,
    NextAction,
    QuestionArc,
)

PASS, FAIL = "  [PASS]", "  [FAIL]"
failures: list[str] = []

# The test asserts on the shipped 5-7 turn behaviour, so pin the bounds rather
# than inheriting INTERVIEW_MIN_TURNS / INTERVIEW_MAX_TURNS from the shell — a
# stray override in the environment should not look like a broken pipeline.
TEST_MIN_TURNS, TEST_MAX_TURNS = 5, 7
orchestrator.MIN_TURNS = TEST_MIN_TURNS
orchestrator.MAX_TURNS = TEST_MAX_TURNS


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"{PASS if condition else FAIL} {label}{(' — ' + detail) if detail else ''}")
    if not condition:
        failures.append(label)


# ---------------------------------------------------------------------------
# Fake model: deterministic, no network
# ---------------------------------------------------------------------------

COMPETENCIES = ["SQL", "Data cleaning", "Statistics", "Business sense", "Communication"]

_calls = {"structured": 0, "text": 0}


def fake_complete_structured(system, user_content, output_model, **kwargs):
    _calls["structured"] += 1

    if output_model is InterviewPlan:
        return InterviewPlan(
            role_summary="Strong analysts pair SQL fluency with business judgement.",
            calibration_note="Student background: start at 3.",
            starting_difficulty=3,
            competencies=COMPETENCIES,
            arcs=[
                QuestionArc(
                    competency=c,
                    topic=f"{c.lower()} scenario",
                    difficulty=3,
                    opening_question=f"Tell me how you would approach a {c.lower()} problem.",
                )
                for c in COMPETENCIES
            ],
        )

    # Evaluation: score from the answer's length so weak answers probe and
    # strong ones move on — enough to drive the adaptation policy.
    answer = user_content.split("CANDIDATE ANSWER:")[-1].strip()
    weak = len(answer) < 60
    score = 2 if weak else 4
    dim = lambda: DimensionScore(score=score, rationale="fake rationale")
    return Evaluation(
        answer_type=AnswerType.weak if weak else AnswerType.strong,
        relevance=dim(), depth=dim(), structure=dim(),
        communication=dim(), role_fit=dim(),
        strengths=[] if weak else ["specific example"],
        gaps=["no metrics"] if weak else [],
        red_flags=[],
        next_action=NextAction.probe_deeper if weak else NextAction.move_on,
        probe_suggestion="ask for a concrete metric" if weak else None,
        difficulty_adjustment=(
            DifficultyAdjustment.decrease if weak else DifficultyAdjustment.increase
        ),
    )


def fake_stream_turn(system, user_content, max_tokens, thinking="low",
                     previous_id=None, on_text=None):
    _calls["text"] += 1
    if "FULL INTERVIEW TRANSCRIPT" in user_content:      # the Coach
        text = (
            "## Overall read\nSolid session.\n\n"
            "## Scorecard\n| Competency | Score | Note |\n|---|---|---|\n"
            "| SQL | 4 | Clear |\n\n"
            "## What worked\n- Concrete examples\n\n"
            "## What to fix\n- Quantify results\n\n"
            "## Practice plan\n1. Rehearse one STAR answer.\n"
        )
    else:                                                 # the Interviewer
        text = f"Fake interviewer question #{_calls['text']}?"
    if on_text:
        on_text(text)
    return text, f"fake-interaction-{_calls['text']}"


agents.complete_structured = fake_complete_structured
agents.stream_turn = fake_stream_turn


# ---------------------------------------------------------------------------
# Run a full session
# ---------------------------------------------------------------------------

def main() -> int:
    print("Running full pipeline against a fake model (no network, no quota)\n")

    overrides = {k: os.environ[k] for k in
                 ("INTERVIEW_MIN_TURNS", "INTERVIEW_MAX_TURNS") if k in os.environ}
    if overrides:
        print(f"  note: ignoring shell overrides {overrides}; "
              f"testing the shipped {TEST_MIN_TURNS}-{TEST_MAX_TURNS} turn behaviour\n")

    profile = CandidateProfile(
        role="Data Analyst",
        focus="technical",
        background="Final-year CS student with Python, SQL and ML experience",
    )

    seen_questions: list[str] = []
    session = InterviewSession(
        profile,
        SessionCallbacks(on_interviewer_text=lambda chunk: seen_questions.append(chunk)),
        max_turns=TEST_MAX_TURNS,
    )

    answers = iter([
        "I would use a LEFT JOIN and filter where the right-hand key is NULL, "
        "then validate the row counts before and after.",
        "Not sure.",                                   # weak -> should trigger a probe
        "I would segment by cohort and compare medians, then check significance.",
        "I would define the metric with the stakeholder before building anything.",
        "I would summarise findings in one slide and lead with the recommendation.",
        "I would document the caveats so the reader knows what the data cannot say.",
        "I would follow up with a short written summary after the meeting.",
    ])
    session.run(lambda question: next(answers))

    print("Pipeline stages")
    check("Planner produced a plan", session.plan is not None,
          f"{len(session.plan.arcs)} arcs")
    check("Interviewer asked questions", len(seen_questions) >= 5,
          f"{len(seen_questions)} utterances")
    check(f"Interview ran {TEST_MIN_TURNS}-{TEST_MAX_TURNS} turns",
          TEST_MIN_TURNS <= len(session.state.turns) <= TEST_MAX_TURNS,
          f"{len(session.state.turns)} turns")
    check("Every turn was evaluated",
          all(t.evaluation is not None for t in session.state.turns))
    check("Coach produced a report", bool(session.report.strip()),
          f"{len(session.report)} chars")

    print("\nAdaptation policy")
    probes = [t for t in session.state.turns if t.was_probe]
    check("Weak answer triggered a probe", len(probes) >= 1,
          f"{len(probes)} probe(s)")
    difficulties = [t.difficulty for t in session.state.turns]
    check("Difficulty adapted", len(set(difficulties)) > 1, f"path {difficulties}")
    competencies = [t.competency for t in session.state.turns]
    non_probe = [t.competency for t in session.state.turns if not t.was_probe]
    check("No repeated topic outside probes", len(non_probe) == len(set(non_probe)),
          " -> ".join(competencies))

    print("\nReport contents")
    for section in ("Overall read", "Scorecard", "What worked",
                    "What to fix", "Practice plan"):
        check(f"Report has '{section}'", section in session.report)

    print("\nTranscript writer")
    original = cli.TRANSCRIPTS_DIR
    with tempfile.TemporaryDirectory() as tmp:
        cli.TRANSCRIPTS_DIR = Path(tmp)
        path = Path(cli._save_transcript(session))
        body = path.read_text(encoding="utf-8")
    cli.TRANSCRIPTS_DIR = original
    check("Transcript file written", bool(body))
    check("Transcript has every turn", body.count("### Turn ") == len(session.state.turns))
    check("Transcript includes the report", "## Coaching Report" in body)

    print(f"\nFake model calls: {_calls['structured']} structured, {_calls['text']} text")
    if failures:
        print(f"\nFAILED ({len(failures)}): " + "; ".join(failures))
        return 1
    print("\nAll checks passed — the pipeline works end to end.")
    print("Only the API call itself is untested here; that needs a key and quota.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
