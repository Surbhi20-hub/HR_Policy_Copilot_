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