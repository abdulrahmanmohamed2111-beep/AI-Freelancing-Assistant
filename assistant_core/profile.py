"""Single-user local profiles. Demo data is stored separately from real data."""
import json
import os
from pathlib import Path
import sqlite3
from contextlib import contextmanager
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]


class Project(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=20, max_length=15000)
    role: str = Field(default="", max_length=500)
    technologies: list[str] = Field(default_factory=list)
    outcomes: str = Field(default="", max_length=3000)
    limitations: str = Field(default="", max_length=3000)
    reviewed: bool = False


class Profile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    display_name: str = Field(default="", max_length=120)
    headline: str = Field(default="", max_length=160)
    summary: str = Field(default="", max_length=5000)
    skills: list[str] = Field(default_factory=list)
    hourly_rate_usd: float = Field(default=0, ge=0, le=10000, allow_inf_nan=False)
    availability_hours_per_week: int = Field(default=0, ge=0, le=168)
    projects: list[Project] = Field(default_factory=list)


def parse_skills(text: str) -> list[str]:
    result = []
    seen = set()
    for value in text.replace("\n", ",").split(","):
        value = value.strip()
        if value and value.casefold() not in seen:
            result.append(value)
            seen.add(value.casefold())
    return result


def database_path() -> Path:
    return Path(os.getenv("FREELANCE_DATA_DIR", str(ROOT / "data"))) / "profiles.sqlite3"


@contextmanager
def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS profiles (workspace TEXT PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL)")
        with connection:
            yield connection
    finally:
        connection.close()


def validate_workspace(workspace):
    if workspace not in {"personal", "demo"}:
        raise ValueError("Unknown profile workspace.")


def load_profile(workspace: Literal["personal", "demo"]) -> tuple[Profile, int]:
    validate_workspace(workspace)
    with connect() as db:
        row = db.execute("SELECT payload, revision FROM profiles WHERE workspace=?", (workspace,)).fetchone()
    return (Profile.model_validate_json(row[0]), row[1]) if row else (Profile(), 0)


def save_profile(workspace: str, profile: Profile, revision: int) -> int:
    validate_workspace(workspace)
    # Revalidate mutated objects before persisting them.
    payload = Profile.model_validate(profile.model_dump()).model_dump_json()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT revision FROM profiles WHERE workspace=?", (workspace,)).fetchone()
        current = row[0] if row else 0
        if current != revision:
            raise ValueError("This profile changed in another session. Reload the page before saving again.")
        db.execute("INSERT INTO profiles VALUES (?, ?, ?) ON CONFLICT(workspace) DO UPDATE SET payload=excluded.payload, revision=excluded.revision",
                   (workspace, payload, current + 1))
    return current + 1


def demo_profile() -> Profile:
    directory = ROOT / "fixtures" / "synthetic"
    details = json.loads((directory / "profile.json").read_text(encoding="utf-8"))
    documents = json.loads((directory / "projects.json").read_text(encoding="utf-8"))["documents"]
    return Profile(display_name=details["display_name"], headline="Python developer · Synthetic demo",
                   skills=details["skills"], hourly_rate_usd=details["hourly_rate_usd"],
                   availability_hours_per_week=details["availability_hours_per_week"],
                   projects=[Project(id=d["id"], title=d["title"], description=d["text"]) for d in documents])
