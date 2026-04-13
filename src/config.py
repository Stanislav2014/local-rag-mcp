# Configuration for Company Knowledge Base Assistant
import os

# Document directory - update this to point to your company documentation
DOCUMENTS_DIR = "./docs"

# Chunking configuration
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100

# Embedding model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# FAISS index paths (relative to src directory)
FAISS_INDEX_PATH = "index.faiss"
CHUNKS_PATH = "chunks.pkl"

# Ollama configuration (env-overridable so Docker compose can point to the
# 'ollama' service container instead of localhost).
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# RAG retrieval configuration
TOP_K = 5

# === Advanced search pipeline ===
HYBRID_ENABLED = True
FUSION_STRATEGY = "rrf"          # "rrf" | "weighted"
RRF_K = 60
N_VEC = 50
N_BM25 = 50
N_HYBRID = 20                    # top-N после fusion (вход реранкера)

RERANKER_ENABLED = False         # включить, когда модель скачана
RERANKER_MODEL = "BAAI/bge-reranker-base"

QUERY_EXPANSION_ENABLED = True
QUERY_EXPANSION_MAX_LEN = 4
