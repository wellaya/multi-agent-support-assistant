from pathlib import Path

from app.rag.chunking import chunk_text
from app.rag.embeddings import Embedder
from app.rag.vector_store import QdrantVectorStore


def ingest_kb(kb_dir: Path, store: QdrantVectorStore, embedder: Embedder) -> int:
    """Chunk and embed every .md file in kb_dir, upsert into store.

    Returns the number of chunks ingested.
    """
    chunks: list[str] = []
    payloads: list[dict] = []

    for path in sorted(kb_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for index, chunk in enumerate(chunk_text(text)):
            chunks.append(chunk)
            payloads.append({"text": chunk, "source": path.name, "chunk_index": index})

    if not chunks:
        return 0

    store.ensure_collection(vector_size=embedder.dimension, recreate=True)
    vectors = embedder.embed(chunks)
    store.upsert(vectors=vectors, payloads=payloads)
    return len(chunks)
