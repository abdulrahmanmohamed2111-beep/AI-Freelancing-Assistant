"""Create local DB settings, start Compose, migrate schema, import legacy profiles."""
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import os

ROOT = Path(__file__).resolve().parent


def main():
    config = ROOT / "data" / "database.json"
    if config.exists():
        url = json.loads(config.read_text())["url"]
    else:
        config.parent.mkdir(exist_ok=True)
        password = secrets.token_hex(24)
        env = ROOT / ".env"
        if env.exists():
            settings = dict(line.split("=",1) for line in env.read_text().splitlines() if "=" in line and not line.startswith("#"))
            password = settings.get("POSTGRES_PASSWORD")
            if not password:
                raise RuntimeError("An .env already exists without POSTGRES_PASSWORD. Preserve its contents and add the database password first.")
        else:
            env.write_text("POSTGRES_PASSWORD="+password+"\n", encoding="utf-8")
        from urllib.parse import quote
        url = "postgresql://freelance:"+quote(password,safe="")+"@127.0.0.1:55432/freelance"
    subprocess.run(["docker","compose","up","-d","--wait"], cwd=ROOT, check=True)
    from assistant_core.database import migrate, load, save
    from assistant_core.profile import Profile
    os.environ["DATABASE_URL"] = url
    migrate()
    legacy = ROOT / "data" / "profiles.sqlite3"
    imported = 0
    if legacy.exists():
        # Read-only; retain original SQLite as a recovery copy.
        db = sqlite3.connect(legacy.resolve().as_uri()+"?mode=ro", uri=True)
        try:
            rows = db.execute("SELECT workspace,payload FROM profiles").fetchall()
        finally:
            db.close()
        for workspace, raw in rows:
            if load(workspace) is None:
                payload = json.loads(raw)
                payload.pop("hourly_rate_usd",None)
                payload = Profile.model_validate(payload).model_dump()
                save(workspace,payload,0)
                imported += 1
    config.write_text(json.dumps({"url":url}), encoding="utf-8")
    print(f"PostgreSQL + pgvector ready. Imported {imported} legacy profile(s). Original SQLite retained.")


if __name__ == "__main__":
    main()
