# NimbusPay Fraud Detection Fix
## Presentation for Business Leadership

---

## SLIDE 1 — Title

**Title:** Our Fraud Scoring System Was Working Against Us — And We Fixed It

**Subtitle:** What went wrong, what we changed, and what it means for fraud losses going forward

---
**SCRIPT:**

"Thank you for your time. Over the past quarter, fraud losses have been climbing, and the team suspected the scoring system might be part of the problem. It was. I want to walk you through what we found, what we fixed, and what the numbers look like now. The short version: our system was accidentally rewarding the riskiest transactions and ignoring the clearest warning signs. We've corrected that, and the impact on detection is significant."

---

## SLIDE 2 — How the Scoring System Works

**The system scores every transaction from 0 to 100:**
- **0–29** → Low risk (no action)
- **30–59** → Medium risk (monitor)
- **60–100** → High risk (review / block)

**It looks at six signals per transaction:**
1. Device risk score
2. Whether the transaction is international
3. Transaction amount
4. Number of transactions in the last 24 hours (velocity)
5. Failed login attempts in the last 24 hours
6. Prior chargeback history on the account

---
**SCRIPT:**

"The scoring system is straightforward. Every transaction gets a score between 0 and 100 based on six risk signals — things like: was this device flagged as risky? Is the transaction coming from overseas? Has this account had chargebacks before? The higher the score, the riskier the transaction looks. Scores of 60 or above get flagged as high risk for review. This is the right approach in principle. The problem was in the math."

---

## SLIDE 3 — What Was Broken

**Four signals were inverted — high-risk indicators were *lowering* the score instead of raising it:**

| Signal | What the code was doing | What it should do |
|---|---|---|
| High device risk score (≥70) | **−25 points** | +25 points |
| International transaction | **−15 points** | +15 points |
| High transaction velocity (≥6 in 24h) | **−20 points** | +20 points |
| Prior chargeback history | **−5 to −20 points** | +5 to +20 points |

**In plain terms: the system was treating red flags as gold stars.**

---
**SCRIPT:**

"Here is the core problem. Four of the six risk signals were coded backwards. When a transaction came in from a high-risk device, the system *lowered* the risk score by 25 points. When a transaction crossed an international border — one of the most consistent fraud indicators in payments — the system *reduced* the score by 15. When an account had 6 or more transactions in a single day, which is a classic account-takeover pattern, the score went down by 20. And when an account already had prior chargebacks — meaning we knew for a fact that account had been involved in fraud before — the score actually *dropped*.

To put it bluntly: a fraudster who hit all four of these triggers would have been handed a lower risk score than a regular customer buying groceries."

---

## SLIDE 4 — The Real-World Impact (Before the Fix)

**We tested the old scoring against our 8 confirmed chargebacks from this period:**

| Metric | Old System |
|---|---|
| Chargebacks correctly flagged as high risk | **0 out of 8** |
| Fraud dollars invisible to the system | **$4,854.98** |
| Legitimate transactions incorrectly flagged | **0** |

**The system had a 0% detection rate on known fraud — while generating no false positives.**
**It wasn't cautious. It was blind.**

---
**SCRIPT:**

"This is where the business impact becomes concrete. We ran the old scoring logic against the 8 confirmed chargebacks from this period — the transactions we know for certain were fraud. The old system flagged zero of them as high risk. Not one. Every single confirmed fraud transaction was labeled 'low risk.' The system was sitting on $4,855 in fraud losses and calling all of it safe.

To be clear, it wasn't generating false alarms on legitimate customers either. It simply wasn't detecting anything. The fraud team had no signal to act on."

---

## SLIDE 5 — After the Fix

**The same 8 confirmed chargebacks, rescored with corrected logic:**

| Metric | Old System | Fixed System |
|---|---|---|
| Chargebacks flagged as high risk | **0 of 8** | **7 of 8** |
| Fraud dollars visible to reviewers | **$0** | **$4,234.99** |
| Fraud dollars still missed | **$4,854.98** | **$620.00** |
| Legitimate transactions incorrectly flagged | 0 | **0** |

**Detection rate improved from 0% to 87.5% — with no increase in false positives.**

---
**SCRIPT:**

