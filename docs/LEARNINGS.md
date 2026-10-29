# Learnings

Numbers below come from the first full evaluation run (40 questions: 30 answerable, 10 that must be refused), see `eval/report.md`.
After my later prompt changes I ran the evaluation again; those results are in the last column of the table and in `eval/failure_analysis.md`.
The judge is an LLM, so scores can move by a question or two between runs (one question is about 3 points).

| Metric | Hybrid (first run) | Hybrid (after prompt change) | Vector only | Target |
|---|---|---|---|---|
| Answer correctness | 83.3% (25/30) | 80.0% (24/30) | 80.0% (24/30) | 80% or more |
| Refusal accuracy | 100% (10/10) | 90.0% (9/10) | 90.0% (9/10) | 90% or more |
| Faithfulness | 100% (26/26) | 92.3% (24/26) | 96.2% (25/26) | - |
| Retrieval hit-rate@5 | 100% (26/26) | 100% (26/26) | 100% (26/26) | - |
| Citation presence | 96.2% (25/26) | 96.2% (25/26) | 100% (26/26) | - |
| Average / p95 latency | 12.61 s / 22.70 s | 10.99 s / 22.04 s | 9.91 s / 18.00 s | under 8 s average |
| Tokens per question | 2,769 | 2,873 | 2,691 | - |
| Estimated cost per question | $0.00031 | $0.00032 | $0.00029 | - (real cost Rs 0) |

## What worked

- **Chunking by policy section, with the section number kept.** Each chunk knows its file and section, so a citation like `leave_policy.md#2` can be checked automatically. The right section was in the top 5 chunks for **26 of 26** answerable policy questions with both hybrid and vector search.
- **Structured output with Pydantic.** The router, the answer (with citations), the fact-check and the question rewriter all return typed objects. A citation quote is cut to 25 words, and an answer with no citation is forced to say "contact HR". That removed a whole class of format bugs.
- **A fact-check step plus a word-for-word quote check, with exactly one stricter retry and then a safe fallback.** Hybrid faithfulness was 100% (26/26). A made-up quote cannot reach the user.
- **Refusal behaviour.** Hybrid refused all 10 questions it should (100%), including a prompt-injection try, another employee's private data, medical and legal advice, and "looks like policy but is not covered" questions (notice period, bonus).
- **The employee ID comes from the app state, never from the typed text.** A test proves that a question naming E1003 still looks up only the logged-in user.
- **Hybrid versus vector.** Hybrid was a little better on correctness (83.3% vs 80.0%) and refusal (100% vs 90%). Retrieval hit-rate was identical, so the difference came from the answers, not from finding the chunk. With 40 questions this is a small, suggestive difference, not proof.
- **Follow-up memory.** A rewrite step turns "and for interns?" into a complete question, and runs only on the policy route. It needed a prompt with a right and a wrong example before it stopped keeping "casual leave" in the rewritten question.
- **Engineering habits that paid off:** an evaluation script that saves after every question and can resume; step-by-step timing and a per-query log with masked IDs; a test that scans the repo for hard-coded keys; 85 tests; LangSmith traces to see every LLM call.

## What didn't

- **Free-tier limits were the biggest practical problem.** Groq's free plan allowed 200,000 tokens per day for this model, and one full evaluation (copilot calls plus judge calls) uses about that much. A re-run after my prompt changes stopped on `429` errors with 5 of 40 questions missing, so I could not finish the before/after comparison the same day. The evaluation had to be resumable, and the report separates waiting time from real latency.
- **Latency missed the target:** 12.61 s average (hybrid) and 9.91 s (vector) against under 8 s. A policy question makes up to 4 LLM calls in a row (router, answer, fact-check, and a rewrite on follow-ups). A few single questions took 50 to 115 s. I think that was free-tier slowing inside the LLM client, but I could not prove it, because those waits cannot be separated from real latency.
- **The first question after start took about 95 s** (the embedding model loading). Loading it once at app start fixed it.
- **Model names and providers change under you.** `llama-3.3-70b-versatile` returned 404 on my account, and a Gemini 2.5 model name was reported as "no longer available to new users". The Gemini connection also failed from my network (`WinError 10053` and read timeouts) even though a plain model-list request worked. Keeping the model name only in `.env` made these one-line fixes, which is the point of the provider switch.
- **The LLM judge is not perfect.** In the vector run it called a correct answer "unfaithful" because the answer said "the policy does not specify whether Pune is metro". Two expected answers were also stricter than the question asked.
- **Prompt changes are hard to prove.** After I changed the answer prompt to include conditions like "within 3 months", a partial re-run showed some new failures I did not expect. It could be noise or a side effect. Final numbers: correctness 80.0% and refusal 90.0%, so both targets pass but exactly on the line, and the change did not help overall (it fixed Q4, but Q5, Q17, Q18, Q32 and Q40 failed in both after-change runs). Lesson: one prompt edit can fix one question and break others, so every prompt change needs a full re-run and a before/after comparison, and I should have kept a copy of the old prompt to revert.
- **Streamlit's file watcher** printed hundreds of `torchvision` messages with `transformers`. It was harmless, and one setting (`fileWatcherType = "none"`) fixed it.

