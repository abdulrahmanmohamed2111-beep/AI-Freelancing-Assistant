"""Synthetic end-to-end evaluation. Database test writes are rolled back."""
from contextlib import contextmanager
from functools import partial
import json
from pathlib import Path
import time
import tomllib
from unittest.mock import patch

from assistant_core import database
from assistant_core.profile import demo_profile,load_profile,save_profile
from assistant_core.rag import build_index,retrieve
from assistant_core.matching import match_requirements
from assistant_core.workflow import build_graph
from assistant_core.providers import Settings,generate,ProviderError
from assistant_core.runs import persist_match

ROOT = Path(__file__).resolve().parent


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", help="Evaluate one fixture job ID")
    args = parser.parse_args()
    database.migrate()
    config = tomllib.loads((ROOT/".streamlit/secrets.toml").read_text())
    settings = Settings(config["LLM_PROVIDER"],config["LLM_BASE_URL"],config["LLM_MODEL"],config["LLM_API_KEY"])
    jobs = json.loads((ROOT/"fixtures/synthetic/jobs.json").read_text())["jobs"]
    if args.job:
        jobs = [job for job in jobs if job["id"]==args.job]
        if not jobs:
            raise ValueError("Unknown fixture job ID")
    # Labels never enter the index or model prompt.
    labels = {c["job_id"]:c for c in json.loads((ROOT/"fixtures/synthetic/evaluation.json").read_text())["cases"]}
    results = []
    with database.connection() as db:
        with db.transaction(force_rollback=True):
            @contextmanager
            def shared():
                yield db
            with patch.object(database,"connection",shared):
                profile = demo_profile()
                for project in profile.projects:
                    project.reviewed = True
                _,old_revision = load_profile("demo")
                revision = save_profile("demo",profile,old_revision)
                index = build_index("demo")
                print("Index:",index,flush=True)
                for job in jobs:
                    if results:
                        print("Waiting 30 seconds between fixtures to respect free-plan token limits…",flush=True)
                        time.sleep(30)
                    start = time.perf_counter()
                    try:
                        graph = build_graph(partial(generate,settings),
                            retrieve=lambda a:retrieve("demo",a,revision),
                            match=lambda a,r:match_requirements(settings,a,r))
                        result = graph.invoke({"job_text":job["description"]})
                        if result.get("error"):
                            raise ValueError(result["error"])
                        persist_match("demo",job["description"],result,revision)
                        expected = labels[job["id"]]
                        retrieved = {c["metadata"]["source_id"].removeprefix("project:") for item in result["retrieval"] for c in item["candidates"]}
                        relevant = set(expected["relevant_document_ids"])
                        record = {"job_id":job["id"],"expected_fit":expected["expected_fit"],
                                  "observed_fit":result["matching"]["fit_tier"],"score":result["matching"]["score"],
                                  "tier_agreement":result["matching"]["fit_tier"]==expected["expected_fit"],
                                  "relevant_document_recall":len(relevant&retrieved)/len(relevant) if relevant else None,
                                  "top1_relevant_fraction":sum(bool(item["candidates"]) and item["candidates"][0]["metadata"]["source_id"].removeprefix("project:") in relevant for item in result["retrieval"])/len(result["retrieval"]) if relevant and result["retrieval"] else None,
                                  "result":result}
                    except (ValueError,OSError,ProviderError) as exc:
                        record = {"job_id":job["id"],"error":str(exc),"tier_agreement":False}
                    record["seconds"] = round(time.perf_counter()-start,2)
                    results.append(record)
                    print({k:v for k,v in record.items() if k!="result"},flush=True)
                # Isolation: personal queries cannot see demo vectors.
                personal = db.execute("SELECT count(*) FROM document_chunks WHERE workspace_id='personal'").fetchone()[0]
                print("Personal chunks untouched:",personal,flush=True)
    report = {"synthetic":True,"cases":results,"tier_agreement":sum(r["tier_agreement"] for r in results)/len(results),
              "limitations":"Six development fixtures, not held-out real-data validation. Recall measures candidate inclusion only. Similarity and quote checks do not prove semantic correctness. Test database writes rolled back."}
    output = ROOT/(f"data/rag-evaluation-{args.job}.json" if args.job else "data/rag-evaluation.json")
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Saved data/rag-evaluation.json. Synthetic database writes rolled back.",flush=True)


if __name__ == "__main__":
    main()
