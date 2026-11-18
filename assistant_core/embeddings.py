"""CPU-only local embeddings; no CV text goes to a remote embedding API."""
from functools import lru_cache
from pathlib import Path

MODEL = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384


@lru_cache(maxsize=1)
def model():
    import os
    os.environ.setdefault("HF_HOME", str(Path(__file__).resolve().parents[1]/"data"/"huggingface"))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from fastembed import TextEmbedding
    cache = Path(__file__).resolve().parents[1] / "data" / "embedding-cache"
    return TextEmbedding(model_name=MODEL, cache_dir=str(cache), threads=2)


def embed_documents(texts):
    try:
        return [v.tolist() for v in model().passage_embed(texts)]
    except Exception:
        raise OSError("Embedding model could not run. Check the initial model download and available memory.") from None


def embed_query(text):
    try:
        return next(model().query_embed(text)).tolist()
    except Exception:
        raise OSError("Could not embed the query. Check the local embedding model.") from None
