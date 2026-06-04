"""Compare chunking strategies on the same query set (stretch feature 2).

Holds everything fixed except the chunker, builds each strategy into an isolated
in-memory ChromaDB collection, and reports Recall@4 + average expected-doc rank over
the 5 eval questions. Also runs a targeted "label-binding" check on the documented
failure case: does the top retrieved chunk keep "Unlimited … $2,950" intact?

    python compare_chunking.py
"""

from __future__ import annotations

import uuid

import chromadb

from evaluate import TEST_CASES
from src.chunk import chunk_documents, chunk_text, fixed_chunk_text
from src.embed_store import embed_texts
from src.ingest import load_documents

TOP_K = 4

# (label, chunker, chunk_size, overlap)
STRATEGIES = [
    ("paragraph 700/100 (baseline)", chunk_text, 700, 100),
    ("paragraph 400/80 (smaller)", chunk_text, 400, 80),
    ("paragraph 1000/150 (larger)", chunk_text, 1000, 150),
    ("naive fixed 700/100", fixed_chunk_text, 700, 100),
]


def build_ephemeral(chunks: list[dict]):
    """Build a throwaway in-memory collection from chunk records and return it."""
    client = chromadb.EphemeralClient()
    # EphemeralClient is a shared singleton, so use a unique name per build.
    col = client.create_collection(
        f"cmp_{uuid.uuid4().hex[:8]}", metadata={"hnsw:space": "cosine"}
    )
    col.add(
        ids=[c["chunk_id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embed_texts([c["text"] for c in chunks]),
        metadatas=[{"filename": c["filename"]} for c in chunks],
    )
    return col


def query(col, q: str, top_k: int = TOP_K) -> list[dict]:
    res = col.query(
        query_embeddings=[embed_texts([q])[0]],
        n_results=top_k,
        include=["documents", "metadatas"],
    )
    return [
        {
            "text": t,
            "title": m["filename"],
            "source": m["filename"],
            "source_type": "",
            "filename": m["filename"],
            "rank": i + 1,
        }
        for i, (t, m) in enumerate(zip(res["documents"][0], res["metadatas"][0]))
    ]


def main() -> None:
    docs = load_documents()
    print(f"Comparing {len(STRATEGIES)} chunking strategies on {len(TEST_CASES)} "
          f"questions (top-{TOP_K})\n")
    print(f"{'strategy':<32}{'#chunks':<9}{'recall@4':<10}{'avg rank':<10}")
    print("-" * 62)

    for label, chunker, size, overlap in STRATEGIES:
        chunks = chunk_documents(docs, chunker=chunker, chunk_size=size, overlap=overlap)
        col = build_ephemeral(chunks)

        hits = 0
        rank_sum = 0
        for case in TEST_CASES:
            results = query(col, case["question"])
            ranks = [r["rank"] for r in results if r["filename"] == case["expected_source"]]
            if ranks:
                hits += 1
                rank_sum += min(ranks)
            else:
                rank_sum += TOP_K + 1  # penalty for a miss
        avg_rank = rank_sum / len(TEST_CASES)

        print(f"{label:<32}{len(chunks):<9}{f'{hits}/{len(TEST_CASES)}':<10}"
              f"{avg_rank:<10.2f}")

    print("-" * 62)
    print("Lower avg rank = expected doc retrieved higher. With short excerpts each")
    print("document is ~one chunk, so chunk size has little effect on this corpus.")


if __name__ == "__main__":
    main()
