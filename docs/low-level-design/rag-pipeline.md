# Low-Level Design: RAG Pipeline

Files: [`app/rag/chunking.py`](../../app/rag/chunking.py),
[`app/rag/embeddings.py`](../../app/rag/embeddings.py),
[`app/rag/vector_store.py`](../../app/rag/vector_store.py),
[`app/rag/ingest.py`](../../app/rag/ingest.py),
[`app/rag/retriever.py`](../../app/rag/retriever.py)

If "chunking", "embeddings", or "vector database" are unfamiliar terms,
read [concepts.md](../concepts.md#rag-retrieval-augmented-generation)
first — this doc assumes you know *what* RAG is and focuses on how this
project implements it.

## Data flow

```
data/kb/*.md  --chunk_text()-->  overlapping text chunks
              --Embedder.embed()-->  384-dim vectors
              --QdrantVectorStore.upsert()-->  stored in Qdrant, with {text, source, chunk_index} as payload

query string  --Embedder.embed_one()-->  384-dim query vector
              --QdrantVectorStore.search()-->  top-k {score, payload} hits
              --retrieve()-->  list[RetrievedChunk(text, source, score)]
```

## Chunking — `chunking.py`

```python
def chunk_text(text: str, chunk_size: int = 200, overlap: int = 40) -> list[str]
```

A dependency-free, word-count-based splitter (not token-based — fine for
this project's short mock KB articles, but see the note in
[decisions-and-limitations.md](../decisions-and-limitations.md)). Splits
`text.split()` into windows of `chunk_size` words, advancing by
`chunk_size - overlap` words each step, so consecutive chunks share
`overlap` words — this avoids losing context for a sentence that happens
to fall right on a chunk boundary.

## Embeddings — `embeddings.py`

`Embedder` wraps `sentence_transformers.SentenceTransformer` (model:
`all-MiniLM-L6-v2`, 384-dimensional output). Loaded once per `Embedder`
instance (the model weights, ~90MB, are downloaded from Hugging Face on
first use and cached locally after — see `~/.cache/huggingface/hub`).
Runs entirely on CPU locally; no network call and no cost per embedding
after that first download.

- `embed(texts: list[str]) -> list[list[float]]` — batch embed
- `embed_one(text: str) -> list[float]` — single-string convenience wrapper
- `dimension` — the model's output size (384); passed to Qdrant when
  creating a collection, so it's never hardcoded twice

## Vector store — `vector_store.py`

`QdrantVectorStore` wraps `qdrant_client.QdrantClient` with exactly the
operations this project needs:

- `ensure_collection(vector_size, recreate=False)` — idempotent
  collection setup; `ingest_kb` always passes `recreate=True` so
  re-running ingestion replaces the collection cleanly rather than
  accumulating duplicates
- `upsert(vectors, payloads)` — stores each chunk as a `PointStruct` with
  a random UUID id and its `{text, source, chunk_index}` payload
- `search(query_vector, top_k)` — cosine-similarity nearest-neighbor
  search, returns `[{"score": float, "payload": dict}, ...]`

**The in-memory/real-server duality that makes testing simple**:
```python
QdrantVectorStore(collection_name="...", url=None)   # QdrantClient(location=":memory:") — tests
QdrantVectorStore(collection_name="...", url="http://localhost:6333")  # real server — app
```
Same class, same behavior, no test-only subclass or mock needed — Qdrant's
own client supports both transparently. `tests/test_rag_retrieval.py`
uses the in-memory mode with a handful of inline fixture texts (still
using the *real* embedding model, since ranking quality is exactly what
that test is checking).

## Ingestion — `ingest.py`

```python
def ingest_kb(kb_dir: Path, store: QdrantVectorStore, embedder: Embedder) -> int
```

Reads every `.md` file in `kb_dir`, chunks each one, embeds *all* chunks
from *all* files in a single batched `embedder.embed()` call (cheaper
than one call per chunk), then upserts everything. Returns the total
chunk count. Invoked by [`scripts/ingest_kb.py`](../../scripts/ingest_kb.py)
as a one-off CLI command — re-run it any time `data/kb/` changes.

## Retrieval — `retriever.py`

```python
@dataclass
class RetrievedChunk:
    text: str
    source: str   # the KB filename this chunk came from — the "citation"
    score: float  # cosine similarity, higher = more relevant

def retrieve(query, store, embedder, top_k=3) -> list[RetrievedChunk]
```

Embeds the query, searches the store, and maps raw Qdrant hits into typed
`RetrievedChunk` objects. This is the function both `POST /rag/query`
(directly) and the agent loop's `retrieve` node (via a small closure in
`app/api/routes.py::get_agent_graph`) call — one retrieval implementation,
two callers.

## Known limitation: `top_k` sourcing is coarse

The agent's `sources` field in `/support/request` responses lists *every*
retrieved chunk's filename, not just the ones the drafted answer actually
cited in its text — e.g. a billing-related draft may still list
`account_deletion.md` in `sources` if that chunk happened to rank in the
top 3 without being used. Acceptable for a demo; a production system
might cross-check citations mentioned in the draft text against the
retrieved set. See [decisions-and-limitations.md](../decisions-and-limitations.md).
