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
