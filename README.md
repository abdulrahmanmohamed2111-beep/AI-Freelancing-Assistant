# AI Freelancing Assistant

DEPI Agentic AI and LLMs project. One developer, 15 days, 4 hours per day.
English UI and proposals; multiple freelance domains with a technical focus.

## Current milestone

PostgreSQL + pgvector infrastructure and a versioned schema are prepared in
`compose.yaml` and `migrations/`. See `DATABASE_AR.md`. Run `setup_database.py`
with Docker Desktop running to migrate existing local profiles, then
`check_database.py` for rollback-only integration checks. Until setup succeeds,
the app retains SQLite storage. This infrastructure has not yet been validated
against a running database on this machine; agent/vector tables are schema
preparation, not completed RAG or workflow persistence.

My Profile now supports editable details, skills, education, experience, weekly availability,
project creation/editing, per-project review and JSON export. Select My profile
from Open page. Synthetic demo and personal profiles have separate storage slots;
loading synthetic fixtures never populates the personal profile.

Profiles persist in the Git-ignored `data/profiles.sqlite3` on the application host.
This is a single-user local implementation, not authenticated multi-user storage.
Set `FREELANCE_DATA_DIR` to override the storage directory (used by isolated tests).
Before online deployment, add access control and migrate to durable hosted storage.
Upload CV is the default profile tab. It supports UTF-8 TXT and text-based PDF
(5 MB, 20 pages, 30,000 extracted characters maximum). Scanned, encrypted or
unreadable PDFs are rejected with an explanation; OCR is not included.
Common email/phone patterns are redacted before a user-editable text preview;
this is not comprehensive anonymization. Only clicking Extract profile sends the
preview text to the configured provider. The user reviews and can edit every
extracted field and project, then explicitly approves saving. The raw upload is
not persisted. Approved source text and project quotes are saved locally for
future retrieval. Removing private details in the preview also removes them from
that retained source text. Empty imported fields preserve existing values;
nonempty fields replace them. Availability is preserved. Exact-source reimports
update matching project IDs rather than duplicating them. Changed source files
can create additional projects and should be reviewed before approval.

Hourly rate has been removed from profiles and old saved records are migrated.
Pricing belongs to a future per-job estimate. RAG is still pending.
Try `fixtures/synthetic/demo_cv.txt` in the Synthetic demo workspace.

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
Job analysis results remain only in the current Streamlit session; profiles persist locally. It is not
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
