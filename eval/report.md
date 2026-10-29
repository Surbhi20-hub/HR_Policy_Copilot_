# Evaluation report

## Metrics - hybrid retriever

Run on 2026-10-29 | LLM: groq / openai/gpt-oss-20b | Judge: groq / openai/gpt-oss-120b | 40 questions (0 with errors)

| Metric | Result | Target | Status |
|---|---|---|---|
| Answer correctness (judge) | 80.0% (24/30) | >= 80.0% | PASS |
| Refusal accuracy | 90.0% (9/10) | >= 90.0% | PASS |
| Faithfulness (judge) | 92.3% (24/26) | - | - |
| Retrieval hit-rate@5 | 100.0% (26/26) | - | - |
| Citation presence | 96.2% (25/26) | - | - |
| Latency average | 10.99 s | < 8 s | FAIL |
| Latency p95 | 22.04 s | - | - |
| Tokens per question (average) | 2873 | - | - |
| Total tokens (input + output) | 114,939 (96,753 + 18,186) | - | - |
| ESTIMATED cost per question | $0.00032 | - | - |
| ESTIMATED total cost | $0.0127 | - | - |

### Speed, tokens and cost - hybrid

| Item | Value |
|---|---|
| Average latency | 10.99 s (target < 8 s) |
| p95 latency | 22.04 s |
| Total tokens | 114,939 (96,753 in + 18,186 out) |
| ESTIMATED cost | $0.0127 total, $0.00032 per question (price guess: $0.075 in / $0.3 out per 1M tokens) |
| Real cost | Rs 0 (free tiers) |
| Free-tier waiting (NOT in latency) | 152 s (retries and pauses between questions) |

Where the time goes (average seconds per question):

| Step | Average seconds | Share |
|---|---|---|
| answer | 5.14 | 47% |
| grounding_check | 4.39 | 40% |
| router | 1.20 | 11% |
| rewrite_question | 0.14 | 1% |
| retrieval | 0.09 | 1% |
| tool | 0.00 | 0% |
| out_of_scope | 0.00 | 0% |

The average is over 8 s. The 3 slowest steps and simple fixes:

- **answer** (5.14 s): Shorter context: lower k or use shorter chunks, so the LLM reads less. Also keep answers short.
- **grounding_check** (4.39 s): Use a smaller, faster model for this check (needs a new model setting in src/config.py; not built yet).
- **router** (1.20 s): Use a smaller, faster model for the router (needs a new model setting in src/config.py; not built yet).

Slowest single questions: Q22 (32 s), Q17 (23 s), Q19 (22 s). If these are far above the rest, my guess is free-tier slowdowns inside the LLM client (not proven; they cannot be separated from real latency).

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
| Answer correctness (judge) | 80.0% (24/30) | 80.0% (24/30) |
| Refusal accuracy | 90.0% (9/10) | 90.0% (9/10) |
| Faithfulness (judge) | 96.2% (25/26) | 92.3% (24/26) |
| Retrieval hit-rate@5 | 100.0% (26/26) | 100.0% (26/26) |
| Citation presence | 100.0% (26/26) | 96.2% (25/26) |
| Latency average | 9.91 s | 10.99 s |
| Latency p95 | 18.00 s | 22.04 s |
| Tokens per question (average) | 2691 | 2873 |
| Total tokens (input + output) | 107,635 (91,416 + 16,219) | 114,939 (96,753 + 18,186) |
| ESTIMATED cost per question | $0.00029 | $0.00032 |
| ESTIMATED total cost | $0.0117 | $0.0127 |

## Failed questions - hybrid (9)

- **Q2** (policy) What is the maximum PL I can carry forward?
  - Expected: 30 days; excess lapses on 31 December.
  - Got (route policy): The maximum amount of earned/privilege leave you can carry forward is 30 days.
  - Why it failed: wrong answer: The answer gives the 30 days limit but omits the expected detail that excess leave lapses on 31 December.
- **Q5** (policy) Can interns work from home?
  - Expected: Interns must work from office unless the manager approves otherwise in writing.
  - Got (route policy): Interns can work from home only if their manager gives written approval. If they want to work fully remote for more than two weeks, they also need approval from the department head and HR.
  - Why it failed: wrong answer: The answer adds extra approval requirements not stated in the expected answer, which goes beyond the policy.
- **Q17** (policy) How many days of PL do I accrue in 6 months?
  - Expected: 9 days (1.5 days per month x 6 months).
  - Got (route policy): Full‑time employees accrue 1.5 PL days per month, so 9 days in six months. Probationary employees accrue PL but may only use up to 5 days during probation; the policy does not state the accrual rate for them.
  - Why it failed: unfaithful: Full‑time employees accrue 1.5 PL days per month, so 9 days in six months.
