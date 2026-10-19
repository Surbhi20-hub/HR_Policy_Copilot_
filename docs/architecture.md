# Architecture

Drawn automatically by `python -m src.graph` (do not edit by hand).

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	router(router)
	policy_rag(policy_rag)
	grounding_check(grounding_check)
	tool(tool)
	sensitive(sensitive)
	out_of_scope(out_of_scope)
	__end__([<p>__end__</p>]):::last
	__start__ --> router;
	grounding_check -. &nbsp;done&nbsp; .-> __end__;
	grounding_check -. &nbsp;retry&nbsp; .-> policy_rag;
	policy_rag --> grounding_check;
	router -.-> out_of_scope;
	router -. &nbsp;policy&nbsp; .-> policy_rag;
	router -.-> sensitive;
	router -. &nbsp;personal&nbsp; .-> tool;
	out_of_scope --> __end__;
	sensitive --> __end__;
	tool --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```

| Node | Job |
|---|---|
| router | Reads the question and picks one of 4 routes |
| policy_rag | Finds policy chunks (hybrid search) and writes a cited answer |
| grounding_check | Second LLM call that fact-checks the answer; retries once, then falls back |
| tool | Looks up the employee's leave balance in the HRMS (ID from state) |
| sensitive | Kind reply that points to the right policy and contact |
| out_of_scope | Polite refusal |
