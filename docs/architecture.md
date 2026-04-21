# Architecture

Архитектурный разрез `local-rag-mcp` и **edge cases**, которые эту архитектуру
формируют. Этот документ отвечает на вопрос: *«почему всё устроено именно так,
а не иначе?»*.

## Общая схема

```
┌──────────────────────────────────────────────────────────────────┐
│                       USER (CLI / MCP client)                   │
└──────────────────┬───────────────────────────┬───────────────────┘
                   │                           │
                   ▼                           ▼
        ┌────────────────────┐       ┌─────────────────────┐
        │ CompanyKBAssistant │       │   MCP Server stdio  │
        │   src/assistant.py │       │    src/mcp/server.py│
        └─────────┬──────────┘       │ read_document       │
                  │                  │ list_documents      │
                  ▼                  │ search_documents    │
   ┌────────────────────────────┐    └─────────────────────┘
   │   Advanced Search Pipeline  │
   │     src/rag/query.retrieve  │
   │                             │
   │  [1] QueryExpander          │
   │  [2] HybridSearchEngine     │
   │      └─ BM25 + FAISS        │
   │      └─ RRF / Weighted      │
   │  [3] CrossEncoderReranker   │
   └──────────────┬──────────────┘
                  ▼
        ┌────────────────────┐
        │   Ollama (LLM)     │
        │   qwen3:0.6b       │
        └────────────────────┘
```

## Ключевые архитектурные решения

### 1. Pipeline как композиция независимых модулей
- `QueryExpander`, `HybridSearchEngine`, `CrossEncoderReranker` — **независимые
  классы** с узким API.
- Каждый этап включается/выключается флагом в `src/config.py`.
- Деградация мягкая: любой уровень можно отключить, pipeline останется работоспособным.

### 2. Dependency Injection для векторного поиска
- `HybridSearchEngine` принимает `vector_search: Callable[[query, k], list[dict]]`.
- Благодаря этому юнит-тесты не требуют faiss / sentence-transformers.
- Та же абстракция позволяет заменить FAISS на любой другой backend без правки гибридки.

### 3. Lazy load тяжёлых моделей
- Cross-encoder загружается только при первом `rerank` и только при `enabled=True`.
- Это позволяет `pytest` и Docker-сборке обходиться без скачивания 1+ GB модели.

### 4. Сохранение контракта MCP
- `src/mcp/server.py` намеренно не тронут. Клиенты, использующие `read_document`,
  `list_documents`, `search_documents`, продолжают работать без изменений.
- Поиск в MCP идёт **по имени файла** — это legacy, но переименовывать нельзя.

### 5. Конфиг как единственная точка правды
- Все настройки (модель, флаги pipeline, размеры top-K, RRF k, пути индекса) —
  в `src/config.py`.
- `OLLAMA_URL` / `OLLAMA_MODEL` / `OLLAMA_HOST` — env-overridable (для Docker).

---

## Edge Cases

Эти случаи **уже учтены** в коде. Если добавляете фичу — проверьте, что ни один
не сломался.

| # | Случай | Что должно произойти | Тест |
|---|---|---|---|
| 1 | Запрос из **точного токена** (`403 Forbidden`, `sqli`) | BM25 поднимает точно совпавший чанк; RRF выводит его выше чисто-семантических соседей | `test_search_engine.py::test_finds_exact_token_query_via_bm25` |
| 2 | Короткая **аббревиатура** (`sqli`, `xss`, `csrf`) | `QueryExpander` добавляет расшифровку из словаря, оригинальный токен сохраняется | `test_query_expansion.py::test_known_abbreviation_expands` |
| 3 | Запрос на **кириллице** (русский) | LLM-rewrite пропускается (маленькие модели «переводят» в кривой английский и ломают матч). Dict по-прежнему работает | `query_expansion.py` (`q.isascii()` гейт) |
| 4 | **Длинный** запрос (`>4` токенов) | Расширение пропускается полностью | `test_query_expansion.py::test_long_query_passthrough` |
| 5 | LLM-клиент **ошибается** при expansion | Возвращаем исходный запрос | `test_query_expansion.py::test_llm_failure_returns_original` |
| 6 | Cross-encoder **отключен** | `rerank` возвращает первые `top_k` кандидатов без сортировки | `test_reranker.py::test_disabled_returns_first_top_k` |
| 7 | Cross-encoder **упал** при predict | Fallback к порядку RRF, warning в лог | `test_reranker.py::test_model_failure_falls_back_to_input_order` |
| 8 | **Пустой корпус** (нет чанков) | `retrieve()` возвращает `[]`, не падает | `test_search_engine.py::test_empty_corpus` |
| 9 | **Пустой запрос** в BM25 / RRF / expander | Возвращаются пустые структуры | `test_bm25::test_empty_query_returns_empty`, `test_rrf::test_empty_inputs` |
| 10 | Документ с одинаковым текстом в двух индексах (BM25+vec) | Дедупликация по `(source, chunk_id)` или `(source, text)` | `test_rrf_fuse::test_dedup_uses_text_source_when_chunk_id_missing` |
| 11 | FAISS индекс **не существует** при старте | `_ensure_index_exists()` строит его из документов автоматически | `rag/query.py::_ensure_index_exists` |
| 12 | Индекс устарел после добавления документа | `python main.py build-index` пересобирает; `reset_pipeline()` очищает кэш | `rag/query.py::reset_pipeline` |
| 13 | MCP-клиент не поднялся | Assistant печатает warning и работает без MCP-инструментов | `assistant.py::_init_mcp` |
| 14 | LLM выдал битый JSON при decide-MCP | Возвращаем `(None, None)` → MCP не вызывается | `assistant.py::_llm_decide_mcp_usage` |
| 15 | Запрос к ollama когда сервис недоступен | Exception прокидывается наверх в CLI (видно пользователю) | — |
| 16 | Unicode в именах файлов (русские PDF) | Работает — FAISS хранит `source` как строку Python, BM25 — тоже | проверено e2e |
| 17 | Индекс на хосте должен переживать `docker compose run --rm` | Bind-mount `./src:/app/src` в compose | `docker-compose.yml` |
| 18 | Реранкер **ниже** fusion-скора — не теряем кандидатов | `rerank()` всегда возвращает **не больше** `top_k`, но сам кандидат уже содержит `score` + `rerank_score` | `test_reranker.py::test_top_k_truncation` |

## Явно НЕ учтено (backlog)

См. [`legacy-warning.md`](./legacy-warning.md) — там тех-долг и костыли.
