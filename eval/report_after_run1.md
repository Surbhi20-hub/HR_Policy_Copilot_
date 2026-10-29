# Evaluation report

## Metrics - hybrid retriever

Run on 2026-10-29 | LLM: groq / openai/gpt-oss-20b | Judge: groq / openai/gpt-oss-120b | 40 questions (0 with errors)

| Metric | Result | Target | Status |
|---|---|---|---|
| Answer correctness (judge) | 76.7% (23/30) | >= 80.0% | FAIL |
| Refusal accuracy | 80.0% (8/10) | >= 90.0% | FAIL |
| Faithfulness (judge) | 88.5% (23/26) | - | - |
| Retrieval hit-rate@5 | 100.0% (26/26) | - | - |
| Citation presence | 96.2% (25/26) | - | - |
| Latency average | 17.18 s | < 8 s | FAIL |
| Latency p95 | 39.27 s | - | - |
| Tokens per question (average) | 2890 | - | - |
| Total tokens (input + output) | 115,581 (96,798 + 18,783) | - | - |
| ESTIMATED cost per question | $0.00032 | - | - |
| ESTIMATED total cost | $0.0129 | - | - |

### Speed, tokens and cost - hybrid

| Item | Value |
|---|---|
| Average latency | 17.18 s (target < 8 s) |
| p95 latency | 39.27 s |
| Total tokens | 115,581 (96,798 in + 18,783 out) |
| ESTIMATED cost | $0.0129 total, $0.00032 per question (price guess: $0.075 in / $0.3 out per 1M tokens) |
| Real cost | Rs 0 (free tiers) |
| Free-tier waiting (NOT in latency) | 448 s (retries and pauses between questions) |

Where the time goes (average seconds per question):

| Step | Average seconds | Share |
|---|---|---|
| grounding_check | 3.41 | 48% |
| answer | 2.32 | 33% |
| router | 1.26 | 18% |
| retrieval | 0.07 | 1% |
| rewrite_question | 0.00 | 0% |

The average is over 8 s. The 3 slowest steps and simple fixes:

- **grounding_check** (3.41 s): Use a smaller, faster model for this check (needs a new model setting in src/config.py; not built yet).
- **answer** (2.32 s): Shorter context: lower k or use shorter chunks, so the LLM reads less. Also keep answers short.
- **router** (1.26 s): Use a smaller, faster model for the router (needs a new model setting in src/config.py; not built yet).

Slowest single questions: Q34 (87 s), Q35 (57 s), Q26 (39 s). If these are far above the rest, my guess is free-tier slowdowns inside the LLM client (not proven; they cannot be separated from real latency).

## Metrics - vector retriever

Run on 2026-10-26 | LLM: groq / openai/gpt-oss-20b | Judge: groq / openai/gpt-oss-120b | 40 questions (0 with errors)

| Metric | Result | Target | Status |
|---|---|---|---|
| Answer correctness (judge) | 80.0% (24/30) | >= 80.0% | PASS |
| Refusal accuracy | 90.0% (9/10) | >= 90.0% | PASS |
| Faithfulness (judge) | 96.2% (25/26) | - | - |
| Retrieval hit-rate@5 | 100.0% (26/26) | - | - |
| Citation presence | 100.0% (26/26) | - | - |
| Latency average | 9.91 s | < 8 s | FAIL |
| Latency p95 | 18.00 s | - | - |
| Tokens per question (average) | 2691 | - | - |
| Total tokens (input + output) | 107,635 (91,416 + 16,219) | - | - |
| ESTIMATED cost per question | $0.00029 | - | - |
| ESTIMATED total cost | $0.0117 | - | - |

### Speed, tokens and cost - vector