- **Q18** (policy) If I travel to a metro city for 3 days, how much daily allowance can I claim in total?
  - Expected: INR 7,500 (3 days x INR 2,500 per day for metro cities).
  - Got (route policy): You can claim INR 7,500 in total (INR 2,500 per day for 3 days).
  - Why it failed: unfaithful: INR 7,500 in total (INR 2,500 per day for 3 days); for 3 days
- **Q23** (policy) When is an employee put on a PIP and how long does it last?
  - Expected: After a rating of 1, or after a rating of 2 in two consecutive cycles. A PIP lasts 60 days, with a review meeting with the manager every 2 weeks.
  - Got (route policy): An employee is put on a PIP after receiving a rating of 1, or after receiving a rating of 2 in two consecutive performance cycles. The PIP lasts 60 days.
  - Why it failed: wrong answer: The answer omits the expected detail that a review meeting with the manager occurs every 2 weeks.
- **Q26** (policy) How much hotel cost can I claim in Bengaluru if I book the hotel myself?
  - Expected: Self-booked hotels are reimbursed up to INR 6,000 per night in metro cities. The policy does not list which cities are metro and gives no limit for non-metro cities, so it cannot confirm Bengaluru. Hotel bookings should normally be made through the company travel desk. Contact HR.
  - Got (route policy): I couldn't find this in the policy. Please contact hr@company.com.
  - Why it failed: wrong answer: The answer does not provide the known reimbursement limit of INR 6,000 per night and fails to note the policy uncertainty about Bengaluru.
  - Why it failed: no citation
- **Q31** (personal) Can I take 5 days of PL next week?
  - Expected: No. Your PL balance is 4.5 days (HRMS), which is less than 5, and probationary employees may take a maximum of 5 days of PL during probation.
  - Got (route personal): Hi Rohan, your remaining leave is: Privilege Leave (PL) 4.5 days, Casual Leave (CL) 6 days and Sick Leave (SL) 10 days. You are on probation, so ask me about the leave policy to see how that affects you.
  - Why it failed: wrong answer: The answer provides the PL balance but does not state that the request is denied or explain the probationary limit, missing key facts from the expected answer.
- **Q32** (sensitive) My manager keeps making uncomfortable comments about me. What can I do?
  - Expected: File a written complaint to the Internal Committee at ic@company.com within 3 months of the incident. Complaints are confidential and retaliation is a disciplinary offence. Be kind, give no legal advice, and suggest contacting HR.
  - Got (route sensitive): You can file a written complaint with the Internal Committee at ic@company.com within 3 months of the incident. The complaint will be handled confidentially, and retaliation against you is prohibited.
  - Why it failed: wrong answer: The answer omits the expected suggestion to contact HR.
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

## Failure analysis (5 cases, hybrid retriever, BEFORE and AFTER the prompt change)

**What I changed between the two runs:** three small edits to the answer prompt in `src/rag_chain.py`:
(1) rule 4, a sentence about limits given for a group such as "metro cities";
(2) rule 8, "include a condition, deadline, frequency or exception stated in the same chunk";
(3) the strict retry rule, "if only PART of the answer is supported, give that part".

**What I measured** (40 questions: 30 answerable, 10 that must be refused; same LLM judge, `groq / openai/gpt-oss-120b`, in all runs):

| Metric | Target | BEFORE (first run) | AFTER (final run) |
|---|---|---|---|
| Answer correctness | 80% or more | 83.3% (25/30) | 80.0% (24/30) |
| Refusal accuracy | 90% or more | 100% (10/10) | 90.0% (9/10) |
| Faithfulness | - | 100% (26/26) | 92.3% (24/26) |
| Retrieval hit-rate@5 | - | 100% (26/26) | 100% (26/26) |
| Citation presence | - | 96.2% (25/26) | 96.2% (25/26) |
| Average latency | under 8 s | 12.61 s | 10.99 s |

**Both Must targets (correctness, refusal) are met, but only exactly on the line** (24/30 is exactly 80%, 9/10 is exactly 90%). One more wrong answer would fail them. Latency (a Should) is still not met.

**The prompt change did not help overall.** It fixed one question (Q4) but 5 questions that passed before failed in BOTH of my after-change runs (Q5, Q17, Q18, Q32, Q40). Because the same questions failed twice, I think this is an effect of my change and not just noise, but I have not proven the cause. An earlier after-change run (finished in two sessions, saved in `eval/results_hybrid_after_run1.json`) scored 76.7% correctness and 80% refusal; its extra failures (Q9, Q14, Q20, Q39) passed in the final run, so single runs move by a few questions. One question is about 3 points.

The causes below are my reading of the answers. I marked "likely" where I have not confirmed it in the LangSmith trace.

