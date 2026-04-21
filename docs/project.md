# Project Overview — local-rag-mcp

**Однострочник:** локальный (offline-first) Q&A-ассистент по корпоративной
документации на Python с Advanced Search Pipeline (BM25 + FAISS + RRF +
cross-encoder rerank + query expansion).

## Назначение

Отвечать на вопросы пользователей по их собственной документации (`.md`,
`.txt`, `.pdf`, `.docx`) **без отправки данных во внешние API**. Всё исполнение
локально: эмбеддинги через `sentence-transformers`, LLM через `ollama`.

## Для кого

- Security-инженеры (искать по своему KB «403 Forbidden», «sqli»)
- HR / support-команды (политики, FAQ)
- Инженерные команды (архитектурные записи, ADR, runbook-и)
- Любая ситуация, где нельзя загружать данные в SaaS

## Что умеет

1. **Advanced Search Pipeline**: Query Expansion → Hybrid BM25+Vector через
   RRF → опциональный Cross-Encoder Reranker → top-K → LLM.
2. **MCP-инструменты**: `read_document`, `list_documents`, `search_documents`
   (поиск по имени файла). LLM сам решает, нужен ли инструмент для ответа.
3. **Score-логирование** на всех стадиях pipeline.
4. **Docker**: one-command bootstrap (`docker compose up -d ollama && docker
   compose run --rm app python main.py`).
5. **Graceful fallback**: любой слой pipeline можно отключить флагом в
   `src/config.py`, поведение деградирует мягко.

## Стек (краткий)

- Python 3.12 (Docker: `python:3.12-slim`)
- `sentence-transformers` (`all-MiniLM-L6-v2`) + `faiss-cpu` — векторный поиск
- `rank_bm25` — лексический поиск
- Свой RRF + опционально weighted fusion
- `sentence-transformers.CrossEncoder` (`BAAI/bge-reranker-base`) — reranker (lazy)
- `ollama` (`qwen3:0.6b` по умолчанию) — LLM
- `fastmcp` — MCP-сервер stdio
- `pytest` — 34 теста, ≤100 ms без загрузки FAISS

Подробнее: [tech-stack.md](./tech-stack.md).

## Карта «где что искать»

| Вопрос | Файл(ы) |
|---|---|
| **«Как запустить?»** | `README.md` в корне, `docs/project.md` § запуск ниже |
| **«Какая архитектура?»** | [architecture.md](./architecture.md), [context-dump.md](./context-dump.md) |
| **«Как устроен pipeline поиска?»** | [search-spec.md](./search-spec.md), `src/rag/query.py::retrieve` |
| **«Что известно про тех-долг?»** | [legacy-warning.md](./legacy-warning.md) |
| **«Какой формат у chunks.pkl?»** | [db-schema.md](./db-schema.md) |
| **«Как тестировать?»** | [testing.md](./testing.md) |
| **«Что сейчас в работе?»** | [current-sprint.md](./current-sprint.md) |
| **«Какой общий бэклог?»** | [tasks.md](./tasks.md) |
| **«Как я должен вести новую задачу?»** | [instructions.md](./instructions.md) |
| **«Какой контракт у MCP?»** | [contracts/mcp-server.md](./contracts/mcp-server.md) |
| **«Почему мы сделали X так, а не иначе?»** | [architecture.md](./architecture.md), [impact-analysis.md](./impact-analysis.md) |

## Структура репозитория (краткая)

```
local-rag-mcp/
├── README.md
├── Dockerfile
├── docker-compose.yml
├── docs/                       ← вся документация
├── src/
│   ├── config.py
│   ├── main.py                 ← CLI entry point
│   ├── assistant.py            ← оркестрация RAG + MCP
│   ├── rag/
│   │   ├── ingest.py           ← читает документы
│   │   ├── chunk.py            ← tiktoken + sliding window
│   │   ├── embed.py            ← sentence-transformers
│   │   ├── build_index.py      ← FAISS
│   │   ├── query.py            ← retrieve() = advanced pipeline
│   │   ├── search_engine.py    ← BM25 + RRF + HybridSearchEngine
│   │   ├── query_expansion.py  ← QueryExpander
│   │   └── reranker.py         ← CrossEncoderReranker (lazy)
│   ├── mcp/
│   │   ├── server.py           ← FastMCP stdio — НЕ менять контракт
│   │   └── client.py           ← subprocess JSON-RPC
│   └── docs/                   ← knowledge base (исходные документы)
└── tests/
    ├── unit/                   ← без faiss — ~0.1 s
    └── integration/            ← через DI, тоже без faiss
```

## Запуск (one-liner)

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3:0.6b
docker compose run --rm app python main.py build-index   # один раз
docker compose run --rm app python main.py               # интерактив
```

Подробнее: корневой [`README.md`](../README.md).

## Текущее состояние

- Ветка `feature/advanced-search-pipeline` запушена в `origin`, PR ещё не создан.
- Pipeline собран, 34 теста зелёные, e2e smoke работает через реальную ollama.
- Открытых P0/P1 нет. Backlog — см. [tasks.md](./tasks.md).
