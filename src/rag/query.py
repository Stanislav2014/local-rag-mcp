import faiss
import pickle
import requests
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    FAISS_INDEX_PATH,
    CHUNKS_PATH,
    EMBEDDING_MODEL,
    OLLAMA_URL,
    OLLAMA_MODEL,
    TOP_K,
    HYBRID_ENABLED,
    FUSION_STRATEGY,
    RRF_K,
    N_VEC,
    N_BM25,
    N_HYBRID,
    RERANKER_ENABLED,
    RERANKER_MODEL,
    QUERY_EXPANSION_ENABLED,
    QUERY_EXPANSION_MAX_LEN,
)
from rag.search_engine import HybridSearchEngine
from rag.query_expansion import QueryExpander
from rag.reranker import CrossEncoderReranker

model = SentenceTransformer(EMBEDDING_MODEL)

# Global variables for index and chunks
index = None
chunks = []
_hybrid_engine: HybridSearchEngine | None = None
_query_expander: QueryExpander | None = None
_reranker: CrossEncoderReranker | None = None


def _ensure_index_exists():
    """Ensure FAISS index exists, build it if it doesn't."""
    global index, chunks
    
    # Resolve paths relative to src directory
    src_dir = Path(__file__).parent.parent
    index_path = src_dir / FAISS_INDEX_PATH
    chunks_path = src_dir / CHUNKS_PATH
    
    # Check if index exists
    if index_path.exists() and chunks_path.exists():
        try:
            index = faiss.read_index(str(index_path))
            with open(chunks_path, "rb") as f:
                chunks = pickle.load(f)
            return True
        except Exception as e:
            print(f"⚠️  Warning: Error loading existing index: {e}")
            print("Rebuilding index...")
    
    # Index doesn't exist or failed to load, build it
    print("📦 Index not found. Building index from documents...")
    try:
        from rag.build_index import build_index
        build_index()
        
        # Load the newly created index
        if index_path.exists() and chunks_path.exists():
            index = faiss.read_index(str(index_path))
            with open(chunks_path, "rb") as f:
                chunks = pickle.load(f)
            print("✅ Index built and loaded successfully")
            return True
        else:
            print("❌ Failed to build index. No documents found or error occurred.")
            from config import DOCUMENTS_DIR
            docs_path = src_dir / DOCUMENTS_DIR
            print(f"   Check that documents exist in: {docs_path}")
            return False
    except Exception as e:
        print(f"❌ Error building index: {e}")
        import traceback
        traceback.print_exc()
        return False


# Initialize index on module load
_ensure_index_exists()


def _vector_search(query: str, k: int) -> list[dict]:
    """Inner FAISS vector search used by both the legacy and hybrid paths."""
    if index is None or len(chunks) == 0:
        return []
    q_emb = model.encode([query])
    faiss.normalize_L2(q_emb)
    scores, ids = index.search(q_emb, k)
    out = []
    for rank, (idx, score) in enumerate(zip(ids[0], scores[0]), start=1):
        if idx < 0 or idx >= len(chunks):
            continue
        out.append({**chunks[idx], "score": float(score), "rank": rank})
    return out


def _get_hybrid_engine() -> HybridSearchEngine:
    global _hybrid_engine
    if _hybrid_engine is None:
        _hybrid_engine = HybridSearchEngine(
            chunks=chunks,
            vector_search=_vector_search,
            k_rrf=RRF_K,
            n_vec=N_VEC,
            n_bm25=N_BM25,
            strategy=FUSION_STRATEGY,
        )
    return _hybrid_engine


def _get_query_expander() -> QueryExpander:
    global _query_expander
    if _query_expander is None:
        try:
            import ollama
            client = ollama.Client()
        except Exception:
            client = None
        _query_expander = QueryExpander(
            llm_client=client,
            model=OLLAMA_MODEL,
            max_len=QUERY_EXPANSION_MAX_LEN,
        )
    return _query_expander


