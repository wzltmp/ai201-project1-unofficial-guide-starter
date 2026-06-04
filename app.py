"""Milestone 5 — Streamlit query interface for The Unofficial Guide.

    streamlit run app.py

A chat interface: ask a question, get a grounded answer with inline [n] citations, and
expand the "Retrieved context" panel to see exactly which chunks (and similarity scores)
the answer was built from. Supports multi-turn follow-ups (conversational memory),
a Semantic/Hybrid retrieval toggle, and source-type filtering.
"""

from __future__ import annotations

import streamlit as st

from src import config
from src.embed_store import get_collection, get_embedding_model
from src.generate import answer_question, rewrite_followup

st.set_page_config(page_title="The Unofficial Guide", page_icon="🎓", layout="centered")


@st.cache_resource(show_spinner="Loading embedding model + index...")
def _warm_up():
    """Load the model and collection once; return (chunk_count, sorted source types)."""
    get_embedding_model()
    collection = get_collection()
    count = collection.count()
    types: set[str] = set()
    if count:
        for meta in collection.get(include=["metadatas"])["metadatas"]:
            types.add(meta.get("source_type", "document"))
    return count, sorted(types)


st.title("🎓 The Unofficial Guide")
st.caption(
    "Ask about campus dining at the University of Michigan. Answers are grounded in real "
    "collected sources — Michigan Daily reviews, M|Dining info, and dining guides — with cited links."
)

chunk_count, available_source_types = _warm_up()

# --- Guard rails: index + API key --------------------------------------
if chunk_count == 0:
    st.error("The index is empty. Build it first:  `python build_index.py`")
    st.stop()

if not config.GROQ_API_KEY:
    st.warning(
        "No `GROQ_API_KEY` found, so answers can't be generated — but retrieval still "
        "works. Copy `.env.example` to `.env` and add a free key from "
        "[console.groq.com](https://console.groq.com) to enable grounded answers."
    )

with st.sidebar:
    st.subheader("Settings")
    top_k = st.slider("Chunks to retrieve (top-k)", 1, 8, config.TOP_K)
    retrieval_mode = st.radio(
        "Retrieval mode",
        ["Semantic", "Hybrid (semantic + BM25)"],
        help="Hybrid fuses dense embedding search with BM25 keyword search via RRF.",
    )
    source_filter = st.multiselect(
        "Filter by source type",
        options=available_source_types,
        default=[],
        help="Restrict retrieval to these document types. Empty = search all sources.",
    )
    st.markdown(f"**Indexed chunks:** {chunk_count}")
    st.markdown(f"**Embedding model:** `{config.EMBEDDING_MODEL}`")
    st.markdown(f"**LLM:** `{config.GROQ_MODEL}`")
    st.divider()
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()
    st.markdown(
        "**Try asking:**\n"
        "- Which dining hall has the only kosher kitchen on campus?\n"
        "- What is Mosher-Jordan (Mojo) known for?\n"
        "- Why do students criticize Bursley?\n"
        "- _(follow-up)_ Is it good for vegans?"
    )


def render_result(result: dict, search_query: str | None = None) -> None:
    """Render an assistant turn: optional rewritten-query note, answer, sources, context."""
    if search_query:
        st.caption(f"🔎 searched for: *{search_query}*")

    if result["answer"]:
        if result["grounded"]:
            st.markdown(result["answer"])
        else:
            st.info(result["answer"])
    else:
        st.caption("No API key set — showing retrieved context only.")

    if result.get("sources"):
        st.markdown("**Sources**")
        for s in result["sources"]:
            label = "".join(f"[{c}]" for c in s["citations"])
            src = f"[{s['source']}]({s['url']})" if s.get("url") else s["source"]
            st.markdown(
                f"- **{label} {s['title']}** — _{s['source_type']}_, "
                f"{src} (similarity {s['score']:.2f})"
            )

    with st.expander(f"🔎 Retrieved context ({len(result['chunks'])} chunks)"):
        if not result["chunks"]:
            st.write("No chunks retrieved.")
        for c in result["chunks"]:
            st.markdown(
                f"**#{c['rank']} · {c['title']}** · _{c['source_type']}_ · "
                f"score **{c['score']:.3f}**"
            )
            st.write(c["text"])
            st.divider()


# --- Chat interface with conversational memory -------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Replay the conversation so far.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_result(msg["result"], msg.get("search_query"))

prompt = st.chat_input("Ask about U-M campus dining…")
if prompt and prompt.strip():
    use_hybrid = retrieval_mode.startswith("Hybrid")
    source_types = source_filter or None  # empty multiselect = search all sources

    # Prior turns become the history used to resolve follow-up references.
    history = [
        {"role": m["role"], "content": m["content"] if m["role"] == "user"
         else m["result"].get("answer") or ""}
        for m in st.session_state.messages
    ]

    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Searching the guide…"):
            if use_hybrid:
                from src.hybrid import hybrid_retrieve as retriever
            else:
                from src.retrieve import retrieve as retriever

            # Conversational memory: rewrite a follow-up into a standalone query.
            search_query = rewrite_followup(history, prompt) if history else prompt
            shown_rewrite = search_query if search_query.strip() != prompt.strip() else None

            if not config.GROQ_API_KEY:
                chunks = retriever(search_query, top_k=top_k, source_types=source_types)
                result = {"answer": None, "sources": [], "chunks": chunks, "grounded": False}
            else:
                result = answer_question(
                    search_query, top_k=top_k, retriever=retriever, source_types=source_types
                )
        render_result(result, shown_rewrite)

    st.session_state.messages.append(
        {"role": "assistant", "result": result, "search_query": shown_rewrite}
    )
