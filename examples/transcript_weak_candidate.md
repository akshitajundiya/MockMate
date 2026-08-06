# Example 2 — Weak candidate (Data Analyst, technical)

> Representative sample session documenting expected system behaviour (shown in
> `--debug` view). Regenerate a live one:
> `python main.py --role "Data Analyst" --focus technical --background "Recent graduate, one internship, knows SQL and Excel" --simulate weak --debug`

**Watch for:** vague answers triggering `probe_deeper`, the **probe budget (max 2 per
topic)** stopping the interrogation spiral, difficulty stepping down 3→2, and a coach
report focused on specificity rather than piling on.

---

**Interviewer:** Hi, I'm Maya — welcome to your mock interview for the Data Analyst role. To start: in your internship, what's an analysis you did that actually changed a decision?

**Candidate:** I did a lot of analysis on sales data. I used SQL and Excel to make reports and dashboards, and the team found them really useful for making decisions.

> `eval: vague | mean 2.0/5 | next: probe_deeper | difficulty: maintain` — *"No specific analysis, decision, or outcome named. Probe: ask for ONE concrete report and what changed because of it."*

**Interviewer:** Can you pick one specific report and tell me what decision it changed?

**Candidate:** There was a monthly sales dashboard. The manager looked at it to see how regions were doing. I think it helped them decide where to focus... I mostly built it and they used it.

> `eval: weak | mean 2.2/5 | next: probe_deeper | difficulty: maintain` — *"Slightly more concrete (regional dashboard) but still no owned insight. One more probe, then move on."* — probe 2 of 2 on this topic

**Interviewer:** Fair enough. Did *you* ever find something in that data that surprised your manager — anything at all?

**Candidate:** Actually yes — one month a region's numbers dropped and I noticed it was mostly one product, because a competitor cut prices. My manager didn't know yet, and they raised it with the sales lead.

> `eval: adequate | mean 2.8/5 | next: move_on | difficulty: maintain` — *"There IS a real insight here (product-level drill-down → competitor pricing) — the candidate buries it. Probe budget spent; moving on."*

**Interviewer:** Good, that's the kind of thing I was after. Let's do something concrete: say I give you a table `orders(order_id, customer_id, order_date, amount)`. How would you find each customer's *second* purchase?

**Candidate:** I would... sort the table by customer and date, and then take the second row for each customer. In SQL maybe with GROUP BY? I'm not fully sure how to get the second one exactly.

> `eval: partially_correct | mean 2.4/5 | next: probe_deeper | difficulty: decrease (applied: 3→2)` — *"Correct mental model (sort within customer, take row 2), wrong tool (GROUP BY can't do this; needs ROW_NUMBER or a self-join). Probe whether they know window functions at all; step difficulty down."*

**Interviewer:** Your instinct to sort within each customer is right. Have you come across window functions — anything like ROW_NUMBER?

**Candidate:** I've seen ROW_NUMBER in a tutorial but I haven't used it in a real query. I think it numbers rows... so maybe you could number each customer's orders by date and take number 2? I'd have to look up the exact syntax.

> `eval: partially_correct | mean 2.8/5 | next: move_on | difficulty: maintain` — *"With a nudge they reconstructed the correct approach — genuine reasoning, shaky recall. Honest about the limit. Good signal for coachability."*

**Interviewer:** That's exactly the idea. Last question, an easier practical one: a stakeholder says your numbers 'look wrong' compared to last month's report. What do you check first?

**Candidate:** First I'd check if we're comparing the same date ranges and filters, because that's usually it. Then whether the data pipeline loaded fully — once during my internship a table only half-loaded and everything was low. And then I'd ask them what number they expected, so I know what 'wrong' means to them.

> `eval: strong | mean 3.8/5 | next: move_on | difficulty: maintain` — *"Best answer of the session: ordered checklist, real war story, and 'ask what they expected' shows stakeholder maturity."*

**Interviewer:** Nice — that last answer was a strong note to end on. Thank you for your time; your feedback report is on its way.

---

## Coaching Report (excerpt)

### Overall read
Right now you'd struggle in a real screen — not because the substance isn't there,
but because you make interviewers dig for it. Three times today your first answer was
generic and the good material ("one product drove the drop — competitor pricing")
only surfaced under probing. The debugging answer proves you can be specific and
structured; you need that to be your default, not your third attempt.

### Scorecard
| Competency | Score | Note |
|---|---|---|
| Impact & ownership | 2.3 | Real insight existed but had to be extracted |
| SQL proficiency | 2.6 | Right mental models, can't yet execute window functions |
| Debugging & data quality | 3.8 | Genuinely good — ordered checks + a real example |
| (Statistics, dashboarding) | — | Untested: turns were spent probing; no score fabricated |

### What to fix
- **Answer with the exception, not the routine.** "I built dashboards the team used"
  is invisible; "I spotted a one-product drop caused by competitor pricing" is
  memorable. You had the second story and led with the first.
- **Close the window-function gap this week.** It cost you the one hands-on SQL
  question, and it is the single most-tested intermediate SQL topic.
- **Honest "not fully sure" was fine — keep it** — but attach your reasoning to it,
  as you did when nudged. That turned a miss into partial credit.

### Practice plan
1. Write and run the second-purchase query for real (ROW_NUMBER over PARTITION BY),
   then the same via a self-join, so you can explain both.
2. Rewrite the internship story in 60 seconds: insight first, dashboard second.
3. Practice out loud: *"Walk me through an analysis where the data contradicted what
   the team believed."*
