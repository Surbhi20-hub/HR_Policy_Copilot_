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
