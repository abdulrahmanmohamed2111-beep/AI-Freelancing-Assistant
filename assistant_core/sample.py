SAMPLE_JOB = """We need a Python developer to build a REST API using FastAPI.
Store customer records in PostgreSQL and include automated tests.
Deliver the source code and setup documentation.
Budget: $500. Timeline: two weeks."""

SAMPLE_ANALYSIS = {
    "title": "Python API Developer",
    "summary": "Build and test a FastAPI service that stores customer records in PostgreSQL.",
    "requirements": [
        {"description": "Python and FastAPI development", "kind": "explicit",
         "evidence_quote": "Python developer to build a REST API using FastAPI"},
        {"description": "PostgreSQL storage", "kind": "explicit",
         "evidence_quote": "Store customer records in PostgreSQL"},
        {"description": "Automated testing", "kind": "explicit",
         "evidence_quote": "include automated tests"},
        {"description": "Clarify access controls for customer records", "kind": "inferred",
         "evidence_quote": "Store customer records"},
    ],
    "tasks": ["Build the REST API", "Store customer records", "Write automated tests",
              "Deliver source code and setup documentation"],
    "missing_information": ["Required endpoints and customer fields", "Authentication requirements",
                            "Deployment target", "Acceptance criteria"],
    "budget": "$500",
    "deadline": "two weeks",
}