"After the fix, we rescore the same transactions. Now 7 of the 8 confirmed chargebacks are flagged as high risk. That's an 87.5% detection rate, up from zero. The fraud team would have had a queue to work from. The one transaction still missed — $620 — scored medium risk, which means it would still be monitored, just not prioritized for immediate review.

Critically, we did not introduce any new false positives. Zero legitimate customer transactions were incorrectly flagged. This is the best possible outcome: we catch far more fraud without creating friction for good customers."

---

## SLIDE 6 — A Concrete Example

**Transaction 50003 — Confirmed $1,250 chargeback:**

| Signal | Value | What it means |
|---|---|---|
| Device risk score | 81 | High-risk device |
| International | Yes | Cross-border transaction |
| Amount | $1,250 | Large purchase |
| Velocity (24h) | 6 transactions | Unusually high activity |
| Failed logins (24h) | 5 | Likely account takeover attempt |

- **Old score: 0 → Labeled LOW RISK**
- **New score: 100 → Labeled HIGH RISK**

---
**SCRIPT:**

"Let me make this real with one transaction. Transaction 50003 is a $1,250 purchase that resulted in a confirmed chargeback. Look at the profile: the device had a risk score of 81 out of 100. The transaction was international. The amount was over $1,000. There were 6 transactions on that account in the same day. And there were 5 failed login attempts — a strong indicator someone was trying to break into the account before succeeding.

Under the old system, all five of those warning signs combined to produce a score of zero. The system looked at this transaction and said: completely safe, no action needed. Under the fixed system, this transaction scores 100 — the maximum — and goes straight to the top of the review queue. The fraud team would have had the opportunity to stop this one."

---

## SLIDE 7 — What We Did to Fix It and Protect Against Regression

**The fix:**
- Five targeted corrections in the scoring code — sign flips only, no logic changes
- No changes to thresholds, no changes to which signals are used

**How we protect against it happening again:**
- Added 73 automated tests covering every scoring rule, every threshold boundary, and the full pipeline
- Tests now verify the exact point value contributed by each signal
- A regression test locked to the Transaction 50003 profile — if that transaction ever scores anything other than "high," the build fails

---
**SCRIPT:**

"The fix itself was surgical — five sign corrections in the scoring code. We didn't redesign the system or change what signals it looks at. We just made sure the math goes in the right direction.

More importantly, we've made this impossible to break silently in the future. We added 73 automated tests. Every scoring rule now has a test that checks the exact number of points it contributes. Every threshold — the boundary between 'medium' and 'high' device risk, the cutoff between 'some velocity' and 'high velocity' — has a before-and-after test. And we locked in a test based on Transaction 50003: if that profile ever comes back as anything other than high risk, the entire deployment stops until someone fixes it. The system now validates itself every time anyone makes a change."

---

## SLIDE 8 — Summary and Next Steps

**What changed:**
- Four inverted risk signals corrected
- Fraud detection rate: 0% → 87.5% on confirmed chargebacks
- Fraud dollars visible to reviewers: $0 → $4,235
- False positive rate: unchanged at 0%

**Recommended next steps:**
1. Monitor the high-risk queue over the next 30 days and compare chargeback rates by label
2. Investigate the one missed chargeback ($620) to understand if a threshold adjustment is warranted
3. Review whether the scoring weights reflect current fraud patterns — the signals are now correct; calibrating the point values is a separate future exercise

---
**SCRIPT:**

"To summarize: the scoring system had four inverted signals that caused it to miss every confirmed fraud transaction we saw this period. We corrected those signals, validated the fix against real data, and locked in tests to prevent regression. The detection rate on known fraud went from zero to 87.5% with no new false positives.

Three things I'd recommend from here. First, run the system in production over the next 30 days and measure chargeback rates by risk label — that will tell us whether the improvements hold up at scale. Second, look at the one transaction we're still missing: a $620 chargeback that scored medium. It may warrant a threshold review. Third, and this is a longer-term project: now that the signals are pointing in the right direction, we should revisit the point values assigned to each one. Are 25 points for a large amount and 15 for an international transaction still the right calibration? That's a data-driven conversation worth having once we have a few months of correctly-scored transactions to learn from.

Happy to take questions."

---
