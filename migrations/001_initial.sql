CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS schema_migrations (
  version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE workspaces (
  id text PRIMARY KEY CHECK (id IN ('personal','demo')),
  synthetic boolean NOT NULL,
  UNIQUE(id, synthetic)
);
INSERT INTO workspaces VALUES ('personal',false),('demo',true);
CREATE TABLE profiles (
  workspace_id text PRIMARY KEY REFERENCES workspaces(id),
  payload jsonb NOT NULL,
  revision integer NOT NULL CHECK (revision > 0),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE profile_versions (
  workspace_id text NOT NULL REFERENCES profiles(workspace_id),
  revision integer NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(workspace_id,revision)
);
CREATE TABLE projects (
  workspace_id text NOT NULL REFERENCES profiles(workspace_id),
  id text NOT NULL,
  payload jsonb NOT NULL,
  reviewed boolean NOT NULL DEFAULT false,
  PRIMARY KEY(workspace_id,id)
);
CREATE TABLE documents (
  workspace_id text NOT NULL REFERENCES workspaces(id),
  id text NOT NULL,
  filename text NOT NULL,
  media_type text NOT NULL,
  content_sha256 text NOT NULL,
  file_bytes bytea,
  approved_text text NOT NULL DEFAULT '',
  status text NOT NULL CHECK (status IN ('uploaded','reviewed','indexed','failed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(workspace_id,id),
  UNIQUE(workspace_id,content_sha256)
);
CREATE TABLE document_chunks (
  workspace_id text NOT NULL,
  document_id text NOT NULL,
  id text NOT NULL,
  ordinal integer NOT NULL CHECK(ordinal >= 0),
  content text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}',
  embedding vector,
  embedding_model text,
  embedding_dimensions integer,
  PRIMARY KEY(workspace_id,id),
  UNIQUE(workspace_id,document_id,ordinal),
  FOREIGN KEY(workspace_id,document_id) REFERENCES documents(workspace_id,id),
  CHECK ((embedding IS NULL AND embedding_model IS NULL AND embedding_dimensions IS NULL)
      OR (embedding IS NOT NULL AND embedding_model IS NOT NULL AND embedding_dimensions > 0
          AND vector_dims(embedding)=embedding_dimensions))
);
CREATE TABLE jobs (
  workspace_id text NOT NULL REFERENCES workspaces(id),
  id text NOT NULL,
  description text NOT NULL,
  description_hash text NOT NULL,
  version integer NOT NULL DEFAULT 1,
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(workspace_id,id),
  UNIQUE(workspace_id,description_hash)
);
CREATE TABLE workflow_runs (
  workspace_id text NOT NULL,
  id text NOT NULL,
  job_id text NOT NULL,
  job_version integer NOT NULL,
  profile_revision integer NOT NULL,
  status text NOT NULL CHECK(status IN ('pending','running','awaiting_approval','completed','failed','stale')),
  checkpoint_ref text,
  metrics jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(workspace_id,id),
  FOREIGN KEY(workspace_id,job_id) REFERENCES jobs(workspace_id,id),
  FOREIGN KEY(workspace_id,profile_revision) REFERENCES profile_versions(workspace_id,revision)
);
CREATE TABLE stage_results (
  workspace_id text NOT NULL,
  run_id text NOT NULL,
  stage text NOT NULL CHECK(stage IN ('analysis','retrieval','matching','estimation','proposal','review')),
  revision integer NOT NULL CHECK(revision>0),
  schema_version integer NOT NULL DEFAULT 1,
  input_refs jsonb NOT NULL,
  output jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(workspace_id,run_id,stage,revision),
  FOREIGN KEY(workspace_id,run_id) REFERENCES workflow_runs(workspace_id,id)
);
CREATE TABLE proposals (
  workspace_id text NOT NULL,
  run_id text NOT NULL,
  id text NOT NULL,
  revision integer NOT NULL,
  technical_text text NOT NULL,
  financial_details jsonb NOT NULL,
  approval_status text NOT NULL CHECK(approval_status IN ('draft','approved','stale')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(workspace_id,id,revision),
  FOREIGN KEY(workspace_id,run_id) REFERENCES workflow_runs(workspace_id,id)
);
CREATE TABLE application_events (
  workspace_id text NOT NULL,
  job_id text NOT NULL,
  id bigint GENERATED ALWAYS AS IDENTITY,
  status text NOT NULL CHECK(status IN ('saved','submitted','interview','accepted','rejected','withdrawn')),
  note text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(id),
  FOREIGN KEY(workspace_id,job_id) REFERENCES jobs(workspace_id,id)
);
CREATE INDEX document_chunks_owner_idx ON document_chunks(workspace_id,document_id);
CREATE INDEX workflow_runs_job_idx ON workflow_runs(workspace_id,job_id);
