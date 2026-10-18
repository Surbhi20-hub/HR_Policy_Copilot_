# Assignment 1 — HR Policy Copilot (Agentic RAG with Citations & Guardrails)

**Duration:** 2 weeks (10 working days) · **Level:** Intermediate–Advanced · **Domain:** HR / Employee Self-Service

---

## 1. Topic

Build an **HR Policy Copilot** that answers employee questions about company policies (leave, travel, WFH, code of conduct) **only from the official policy documents**, always shows **citations**, refuses or escalates when the answer isn't in the documents, and handles **personalised questions** (e.g. "How many leaves do I have left?") by calling a tool instead of guessing.

**Why it matters:** HR teams spend a large share of their time answering repetitive policy questions. A wrong answer (e.g. about leave or reimbursement) creates real compliance risk, so the focus here is **grounded, verifiable answers** — not just a chatbot that sounds right.

---

## 2. Tech Stack

| Layer | Required | Allowed alternatives |
|---|---|---|
| Language | Python 3.10+ | — |
| Orchestration | **LangChain** (LCEL) + **LangGraph** | — |
| LLM | Any via `langchain.chat_models.init_chat_model` (OpenAI / Azure OpenAI / Gemini / Groq / Ollama) | Provider must be switchable from `.env` |
| Embeddings | OpenAI / HuggingFace (`bge-small`, `all-MiniLM`) / Ollama | — |
| Vector store | **Chroma** or **FAISS** | Qdrant, pgvector |
| Loaders / splitters | `PyPDFLoader`, `UnstructuredMarkdownLoader`, `RecursiveCharacterTextSplitter` | — |
| Retrieval | Hybrid: vector + **BM25** (`EnsembleRetriever`) | Add a re-ranker (Cohere / `bge-reranker`) as stretch |
| Structured output | `with_structured_output()` + **Pydantic** | — |
| Tools | `@tool` decorator — mock HRMS leave-balance lookup | — |
| Evaluation | **RAGAS** or a custom LLM-as-judge script | DeepEval |
| Observability | **LangSmith** tracing (free tier) | Langfuse |
| UI | **Streamlit** or Chainlit | Gradio |

---

## 3. POC Summary

An employee types a question in a chat UI. A LangGraph agent decides:

1. **Policy question** → hybrid retrieval → answer grounded in retrieved chunks, with citations (`document name + section`).
2. **Personal data question** ("my leave balance") → calls `get_leave_balance(employee_id)` tool (mock HRMS JSON).
3. **Out-of-scope / not in docs** → politely says it doesn't know and suggests contacting HR (`hr@company.com`). **Never invents policy.**
4. **Sensitive topics** (harassment, grievance, medical) → gives the relevant policy pointer + escalation path, with an empathetic tone.

```
User ─▶ Router node ─┬─▶ Policy RAG node ──▶ Grounding check ──▶ Answer + citations
                     ├─▶ HRMS tool node  ──────────────────────▶ Answer
                     ├─▶ Sensitive node  ──────────────────────▶ Policy pointer + escalation
                     └─▶ Out-of-scope    ──────────────────────▶ Polite refusal
```

---

## 4. Acceptance / Completion Criteria

The POC is **complete** only when ALL "Must" items pass.

| # | Criterion | Priority | How it's verified |
|---|---|---|---|
| AC1 | Ingests all docs in `data/policies/` via one command (`python -m src.ingest`) | Must | Run it on a clean machine |
| AC2 | Every policy answer includes ≥1 citation (doc name + section heading) | Must | Check 10 answers |
| AC3 | Questions in `eval/golden_qa.json` marked `answerable: false` get a refusal / "contact HR" (no invented answers) | Must | Eval script — **≥ 90%** refusal accuracy |
| AC4 | Answer correctness on answerable golden questions | Must | **≥ 80%** (LLM-judge or RAGAS answer_correctness ≥ 0.75) |
| AC5 | Leave-balance questions call the tool, not the vector store | Must | LangSmith trace shows tool call |
| AC6 | LLM provider switchable by changing `.env` only (no code change) | Must | Demo with 2 providers |
| AC7 | Streamlit/Chainlit chat UI with visible sources (expandable) | Must | Live demo |
| AC8 | Eval report `eval/report.md` with metrics table + 5 failure cases analysed | Must | Review |
| AC9 | Hybrid retrieval (BM25 + vector) and a short comparison vs vector-only | Should | Numbers in report |
| AC10 | Conversation memory (follow-up: "and for interns?") | Should | Demo |
| AC11 | Average latency < 8 s per answer; token/cost per query logged | Should | Report |
| AC12 | Re-ranker, PII masking of employee IDs in logs, Docker | Could | Stretch |

