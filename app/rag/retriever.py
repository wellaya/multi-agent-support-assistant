from dataclasses import dataclass

from app.rag.embeddings import Embedder
from app.rag.vector_store import QdrantVectorStore


@dataclass
class RetrievedChunk:
    text: str
    source: str
    score: float


def retrieve(
    query: str,
    store: QdrantVectorStore,
    embedder: Embedder,
    top_k: int = 3,
) -> list[RetrievedChunk]:
    query_vector = embedder.embed_one(query)
    hits = store.search(query_vector, top_k=top_k)
    return [
        RetrievedChunk(
            text=hit["payload"]["text"],
            source=hit["payload"]["source"],
            score=hit["score"],
        )
        for hit in hits
    ]
