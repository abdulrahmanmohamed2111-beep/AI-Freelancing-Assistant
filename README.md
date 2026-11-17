# AI Freelancing Assistant

DEPI Agentic AI and LLMs project. One developer, 15 days, 4 hours per day.
English UI and proposals; multiple freelance domains with a technical focus.

## Current milestone

Streamlit job intake and a LangGraph workflow:
`START -> prepare -> analyze -> verify -> END`.
Failed JSON/schema/evidence validation routes back to analyze once, then stops.
Pydantic validates structured output. Every requirement must quote the original job.
Quote presence does not prove semantic correctness: human review is still required.

The sample walkthrough is a FIXED fixture, not live AI inference. Connected mode
supports Ollama or a chat-completions-compatible API with JSON-object output.
No model or API key is included. No model quality claims have been established.

## Run on Windows

From this project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If `venv` fails during ensurepip, install pip into that environment with:

```powershell
python -m pip --python .\.venv\Scripts\python.exe install -r requirements.txt
```

Start with Sample walkthrough, then click Analyze job. To use a real model,
copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, fill in your
provider details and choose Connected model. Environment variables with the same
names also work. `.env` files are NOT loaded automatically.

Ollama must already be running with the chosen model installed. Do not expect a
cloud app's localhost to reach your laptop. Use a reachable HTTPS model endpoint
for cloud deployment. Remote job text is transmitted to the configured provider.

## Project map

- `app.py`: English UI, session-local results and JSON export.
- `assistant_core/schemas.py`: data contract and source-quote validation.
- `assistant_core/providers.py`: model adapters and safe connection errors.
- `assistant_core/workflow.py`: LangGraph nodes and bounded repair loop.
- `assistant_core/sample.py`: fixed demonstration data.
- `tests/`: graph, validation, provider and UI checks without paid model calls.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Deployment preparation

Deploy this directory as the repository root; select `app.py` as the Streamlit
entrypoint. Configure credentials through deployment secrets, never source code.
This milestone stores results only in the current Streamlit session. It is not
yet the persistent final application. Use synthetic jobs for a public demo until
authentication and data retention controls are implemented.

## Remaining milestones

1. Reviewed profile and document ingestion; RAG with source references.
2. Matching with an explicit scoring rubric and estimation calculation tools.
3. Proposal and reviewer agents, bounded revision and human approval.
4. Durable graph checkpoints, application tracking and PostgreSQL/pgvector.
5. Labeled evaluations, deployment hardening and final demonstration.

RAG, multi-agent tools, persistence and approval are requirements for the final
project; they are not implemented in this first analysis slice.

## References

- https://docs.langchain.com/oss/python/langgraph/graph-api
- https://docs.ollama.com/api/chat
- https://docs.streamlit.io/develop/api-reference/app-testing