### Case 1 - Q2 and Q23 (strict expected answer), BEFORE: failed, AFTER: failed
- **Q2** "What is the maximum PL I can carry forward?" Got "30 days". Expected "30 days; excess lapses on 31 December".
- **Q23** "When is an employee put on a PIP and how long does it last?" Got the trigger and "60 days". Expected the same plus "review every 2 weeks".
- **Why they failed:** the judge wanted a detail the question did not ask for.
- **Type:** mostly an evaluation problem (the expected answer is wider than the question). It is also a small real gap, because the extra detail matters to the employee.
- **Fix tried:** rule 8 (include conditions and frequencies from the same chunk). **Result:** no change. The answers still leave these details out.
- **Next step:** shorten the two expected answers to what the question asks, or tell the judge to ignore extra detail. I left them as they are so the score stays honest.

### Case 2 - Q4 "How long is paternity leave?", BEFORE: failed, AFTER: passed
- **Before:** "10 working days", without the time limit ("within 3 months of childbirth or adoption").
- **After:** the answer now includes the condition.
- **Type:** small real gap, fixed by rule 8. This is the one clear gain from the change.
- **Side effect (likely):** the same rule makes answers longer and can add details. In the final run the judge marked Q5 as going beyond the expected answer (it added department head and HR approval for more than two weeks of remote work) and Q17 as unfaithful (it added a sentence about probationary accrual).

### Case 3 - Q26 "How much hotel cost can I claim in Bengaluru if I book it myself?", BEFORE: failed, AFTER: failed
- **Got (both runs):** "I couldn't find this in the policy. Please contact hr@company.com." (no citation). With the vector retriever the bot instead said "INR 6,000 per night in Bengaluru" with no warning.
- **Why it failed:** the policy gives INR 6,000 only for "metro cities" and never lists them. The right answer states the limit and says the city list is missing.
- **Likely cause (not confirmed):** the grounding check rejected the half answer, the strict retry did not rescue it, and the safe fallback was used. The guardrail worked, but the user got no help.
- **Fix tried:** rule 4 (group sentence) and the "give the supported part" wording in the strict rule. **Result:** not fixed.
- **Next step:** open this question in LangSmith, read the first answer and the two grounding_check steps, and fix the step that rejects it.

### Case 4 - Q40 "What bonus does a rating of 5 get?", BEFORE: passed (refused), AFTER: failed
- **Got (both after runs):** "A rating of 5 earns an increment of 12% to 15%." **Expected:** refuse, because the policy covers increments, not bonuses.
- **Why it failed:** a look-alike question. The model answered the nearest thing it found. The vector retriever also failed this question before my change.
- **Likely cause:** the new "give the supported part" wording in the strict rule makes the model more willing to answer part of a question. Not confirmed.
- **Next step:** make the strict rule say "if the question asks for something the context does not mention (for example a bonus when the context only has increments), say it is not covered". This is the refusal metric that sits exactly on its 90% line, so it is the most important next fix.

### Case 5 - Q31 "Can I take 5 days of PL next week?" as E1002, BEFORE: failed, AFTER: failed
- **Got:** the leave balances only (route personal). **Expected:** "No: 4.5 days left, and probation allows at most 5 days of PL".
- **Why it failed:** the router sends any question about my leave to the HRMS tool, and the tool only prints balances. It never looks at the policy.
- **Type:** design limit of the 4-route graph. The assignment describes personal questions as tool-only, so this is outside the required scope.
- **What I would do in production:** a route that uses the tool and the policy search together.

### Other failures in the final run
| Question | What happened | Likely type |
|---|---|---|
| Q17, Q18 | Marked "unfaithful", but the answers (9 days, INR 7,500) are correct. The judge's reason only repeats the answer | Judge too strict about simple arithmetic. Q17 also has an extra sentence worth checking by hand |
| Q5 | Added approval rules for more than two weeks of remote work | Extra detail (see Case 2). The detail may exist in the WFH policy, check by hand |
| Q32 | Sensitive question: gave the Internal Committee steps but did not say "contact HR" | Small real gap in the sensitive prompt |

### Summary
| Type | Questions |
|---|---|
| Evaluation too strict | Q2, Q23, Q17, Q18 |
| Fixed by the prompt change | Q4 |
| Possible side effect of the prompt change | Q5, Q32, Q40 (and Q17) |
| Real weakness, not fixed | Q26, Q31 |

## How to read this

- Correctness, refusal and faithfulness are decided by an LLM judge, so they can be a little wrong. Check every failed question by eye before trusting the number.
- Hit-rate skips unanswerable questions and personal (HRMS tool) questions, which never retrieve chunks.
- Cost is an ESTIMATE from token counts and the small price table in src/query_log.py.
