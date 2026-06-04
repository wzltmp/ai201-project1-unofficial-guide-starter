"""Milestone 3 — Document ingestion.

Loads raw documents from ``documents/``, strips the ``---`` metadata header and
markdown noise, and returns clean, structured records ready for chunking.

Each document starts with a lightweight header block::

    ---
    title: Hillside Commons — honest reviews
    source_type: forum_thread
    source: r/BrightwoodU (simulated)
    ---
    <body text...>

The header gives us per-source attribution (title / source / source_type) that we
carry all the way through to the cited answer.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from . import config


def _read_pdf(path: Path) -> str:
    """Extract text from a digitally-created PDF using pdfplumber.

    NOTE: pdfplumber does not OCR — scanned image-only PDFs yield empty text and are
    skipped. Anything you can select text in (housing guides, syllabi, handbooks) works.
    """
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            f"{path.name} is a PDF but pdfplumber isn't installed. "
            "Run: pip install pdfplumber  (or uncomment it in requirements.txt)"
        ) from exc

    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() for p in pdf.pages]
    return "\n\n".join(t for t in pages if t)


def _read_raw(path: Path) -> str:
    """Return raw text for a document, extracting from PDF when needed."""
    if path.suffix.lower() == ".pdf":
        return _read_pdf(path)
    return path.read_text(encoding="utf-8")


def _parse_header(raw: str, filename: str) -> tuple[dict, str]:
    """Split a raw document into (metadata dict, body text).

    Falls back to sensible defaults if a file has no ``---`` header so the
    pipeline never crashes on an unexpected drop-in document.
    """
    meta = {"title": filename, "source": filename, "source_type": "document"}

    header_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
    if header_match:
        header_block, body = header_match.group(1), header_match.group(2)
        for line in header_block.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
    else:
        body = raw

    return meta, body


def _clean_body(body: str) -> str:
    """Preprocess body text: drop markdown noise, normalize whitespace.

    Reviews and forum threads carry markdown headings (``#``), emphasis markers,
    and ragged blank lines. We strip the markup that adds no semantic signal while
    keeping the words, then collapse runs of blank lines so chunking sees clean
    paragraphs.

    Real scraped/HTML drop-ins are handled first: HTML tags are removed and entities
    (``&amp;``, ``&nbsp;``) are decoded before the markdown cleanup, so cleaning catches
    the boilerplate the document pipeline must strip.
    """
    text = body

    # Strip HTML tags, then decode HTML entities (handles scraped/HTML documents).
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)

    # Drop leading markdown heading hashes but keep the heading text.
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers and inline-code backticks (keep the content).
    text = re.sub(r"[*_`]+", "", text)
    # Normalize list bullets to a simple dash.
    text = re.sub(r"^\s*[-*+]\s+", "- ", text, flags=re.MULTILINE)
    # Collapse 3+ newlines down to a paragraph break.
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Trim trailing spaces on each line.
    text = re.sub(r"[ \t]+\n", "\n", text)

    return text.strip()


def load_documents(documents_dir: Path | str = config.DOCUMENTS_DIR) -> list[dict]:
    """Load and preprocess every document in ``documents_dir``.

    Returns a list of records::

        {"doc_id", "filename", "title", "source", "source_type", "text"}

    sorted by filename for stable, reproducible chunk IDs.
    """
    documents_dir = Path(documents_dir)
    records: list[dict] = []

    paths = sorted(
        p for p in documents_dir.glob("*")
        if p.suffix.lower() in {".md", ".txt", ".pdf"} and p.name != ".gitkeep"
    )

    for path in paths:
        raw = _read_raw(path)
        meta, body = _parse_header(raw, path.stem)
        text = _clean_body(body)
        if not text:
            continue  # skip empty files
        records.append(
            {
                "doc_id": path.stem,
                "filename": path.name,
                "title": meta.get("title", path.stem),
                "source": meta.get("source", path.stem),
                "source_type": meta.get("source_type", "document"),
                "text": text,
            }
        )

    return records


if __name__ == "__main__":
    # Quick manual check: how many docs and a preview of the first.
    docs = load_documents()
    print(f"Loaded {len(docs)} documents from {config.DOCUMENTS_DIR}\n")
    for d in docs:
        print(f"  [{d['source_type']:>13}] {d['title']}  ({len(d['text'])} chars)")
