# Plan — Roadmap

Высокоуровневый план работ по фазам. Детализация задач — в
[tasks.md](./tasks.md), активная доска — в [current-sprint.md](./current-sprint.md).

## Phase D-1 — Foundation (done)
**Срок:** 2026-04-12 – 2026-04-13
**Статус:** ✅ Done

- Построен Advanced Search Pipeline (D-01): hybrid BM25+Vector через RRF,
  cross-encoder reranker (lazy), query expansion (dict + LLM).
- Docker обёртка: `app` + `ollama` сервисы, `src:/app/src` bind mount для dev.
- Полная документация: `project.md`, `architecture.md`, `context-dump.md`,
  `search-spec.md`, `tech-stack.md`, `db-schema.md`, `ui-kit.md`,
  `legacy-warning.md`, `instructions.md`, `tasks.md`, `change-request*.md`,
  `links.md`, `testing.md`, `plan.md`, `ideas.md`, `discuss.md`, `README.md`
  (индекс), `contracts/mcp-server.md`.
- 34 теста (unit + integration), без зависимости от faiss в тестах.
- Починены 2 legacy бага (B-01, B-02).

## Phase D-2 — Observability (next)
**Срок:** ориентировочно апрель 2026
**Цель:** научиться мерить качество ответов и не терять историю запросов.

| Задача | ID | Детали |
|---|---|---|
| Лог запросов в JSONL | D-02 | `src/logs/queries.jsonl` append-only, поля: `ts`, `query`, `expanded`, `top_chunks`, `answer`, `sources`, `mcp_used`, `mcp_tool` |
| Metrics middleware | D-04 | `score@1`, `recall@5`, `mrr` → SQLite |
| Runtime A/B флаги | D-05 | переключать `HYBRID_ENABLED` / `FUSION_STRATEGY` / `RERANKER_ENABLED` без рестарта |

Критерий выхода: можно сравнить две конфигурации pipeline на одном корпусе.

## Phase C-1 — Tech debt batch 1 (parallel with D-2)
**Срок:** постепенно

| Задача | ID | LW |
|---|---|---|
| Единый `get_embedding_model()` (`functools.lru_cache`) | C-02 | LW-002 |
| Persisted BM25 (`bm25.pkl`) | D-03 | LW-001's twin |
| Explicit `reset_pipeline()` вместо identity-check | C-04 | LW-004 |
| `PROMPT_PROFILES` dict в config | C-09 | LW-009 |

Цель: убрать верхние записи из `legacy-warning.md` без расширения фич.

## Phase D-3 — Quality (optional)
**Срок:** Q2 2026

| Задача | ID | Детали |
|---|---|---|
| Reranker через ONNX | D-06 | заменить HF CrossEncoder → optimum.onnxruntime |
| Промпт-профили | D-07 | security / HR / dev пресеты |
| MCP `semantic_search_documents` | C-01 | новый инструмент рядом со старым, старый deprecated |

## Phase D-4 — Infra
**Срок:** когда будет >1 разработчика

| Задача | ID | Детали |
|---|---|---|
| CI-пайплайн GitHub Actions | D-09 | pytest, ruff, mypy |
| Интеграционные тесты с настоящим FAISS | D-08 | отдельный slow suite |
| Production-образ без bind mount | — | чтобы COPY в Dockerfile не был no-op |

## Milestones

| Майлстоун | Дата (план) | Определение «done» |
|---|---|---|
| M1 — Foundation | 2026-04-13 ✅ | Advanced Pipeline собран и задокументирован |
| M2 — Observability | TBD | Можно померить качество + посмотреть историю запросов |
| M3 — Tech debt -50% | TBD | Половина записей из `legacy-warning.md` закрыта |
| M4 — Quality bake-off | TBD | A/B-сравнение дефолтной и «full» конфигураций на реальном корпусе |
