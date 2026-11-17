# Synthetic development fixtures

All names, experience, projects and jobs in this directory are invented.
They must never be merged into a real user's profile or represented as real work.

The dataset contains one profile, three source documents and six job descriptions.
Two jobs have strong experience overlap, one has partial overlap and three lack
supporting evidence. These labels do not assess price or availability feasibility.

Use projects.json as the future RAG corpus, jobs.json as queries, and
evaluation.json as reference labels. Keep evaluation.json OUT of the retrieval
index and model prompt: supplying the answers would invalidate the evaluation.
Document IDs are stable references for citations and expected retrieval results.

The application supports job analysis and reviewed CV import into a local profile.
Use demo_cv.txt to test upload in the Synthetic demo workspace.
These fixtures prepare the RAG milestone; no retrieval evaluation has been executed yet.
For immediate analysis testing, paste a description from jobs.json into Connected
model. Compare explicit requirements, budget, deadline and missing information.

When real data becomes available, store it in the Git-ignored data/ or uploads/
directory, record provenance and usage permission, and create separate held-out
evaluation examples. Do not commit personal CVs to this public repository.
