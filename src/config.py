"""Central configuration for the RAG pipeline.

Every tunable knob lives here so the rest of the code reads from one source of
truth and the planning.md / README numbers stay in sync with what actually runs.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load GROQ_API_KEY (and anything else) from a local .env file if present.
load_dotenv()

# --- Paths ---------------------------------------------------------------
# Resolve relative to this file so scripts work from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
CHROMA_DIR = str(PROJECT_ROOT / "chroma_db")  # chromadb wants a str path

# --- Chunking (Milestone 3) ---------------------------------------------
# Corpus is review/forum-thread style: many short, self-contained opinions.
# 700 chars (~150 tokens) stays well under all-MiniLM-L6-v2's 256-token input
# cap (no silent truncation) while holding one complete thought. 100-char
# overlap keeps a review that straddles a boundary from being cut mid-sentence.
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100

# --- Embedding + vector store (Milestone 4) -----------------------------
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # local, fast, 384-dim
COLLECTION_NAME = "unofficial_guide"
TOP_K = 4

# Retrieved chunks below this cosine similarity are treated as off-topic.
# Used to short-circuit out-of-corpus questions to a "not enough info" answer
# instead of feeding the LLM weak context it would hallucinate from.
MIN_RELEVANCE_SCORE = 0.25

# --- Generation (Milestone 5) -------------------------------------------
# Verified current Groq production model (June 2026). If this 404s, list
# active models at GET https://api.groq.com/openai/v1/models and swap here.
# Alternates: "llama-3.1-8b-instant", "meta-llama/llama-4-scout-17b-16e-instruct".
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
