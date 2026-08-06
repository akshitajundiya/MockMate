"""Terminal interface (rich). Also writes the session transcript to disk."""

from __future__ import annotations

import argparse
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from .config import MAX_TURNS, MODEL, TRANSCRIPTS_DIR
from .llm import friendly_api_error, set_retry_notifier
from .orchestrator import InterviewSession, SessionCallbacks
from .schemas import CandidateProfile, TurnRecord

console = Console()

FOCUS_CHOICES = ["behavioral", "technical", "case", "mixed"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ai-mock-interview-coach",
        description="Multi-agent AI mock interview with adaptive follow-ups and structured coaching.",
    )
    p.add_argument("--role", help="Target role, e.g. 'Product Manager'")
    p.add_argument("--focus", choices=FOCUS_CHOICES, help="Session focus area")
    p.add_argument("--background", default=None, help="2-3 line background / resume snippet")
    p.add_argument("--turns", type=int, default=MAX_TURNS,
                   help="Max question turns (clamped to 5-7)")
    p.add_argument(
        "--simulate",
        choices=["strong", "weak", "edge"],
        help="Replace the human with a simulated candidate persona (demo/testing)",
    )
    p.add_argument("--debug", action="store_true", help="Show evaluator output after each turn")
    return p


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    profile = _collect_profile(args)

    console.print(
        Panel(
            f"[bold]Role:[/bold] {profile.role}   [bold]Focus:[/bold] {profile.focus}   "
            f"[bold]Model:[/bold] {MODEL}\n"
            "Answer in your own words. Type [bold]quit[/bold] on a line by itself to end "
            "early — you'll still get coaching on what you answered.",
            title="AI Mock Interview Coach",
            border_style="cyan",
        )
    )

    callbacks = SessionCallbacks(
        on_interviewer_text=lambda chunk: console.print(chunk, end="", style="bold white"),
        on_phase=lambda msg: console.print(f"\n[dim]{msg}[/dim]"),
        on_turn_evaluated=(_debug_eval if args.debug else None),
    )

    def _describe_retry(code) -> str:
        if code == 429:
            return "Rate limited"
        if code is None:
            return "Connection dropped"
        return f"API error {code}"

    set_retry_notifier(
        lambda delay, code: console.print(
            f"[dim]{_describe_retry(code)} — waiting {delay:.0f}s, then continuing…[/dim]"
        )
    )

    session = InterviewSession(profile, callbacks, max_turns=args.turns)
    candidate = _make_candidate(args, profile)

    try:
        session.run(candidate)
    except KeyboardInterrupt:
        console.print("\n[yellow]Session interrupted.[/yellow]")
        return 130
    except Exception as exc:  # surface a friendly message, keep traceback out of the demo
        console.print(f"\n[red]{friendly_api_error(exc)}[/red]")
        return 1

    console.print("\n")
    if session.report.strip():
        console.print(
            Panel(Markdown(session.report), title="Coaching Report", border_style="green")
        )
    else:
        console.print(
            "[red]The coaching report came back empty — the transcript below was still "
            "saved. Re-run to try again.[/red]"
        )

    path = _save_transcript(session)
    console.print(f"[dim]Transcript saved to {path}[/dim]")
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_profile(args) -> CandidateProfile:
    role = args.role or Prompt.ask("[cyan]Target role[/cyan] (e.g. 'Data Analyst')")
    focus = args.focus or Prompt.ask(
        "[cyan]Focus area[/cyan]", choices=FOCUS_CHOICES, default="mixed"
    )
    background = (
        args.background
        if args.background is not None
        else Prompt.ask("[cyan]Background (2-3 lines, optional)[/cyan]", default="")
    )
    return CandidateProfile(role=role.strip(), focus=focus, background=background.strip())


def _make_candidate(args, profile: CandidateProfile):
    if args.simulate:
        from .agents import SimulatedCandidate

        sim = SimulatedCandidate(profile, args.simulate)
        console.print(f"[magenta]Simulated candidate persona: {args.simulate}[/magenta]")

        def simulated(question: str) -> str:
            answer = sim.answer(question)
            console.print(f"\n\n[italic magenta]Candidate:[/italic magenta] {answer}")
            return answer

        return simulated

    def human(question: str) -> str:
        console.print("\n")
        while True:
            answer = Prompt.ask("[green]Your answer[/green]").strip()
            if answer:
                return answer
            # An empty line used to be scored as a real (terrible) answer and burn
            # a turn — re-ask instead.
            console.print(
                "[yellow]That came through blank. Type your answer, or [bold]quit[/bold] "
                "on a line by itself to end the interview.[/yellow]"
            )

    return human


def _debug_eval(turn: TurnRecord) -> None:
    ev = turn.evaluation
    console.print(
        f"[dim]eval: {ev.answer_type.value} | mean {ev.mean_score:.1f}/5 | "
        f"next: {ev.next_action.value} | difficulty: {ev.difficulty_adjustment.value}[/dim]"
    )


def _save_transcript(session: InterviewSession) -> str:
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = TRANSCRIPTS_DIR / f"session_{stamp}.md"
    p = session.profile
    lines = [
        f"# Mock Interview — {p.role} ({p.focus})",
        f"_Generated {datetime.now():%Y-%m-%d %H:%M} · model {MODEL}_",
        "",
        f"**Background:** {p.background or '(none)'}",
        "",
        f"**Session:** {len(session.state.turns)} answered turn(s)"
        f"{' — ended early by the candidate' if session.state.ended_early else ''}",
        "",
        "## Transcript",
        "",
    ]
    for t in session.state.turns:
        ev = t.evaluation
        lines += [
            f"### Turn {t.number} — {t.competency} (difficulty {t.difficulty}"
            f"{', probe' if t.was_probe else ''})",
            f"**Interviewer:** {t.question}",
            "",
            f"**Candidate:** {t.answer}",
            "",
        ]
        if ev:
            lines += [
                f"> Evaluator: {ev.answer_type.value} · mean {ev.mean_score:.1f}/5 · "
                f"next action: {ev.next_action.value}",
                "",
            ]
    lines += ["## Coaching Report", "", session.report, ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
