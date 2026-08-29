from app.rag.embeddings import Embedder
from app.rag.retriever import retrieve
from app.rag.vector_store import QdrantVectorStore

FIXTURES = {
    "password_reset.md": "To reset your password, click 'Forgot password?' on the login page and follow the emailed link.",
    "refund_policy.md": "Refunds are issued within 14 days of purchase back to your original payment method.",
    "shipping_info.md": "Standard shipping takes 5-7 business days and includes a tracking number by email.",
}


def _build_store(embedder: Embedder) -> QdrantVectorStore:
    store = QdrantVectorStore(collection_name="test_kb", url=None)
    store.ensure_collection(vector_size=embedder.dimension, recreate=True)
    vectors = embedder.embed(list(FIXTURES.values()))
    payloads = [
        {"text": text, "source": source, "chunk_index": 0}
        for source, text in FIXTURES.items()
    ]
    store.upsert(vectors=vectors, payloads=payloads)
    return store


def test_retrieve_returns_topically_correct_source():
    embedder = Embedder()
    store = _build_store(embedder)

    results = retrieve(
        "how do I reset my password", store=store, embedder=embedder, top_k=1
    )

    assert len(results) == 1
    assert results[0].source == "password_reset.md"


def test_retrieve_top_k_respected():
    embedder = Embedder()
    store = _build_store(embedder)

    results = retrieve("account help", store=store, embedder=embedder, top_k=2)

    assert len(results) == 2
