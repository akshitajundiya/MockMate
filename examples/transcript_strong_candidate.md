# Example 1 — Strong candidate (Data Analyst, technical)

> **A real session, reproduced verbatim** from `transcripts/session_20260806_215119.md`.
> Generated 2026-08-06 on `gemini-3-flash-preview` with:
> `python main.py --role "Data Analyst" --focus technical --background "Final-year CS student with Python, SQL and ML experience" --simulate strong --debug --turns 5`
>
> Every **Interviewer**, **Candidate** and `> Evaluator:` line below is system output.
> The indented *Annotation* lines are commentary written for this README — they are
> **not** produced by the system.
>
> One exception to "from the transcript file": the interviewer's closing line is taken
> from the run's console output. It carries no candidate answer, so it never becomes a
> turn record and the saved transcript does not contain it.

**Watch for:** difficulty climbing 2 → 3 → 4 → 5 as answers hold up; a `follow_up` at
turn 3 that makes turn 4 a probe on the *same* competency instead of a new topic; and a
competency the session never reached being scored `N/A` rather than guessed at.

---

### Turn 1 — SQL Logic & Data Manipulation (difficulty 2)

**Interviewer:** Hi, I'm Maya, and I'll be leading our technical session today to look at how you approach data problems. Let's start with a SQL scenario: suppose you have a table of user logins and a table of purchases. How would you write a query to find the percentage of users who made a purchase on the same day they first signed up?

**Candidate:** That is a great question. Just to clarify before I dive into the logic, are the timestamps in the logins and purchases tables stored as date-time objects where I would need to truncate them to a date format for an exact match, or are we assuming the dates are already standardized?

Assuming I need to handle the time component, I would start by creating a Common Table Expression to find the minimum login date for each user, which represents their first sign-up. Then, I would perform a left join from that CTE to the purchases table, joining on the user ID and the condition that the purchase date matches the sign-up date. To calculate the final percentage, I would take the count of distinct users with a matching purchase and divide it by the total count of distinct users from the sign-up CTE, making sure to multiply by 100.0 to avoid integer division issues.

> Evaluator: strong · mean 4.6/5 · next action: move_on

> *Annotation: complete answer plus an unprompted clarifying question. Nothing left to probe, so the orchestrator moves on and the next question starts one level harder.*

### Turn 2 — Data Cleaning & Integrity (difficulty 3)

**Interviewer:** Good point to clarify—standardizing those timestamps is usually a necessary first step in the real world. Moving on, let's say you’re analyzing a dataset of customer ages and notice that 10% of the entries are missing and another 5% are listed as '999'. How would you decide whether to drop, impute, or flag these records?

**Candidate:** In this situation, I would first investigate whether those 999 values and nulls are Missing Completely at Random or if there is a underlying pattern. The 999 is almost certainly a sentinel value used by an older system or a default entry, so I would treat those as nulls rather than actual ages to avoid heavily skewing the mean and variance.

If the missingness is truly random and 15% of the data is a small enough portion that I still have statistical power, I might drop them for a quick preliminary analysis. However, for a more robust model, I would likely impute the values using the median age to stay resilient against outliers, or use a more sophisticated method like K-Nearest Neighbors if age correlates with other features like income or location. I would also definitely create a binary indicator variable or flag to mark those records as originally missing. This allows the model to capture any potential signal that the lack of data itself provides.

> Evaluator: strong · mean 4.6/5 · next action: move_on

> *Annotation: spotted the sentinel value unprompted. Difficulty steps up again.*

### Turn 3 — Metric Definition & Business Logic (difficulty 4)

**Interviewer:** Identifying the specific intent behind those sentinel values is definitely a smart move. Switching gears to a business problem: if you were tasked with measuring the success of a new 'Recommended for You' carousel on an e-commerce homepage, what two or three primary metrics would you track?

**Candidate:** I would focus on three primary metrics to get a full picture of the carousel's performance. First, I would look at the Click-Through Rate specifically for the items within the carousel. This tells us immediately if the recommendation algorithm is surfaced items that are actually relevant or appealing to the users.

Second, I would track the Conversion Rate of users who interacted with the carousel compared to a control group who didn't see it. It is important to know if those clicks actually lead to completed purchases or if people are just window shopping.

Finally, I'd monitor Average Order Value. Sometimes recommendations can encourage users to add smaller, "impulse buy" items to their cart, which might increase the number of transactions but potentially lower the average spend per basket. Measuring this helps ensure the feature is driving high-value growth and not just shifting where users find the items they were already planning to buy.

> Evaluator: strong · mean 4.6/5 · next action: follow_up

> *Annotation: a good answer with a loose thread — "users who interacted" is never defined. This is the one `follow_up` of the session, and it turns the next turn into a probe.*

### Turn 4 — Metric Definition & Business Logic (difficulty 5, probe)

**Interviewer:** That's a helpful set of metrics for a starting point. Regarding that second metric, how exactly would you define an "interaction" with the carousel to ensure you're making a fair conversion rate comparison between the test group and the control group?

**Candidate:** That is an important distinction because a passive view is very different from an intentional click. I would define an interaction as a user either clicking on an item within the carousel or using the navigation arrows to scroll through the recommendations. This demonstrates active engagement with the feature.

