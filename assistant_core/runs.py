"""Persist a completed analysis/retrieval/matching slice and source revisions."""
from hashlib import sha256
from uuid import uuid4
from psycopg.types.json import Jsonb
from assistant_core import database


def persist_match(workspace,job,result,profile_revision):
    digest = sha256(job.encode()).hexdigest()
    with database.connection() as db:
        db.execute("SELECT id FROM workspaces WHERE id=%s FOR UPDATE",(workspace,))
        row = db.execute("SELECT revision FROM profiles WHERE workspace_id=%s",(workspace,)).fetchone()
        if not row or row[0] != profile_revision:
            raise ValueError("Profile changed during matching. Run the assessment again.")
        db.execute("INSERT INTO jobs(workspace_id,id,description,description_hash) VALUES (%s,%s,%s,%s) ON CONFLICT(workspace_id,description_hash) DO NOTHING",(workspace,str(uuid4()),job,digest))
        job_id,job_version = db.execute("SELECT id,version FROM jobs WHERE workspace_id=%s AND description_hash=%s",(workspace,digest)).fetchone()
        run_id = str(uuid4())
        db.execute("INSERT INTO workflow_runs(workspace_id,id,job_id,job_version,profile_revision,status) VALUES (%s,%s,%s,%s,%s,'completed')",(workspace,run_id,job_id,job_version,profile_revision))
        for stage,key in [("analysis","analysis"),("retrieval","retrieval"),("matching","matching")]:
            refs = {"job_id":job_id,"job_version":job_version,"profile_revision":profile_revision,"previous_stage":None if stage=="analysis" else "analysis" if stage=="retrieval" else "retrieval"}
            db.execute("INSERT INTO stage_results(workspace_id,run_id,stage,revision,input_refs,output) VALUES (%s,%s,%s,1,%s,%s)",(workspace,run_id,stage,Jsonb(refs),Jsonb(result[key])))
    return run_id
