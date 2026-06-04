"""Stretch feature 1 — Hybrid retrieval (semantic + BM25).

Dense embedding search is great at meaning but can miss exact-term matches (proper
nouns, prices, plan names). BM25 lexical search is the opposite. We run both and fuse
their rankings with Reciprocal Rank Fusion (RRF), which combines by *rank* and so
needs no normalization between the two different score scales.

    semantic rank  ─┐
                    ├─ RRF: score(d) = Σ 1/(k + rank_r(d)) ─► fused top-k
    BM25 rank      ─┘
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from . import config
from .chunk import chunk_documents
from .embed_store import embed_texts, get_collection
from .ingest import load_documents

RRF_K = 60  # standard RRF dampening constant

# Cache the BM25 index + chunk records so repeated queries don't rebuild it.
_bm25: BM25Okapi | None = None
_chunk_records: list[dict] | None = None


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenization for BM25."""
    return re.findall(r"[a-z0-9$]+", text.lower())


def _build_bm25() -> tuple[BM25Okapi, list[dict]]:
    """Build (or return cached) BM25 index over the same chunks ChromaDB holds.

    Chunks are regenerated deterministically from documents/ so their ``chunk_id``s
    line up exactly with what ``build_index.py`` stored in the vector DB.
    """
    global _bm25, _chunk_records
    if _bm25 is None or _chunk_records is None:
        records = chunk_documents(load_documents())
        corpus = [_tokenize(c["text"]) for c in records]
        _bm25 = BM25Okapi(corpus)
        _chunk_records = records
    return _bm25, _chunk_records


def _semantic_ranking(query: str, pool: int) -> list[str]:
    """Return chunk_ids ordered best-first by semantic similarity."""
    collection = get_collection()
    n = min(pool, collection.count())
    if n == 0:
        return []
    result = collection.query(
        query_embeddings=[embed_texts([query])[0]],
        n_results=n,
        include=[],  # we only need the ids, which come back by default
    )
    return result["ids"][0]


def _bm25_ranking(query: str, pool: int) -> list[str]:
    """Return chunk_ids ordered best-first by BM25 score."""
    bm25, records = _build_bm25()
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(range(len(records)), key=lambda i: scores[i], reverse=True)
    return [records[i]["chunk_id"] for i in ranked[:pool]]


def hybrid_retrieve(
    query: str,
    top_k: int = config.TOP_K,
    pool: int = 20,
    source_types: list[str] | None = None,
) -> list[dict]:
    """Retrieve top-k chunks by fusing semantic and BM25 rankings with RRF.

    ``pool`` is how many candidates each retriever contributes before fusion.
    ``source_types`` optionally restricts results to those document source types
    (metadata filtering, applied to the fused candidates). Returns the same record
    shape as ``retrieve.retrieve`` with an RRF ``score``.
    """
    _, records = _build_bm25()
    by_id = {c["chunk_id"]: c for c in records}
    allowed = set(source_types) if source_types else None

    semantic = _semantic_ranking(query, pool)
    lexical = _bm25_ranking(query, pool)

    rrf: dict[str, float] = {}
    for ranking in (semantic, lexical):
        for rank, chunk_id in enumerate(ranking):
            rrf[chunk_id] = rrf.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)

    ordered = [cid for cid in sorted(rrf, key=lambda c: rrf[c], reverse=True)
               if allowed is None or by_id[cid]["source_type"] in allowed][:top_k]

    results: list[dict] = []
    for rank, chunk_id in enumerate(ordered):
        rec = by_id[chunk_id]
        results.append(
            {
                "text": rec["text"],
                "title": rec["title"],
                "source": rec["source"],
                "source_type": rec["source_type"],
                "url": rec.get("url", ""),
                "filename": rec["filename"],
                "score": round(rrf[chunk_id], 4),  # RRF score (not cosine)
                "rank": rank + 1,
            }
        )
    return results


if __name__ == "__main__":
    for q in ["How much does the unlimited meal plan cost?", "best vegan dining hall"]:
        print(f"\nQUERY: {q}")
        for r in hybrid_retrieve(q):
            print(f"  rrf={r['score']:.4f}  [{r['filename']}]  {r['text'][:70]}...")