| Item | Value |
|---|---|
| Average latency | 9.91 s (target < 8 s) |
| p95 latency | 18.00 s |
| Total tokens | 107,635 (91,416 in + 16,219 out) |
| ESTIMATED cost | $0.0117 total, $0.00029 per question (price guess: $0.075 in / $0.3 out per 1M tokens) |
| Real cost | Rs 0 (free tiers) |
| Free-tier waiting (NOT in latency) | 156 s (retries and pauses between questions) |

No per-step timing in this results file (it was made before step timing existed).

## Vector vs hybrid

| Metric | Vector | Hybrid |
|---|---|---|
| Answer correctness (judge) | 80.0% (24/30) | 76.7% (23/30) |
| Refusal accuracy | 90.0% (9/10) | 80.0% (8/10) |
| Faithfulness (judge) | 96.2% (25/26) | 88.5% (23/26) |
| Retrieval hit-rate@5 | 100.0% (26/26) | 100.0% (26/26) |
| Citation presence | 100.0% (26/26) | 96.2% (25/26) |
| Latency average | 9.91 s | 17.18 s |
| Latency p95 | 18.00 s | 39.27 s |
| Tokens per question (average) | 2691 | 2890 |
| Total tokens (input + output) | 107,635 (91,416 + 16,219) | 115,581 (96,798 + 18,783) |
| ESTIMATED cost per question | $0.00029 | $0.00032 |
| ESTIMATED total cost | $0.0117 | $0.0129 |

## Failed questions - hybrid (12)

- **Q2** (policy) What is the maximum PL I can carry forward?
  - Expected: 30 days; excess lapses on 31 December.
  - Got (route policy): The maximum amount of earned/privilege leave you can carry forward is 30 days.
  - Why it failed: wrong answer: The answer gives the 30‑day limit but omits the expected detail that excess leave lapses on 31 December.
- **Q5** (policy) Can interns work from home?
  - Expected: Interns must work from office unless the manager approves otherwise in writing.
  - Got (route policy): Interns can work from home only if their manager gives written approval. If they are approved for fully remote work beyond two weeks, that also needs approval from the department head and HR.
  - Why it failed: wrong answer: The answer adds extra approval requirements beyond manager written approval, which contradicts the expected policy that only manager approval is needed.
- **Q9** (policy) Can I accept a gift worth INR 3,000 from a vendor?
  - Expected: No, gifts above INR 2,000 must be declined or declared to compliance.
  - Got (route policy): No, you must decline or declare it to compliance@company.com.
  - Why it failed: wrong answer: The answer omits the key threshold amount of INR 2,000 required by the expected answer.
- **Q14** (policy) Can I fly business class to Delhi?
  - Expected: Economy class for all employees; business class only for flights over 6 hours for Director and above. The policy does not say how long a Delhi flight is or what your grade is, so it cannot give a yes or no; contact HR.
  - Got (route policy): Business class is only allowed for flights over 6 hours for Directors and above. The policy does not state the flight duration to Delhi, so we cannot confirm if it qualifies.
  - Why it failed: wrong answer: The answer omits the policy's economy‑class rule for all employees and does not mention contacting HR, missing key facts.
- **Q17** (policy) How many days of PL do I accrue in 6 months?
  - Expected: 9 days (1.5 days per month x 6 months).
  - Got (route policy): Full‑time employees accrue 1.5 PL days per month, so 9 days in six months. Probationary employees accrue PL but may only use up to 5 days during probation; the policy does not state the accrual rate for them.
  - Why it failed: unfaithful: Full‑time employees accrue 1.5 PL days per month, so 9 days in six months.
- **Q18** (policy) If I travel to a metro city for 3 days, how much daily allowance can I claim in total?
  - Expected: INR 7,500 (3 days x INR 2,500 per day for metro cities).
  - Got (route policy): You can claim INR 7,500 in total for a 3‑day stay in a metro city (INR 2,500 per day).
  - Why it failed: unfaithful: INR 7,500 total for a 3‑day stay; 3‑day stay
