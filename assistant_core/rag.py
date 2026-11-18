"""Revision-bound, workspace-filtered exact pgvector retrieval."""
from hashlib import sha256
import math

from psycopg.types.json import Jsonb

from assistant_core import database, embeddings
from assistant_core.profile import load_profile, validate_workspace
from assistant_core.schemas import capability_requirements


def chunks(text, size=900, overlap=150):
    """Character-bounded spans (incl. overlap) preserve exact source excerpts."""
    if size <= overlap or overlap < 0:
        raise ValueError("Chunk size must exceed overlap.")
    start = 0
    while start < len(text):
        end = min(start+size, len(text))
        span = text[start:end]
        if span.strip():
            yield start, end, span
        if end == len(text):
            break
        start = end-overlap


def sources(profile):
    docs = []
    if profile.cv_source_text:
        docs.append(("cv:"+profile.cv_source_id, "Approved CV text", profile.cv_source_text))
    for project in profile.projects:
        if project.reviewed:
            text = "\n".join([project.title, project.description, "Role: "+project.role,
                               "Technologies: "+", ".join(project.technologies),
                               "Outcomes: "+project.outcomes, "Limitations: "+project.limitations])
            docs.append(("project:"+project.id, project.title, text))
    return docs


def vector_literal(values):
    if len(values) != embeddings.DIMENSIONS or not all(math.isfinite(v) for v in values):
        raise ValueError("Invalid embedding dimensions or values.")
    return "["+",".join(str(float(v)) for v in values)+"]"


def index_status(workspace):
    validate_workspace(workspace)
    with database.connection() as db:
        row = db.execute("SELECT profile_revision,embedding_model,chunk_count FROM rag_indexes WHERE workspace_id=%s", (workspace,)).fetchone()
    return row


def build_index(workspace):
    validate_workspace(workspace)
    profile, revision = load_profile(workspace)
    docs = sources(profile)
    if not docs:
        raise ValueError("Upload and approve a CV, or review at least one project, before indexing.")
    entries = [(doc_id, title, start, end, span) for doc_id,title,text in docs for start,end,span in chunks(text)]
    vectors = embeddings.embed_documents([e[4] for e in entries])
    if len(vectors) != len(entries):
        raise ValueError("Embedding count did not match source chunks.")
    with database.connection() as db:
        db.execute("SELECT id FROM workspaces WHERE id=%s FOR UPDATE", (workspace,))
        current = db.execute("SELECT revision FROM profiles WHERE workspace_id=%s", (workspace,)).fetchone()
        if current is None or current[0] != revision:
            raise ValueError("Profile changed during indexing. Build the index again.")
        # Only index-owned text documents are replaced. Original CV uploads are untouched.
        db.execute("DELETE FROM document_chunks WHERE workspace_id=%s AND document_id LIKE %s", (workspace,'rag:%'))
        db.execute("DELETE FROM documents WHERE workspace_id=%s AND id LIKE %s", (workspace,'rag:%'))
        for doc_id,title,text in docs:
            db.execute("INSERT INTO documents(workspace_id,id,filename,media_type,content_sha256,approved_text,status) VALUES (%s,%s,%s,'text/plain',%s,%s,'indexed')",
                       (workspace,"rag:"+doc_id,title,sha256((doc_id+text).encode()).hexdigest(),text))
        ordinals = {}
        for entry, vector in zip(entries,vectors):
            doc_id,title,start,end,span = entry
            ordinal = ordinals.get(doc_id,0); ordinals[doc_id] = ordinal+1
            chunk_id = sha256((workspace+str(revision)+doc_id+str(start)).encode()).hexdigest()[:24]
            metadata = {"title":title,"source_id":doc_id,"start":start,"end":end,"profile_revision":revision,"synthetic":workspace=="demo"}
            db.execute("INSERT INTO document_chunks VALUES (%s,%s,%s,%s,%s,%s,%s::vector,%s,%s)",
                       (workspace,"rag:"+doc_id,chunk_id,ordinal,span,Jsonb(metadata),vector_literal(vector),embeddings.MODEL,embeddings.DIMENSIONS))
        db.execute("INSERT INTO rag_indexes(workspace_id,profile_revision,embedding_model,dimensions,chunk_count) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(workspace_id) DO UPDATE SET profile_revision=excluded.profile_revision,embedding_model=excluded.embedding_model,dimensions=excluded.dimensions,chunk_count=excluded.chunk_count,created_at=now()",
                   (workspace,revision,embeddings.MODEL,embeddings.DIMENSIONS,len(entries)))
    return {"profile_revision":revision,"documents":len(docs),"chunks":len(entries)}


def retrieve(workspace, analysis, revision, limit=3):
    """Retrieve candidates per explicit requirement; similarity is not evidence of fit."""
    validate_workspace(workspace)
    result = []
    requirements = capability_requirements(analysis)
    for index, requirement in enumerate(requirements):
        vector = embeddings.embed_query(requirement["description"])
        with database.connection() as db:
            status = db.execute("SELECT profile_revision,embedding_model FROM rag_indexes WHERE workspace_id=%s", (workspace,)).fetchone()
            current = db.execute("SELECT revision FROM profiles WHERE workspace_id=%s", (workspace,)).fetchone()
            if not status or not current or status[0] != revision or current[0] != revision or status[1] != embeddings.MODEL:
                raise ValueError("The evidence index is missing or out of date. Rebuild it from My profile.")
            rows = db.execute("WITH eligible AS MATERIALIZED (SELECT id,content,metadata,embedding FROM document_chunks WHERE workspace_id=%s AND embedding_model=%s AND embedding_dimensions=%s) SELECT id,content,metadata,1-(embedding <=> %s::vector) AS similarity FROM eligible ORDER BY embedding <=> %s::vector LIMIT %s",
                              (workspace,embeddings.MODEL,embeddings.DIMENSIONS,vector_literal(vector),vector_literal(vector),limit)).fetchall()
        result.append({"requirement_index":index,"requirement":requirement["description"],
                       "candidates":[{"chunk_id":r[0],"content":r[1],"metadata":r[2],"similarity":round(r[3],4)} for r in rows]})
    return result
