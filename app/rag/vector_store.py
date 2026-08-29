import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models


class QdrantVectorStore:
    """Thin wrapper over qdrant-client.

    Pass `url=None` for an in-memory instance (tests, no Docker needed);
    pass a real URL (e.g. settings.qdrant_url) to talk to a running server.
    """

    def __init__(self, collection_name: str, url: str | None = None):
        self._client = QdrantClient(location=":memory:") if url is None else QdrantClient(url=url)
        self._collection_name = collection_name

    def ensure_collection(self, vector_size: int, recreate: bool = False) -> None:
        exists = self._client.collection_exists(self._collection_name)
        if exists and not recreate:
            return
        if exists:
            self._client.delete_collection(self._collection_name)
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=models.VectorParams(
                size=vector_size, distance=models.Distance.COSINE
            ),
        )

    def upsert(self, vectors: list[list[float]], payloads: list[dict]) -> None:
        points = [
            models.PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)
            for vector, payload in zip(vectors, payloads)
        ]
        self._client.upsert(collection_name=self._collection_name, points=points)

    def search(self, query_vector: list[float], top_k: int = 3) -> list[dict]:
        results = self._client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            limit=top_k,
        ).points
        return [{"score": hit.score, "payload": hit.payload} for hit in results]