- **Q20** (policy) I am an intern. Can I work from home, and how many days of leave will I have after 6 months of internship?
  - Expected: Interns must work from office unless their manager approves otherwise in writing. Interns get 1 day of leave per month, so 6 days after 6 months.
  - Got (route policy): Interns must work from the office unless their manager approves otherwise in writing. They earn 1 day of leave per month, so after 6 months they have 6 days of leave.
  - Why it failed: unfaithful: after 6 months they have 6 days of leave
- **Q23** (policy) When is an employee put on a PIP and how long does it last?
  - Expected: After a rating of 1, or after a rating of 2 in two consecutive cycles. A PIP lasts 60 days, with a review meeting with the manager every 2 weeks.
  - Got (route policy): An employee is put on a PIP after receiving a rating of 1, or after receiving a rating of 2 in two consecutive performance cycles. The PIP lasts 60 days.
  - Why it failed: wrong answer: The answer omits the expected detail that a review meeting occurs every 2 weeks.
- **Q26** (policy) How much hotel cost can I claim in Bengaluru if I book the hotel myself?
  - Expected: Self-booked hotels are reimbursed up to INR 6,000 per night in metro cities. The policy does not list which cities are metro and gives no limit for non-metro cities, so it cannot confirm Bengaluru. Hotel bookings should normally be made through the company travel desk. Contact HR.
  - Got (route policy): I couldn't find this in the policy. Please contact hr@company.com.
  - Why it failed: wrong answer: The answer fails to provide the known reimbursement limit of INR 6,000 per night and does not acknowledge the policy uncertainty for Bengaluru.
  - Why it failed: no citation
- **Q31** (personal) Can I take 5 days of PL next week?
  - Expected: No. Your PL balance is 4.5 days (HRMS), which is less than 5, and probationary employees may take a maximum of 5 days of PL during probation.
  - Got (route personal): Hi Rohan, your remaining leave is: Privilege Leave (PL) 4.5 days, Casual Leave (CL) 6 days and Sick Leave (SL) 10 days. You are on probation, so ask me about the leave policy to see how that affects you.
  - Why it failed: wrong answer: The answer gives the PL balance but does not state the request is denied or mention the probationary max, missing key expected facts.
- **Q39** (personal) What is my current salary?
  - Expected: REFUSE - salary is not available in the HRMS data or policies; contact HR or payroll.
  - Got (route personal): Hi Asha, your remaining leave is: Privilege Leave (PL) 12.5 days, Casual Leave (CL) 5 days and Sick Leave (SL) 9 days.
  - Why it failed: should have refused: The response did not refuse the salary query and instead provided unrelated personal data.
- **Q40** (policy) What bonus does a rating of 5 get?
  - Expected: REFUSE - the performance policy covers increments, not bonuses; contact HR.
  - Got (route policy): A rating of 5 earns an increment of 12% to 15%.
  - Why it failed: should have refused: The answer provided the requested increment details instead of refusing.

## Failed questions - vector (8)

- **Q2** (policy) What is the maximum PL I can carry forward?
  - Expected: 30 days; excess lapses on 31 December.
  - Got (route policy): The maximum number of PL days you can carry forward is 30 days.
  - Why it failed: wrong answer: The answer gives the 30‑day carry‑forward limit but omits the expected detail that any excess lapses on 31 December.
- **Q4** (policy) How long is paternity leave?
  - Expected: 10 working days within 3 months of childbirth or adoption.
  - Got (route policy): Paternity leave is 10 working days.
  - Why it failed: wrong answer: The answer omits the condition that the 10 working days must be taken within 3 months of childbirth or adoption.
- **Q10** (policy) What is the daily allowance in Pune?
  - Expected: Depends on metro classification; metro INR 2,500, non-metro INR 1,800. Should note the policy does not list which cities are metro.
  - Got (route policy): The policy states that daily allowance is INR 2,500 for metro cities and INR 1,800 for non‑metro cities. It does not specify whether Pune is classified as a metro or non‑metro city.
  - Why it failed: unfaithful: It does not specify whether Pune is classified as a metro or non‑metro city.
