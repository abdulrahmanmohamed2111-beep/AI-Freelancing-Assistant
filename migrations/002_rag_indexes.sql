CREATE TABLE rag_indexes (
  workspace_id text PRIMARY KEY REFERENCES profiles(workspace_id),
  profile_revision integer NOT NULL,
  embedding_model text NOT NULL,
  dimensions integer NOT NULL,
  chunk_count integer NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY(workspace_id,profile_revision) REFERENCES profile_versions(workspace_id,revision)
);
