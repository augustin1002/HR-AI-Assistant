# Enterprise HR AI Assistant

A chatbot that answers questions about **company policy** (leave, benefits,
IT security, code of conduct, recruitment, employee handbook) and
**employee data** (salary, department, performance, absences), by combining:

- **RAG** over the 6 policy PDFs (semantic search)
- **SQL** over the HR dataset (311 employees, in SQLite)
- **Tools**: calculator, current date/time, document search
- An **LLM** (OpenAI, Anthropic/Claude, local Ollama, or offline mock) that
  writes the final answer from whichever context is relevant

## Quick start

```bash
cd HR-AI-Assistant
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# edit .env: set LLM_PROVIDER and the matching API key
#   LLM_PROVIDER=anthropic   ANTHROPIC_API_KEY=sk-ant-...
#   LLM_PROVIDER=openai      OPENAI_API_KEY=sk-...
#   LLM_PROVIDER=mock        (no key needed - runs with a canned response,
#                             good for testing RAG/SQL routing without a key)

streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501).

The employee database (`data/hr.db`) and the document vector index
(`vectorstore/`) are built automatically on first run.

## How it's organized

```
app.py                  Streamlit chat UI (entry point)
data/
  HRDataset_v14.csv     Source employee data
  hr.db                 SQLite DB, built automatically from the CSV
documents/               The 6 policy documents (as .txt, extracted from your PDFs)
database/
  db.py                 CSV -> SQLite, schema helpers
  queries.py             Safe, read-only SQL query helpers
rag/
  loader.py              Reads PDFs/TXT from documents/
  splitter.py             Chunks text for embedding
  embeddings.py           TF-IDF (offline) or sentence-transformers+FAISS backend
  retriever.py            Builds/loads the vector index, does similarity search
llm/
  model.py                Unified call to OpenAI / Anthropic / Ollama / mock
  prompts.py              System prompt + prompt assembly
mcp_tools/
  sql_tool.py, calculator.py, datetime_tool.py, file_tool.py
  server.py               Optional: exposes the same tools as a REAL MCP
                          server (stdio) so any MCP client (e.g. Claude
                          Desktop) can use them too: `python -m mcp_tools.server`
agent/
  router.py               Decides RAG vs SQL vs tool vs combined, gathers
                          context, and asks the LLM to compose the answer
```

## Design choices worth knowing about

- **Embeddings fall back automatically.** `EMBEDDING_BACKEND=auto` (default)
  tries `sentence-transformers` + FAISS first (best quality, needs internet
  to download the model once) and falls back to scikit-learn TF-IDF if
  that's not installed or fails - so the app still works fully offline.
- **The agent is rule-based, not LangGraph.** The brief suggested
  LangChain/LangGraph for orchestration. This build uses a simpler
  keyword/regex router (`agent/router.py`) instead: zero extra
  dependencies, transparent to debug, and easy to extend. It's a drop-in
  replacement point - swap that one file for a LangGraph `StateGraph` later
  without touching the UI, RAG, SQL, or LLM layers, which are already
  decoupled for that.
- **SQL safety.** `database/queries.py` only allows `SELECT` statements and
  blocks `INSERT/UPDATE/DELETE/DROP/ALTER/ATTACH/PRAGMA` etc. When a real
  LLM provider is configured, the router can also ask the LLM to write SQL
  for questions that don't match a canned pattern - that generated SQL
  still passes through the same safety filter before running.
- **Mock LLM mode.** With no API key, `LLM_PROVIDER=mock` still runs the
  full RAG + SQL retrieval and shows you exactly what context would be
  sent to a real LLM - useful for verifying routing/retrieval before you
  wire up billing.

## Extending it

- **Add a document:** drop a PDF or .txt into `documents/`, then click
  "Rebuild document index" in the sidebar (or delete `vectorstore/`).
- **Add a new employee-data question pattern:** add a regex + query
  function pair in `database/queries.py` and `agent/router.py`.
- **Swap in a real agent framework:** replace `agent/router.py`'s `answer()`
  with a LangGraph graph that calls the same `rag/retriever.py`,
  `database/queries.py`, and `llm/model.py` functions as tools.
- **Deploy:** containerize with the included structure (add a `Dockerfile`
  that runs `streamlit run app.py --server.port 8501 --server.address
  0.0.0.0`), then push to Render/Railway/AWS/Azure per the original brief.

## Known limitations (be upfront with stakeholders about these)

- The employee dataset has no explicit "probation" flag; the
  `employees_on_probation_like()` helper approximates it using recent hire
  date + active status and is clearly commented as an approximation, not a
  real probation-status field.
- The rule-based router covers common question phrasings but isn't a full
  NLU system; very unusual phrasings may fall through to a generic
  RAG-only response. Adding more keyword patterns to `agent/router.py` is
  the quick fix; a real LLM-driven intent classifier is the long-term fix.