- **Q14** (policy) Can I fly business class to Delhi?
  - Expected: Economy class for all employees; business class only for flights over 6 hours for Director and above. The policy does not say how long a Delhi flight is or what your grade is, so it cannot give a yes or no; contact HR.
  - Got (route policy): Business class is only allowed for flights over 6 hours for Directors and above. We don’t know if your flight to Delhi is over 6 hours or if you are a Director.
  - Why it failed: wrong answer: The answer omits the policy detail that all employees are limited to economy class, a key fact from the expected answer.
- **Q23** (policy) When is an employee put on a PIP and how long does it last?
  - Expected: After a rating of 1, or after a rating of 2 in two consecutive cycles. A PIP lasts 60 days, with a review meeting with the manager every 2 weeks.
  - Got (route policy): An employee is put on a PIP after receiving a rating of 1, or after receiving a rating of 2 in two consecutive performance cycles. The PIP lasts 60 days.
  - Why it failed: wrong answer: The answer omits the expected detail that a review meeting with the manager occurs every 2 weeks.
- **Q26** (policy) How much hotel cost can I claim in Bengaluru if I book the hotel myself?
  - Expected: Self-booked hotels are reimbursed up to INR 6,000 per night in metro cities. The policy does not list which cities are metro and gives no limit for non-metro cities, so it cannot confirm Bengaluru. Hotel bookings should normally be made through the company travel desk. Contact HR.
  - Got (route policy): You can claim up to INR 6,000 per night for a self‑booked hotel in Bengaluru.
  - Why it failed: wrong answer: The answer asserts a claim amount for Bengaluru, but the policy cannot confirm Bengaluru as a metro city, so it incorrectly provides a definitive amount.
- **Q31** (personal) Can I take 5 days of PL next week?
  - Expected: No. Your PL balance is 4.5 days (HRMS), which is less than 5, and probationary employees may take a maximum of 5 days of PL during probation.
  - Got (route personal): Hi Rohan, your remaining leave is: Privilege Leave (PL) 4.5 days, Casual Leave (CL) 6 days and Sick Leave (SL) 10 days. You are on probation, so ask me about the leave policy to see how that affects you.
  - Why it failed: wrong answer: The answer gives the correct PL balance but does not state that the request is denied nor mention the probationary maximum of 5 days.
- **Q40** (policy) What bonus does a rating of 5 get?
  - Expected: REFUSE - the performance policy covers increments, not bonuses; contact HR.
  - Got (route policy): A rating of 5 earns an increment of 12% to 15%.
  - Why it failed: should have refused: Answer provided the requested increment information instead of refusing as required.

## Stretch feature: cross-encoder re-ranker

Hybrid search takes 20 candidate chunks, then the cross-encoder `BAAI/bge-reranker-base` re-scores every (question, chunk) pair and keeps the best 5. Measured on 26 questions that have a right section to find, on 2026-10-28. No LLM was used, so this cost no Groq tokens.

| Metric | Hybrid (before) | Hybrid + re-ranker (after) |
|---|---|---|
| Hit-rate@1 | 76.9% | 80.8% |
| Hit-rate@3 | 100.0% | 92.3% |
| Hit-rate@5 | 100.0% | 92.3% |
| Mean reciprocal rank (1.0 is best) | 0.872 | 0.859 |
| Search time per question | 105 ms | 6970 ms |

Position of the right section changed for 5 of 26 questions (2 better, 3 worse).

| Question | Before | After |
|---|---|---|
| Q9 Can I accept a gift worth INR 3,000 from a vendor? | 2 | 1 |
| Q17 How many days of PL do I accrue in 6 months? | 2 | 1 |
| Q19 I am working from a cafe on public Wi-Fi. What do I need to  | 1 | 2 |
| Q20 I am an intern. Can I work from home, and how many days of l | 2 | - |
| Q32 My manager keeps making uncomfortable comments about me. Wha | 3 | - |

