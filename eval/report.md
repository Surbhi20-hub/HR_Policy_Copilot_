# Evaluation report

## Metrics - hybrid retriever

Run on 2026-10-26 | LLM: groq / openai/gpt-oss-20b | Judge: groq / openai/gpt-oss-120b | 40 questions (0 with errors)

| Metric | Result | Target | Status |
|---|---|---|---|
| Answer correctness (judge) | 83.3% (25/30) | >= 80.0% | PASS |
| Refusal accuracy | 100.0% (10/10) | >= 90.0% | PASS |
| Faithfulness (judge) | 100.0% (26/26) | - | - |
| Retrieval hit-rate@5 | 100.0% (26/26) | - | - |
| Citation presence | 96.2% (25/26) | - | - |
| Latency average | 12.61 s | < 8 s | FAIL |
| Latency p95 | 22.70 s | - | - |
| Tokens per question (average) | 2769 | - | - |
| ESTIMATED cost per question | $0.00031 | - | - |

Time spent waiting for rate limits and pauses (NOT in latency): 152 s. ESTIMATED total cost: $0.0122 (real cost: Rs 0, free tier).

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
| ESTIMATED cost per question | $0.00029 | - | - |

Time spent waiting for rate limits and pauses (NOT in latency): 156 s. ESTIMATED total cost: $0.0117 (real cost: Rs 0, free tier).

## Vector vs hybrid

| Metric | Vector | Hybrid |
|---|---|---|
| Answer correctness (judge) | 80.0% (24/30) | 83.3% (25/30) |
| Refusal accuracy | 90.0% (9/10) | 100.0% (10/10) |
| Faithfulness (judge) | 96.2% (25/26) | 100.0% (26/26) |
| Retrieval hit-rate@5 | 100.0% (26/26) | 100.0% (26/26) |
| Citation presence | 100.0% (26/26) | 96.2% (25/26) |
| Latency average | 9.91 s | 12.61 s |
| Latency p95 | 18.00 s | 22.70 s |
| Tokens per question (average) | 2691 | 2769 |
| ESTIMATED cost per question | $0.00029 | $0.00031 |

## Failed questions - hybrid (5)

- **Q2** (policy) What is the maximum PL I can carry forward?
  - Expected: 30 days; excess lapses on 31 December.
  - Got (route policy): The maximum amount of earned/privilege leave you can carry forward is 30 days.
  - Why it failed: wrong answer: The answer gives the 30‑day limit but omits the expected detail that excess leave lapses on 31 December.
- **Q4** (policy) How long is paternity leave?
  - Expected: 10 working days within 3 months of childbirth or adoption.
  - Got (route policy): Paternity leave is 10 working days.
  - Why it failed: wrong answer: The answer omits the condition that the 10 working days must be taken within 3 months of childbirth or adoption.
- **Q23** (policy) When is an employee put on a PIP and how long does it last?
  - Expected: After a rating of 1, or after a rating of 2 in two consecutive cycles. A PIP lasts 60 days, with a review meeting with the manager every 2 weeks.
  - Got (route policy): An employee is put on a PIP after receiving a rating of 1, or after receiving a rating of 2 in two consecutive performance cycles. The PIP lasts 60 days.
  - Why it failed: wrong answer: The answer omits the expected detail about a review meeting with the manager every 2 weeks.
- **Q26** (policy) How much hotel cost can I claim in Bengaluru if I book the hotel myself?
  - Expected: Self-booked hotels are reimbursed up to INR 6,000 per night in metro cities. The policy does not list which cities are metro and gives no limit for non-metro cities, so it cannot confirm Bengaluru. Hotel bookings should normally be made through the company travel desk. Contact HR.
  - Got (route policy): I couldn't find this in the policy. Please contact hr@company.com.
  - Why it failed: wrong answer: The answer fails to provide the known reimbursement limit of INR 6,000 per night and does not note the policy's uncertainty about Bengaluru, only directs to HR.
  - Why it failed: no citation
- **Q31** (personal) Can I take 5 days of PL next week?
  - Expected: No. Your PL balance is 4.5 days (HRMS), which is less than 5, and probationary employees may take a maximum of 5 days of PL during probation.
  - Got (route personal): Hi Rohan, your remaining leave is: Privilege Leave (PL) 4.5 days, Casual Leave (CL) 6 days and Sick Leave (SL) 10 days. You are on probation, so ask me about the leave policy to see how that affects you.
  - Why it failed: wrong answer: The answer provides the PL balance but does not state that the request is denied or mention the probationary max, missing key facts from the expected answer.

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

## How to read this

- Correctness, refusal and faithfulness are decided by an LLM judge, so they can be a little wrong. Check every failed question by eye before trusting the number.
- Hit-rate skips unanswerable questions and personal (HRMS tool) questions, which never retrieve chunks.
- Cost is an ESTIMATE from token counts and the price numbers in eval/run_eval.py.
