"""Milestone 3 — Chunking.

Splits documents into overlapping, paragraph-aware chunks. The strategy (see
planning.md) packs whole paragraphs up to ``CHUNK_SIZE`` and only hard-splits a
paragraph that is itself longer than the limit, so we never break words or merge
unrelated forum posts. ``CHUNK_OVERLAP`` characters of the previous chunk are
prepended to the next so a thought that straddles a boundary isn't cut in half.
"""

from __future__ import annotations

from . import config


def _split_long_paragraph(paragraph: str, chunk_size: int) -> list[str]:
    """Hard-split a single paragraph longer than ``chunk_size`` on word boundaries."""
    words = paragraph.split()
    pieces: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > chunk_size:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        pieces.append(current)
    return pieces


def chunk_text(
    text: str,
    chunk_size: int = config.CHUNK_SIZE,
    overlap: int = config.CHUNK_OVERLAP,
) -> list[str]:
    """Split ``text`` into overlapping chunks of at most ``chunk_size`` characters.

    Paragraphs (blank-line separated) are the atomic unit: we greedily pack them
    into a chunk until adding the next would exceed ``chunk_size``, then start a
    new chunk seeded with the last ``overlap`` characters of the previous one.
    """
    # Normalize to paragraphs; pre-split any paragraph that alone exceeds the size.
    paragraphs: list[str] = []
    for para in (p.strip() for p in text.split("\n\n")):
        if not para:
            continue
        if len(para) > chunk_size:
            paragraphs.extend(_split_long_paragraph(para, chunk_size))
        else:
            paragraphs.append(para)

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        # Flush the current chunk and start a new one with overlap context.
        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{para}".strip() if tail else para
            # An overlap tail + a near-max paragraph can exceed chunk_size; that's
            # acceptable (still under the embedder's token cap) and keeps the thought whole.
        else:
            current = para

    if current:
        chunks.append(current)

    return chunks


def fixed_chunk_text(
    text: str,
    chunk_size: int = config.CHUNK_SIZE,
    overlap: int = config.CHUNK_OVERLAP,
) -> list[str]:
    """Naive fixed-width sliding window over characters (no paragraph awareness).

    Provided only as a baseline for the chunking-strategy comparison — it blindly
    cuts every ``chunk_size`` characters with ``overlap`` carryover, ignoring
    paragraph and word boundaries. Not used by the production pipeline.
    """
    if not text:
        return []
    step = max(1, chunk_size - overlap)
    return [text[i : i + chunk_size].strip() for i in range(0, len(text), step)]


def chunk_documents(
    documents: list[dict],
    chunker=chunk_text,
    chunk_size: int = config.CHUNK_SIZE,
    overlap: int = config.CHUNK_OVERLAP,
) -> list[dict]:
    """Chunk a list of ingested document records into chunk records.

    ``chunker`` is the splitting strategy (defaults to paragraph-aware ``chunk_text``;
    ``fixed_chunk_text`` is available for comparison). Each chunk record carries the
    parent document's attribution metadata plus a stable ``chunk_id`` so retrieval
    results can be cited back to a source.
    """
    chunk_records: list[dict] = []
    for doc in documents:
        pieces = chunker(doc["text"], chunk_size, overlap)
        # Guard: never emit empty/whitespace-only chunks for embedding.
        pieces = [p for p in pieces if p.strip()]
        for i, piece in enumerate(pieces):
            chunk_records.append(
                {
                    "chunk_id": f"{doc['doc_id']}::chunk_{i}",
                    "text": piece,
                    "doc_id": doc["doc_id"],
                    "filename": doc["filename"],
                    "title": doc["title"],
                    "source": doc["source"],
                    "source_type": doc["source_type"],
                    "url": doc.get("url", ""),
                    "chunk_index": i,
                }
            )
    return chunk_records


if __name__ == "__main__":
    from .ingest import load_documents

    docs = load_documents()
    chunks = chunk_documents(docs)
    sizes = [len(c["text"]) for c in chunks]
    print(f"{len(docs)} documents -> {len(chunks)} chunks")
    print(f"chunk size: min={min(sizes)} max={max(sizes)} avg={sum(sizes)//len(sizes)}")
    print("\n--- sample chunk ---")
    print(chunks[0]["text"][:400])