## Biggest failure modes found in eval

The five questions that failed in the first hybrid run (BEFORE the prompt change), with my reading of each cause. Their results after the change are in the last bullet of this section:

| Question | What happened | Cause |
|---|---|---|
| Q2 maximum PL carry forward | Answered "30 days" and left out "excess lapses on 31 December" | The expected answer was wider than the question. Answers were also short because the prompt asked for 1 to 4 short sentences |
| Q4 paternity leave | Answered "10 working days" and left out "within 3 months" | Prompt: details next to the number were dropped. A small real gap |
| Q23 PIP | Left out the "review every 2 weeks" | Same as Q2: strict expected answer plus a short answer |
| Q26 hotel limit in Bengaluru | Hybrid: "I couldn't find this in the policy". Vector: a confident "INR 6,000" | The policy gives INR 6,000 only for "metro cities" and never lists them. The right answer is a half answer: the limit, plus "the policy does not say if Bengaluru is metro". Hybrid's fallback was safe but not helpful (likely cause: the strict retry told the model to give up; not confirmed). Vector guessed |
| Q31 "Can I take 5 days of PL?" as a probation employee | Only the leave balances were shown | Design limit: the personal route is tool-only and never looks at the policy. Fixing it needs a mixed route, which the assignment does not ask for |

Other things found:

- **Vector-only failures:** Q40 ("what bonus does a rating of 5 get?") was answered with the increment instead of a refusal, so a look-alike question fooled it. Q14 (business class to Delhi) left out the rule that economy applies to everyone.
- **Latency outliers and rate limits** (above).
- **Run-to-run noise.** A question can pass in one run and fail in the next, so a single run is weak evidence for small changes.
- **Policy gaps, not bugs.** The policies never list which cities are "metro", give no hotel limit for non-metro cities, and do not define "Director and above". Questions that depend on these can only be half-answered.
- **After-fix results for the five cases:** Q4 was fixed. Q2, Q23, Q26 and Q31 still fail. Q40 (bonus versus increment) went from a correct refusal to a wrong answer, which is the most important next fix because refusal sits exactly on its 90% target. Details in `eval/failure_analysis.md`.

## What I'd change for production

- **The re-ranker I tried did not help.** The optional cross-encoder (`RETRIEVER_MODE=rerank`) raised hit-rate@1 from 76.9% to 80.8% (one question) but lowered hit-rate@5 from 100% to 92.3% (two questions lost) and made search about 66 times slower (105 ms to 6,970 ms). Details are in `eval/rerank_report.md`. I would not use it as built. Things to try: split chunks smaller so they fit the model's 512-token limit, a different re-ranker model, or re-ranking only when hybrid scores are close. I measured retrieval only, not answer quality.
- **Faster models for small jobs.** Use a small, quick model for the router, the rewrite and the fact-check, and keep the bigger model for the answer. Add provider failover and retries for rate limits, or a paid tier.
- **Real login.** Replace the sidebar dropdown with company sign-in (SSO). The employee ID must come from the verified identity on the server side. Read leave balances from the real HRMS through a limited API, with an audit log of every lookup.
- **Privacy of employee data.** Mask or remove personal data before it reaches the LLM or traces. Our own logs already mask IDs and store no question text, but LangSmith traces still contain the real ID. Decide what may leave the company, how long logs are kept, and check the rules that apply (for example India's data-protection law) with legal and compliance.
- **Caching.** Cache answers by normalized question and policy version (many employees ask the same things), cache embeddings, and use the provider's prompt caching for the long system prompt.
- **Monitoring.** Use the per-query log (seconds per step, tokens, cost) for dashboards and alerts on p95 latency, cost, refusal rate, "fallback" rate and thumbs-down. Run the golden set on a schedule and after every prompt or model change, and keep the judge fixed so results can be compared.
- **Policy versioning.** Chunks already carry the policy's effective date. In production: keep old versions, retrieve by date, re-ingest when a policy changes (the chunk IDs make that safe to repeat), show the effective date in answers, and re-run the golden set on every policy update.
- **A mixed route and better half answers.** Let a question like Q31 use the HRMS record and the policy together. Teach the answer step to give the known part and name the missing fact, instead of guessing or giving up.
- **Fix the policies themselves.** List the metro cities, define the grades, and give the hotel limit for non-metro cities, so the assistant has something to quote.
- **Keep a human in the loop.** Sensitive questions already always point to HR. In production they would also open a ticket for a person to follow up.