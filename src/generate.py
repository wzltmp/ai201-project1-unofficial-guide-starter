"""Milestone 5 — Grounded answer generation.

Takes the retrieved chunks and asks a Groq-hosted LLM to answer using ONLY that
context, with inline [n] citations that map back to a source. Grounding is
enforced two ways:

1. Structure  — context is a numbered list, each item prefixed with its source
   title, so the model has explicit, citable units to point at.
2. Instruction — a strict system prompt forbids outside knowledge and requires a
   "not enough information" answer when the context doesn't cover the question.

A low-relevance guard short-circuits out-of-corpus questions before the LLM is
ever called, so the system fails closed instead of hallucinating.
"""

from __future__ import annotations

from . import config
from .retrieve import retrieve

SYSTEM_PROMPT = """You are The Unofficial Guide, a campus assistant that answers \
questions using ONLY student-written documents retrieved from a knowledge base.

Rules:
1. Answer using ONLY the information in the numbered CONTEXT below. Do not use any \
outside or prior knowledge, even if you think you know the answer.
2. Cite your sources inline with bracketed numbers like [1] or [2], matching the \
numbered context items you used. Every claim should carry a citation. Cite only the \
specific items you actually used — do NOT append a list of all source numbers at the end.
3. The documents are opinions from different students and may disagree. When they \
do, report the range of views ("some students say X, others Y") and cite each — \
do not flatten it into one false consensus.
4. If the context does not contain enough information to answer, reply exactly: \
"I don't have enough information in the collected documents to answer that." Do not \
guess or fill gaps with general knowledge.
5. Keep the answer concise and practical — these are students looking for a quick, \
useful answer."""

NOT_ENOUGH_INFO = (
    "I don't have enough information in the collected documents to answer that."
)


def build_context(chunks: list[dict]) -> str:
    """Render retrieved chunks as a numbered, source-titled context block."""
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        lines.append(f"[{i}] (Source: {chunk['title']})\n{chunk['text']}")
    return "\n\n".join(lines)


def _format_sources(chunks: list[dict]) -> list[dict]:
    """Group retrieved chunks into a per-document source list for display.

    The context numbers chunks [1..k] and the model cites those per-chunk numbers, but
    several chunks often come from the same document. We group by document and keep the
    full list of citation numbers that map to it, so EVERY inline [n] in the answer
    resolves to a source — even when one document supplied multiple cited chunks.
    """
    grouped: dict[str, dict] = {}
    for i, chunk in enumerate(chunks, start=1):
        key = chunk["filename"]
        if key not in grouped:
            grouped[key] = {
                "citations": [i],
                "title": chunk["title"],
                "source": chunk["source"],
                "source_type": chunk["source_type"],
                "url": chunk.get("url", ""),
                "filename": chunk["filename"],
                "score": chunk["score"],  # best (first/highest) similarity for this doc
            }
        else:
            grouped[key]["citations"].append(i)
    return list(grouped.values())


def _citation_label(citations: list[int]) -> str:
    """Render a source's citation numbers as ``[1][2]``."""
    return "".join(f"[{c}]" for c in citations)


def generate_answer(query: str, chunks: list[dict]) -> str:
    """Call the Groq LLM with the grounding prompt and numbered context."""
    # Import here so retrieval-only workflows (and evaluate.py's retrieval metrics)
    # don't require the groq package or an API key.
    from groq import Groq

    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://console.groq.com"
        )

    context = build_context(chunks)
    user_message = (
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {query}\n\n"
        "Answer using only the context above, with [n] citations."
    )

    client = Groq(api_key=config.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,  # low: we want faithful, not creative
    )
    return response.choices[0].message.content.strip()


REWRITE_PROMPT = """You rewrite a user's latest question into a standalone search query \
using the conversation so far. Resolve pronouns and references ("it", "that one", "there") \
to the specific entity from earlier turns. Output ONLY the rewritten query, nothing else. \
If the latest question is already self-contained, output it unchanged."""


def rewrite_followup(history: list[dict], query: str) -> str:
    """Rewrite a follow-up question into a standalone query using prior turns.

    ``history`` is a list of ``{"role": "user"|"assistant", "content": str}``. With no
    history (first turn) the query is returned unchanged. Used by the conversational
    interface so retrieval of a follow-up like "is it open late?" resolves "it" to the
    entity from earlier turns — memory affects only the *search query*, never grounding.
    """
    if not history:
        return query
    if not config.GROQ_API_KEY:
        return query  # no key: fall back to the raw query

    from groq import Groq

    turns = "\n".join(f"{t['role']}: {t['content']}" for t in history[-6:])
    client = Groq(api_key=config.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": REWRITE_PROMPT},
            {"role": "user", "content": f"Conversation so far:\n{turns}\n\nLatest question: {query}"},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content.strip().strip('"')


def answer_question(
    query: str,
    top_k: int = config.TOP_K,
    retriever=retrieve,
    source_types: list[str] | None = None,
) -> dict:
    """End-to-end: retrieve -> ground -> generate.

    ``retriever`` selects the retrieval strategy (semantic ``retrieve`` by default,
    or ``hybrid.hybrid_retrieve``). ``source_types`` optionally restricts retrieval to
    those document source types (metadata filtering). Returns ``{"answer", "sources",
    "chunks", "grounded"}``. If nothing relevant is found, returns the not-enough-info
    answer WITHOUT calling the LLM, so out-of-corpus questions fail closed.

    The off-topic guard always judges relevance on a *semantic cosine* score (via a
    cheap top-1 semantic lookup) so the cutoff stays comparable regardless of which
    retriever supplies the display context — hybrid RRF scores aren't on that scale.
    """
    chunks = retriever(query, top_k=top_k, source_types=source_types)

    semantic_top = retrieve(query, top_k=1, source_types=source_types)
    relevant = bool(semantic_top) and semantic_top[0]["score"] >= config.MIN_RELEVANCE_SCORE
    if not chunks or not relevant:
        return {
            "answer": NOT_ENOUGH_INFO,
            "sources": [],
            "chunks": chunks,
            "grounded": False,
        }

    answer = generate_answer(query, chunks)

    # If the guard let context through but the model still grounded-refuses (e.g. an
    # on-topic question the excerpts don't actually answer), treat it like a refusal:
    # no sources, grounded=False — so a refusal never displays a contradictory source list.
    if NOT_ENOUGH_INFO.rstrip(".").lower() in answer.lower():
        return {"answer": answer, "sources": [], "chunks": chunks, "grounded": False}

    return {
        "answer": answer,
        "sources": _format_sources(chunks),
        "chunks": chunks,
        "grounded": True,
    }


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "Which dining hall is best for vegan options?"
    result = answer_question(q)
    print(f"Q: {q}\n")
    print(result["answer"])
    print("\nSources:")
    for s in result["sources"]:
        print(f"  {_citation_label(s['citations'])} {s['title']} ({s['source']})")
