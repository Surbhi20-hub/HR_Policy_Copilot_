## Optional feature: standard graph against ReAct agent

The same 10 golden questions were run in both modes on 2026-11-23, with a pause between questions so the free Groq key is not used up. Tokens are the total of every LLM call of a question.

| Measure | Standard | Agent |
|---|---|---|
| Questions answered without an error | 10/10 | 10/10 |
| Automatic check passed (right section cited, or refused when it must be) | 7/8 | 7/8 |
| Passed the grounding check | 10/10 | 10/10 |
| Average time per question | 7.7 s | 20.0 s |
| Average tokens per question | 2,539 | 5,135 |
| Average tool calls per question | - | 1.0 |

| Question | Standard route | Standard time | Standard check | Agent route | Agent time | Agent tools | Agent check |
|---|---|---|---|---|---|---|---|
| Q1 | policy | 24.3 s | pass | policy | 28.1 s | 1 | pass |
| Q3 | policy | 2.7 s | pass | policy | 26.3 s | 1 | pass |
| Q5 | policy | 2.8 s | pass | policy | 6.5 s | 1 | pass |
| Q8 | policy | 3.2 s | pass | policy | 5.8 s | 1 | pass |
| Q10 | policy | 11.0 s | pass | policy | 27.6 s | 1 | pass |
| Q12 | policy | 11.1 s | pass | policy | 30.4 s | 1 | pass |
| Q28 | personal | 1.0 s | n/a | personal | 10.2 s | 1 | n/a |
| Q31 | personal | 0.6 s | n/a | policy | 41.7 s | 2 | n/a |
| Q34 | out_of_scope | 0.9 s | pass | out_of_scope | 2.7 s | 0 | pass |
| Q40 | policy | 19.3 s | fail | policy | 20.7 s | 1 | fail |

Notes:
- In the first run, agent Q5 took 1346 s (about 22 minutes), a one-off wait that was not repeated. When Q5 was run again alone it took 6.5 s, and that value is used above. With the 1346 s value, the agent average would be 154.0 s.
- The standard average includes the first question (24.3 s), which also loads the models. Without it the standard average is about 5.8 s.
- Agent tokens for Q5 were 4,690 in the first run and 4,691 in the second, so the work was the same.

How to read this: the automatic check is simpler than the LLM judge of `run_eval.py`, so these numbers are NOT the correctness score. 10 questions is a small sample. The agent makes more LLM calls per question, which costs more tokens (about 2 times here) and time (typically 20 to 30 s for a policy question against 3 to 11 s) and makes a free-tier rate limit more likely. Correctness on this sample was the same in both modes, so agent mode stays optional and off by default.