"""PostgreSQL adapter. Schema changes are applied only by setup_database.py."""
import json
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]


def database_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    # Tests explicitly select isolated local data without touching a real DB.
    if os.environ.get("FREELANCE_DATA_DIR"):
        return None
    config = ROOT / "data" / "database.json"
    return json.loads(config.read_text())["url"] if config.exists() else None


@contextmanager
def connection():
    url = database_url()
    if not url:
        raise RuntimeError("PostgreSQL is not configured.")
    try:
        with psycopg.connect(url, connect_timeout=5) as db:
            yield db
    except psycopg.Error:
        raise OSError("PostgreSQL is unavailable or the database operation failed. Check Docker and database setup.") from None


def migrate():
    with connection() as db:
        db.execute("SELECT pg_advisory_xact_lock(20261118)")
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        for path in sorted((ROOT / "migrations").glob("*.sql")):
            if not db.execute("SELECT 1 FROM schema_migrations WHERE version=%s", (path.stem,)).fetchone():
                db.execute(path.read_text(encoding="utf-8"))
                db.execute("INSERT INTO schema_migrations(version) VALUES (%s)", (path.stem,))


def load(workspace):
    with connection() as db:
        row = db.execute("SELECT payload,revision FROM profiles WHERE workspace_id=%s", (workspace,)).fetchone()
    return row


def save(workspace, payload, revision):
    with connection() as db:
        # Serialize first saves as well as updates; stale writers are rejected.
        db.execute("SELECT id FROM workspaces WHERE id=%s FOR UPDATE", (workspace,))
        row = db.execute("SELECT revision FROM profiles WHERE workspace_id=%s", (workspace,)).fetchone()
        current = row[0] if row else 0
        if current != revision:
            raise ValueError("This profile changed in another session. Reload the page before saving again.")
        db.execute("INSERT INTO profiles(workspace_id,payload,revision) VALUES (%s,%s,%s) ON CONFLICT(workspace_id) DO UPDATE SET payload=excluded.payload,revision=excluded.revision,updated_at=now()",
                   (workspace, Jsonb(payload), current+1))
        db.execute("INSERT INTO profile_versions(workspace_id,revision,payload) VALUES (%s,%s,%s)", (workspace,current+1,Jsonb(payload)))
        db.execute("DELETE FROM projects WHERE workspace_id=%s", (workspace,))
        for project in payload["projects"]:
            db.execute("INSERT INTO projects VALUES (%s,%s,%s,%s)", (workspace,project["id"],Jsonb(project),project["reviewed"]))
        db.execute("UPDATE workflow_runs SET status='stale' WHERE workspace_id=%s AND profile_revision<>%s", (workspace,current+1))
        db.execute("UPDATE proposals SET approval_status='stale' WHERE workspace_id=%s", (workspace,))
    return current+1
