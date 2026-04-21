# Tech Stack

Полный список технологий, библиотек и сервисов, на которых держится
`local-rag-mcp`. Обновляется при любом изменении `src/requirements.txt` или
`docker-compose.yml`.

## Runtime

| Слой | Технология | Версия / примечание |
|---|---|---|
| Язык | Python | 3.12 (`python:3.12-slim`) |
| Контейнеризация | Docker + Docker Compose | v29+ / Compose v2.31+ |
| Виртуальное окружение (dev) | virtualenv | любой venv |

## RAG / Поиск

| Компонент | Библиотека | Где используется |
|---|---|---|
| Эмбеддинги | `sentence-transformers` (all-MiniLM-L6-v2, 384-dim) | `src/rag/embed.py`, `src/rag/query.py` |
| Векторный индекс | `faiss-cpu` (`IndexFlatIP` + `normalize_L2` ≡ cosine) | `src/rag/build_index.py`, `src/rag/query.py` |
| Лексический поиск | `rank_bm25` (`BM25Okapi`) | `src/rag/search_engine.py` |
| Fusion | RRF + Weighted Sum (свой код) | `src/rag/search_engine.py` |
| Reranker | `sentence-transformers.CrossEncoder` + `BAAI/bge-reranker-base` (lazy load) | `src/rag/reranker.py` |
| Токенизация для chunking | `tiktoken` (`cl100k_base`), окно 700 / overlap 100 | `src/rag/chunk.py` |

## LLM

| Слой | Стэк |
|---|---|
| Inference | `ollama` (Docker-образ `ollama/ollama:latest`) |
| Python-клиент | `ollama` (HTTP) + `requests` |
| Модель (по умолчанию) | `qwen3:0.6b` — маленькая, для dev |
| Альтернатива для RU | `qwen2.5:7b` (лучше с русским) |

## MCP (Model Context Protocol)

| Роль | Библиотека |
|---|---|
| Сервер (stdio) | `fastmcp` |
| Клиент | subprocess + ручной JSON-RPC (`src/mcp/client.py`) |
| Инструменты | `read_document`, `list_documents`, `search_documents` (по имени файла) |

## Документы

| Формат | Библиотека |
|---|---|
| `.md`, `.txt` | stdlib |
| `.pdf` | `pypdf` |
| `.docx` | `python-docx` |

## CLI / UX

- `rich` — markdown-рендер ответов в интерактивном режиме.

## Тесты

- `pytest`, `pytest-asyncio`, `unittest.mock` — 34 теста (unit + integration).
- Юнит-тесты построены так, чтобы **не требовать** faiss и sentence-transformers
  (vector-search внедряется через DI).

## Dev tooling

- `virtualenv` — локальный dev (система не даёт `python3 -m venv`).
- `gh` — git/GitHub операции.

## Взаимодействия (кратко)

```
user → CLI (main.py) → CompanyKBAssistant.query()
                          │
                          ├─ QueryExpander      (dict + LLM rewrite)
                          ├─ HybridSearchEngine (BM25 + Vector → RRF)
                          ├─ CrossEncoderReranker (lazy)
                          │
                          ├─ _llm_decide_mcp_usage (ollama JSON-mode)
                          ├─ MCPClient → mcp/server.py (stdio)
                          │
                          └─ ask_llm (ollama /api/generate)
```

Подробный дамп взаимодействий — в [`context-dump.md`](./context-dump.md).
