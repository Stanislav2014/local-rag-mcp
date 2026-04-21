# Tasks — Master Catalog

Все задачи проекта с префиксами по фазам (manbot-style). Это **master-каталог**,
а не активная доска. Активная доска — [current-sprint.md](./current-sprint.md).

Нумерация: сквозная внутри фазы. Пропуски разрешены.

## Phase A — Критичные дефекты (P0/P1)

_Пусто — открытых критичных дефектов нет._

## Phase B — Исправленные баги (история)

| ID | Тикет | Описание | Commit | Дата | Статус |
|---|---|---|---|---|---|
| B-01 | LR-0002 | Мёртвый рекурсивный путь в `rag.ingest.ingest_documents` (падение `TypeError: ingest_documents() takes 0 positional arguments but 1 was given` при повторном обходе) | `ed6951e` | 2026-04-13 | ✅ |
| B-02 | LR-0003 | `.gitignore` блокировал `docs/*.md` и корневой `README.md` (правила `docs/*.md`, `/**.md`) | `ed6951e` | 2026-04-13 | ✅ |

## Phase C — Технический долг

Привязан 1-к-1 к записям в [legacy-warning.md](./legacy-warning.md). ID в колонке
«LW» — это ID там.

| ID | LW | Тикет | Описание | Приоритет | Статус |
|---|---|---|---|---|---|
| C-01 | LW-001 | LR-0201 | MCP `search_documents` ищет по имени файла, а не по содержимому (legacy контракт) | ⚠ | Open |
| C-02 | LW-002 | LR-0202 | Дублированная загрузка `SentenceTransformer` в `embed.py` и `query.py` (2× RAM) | ⚠ | Open |
| C-03 | LW-003 | LR-0203 | `QueryExpander` полностью отключает LLM-rewrite для non-ASCII запросов | 🧟 | Open |
| C-04 | LW-004 | LR-0204 | `HybridSearchEngine` пересинхронизирует чанки через `is not` identity-check | 🧟 | Open |
| C-05 | LW-005 | LR-0205 | `chunks.pkl` — pickle, не JSON/Parquet (непереносимо) | 🧟 | Open |
| C-06 | LW-006 | — | Огромный `.gitignore` с конфликтующими правилами (уже частично исправлено в B-02) | 🧟 | Partially resolved |
| C-07 | LW-007 | LR-0207 | Дефолт `qwen3:0.6b` даёт плохие ответы на русском | 🧟 | Open (design choice) |
| C-08 | LW-008 | LR-0208 | Cross-encoder reranker выключен по умолчанию (чтобы не тянуть 400 MB модель в dev) | 🧟 | Open (design choice) |
| C-09 | LW-009 | LR-0209 | `build_prompt` — один системный промпт для всех ролей | ⚠ | Open |
| C-10 | LW-010 | LR-0210 | CLI не сохраняет историю запросов (пользователь не может посмотреть что спрашивал) | ⚠ | Open (→ см. D-02) |

## Phase D — Фичи / enhancements

### D-01 Advanced Search Pipeline
**Тикет:** LR-0001
**Ветка:** `feature/advanced-search-pipeline`
**Статус:** ✅ Done — 2026-04-13, commit `4efedb9` (push), `ed6951e` (initial)
**Описание:** Hybrid BM25+Vector (RRF), Cross-Encoder Reranker (lazy), Query
Expansion (dict + LLM). Сохранён MCP контракт. 34 теста, Docker обёртка,
полная документация. См. [search-spec.md](./search-spec.md) и CR-001 в
[change-request.md](./change-request.md).

### D-02 Append-JSONL лог запросов
**Тикет:** LR-0102
**Статус:** Open (высший приоритет бэклога)
**Описание:** В `src/logs/queries.jsonl` писать каждый запрос пользователя:
`{ts, query, expanded, top_chunks, answer, sources}`. Нужен пользователю как
история + основа для метрик качества.

### D-03 Persisted BM25
**Тикет:** LR-0103
**Статус:** Open
**Зависимость:** blocked by LW-002 (первый запрос не должен тянуть две модели)
**Описание:** Сохранять `bm25.pkl` рядом с `chunks.pkl`, подгружать в
`_get_hybrid_engine`. Для корпусов >50K чанков cold-start заметно быстрее.

### D-04 Metrics middleware
**Тикет:** LR-0104
**Статус:** Open
**Описание:** `score@1`, `recall@5`, `mrr` на каждом запросе → SQLite.
Нужно для сравнения `HYBRID_ENABLED=True/False` и `FUSION_STRATEGY=rrf/weighted`.

### D-05 Runtime A/B флаги
**Тикет:** LR-0105
**Статус:** Open
**Описание:** Переключать pipeline без правки `config.py` и перезапуска.

### D-06 Reranker через ONNX
**Тикет:** LR-0106
**Статус:** Open
**Описание:** Заменить `sentence_transformers.CrossEncoder` на
`optimum.onnxruntime.ORTModelForSequenceClassification`. Быстрее на CPU +
меньше памяти.

### D-07 Промпт-профили по роли
**Тикет:** LR-0107
**Статус:** Open
**Зависимость:** C-09 (сначала выделить `PROMPT_PROFILES` dict).
**Описание:** Разные промпты под security / HR / dev контексты.

### D-08 Интеграционные тесты с настоящим FAISS
**Тикет:** LR-0108
**Статус:** Open
**Описание:** Медленный suite (≤30 с), запускать только в CI или по метке.
Ловить регрессии на уровне реальной интеграции FAISS + sentence-transformers.

### D-09 CI-пайплайн GitHub Actions
**Тикет:** LR-0109
**Статус:** Open
**Описание:** pytest, ruff, mypy. Пока тесты гоняются только локально.

## Legend

- ✅ Done
- 🟡 In Progress
- 🔄 In Review
- 🔴 Blocked
- Open — пока не начата
- 🔥 критичный приоритет (ронит прод / data loss / security)
- ⚠ архитектурный долг (нестрашно, но больно рефакторить потом)
- 🧟 стилевой / низкоприоритетный