To ensure a fair comparison with the control group, I would use an intent-to-treat analysis. I would compare the conversion rate of all users who were eligible to see the carousel against the conversion rate of the control group who saw the old layout or no carousel at all. If I only compared "interactors" to the control group, I would introduce selection bias, because users who are already more likely to buy are also more likely to click on things. By comparing the entire test bucket to the control bucket, we measure the true causal impact of the feature's presence on the page.

> Evaluator: strong · mean 5.0/5 · next action: move_on

> *Annotation: note the turn header says `probe` — same competency as turn 3, not a new topic. The probe paid off: selection bias and intent-to-treat were absent from the original answer, and this is the session's only 5.0.*

### Turn 5 — Statistical Interpretation (difficulty 5)

**Interviewer:** I appreciate you bringing up selection bias, as that often complicates those kinds of comparisons. Imagine you run an A/B test and the conversion rate for the variant is 5% higher than the control, but the p-value is 0.11. How would you explain these results to a non-technical product manager?

**Candidate:** I would explain to the product manager that while our new carousel showed a promising 5% increase in conversions, the results currently fall into a bit of a gray area. I’d use the p-value of 0.11 to explain that there is roughly an 11% chance that this increase was just due to random noise or luck, rather than the carousel itself. Usually, in these tests, we look for that risk to be 5% or lower before we call it a win.

I would tell them that we haven't quite reached the level of certainty we need to be confident in a full rollout yet. I'd suggest a few options: we could keep the test running longer to collect more data and see if the result stabilizes, or we could look at the data to see if the carousel performed better for specific segments, like mobile users. Ultimately, it's a positive signal, but it's not yet a statistically "proven" success.

> Evaluator: adequate · mean 4.2/5 · next action: follow_up

> *Annotation: the session's only non-`strong` verdict — "keep the test running longer" is the peeking problem, and the Coach picks it up below. The evaluator asked to probe, but the 5-turn cap ended the interview instead: the orchestrator's stopping rule overrides the evaluator's recommendation.*

**Interviewer:** Thanks for walking me through your thought process on those scenarios. It's been a pleasure speaking with you, and you can expect a feedback report with more details soon.

---

## Coaching Report

## Overall read
You would be an exceptionally strong candidate for a Data Analyst role. You demonstrated a level of technical maturity usually seen in mid-level analysts, particularly in your understanding of experimental design (Intent-to-Treat) and data integrity (sentinel values). The single biggest thing that would elevate you further is tightening your precision on statistical trade-offs—specifically the risks of "peeking" at A/B test results.

## Scorecard

| Competency | Score | Note |
| :--- | :--- | :--- |
| **SQL Logic & Data Manipulation** | 4.5/5 | Strong logic and awareness of integer division; could have offered code. |
| **Data Cleaning & Integrity** | 4.5/5 | Excellent recognition of sentinel values and "Missing Not at Random" patterns. |
| **Metric Definition & Business Logic** | 4.8/5 | Top-tier; identified selection bias and applied Intent-to-Treat logic correctly. |
| **Statistical Interpretation** | 4.0/5 | Clear communication to non-tech peers, but missed power/peeking nuances. |
| **ML Model Evaluation** | N/A | Session ended before this competency was reached. |

## What worked
- **Experimental Nuance:** Your explanation of "selection bias" in Turn 4 was your best moment. Recognizing that comparing only "interactors" to a control group is a flawed methodology shows you understand causal inference, not just basic arithmetic.
- **Data Intuition:** In the data cleaning scenario, you didn't just suggest "dropping nulls." You correctly identified '999' as a sentinel value, which is a classic real-world trap that many junior candidates miss.
- **Proactive Clarification:** In the SQL task, you started by asking about timestamp granularity. This prevents you from writing a "perfect" query for the wrong data format—a habit interviewers love.

## What to fix
- **SQL Syntax Specificity:** While your verbal logic was flawless (CTEs, joins, 100.0 for floats), you didn't actually write the code. In a technical interview, even if the interviewer asks "how would you," always follow up with: "Would you like me to sketch the syntax for that?" to prove you can actually implement the logic.
- **Metric Denominator Precision:** For the Click-Through Rate (CTR) question, you were slightly vague on the denominator. A stronger version is: "I'd define CTR as (Total Clicks on Carousel) / (Total Sessions where the Carousel was rendered in the viewport)." This shows you're thinking about technical logging, not just high-level math.
- **The "Peeking" Problem:** In the A/B test scenario, you suggested "keep the test running longer" to reach significance. In a real interview, this can be a red flag for the "Peeking Problem" (repeatedly checking p-values increases the false positive rate). **Rewrite:** "I'd suggest checking if we reached our pre-calculated required sample size. If not, we continue until we hit that target. If we have, we must accept the null result rather than just 'waiting' for the p-value to drop."

## Practice plan
1. **The "Peeking" Deep Dive:** Spend 30 minutes reading about the "Peeking Problem" and "Alpha Spending" in A/B testing. This is the difference between a Junior and Senior Analyst.
2. **SQL Window Functions:** You mentioned using an aggregation (MIN) for sign-up dates. Practice writing that same logic using `ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY login_time)`—it's often more performant and a common follow-up question.
3. **Out-loud Practice:** Answer this question: *"We ran a test that reached statistical significance (p=0.04), but the sample size was very small. Should we roll it out?"* (Focus on the concept of 'Statistical Power' and 'Minimum Detectable Effect').
