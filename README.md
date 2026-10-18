# HR Policy Copilot — Starter Kit

Read **ASSIGNMENT.md** first. This folder is your starter skeleton.

```
data/policies/      sample HR policies (add ≥2 more, convert 1 to PDF)
data/hrms_mock.json mock leave balances for the tool
eval/golden_qa.json 15 starter Q&A (extend to ≥30)
src/                ingest.py, graph.py, tools.py, config.py (skeletons)
app/                streamlit_app.py (skeleton)
tests/              add unit tests here
docs/               LEARNINGS.md + architecture diagram
```

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in provider + key
python -m src.ingest
streamlit run app/streamlit_app.py
```
