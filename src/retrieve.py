"""Milestone 4 — Semantic retrieval.

Given a natural-language query, embed it with the same model used to index the
corpus and return the top-k most similar chunks from ChromaDB. Cosine *distance*
returned by Chroma is converted to a *similarity* score (1 - distance) so higher
is better, which is what the relevance cutoff and the UI display expect.
"""

from __future__ import annotations

from . import config
from .embed_store import embed_texts, get_collection


def _build_where(source_types: list[str] | None) -> dict | None:
    """Build a ChromaDB metadata `where` clause for an optional source-type filter."""
    if not source_types:
        return None
    if len(source_types) == 1:
        return {"source_type": source_types[0]}
    return {"source_type": {"$in": list(source_types)}}


def retrieve(
    query: str,
    top_k: int = config.TOP_K,
    source_types: list[str] | None = None,
) -> list[dict]:
    """Return the top-k chunks most semantically similar to ``query``.

    ``source_types`` optionally restricts retrieval to chunks whose ``source_type``
    metadata is in the given list (metadata filtering, via a ChromaDB ``where`` clause).

    Each result::

        {"text", "title", "source", "source_type", "filename", "score", "rank"}

    ``score`` is cosine similarity in [~0, 1]; results are ordered best-first.
    """
    collection = get_collection()
    if collection.count() == 0:
        return []

    query_embedding = embed_texts([query])[0]
    where = _build_where(source_types)
    raw = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    documents = raw["documents"][0]
    metadatas = raw["metadatas"][0]
    distances = raw["distances"][0]

    results: list[dict] = []
    for rank, (text, meta, distance) in enumerate(zip(documents, metadatas, distances)):
        results.append(
            {
                "text": text,
                "title": meta.get("title", "Unknown source"),
                "source": meta.get("source", ""),
                "source_type": meta.get("source_type", ""),
                "url": meta.get("url", ""),
                "filename": meta.get("filename", ""),
                "score": round(1.0 - distance, 4),  # cosine distance -> similarity
                "rank": rank + 1,
            }
        )
    return results


if __name__ == "__main__":
    # No-LLM smoke test: confirm semantic search returns on-topic chunks.
    for q in ["best vegan dining hall", "quiet place to study late at night"]:
        print(f"\nQUERY: {q}")
        for r in retrieve(q):
            print(f"  {r['score']:.3f}  [{r['title']}]")
            print(f"         {r['text'][:90]}...")
