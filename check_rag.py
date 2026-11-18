"""Live PostgreSQL/embedding integration checks; all test writes roll back."""
from contextlib import contextmanager
from unittest.mock import patch
from psycopg.types.json import Jsonb

from assistant_core import database
from assistant_core.profile import demo_profile,load_profile,save_profile
from assistant_core.rag import build_index,retrieve
from assistant_core.runs import persist_match
from assistant_core.sample import SAMPLE_ANALYSIS,SAMPLE_JOB


def main():
    database.migrate()
    with database.connection() as db:
        with db.transaction(force_rollback=True):
            @contextmanager
            def shared():
                yield db
            with patch.object(database,"connection",shared):
                before = db.execute("SELECT count(*) FROM document_chunks WHERE workspace_id='personal'").fetchone()[0]
                profile = demo_profile()
                for p in profile.projects:
                    p.reviewed = True
                _,revision = load_profile("demo")
                revision = save_profile("demo",profile,revision)
                first = build_index("demo")
                second = build_index("demo")
                assert first == second
                count = db.execute("SELECT count(*) FROM document_chunks WHERE workspace_id='demo'").fetchone()[0]
                assert count == first["chunks"]
                # Same workspace, different model/dimensions: must be excluded
                # before vector distance, otherwise PostgreSQL raises a mismatch.
                doc_id = db.execute("SELECT id FROM documents WHERE workspace_id='demo' AND id LIKE 'rag:%' LIMIT 1").fetchone()[0]
                db.execute("INSERT INTO document_chunks VALUES ('demo',%s,'wrong-dimensions',999,'synthetic test',%s,'[1,0,0]'::vector,'other-model',3)",(doc_id,Jsonb({})))
                evidence = retrieve("demo",SAMPLE_ANALYSIS,revision)
                assert evidence and all(c["chunk_id"]!="wrong-dimensions" and c["metadata"]["synthetic"] for r in evidence for c in r["candidates"])
                result = {"analysis":SAMPLE_ANALYSIS,"retrieval":evidence,"matching":{"score":0,"requirements":[],"test_only":True}}
                run_id = persist_match("demo",SAMPLE_JOB,result,revision)
                assert db.execute("SELECT count(*) FROM stage_results WHERE workspace_id='demo' AND run_id=%s",(run_id,)).fetchone()[0] == 3
                save_profile("demo",profile,revision)
                assert db.execute("SELECT status FROM workflow_runs WHERE workspace_id='demo' AND id=%s",(run_id,)).fetchone()[0] == "stale"
                try:
                    retrieve("demo",SAMPLE_ANALYSIS,revision)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Stale index was accepted")
                after = db.execute("SELECT count(*) FROM document_chunks WHERE workspace_id='personal'").fetchone()[0]
                assert before == after
    print("PASS: idempotent indexing, vector retrieval, model/dimension filtering, workspace isolation, persisted stage links and stale-index rejection. Test writes rolled back.")


if __name__ == "__main__":
    main()
