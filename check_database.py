"""Integration smoke checks; all test writes are rolled back."""
from contextlib import contextmanager
from unittest.mock import patch

from assistant_core import database
from assistant_core.profile import demo_profile, load_profile, save_profile


def main():
    with database.connection() as db:
        assert db.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
        distance = db.execute("SELECT '[1,0,0]'::vector <=> '[1,0,0]'::vector").fetchone()[0]
        assert distance == 0
        with db.transaction(force_rollback=True):
            @contextmanager
            def shared():
                yield db
            with patch.object(database, "connection", shared):
                _, revision = load_profile("demo")
                next_revision = save_profile("demo", demo_profile(), revision)
                restored, saved_revision = load_profile("demo")
                assert saved_revision == next_revision and len(restored.projects) == 3
                try:
                    save_profile("demo", demo_profile(), revision)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Stale writer was accepted")
                assert db.execute("SELECT count(*) FROM projects WHERE workspace_id='demo'").fetchone()[0] == 3
                assert db.execute("SELECT count(*) FROM profile_versions WHERE workspace_id='demo' AND revision=%s", (saved_revision,)).fetchone()[0] == 1
    print("PASS: pgvector distance, profile round trip, project rows, version history and stale-write protection. Test writes rolled back.")


if __name__ == "__main__":
    main()