def _get_reranker() -> CrossEncoderReranker:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker(
            model_name=RERANKER_MODEL,
            enabled=RERANKER_ENABLED,
        )
    return _reranker


def reset_pipeline():
    """Reset cached pipeline components (used after rebuilding the index)."""
    global _hybrid_engine, _query_expander, _reranker
    _hybrid_engine = None
    _query_expander = None
    _reranker = None


def retrieve(query: str, k: int = TOP_K, with_scores: bool = False):
    """Retrieve relevant chunks for a query.

    Pipeline:
      1. Query expansion  (short queries / abbreviations)
      2. Hybrid search    (BM25 ⊕ Vector → RRF)
      3. Cross-encoder reranker (top-N → top-K)

    Each stage is independently switchable via ``config.py`` and has a
    graceful fallback so that the legacy path keeps working unchanged.
    Per-chunk similarity scores are logged at every stage.
    """
    if index is None or len(chunks) == 0:
        if not _ensure_index_exists():
            return []
    if index is None or len(chunks) == 0:
        return []

    # ---- 1. Query expansion ------------------------------------------------
    if QUERY_EXPANSION_ENABLED:
        original = query
        query = _get_query_expander().expand(query)
        if query != original:
            print(f"📝 query expanded: {original!r} → {query!r}")

    # ---- 2. Search ---------------------------------------------------------
    if HYBRID_ENABLED:
        engine = _get_hybrid_engine()
        # keep the engine in sync with the (lazily) loaded chunks list
        if engine.chunks is not chunks:
            engine.chunks = chunks
            from rag.search_engine import BM25Index
            engine.bm25 = BM25Index(chunks)
        candidates = engine.search(query, k=N_HYBRID)
        print(f"🔎 hybrid({FUSION_STRATEGY}) → {len(candidates)} candidates")
    else:
        candidates = _vector_search(query, k=N_HYBRID)
        print(f"🔎 vector → {len(candidates)} candidates")

    for rank, c in enumerate(candidates[:10], start=1):
        print(f"  [{rank:>2}] score={c.get('score', 0):.4f}  source={c.get('source','?')}")

    # ---- 3. Rerank ---------------------------------------------------------
    reranker = _get_reranker()
    final = reranker.rerank(query, candidates, top_k=k)
    if reranker.enabled:
        print(f"♻️  rerank → top-{len(final)}")
        for rank, c in enumerate(final, start=1):
            print(f"  [{rank:>2}] rerank_score={c.get('rerank_score', 0):.4f}  source={c.get('source','?')}")

    if with_scores:
        return final
    return [{k_: v for k_, v in c.items() if k_ not in {"score", "rank", "rerank_score"}} for c in final]


def build_prompt(query, contexts):
    """Build prompt with retrieved context."""
    if not contexts:
        return f"""
<role>You are a helpful assistant that answers questions about company information.</role>
<instructions>Answer the question based on your general knowledge. If you don't know, say so.</instructions>

<query>
{query}
</query>

<assistant>
"""

    context_text = "\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}"
        for c in contexts
    )

    return f"""
<role>You are a helpful assistant that answers questions about company information.</role>
<instructions>Answer the question ONLY based on the context provided below. If the answer is not in the context, say "I don't have that information in the knowledge base."</instructions>

<context>
{context_text}
</context>

<query>
{query}
</query>

<assistant>
"""


def ask_llm(prompt):
    """Query Ollama LLM."""
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
    )
    return response.json()["response"]


def ask(query: str):
    """Answer a question using RAG."""
    contexts = retrieve(query)
    prompt = build_prompt(query, contexts)
    return ask_llm(prompt), contexts


if __name__ == "__main__":
    while True:
        q = input("\n❓ Question: ")
        if q.lower() in {"exit", "quit"}:
            break
        print("\n🤖 Answer:\n")
        answer, sources = ask(q)
        print(answer)
        if sources:
            print("\n📚 Sources:")
            for src in sources:
                print(f"  - {src['source']}")
