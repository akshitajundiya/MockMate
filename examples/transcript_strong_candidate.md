# Example 1 — Strong candidate (Product Manager, behavioral)

> Representative sample session documenting expected system behaviour (shown in
> `--debug` view, so the evaluator's normally-hidden verdicts are visible).
> Regenerate a live one: `python main.py --role "Product Manager" --focus behavioral --background "3 years as APM at a fintech, shipped a payments onboarding flow" --simulate strong --debug`

**Watch for:** difficulty ratcheting 3→4→5, `move_on` after complete answers so no
turn is wasted, and one `follow_up` where the evaluator spots a thread worth pulling.

---

**Interviewer:** Hi, I'm Maya — I'll be running your mock interview for the Product Manager role today. Let's start with your recent work: tell me about a product decision you made on the payments onboarding flow that you had to defend to stakeholders.

**Candidate:** Sure. When we redesigned onboarding, compliance wanted every user to complete full KYC upfront, but our data showed 68% of drop-off happened on the document-upload step. I proposed progressive KYC — let users explore with a capped wallet, verify fully only before their first real transaction. I built the case with a funnel analysis and a risk model the compliance lead co-signed, piloted it in one market, and activation rose 22% with no increase in fraud losses. The hardest part was reframing it for compliance as risk-tiering rather than risk-removal.

> `eval: strong | mean 4.6/5 | next: move_on | difficulty: increase` — *"Quantified, structured (problem → decision → result), shows stakeholder judgment. No need to probe; raise the bar."*

**Interviewer:** That's a clear story, thanks. Let's switch gears — tell me about a time you were wrong about something you'd advocated for strongly. What happened after?

**Candidate:** I pushed hard for an in-app referral program because our CAC was climbing. I got engineering to spend a sprint on it. Referral share of signups stalled at about 1.5% — my benchmark assumed a social product, and payments just isn't one. I wrote a short post-mortem, the main lesson being that I'd benchmarked on the wrong comparable set. I then killed it myself rather than letting it linger, and reallocated the roadmap slot to SEO landing pages, which ended up cutting blended CAC by 12%.

> `eval: strong | mean 4.4/5 | next: follow_up | difficulty: increase (applied: 4→5)` — *"Genuine ownership of the mistake. Thread worth pulling: how they got engineering buy-in to kill their own feature."*

**Interviewer:** You said you killed it yourself — walk me through that conversation with the engineers who'd just spent a sprint building it.

**Candidate:** I didn't frame it as "we're deleting your work." I brought the data to the team retro, showed the benchmark error was mine, and asked whether anyone saw a pivot worth two more weeks. One engineer suggested keeping the referral infrastructure for a future B2B invite flow, which we did — so the sprint wasn't wasted, it became plumbing. I think owning the error out loud is what kept trust intact; the same team backed my next bet without friction.

> `eval: strong | mean 4.4/5 | next: move_on | difficulty: maintain` — *"Handled the probe with new, specific material rather than repeating the earlier answer."*

**Interviewer:** Last one, and it's deliberately hard: your CEO wants a feature shipped in six weeks that you believe will hurt retention. You've made your case once and been overruled. What do you do?

**Candidate:** First I'd make sure I'm executing well, because relitigating every decision destroys a PM's credibility. But I'd negotiate instrumentation as part of the build — define upfront with the CEO what retention signal would validate or falsify the concern, and a checkpoint at week eight post-launch. That converts a disagreement into an experiment with an agreed kill criterion. If the data proves the concern right, the decision reverses itself without me having to win an argument. And honestly — if I'm overruled with data repeatedly and there's no learning loop, that's a signal about the org I'd weigh separately.

> `eval: strong | mean 4.8/5 | next: move_on | difficulty: maintain` — *"Disagree-and-commit plus falsifiable checkpoint; senior-level judgment at difficulty 5."*

**Interviewer:** That's everything from me — thank you, this was a genuinely enjoyable conversation. Your feedback report is being prepared now.

---

## Coaching Report (excerpt)

### Overall read
This session would land very well with a real interviewer. You consistently answer in
decision → evidence → result shape, you quantify without being prompted, and you're
credible about failure. The one thing between you and senior-PM interviews is
concision: two answers ran past the 90-second mark before reaching the result.

### Scorecard
| Competency | Score | Note |
|---|---|---|
| Stakeholder management | 4.6 | Reframing KYC as risk-tiering was the standout moment |
| Ownership & learning from failure | 4.4 | Named your own benchmark error unprompted |
| Team leadership | 4.4 | The "sprint became plumbing" reframe is a keeper |
| Executive judgment | 4.8 | Agreed kill-criterion answer was near-perfect |

### What to fix
- **Front-load the result.** In the referral story the 12% CAC win arrived last;
  in a time-boxed interview it risks being cut off. Lead with it, then unpack.

### Practice plan
1. Rehearse the KYC story in 75 seconds flat — it's your best material and currently runs long.
2. Prepare one story about influencing *without* data, since every answer today leaned on metrics.
3. Practice out loud: *"Tell me about a time you had to ship something you disagreed with — and it turned out you were wrong to disagree."*