---

## 5. Detailed POC Specification

### 5.1 Data
- `data/policies/` contains 4 sample policies (Markdown). **Intern must add at least 2 more** realistic policies (e.g. IT Acceptable Use, Performance Review & Appraisal) — can be written with an LLM but must be reviewed for consistency. Convert at least one to **PDF** to prove PDF ingestion works.
- `data/hrms_mock.json` — mock employee leave data for the tool.

### 5.2 Ingestion (`src/ingest.py`)
- Load MD + PDF, split with header-aware chunking (`MarkdownHeaderTextSplitter` then `RecursiveCharacterTextSplitter`, ~500–800 tokens, overlap 50–100).
- Store metadata: `source`, `section`, `policy_effective_date`.
- Persist index to disk; re-running must not duplicate chunks (use deterministic IDs).

### 5.3 Graph (`src/graph.py`)
- **State:** `messages`, `route`, `retrieved_docs`, `answer`, `citations`, `grounded: bool`.
- **Router node:** LLM with structured output → `Literal["policy", "personal", "sensitive", "out_of_scope"]`.
- **RAG node:** hybrid retriever (k=5) → answer prompt that forces "answer only from context".
- **Grounding check node:** second LLM call (or same model) verifies each claim is supported; if not → regenerate once, else fall back to "I couldn't find this in the policy".
- **Tool node:** `get_leave_balance(employee_id: str)` reads `hrms_mock.json`. Employee ID comes from a sidebar "logged-in user" dropdown (no real auth needed).
- **Output schema (Pydantic):**
  ```python
  class PolicyAnswer(BaseModel):
      answer: str
      citations: list[Citation]   # {source, section, quote<=25 words}
      confidence: Literal["high","medium","low"]
      escalate_to_hr: bool
  ```

### 5.4 UI (`app/streamlit_app.py`)
- Chat window, sidebar with employee selector + provider name shown, expandable "Sources" under each answer, 👍/👎 feedback saved to `feedback.jsonl`.

### 5.5 Evaluation (`eval/run_eval.py`)
- Use `eval/golden_qa.json` (15 provided). **Intern must extend to ≥ 30**, including at least 8 unanswerable/trick questions.
- Report: correctness, faithfulness, refusal accuracy, retrieval hit-rate@5, latency, est. cost.

---

## 6. Other Important Info

### 6.1 Suggested 2-week plan
| Day | Milestone |
|---|---|
| 1 | Setup, read docs, LangSmith account, write extra policies |
| 2–3 | Ingestion + basic RAG chain in a notebook |
| 4–5 | LangGraph router + tool + grounding check |
| 6 | **Mid-point check-in (demo to mentor, 15 min)** |
| 7 | Streamlit UI + memory |
| 8 | Golden set expansion + eval script |
| 9 | Improve on failures (hybrid, prompt fixes), write report |
| 10 | **Final demo (15 min) + code walkthrough (10 min)** |

### 6.2 Deliverables
1. Git repo (clean history, meaningful commits) following the given `src/ app/ eval/` structure
2. `README.md` with setup, architecture diagram, how to run, how to switch LLM provider
3. `eval/report.md` with metrics and failure analysis
4. 3–5 min screen-recorded demo video
5. `docs/LEARNINGS.md` — what worked, what didn't, what you'd do in production

### 6.3 Evaluation rubric (100 pts)
| Area | Pts |
|---|---|
| Functionality vs acceptance criteria | 35 |
| Answer quality & guardrails (eval numbers) | 20 |
| Code quality (structure, typing, config, no hard-coded keys) | 15 |
| Evaluation rigour & failure analysis | 15 |
| Demo & communication | 10 |
| Stretch goals | 5 |

### 6.4 Rules / constraints
- **No real employee or company data.** Synthetic only.
- **Never commit API keys** — use `.env` (provided `.env.example`).
- Cost cap: keep total API spend under the budget your mentor gives (suggest ≤ $5); prefer small models (`gpt-4o-mini`, `gemini-flash`, `llama-3.1-8b` on Groq) for dev.
- Using AI coding assistants is allowed, but you must be able to explain every line in the walkthrough.

### 6.5 Stretch ideas
- Re-ranker; query rewriting for follow-ups; "policy changed since date X" answering using `effective_date` metadata
- Multilingual answers (Hindi/Marathi) while citing English source
- Admin page: upload new policy → auto re-index

### 6.6 Useful references
- LangGraph agentic RAG tutorial — https://langchain-ai.github.io/langgraph/
- LangChain retrievers (Ensemble/BM25) — https://python.langchain.com/docs/
- RAGAS docs — https://docs.ragas.io/