How to read this: hit-rate@5 of hybrid was already high, so the re-ranker cannot raise it much. The useful signals are hit@1, hit@3 and MRR (is the right chunk nearer the top?) and the search time. '-' means the right section was not in the top 5. A small sample, so small differences are not proof. Whether answers get better was NOT measured here: that needs `python eval/run_eval.py --retriever rerank` (uses Groq tokens).

## Failure analysis (5 cases, hybrid retriever)

Source: the 5 failed questions of the hybrid run (see "Failed questions - hybrid" above).
Three of them are judged too strictly; two are real weaknesses of the copilot.
Only the evaluation numbers were measured; the causes below are my reading of the answers
(marked "likely" where I have not yet confirmed it in the LangSmith trace).

### Case 1 - Q2 "What is the maximum PL I can carry forward?" (strict expected answer)
- **Got:** "30 days." **Expected:** "30 days; excess lapses on 31 December."
- **Why it failed:** the judge wanted a detail the question did not ask for.
- **Type:** evaluation problem (expected answer wider than the question), not a wrong answer.
- **What I would do:** shorten the expected answer to what the question asks, or tell the judge to ignore extra detail. Not changed yet, so the score stays honest.

### Case 2 - Q4 "How long is paternity leave?" (borderline)
- **Got:** "10 working days." **Expected:** "10 working days within 3 months of childbirth or adoption."
- **Why it failed:** the answer left out the time limit.
- **Type:** small real gap. The limit matters to the employee, but the question did not ask for it.
- **What I would do:** ask the answer prompt to include conditions that are stated next to the number.

### Case 3 - Q23 "When is an employee put on a PIP and how long does it last?" (strict expected answer)
- **Got:** the trigger and "60 days". **Expected:** the same plus "review every 2 weeks".
- **Why it failed:** the judge wanted the review frequency, which was not asked.
- **Type:** evaluation problem, like Case 1.
- **What I would do:** same as Case 1.

### Case 4 - Q26 "How much hotel cost can I claim in Bengaluru if I book it myself?" (real: half answer)
- **Got (hybrid):** "I couldn't find this in the policy. Please contact hr@company.com." (no citation).
  With the vector retriever the bot instead said "INR 6,000 per night in Bengaluru" with no warning.
- **Why it failed:** the policy gives INR 6,000 only for "metro cities" and never lists them. The right answer states the limit and says the city list is missing.
- **Likely cause:** the grounding check rejected a confident Bengaluru answer twice, so the safe fallback was used. The guardrail worked, but the user got no help. To confirm: open this question in LangSmith and look at the two grounding_check steps.
- **What I would do:** make the answer prompt say "state the known limit, then say what the policy does not cover".

### Case 5 - Q31 "Can I take 5 days of PL next week?" as E1002 (real: personal + policy mixed)
- **Got:** the leave balances only (route personal). **Expected:** "No: 4.5 days left, and probation allows at most 5 days of PL".
- **Why it failed:** the router sends any question about my leave to the HRMS tool, and the tool only prints balances. It never looks at the policy.
- **Type:** design limit of the 4-route graph. The assignment describes personal questions as tool-only, so this is outside the required scope.
- **What I would do in production:** a route that uses the tool and the policy search together.

### Summary
| Type | Cases |
|---|---|
| Evaluation too strict | Q2, Q23 |
| Small real gap | Q4 |
| Real weakness | Q26, Q31 |

## How to read this

- Correctness, refusal and faithfulness are decided by an LLM judge, so they can be a little wrong. Check every failed question by eye before trusting the number.
- Hit-rate skips unanswerable questions and personal (HRMS tool) questions, which never retrieve chunks.
- Cost is an ESTIMATE from token counts and the small price table in src/query_log.py.
