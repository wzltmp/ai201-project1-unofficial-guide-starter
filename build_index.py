"""Build the vector index from documents/ (run once, then run the app).

Pipeline: ingest -> chunk -> embed -> store. Rerun any time you add or edit a
document; the store is rebuilt from scratch so it always matches documents/.

    python build_index.py
"""

from src.chunk import chunk_documents
from src.embed_store import build_store
from src.ingest import load_documents


def main() -> None:
    print("Loading documents...")
    docs = load_documents()
    print(f"  loaded {len(docs)} documents")

    print("Chunking...")
    chunks = chunk_documents(docs)
    sizes = [len(c["text"]) for c in chunks]
    print(
        f"  produced {len(chunks)} chunks "
        f"(min={min(sizes)}, max={max(sizes)}, avg={sum(sizes) // len(sizes)} chars)"
    )

    print("Embedding + building vector store (first run downloads the model)...")
    collection = build_store(chunks)
    print(f"  stored {collection.count()} chunks in collection '{collection.name}'")
    print("\nDone. Now run:  streamlit run app.py")


if __name__ == "__main__":
    main()
