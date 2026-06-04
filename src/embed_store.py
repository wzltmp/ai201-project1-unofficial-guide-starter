"""Milestone 4 — Embedding + vector store.

Wraps the sentence-transformers embedding model and a persistent ChromaDB
collection. The model is loaded once and cached at module level (it's a few
hundred MB), and the collection uses cosine distance to match how we score
similarity at retrieval time.
"""

from __future__ import annotations

import chromadb
from sentence_transformers import SentenceTransformer

from . import config

# Lazily-loaded singletons so importing this module is cheap and we never load
# the model or open the DB more than once per process.
_model: SentenceTransformer | None = None
_client: chromadb.ClientAPI | None = None


def get_embedding_model() -> SentenceTransformer:
    """Return the shared embedding model, loading it on first use."""
    global _model
    if _model is None:
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into plain Python lists (what ChromaDB expects)."""
    model = get_embedding_model()
    vectors = model.encode(texts, show_progress_bar=False, normalize_embeddings=False)
    return [v.tolist() for v in vectors]


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    return _client


def get_collection() -> chromadb.Collection:
    """Get (or create) the persistent collection used for querying."""
    client = _get_client()
    return client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_store(chunks: list[dict]) -> chromadb.Collection:
    """(Re)build the vector store from chunk records.

    Drops any existing collection first so the build is idempotent — rerunning
    ``build_index.py`` always reflects the current ``documents/`` exactly, with no
    stale or duplicate chunks. Embeds all chunk texts in a single batch.
    """
    client = _get_client()

    # Idempotent rebuild: delete then recreate.
    try:
        client.delete_collection(config.COLLECTION_NAME)
    except Exception:
        pass  # collection didn't exist yet

    collection = client.create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    metadatas = [
        {
            "title": c["title"],
            "source": c["source"],
            "source_type": c["source_type"],
            "url": c.get("url", ""),
            "filename": c["filename"],
            "doc_id": c["doc_id"],
            "chunk_index": c["chunk_index"],
        }
        for c in chunks
    ]
    ids = [c["chunk_id"] for c in chunks]

    collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
    return collection
