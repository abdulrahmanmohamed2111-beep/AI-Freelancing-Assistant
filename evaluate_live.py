"""Two synthetic live-model smoke checks; writes no credentials to the report."""
import json
import os
from pathlib import Path
import time
import tomllib
from functools import partial

from assistant_core.providers import Settings, ProviderError, generate
from assistant_core.workflow import build_graph

CASES = [
    {"id": "technical", "job": "Build a REST API using Python and FastAPI. Store customer records in PostgreSQL. Include automated tests and setup documentation. Budget: $500. Deliver within two weeks.",
     "terms": ["python", "fastapi", "postgresql", "test"], "has_budget": True},
    {"id": "content_writing", "job": "We need an English content writer to write three 800-word blog posts about home gardening. Use a friendly tone, cite reliable sources, and deliver editable documents. Include one revision per article. Please provide your availability and quote.",
     "terms": ["english", "800", "sources", "revision"], "has_budget": False},
]


def main():
    root = Path(__file__).resolve().parent
    path = root / ".streamlit" / "secrets.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    def value(name, default=""):
        return os.environ.get(name, data.get(name, default))
    settings = Settings(value("LLM_PROVIDER", "compatible_api"),
                        value("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
                        value("LLM_MODEL", "openai/gpt-oss-20b"), value("LLM_API_KEY"))
    if settings.provider == "compatible_api" and not settings.api_key:
        print("Setup needed: run python setup_groq.py locally first. No model requests were made.")
        return 2
    report = {"model": settings.model, "cases": [],
              "limitations": "Two smoke checks only. Keyword coverage is a heuristic, not a semantic quality score; human review is required."}
    for case in CASES:
        started = time.perf_counter()
        try:
            result = build_graph(partial(generate, settings)).invoke({"job_text": case["job"]})
            analysis = result.get("analysis", {})
            explicit = " ".join(r["description"] + " " + r["evidence_quote"] for r in analysis.get("requirements", []) if r["kind"] == "explicit").lower()
            checks = {"schema_and_quotes": not bool(result["error"]),
                      "explicit_keyword_coverage": all(term in explicit for term in case["terms"]),
                      "tasks_present": bool(analysis.get("tasks"))}
            if case["has_budget"]:
                checks["budget_preserved"] = "500" in str(analysis.get("budget"))
                checks["deadline_preserved"] = any(t in str(analysis.get("deadline")).lower() for t in ["two weeks", "2 weeks", "14 days"])
            else:
                checks["no_invented_budget_or_deadline"] = analysis.get("budget") is None and analysis.get("deadline") is None
            record = {"id": case["id"], "checks": checks, "analysis": analysis,
                      "passed": all(checks.values()), "attempts": result["attempts"]}
        except (ProviderError, ValueError) as exc:
            record = {"id": case["id"], "passed": False, "error": str(exc)}
        record["seconds"] = round(time.perf_counter() - started, 2)
        report["cases"].append(record)
        print(case["id"], "PASS" if record["passed"] else "REVIEW NEEDED", record["seconds"], "seconds")
    destination = root / "evaluation-results.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Saved evaluation-results.json. Review the evidence and inferred suggestions manually.")
    return 0 if all(case["passed"] for case in report["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
