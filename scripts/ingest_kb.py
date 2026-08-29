"""Ingest data/kb/*.md into the running Qdrant instance.

Usage: python scripts/ingest_kb.py  (run after `docker compose up -d`)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.rag.embeddings import Embedder
from app.rag.ingest import ingest_kb
from app.rag.vector_store import QdrantVectorStore

KB_DIR = Path(__file__).resolve().parent.parent / "data" / "kb"


def main():
    embedder = Embedder()
    store = QdrantVectorStore(
        collection_name=settings.qdrant_collection, url=settings.qdrant_url
    )
    count = ingest_kb(KB_DIR, store, embedder)
    files = len(list(KB_DIR.glob("*.md")))
    print(f"Ingested {count} chunks from {files} files into '{settings.qdrant_collection}'")


if __name__ == "__main__":
    main()
