# Context Dump — как работают и взаимодействуют компоненты

> Дамп всей внутренней механики приложения. Цель — чтобы новый разработчик
> (или будущая ИИ-сессия) могли восстановить полную картину без чтения кода.

## 0. Глоссарий

- **Chunk** — фрагмент исходного документа после tiktoken-токенизации (700 ток.,
  overlap 100). Структура: `{"text": str, "source": str (rel path), "chunk_id": int}`.
- **RAG** — Retrieval-Augmented Generation: ищем релевантные чанки → подмешиваем
  в промпт LLM.
- **MCP** — Model Context Protocol: stdio JSON-RPC «инструменты», к которым LLM
  обращается во время диалога (`read_document`, `list_documents`, `search_documents`).
- **RRF** — Reciprocal Rank Fusion, формула `Σ 1/(k+rank)`.
- **Pipeline** — последовательность Query Expansion → Hybrid Search → Reranker.

---

## 1. Карта файлов и ответственности

| Файл | Что делает | С чем взаимодействует |
|---|---|---|
| `src/config.py` | Все настройки: пути, модели, флаги pipeline | импортируется почти отовсюду |
| `src/main.py` | Интерактивный CLI, точка входа `python main.py` | `assistant.CompanyKBAssistant` |
| `src/assistant.py` | Оркестрация: RAG → решение про MCP → LLM | `rag.query`, `mcp.client`, `ollama` |
| `src/rag/ingest.py` | Загружает `.txt/.md/.pdf/.docx` из `DOCUMENTS_DIR` | `pypdf`, `python-docx` |
| `src/rag/chunk.py` | tiktoken-токенизация, окно `CHUNK_SIZE=700`, `overlap=100` | `tiktoken` |
| `src/rag/embed.py` | `SentenceTransformer("all-MiniLM-L6-v2").encode(...)` | sentence-transformers |
| `src/rag/build_index.py` | Собирает FAISS-индекс, сохраняет `index.faiss` + `chunks.pkl` | ingest/chunk/embed + faiss |
| `src/rag/query.py` | **Главная точка retrieve**: pipeline + `ask_llm()` | search_engine, query_expansion, reranker, faiss, ollama |
| `src/rag/search_engine.py` | `tokenize`, `BM25Index`, `rrf_fuse`, `HybridSearchEngine` | `rank_bm25` |
| `src/rag/query_expansion.py` | `QueryExpander` (dict + LLM rewrite) | (опц.) `ollama` |
| `src/rag/reranker.py` | `CrossEncoderReranker` с lazy-loading и fallback | (опц.) `sentence-transformers` |
| `src/mcp/server.py` | FastMCP-сервер с 3 инструментами | `fastmcp` |
| `src/mcp/client.py` | stdio JSON-RPC клиент к серверу | `subprocess` |
| `tests/conftest.py` | Фикстуры `sample_chunks`, `fake_vector_search` | pytest |

---

## 2. Поток данных при offline-индексации

```
DOCUMENTS_DIR (./docs/)
       │
       ▼  rag.ingest.ingest_documents()
List[{"path","text"}]
       │
       ▼  rag.chunk.chunk_documents()  (CHUNK_SIZE=700, OVERLAP=100, cl100k_base)
List[{"text","source","chunk_id"}]
       │
       ▼  rag.embed.embed_chunks()  (all-MiniLM-L6-v2)
np.ndarray (N, 384)
       │
       ▼  rag.build_index.build_index()
faiss.IndexFlatIP(384) + normalize_L2
       │
       ▼  pickle.dump
src/index.faiss  +  src/chunks.pkl
```

Запускается командой `python main.py build-index` или автоматически при первом
вызове `retrieve()` если индекс отсутствует (см. `_ensure_index_exists`).

---

## 3. Поток данных при online-запросе (Advanced Pipeline)

```
user query
   │
   ▼  CompanyKBAssistant.query()
   │
   ├──► retrieve(query)  ───────────────────────────────────────────────┐
   │       │                                                            │
   │       ▼  QueryExpander.expand(query)        [config: QUERY_EXPANSION_ENABLED]
   │     "sqli" → "sqli SQL Injection vulnerability"
   │       │
   │       ▼  HybridSearchEngine.search(query, k=N_HYBRID)
   │       │    ├── BM25Index.search → top-N_BM25
   │       │    ├── _vector_search (FAISS) → top-N_VEC
   │       │    └── rrf_fuse([...], k_rrf=60)
   │     20 candidates
   │       │
   │       ▼  CrossEncoderReranker.rerank(query, cands, top_k=TOP_K)
   │     5 final chunks
   │       │
   │       ▼  печать score / source каждого этапа
   │       │
   │       └──► return chunks (cleaned: без score/rank/rerank_score)
   │                                                                    │
   ├──► _llm_decide_mcp_usage(query, contexts)  → JSON {use_mcp, tool, args}
   │       (qwen3:0.6b через ollama-python)
   │
   ├──► (опционально) MCPClient.call_tool(tool, args)  ─► stdio JSON-RPC
   │       MCPClient.proc.stdin  ──►  mcp/server.py mcp.run()
   │       mcp/server.py @mcp.tool function ──►  result
   │
   ├──► build_prompt(query, ctx) [+ <additional_info_from_mcp_tool>]
   │
   ├──► ask_llm(prompt)  ─►  POST OLLAMA_URL  (http://localhost:11434)
   │       JSON {"model": OLLAMA_MODEL, "prompt": …, "stream": false}
   │
   └──► return {answer, sources, mcp_used, mcp_tool}
```

---

## 4. Подробное описание ключевых компонентов

### 4.1 `rag/query.retrieve()` — главный entrypoint
- **Сигнатура**: `retrieve(query: str, k: int = TOP_K, with_scores: bool = False)`.
- **Состояние**: ленивый кэш `_hybrid_engine`, `_query_expander`, `_reranker`,
  `_ensure_index_exists()` загружает `index` и `chunks` из pickle.
- **Логирование**: каждый чанк — `[rank] score=…  source=…`. После expansion
  выводится `📝 query expanded: 'sqli' → 'sqli SQL Injection vulnerability'`.
- **Очистка результата**: возвращаются чанки без служебных полей `score`,
  `rank`, `rerank_score`, чтобы не сломать legacy потребителей (`assistant.py`).
- **Обратная совместимость**: если флаги pipeline = `False`, поведение
  деградирует к чисто векторному top-K.

### 4.2 `rag/search_engine.HybridSearchEngine`
- **Зависимости через DI**: `vector_search: Callable[[query, k], list[chunk]]`.
  Это позволяет тестировать engine без FAISS / sentence-transformers
  (см. `tests/conftest.py::fake_vector_search`).
- **BM25Index** строится сразу из чанков, без сериализации (быстро для
  ≤50K чанков; для больших корпусов можно добавить `bm25.pkl` рядом с
  `chunks.pkl`).
- **Стратегии fusion**:
  - `rrf` — `Σ 1/(k_rrf + rank)`. Рекомендуется по умолчанию: устойчиво к
    разным шкалам, не требует нормализации.
  - `weighted` — min-max нормализация скоров каждого источника + взвешенная
    сумма. Полезно, когда нужна интерпретируемость веса BM25 vs Vector.
- **Дедупликация**: по `(source, chunk_id)` или `(source, text)` если
  `chunk_id` отсутствует.

### 4.3 `rag/query_expansion.QueryExpander`
- Порядок проверки: длина → словарь `ABBREVIATIONS` → LLM.
- **Никогда не теряет оригинал**: возвращает `{original} {expansion}`. Это
  важно, чтобы BM25 продолжил матчить редкий токен.
- LLM-вызов поддерживает оба формата: `dict` (ollama-python) и объекты с
  `.message.content` — для удобства тестирования через MagicMock.
- **Graceful failure**: любая ошибка LLM → возвращаем оригинал.

### 4.4 `rag/reranker.CrossEncoderReranker`
- **Lazy load**: реальная модель тянется только в момент первого `rerank`,
  и только если `enabled=True`. Это позволяет:
  - запускать unit-тесты без скачивания 1+ ГБ;
  - собирать Docker-образ без pre-download;
  - включать reranker через флаг в `config.py` после `ollama pull`-аналога.
- **Fallback** при `enabled=False`: возвращает первые `top_k` кандидатов.
- **Fallback** при ошибке predict: то же самое + warning в лог.

### 4.5 `assistant.CompanyKBAssistant`
- Инициализирует MCP-клиент (subprocess к `mcp/server.py`).
- Вызывает `retrieve` (теперь = pipeline).
- Спрашивает LLM, нужно ли вызывать MCP-инструмент (см.
  `_llm_decide_mcp_usage`). Это **отдельный** LLM call с маленьким
  decision-промптом.
- Если LLM выбрал tool → дёргает MCP, добавляет результат в финальный промпт.
- Финальный `ask_llm()` через `requests` POST в `http://localhost:11434/api/generate`.

### 4.6 MCP сервер и клиент
- **Сервер** (`mcp/server.py`) — `FastMCP("doc-tools")`, 3 инструмента:
  - `read_document(file_path)` — read-only, проверяет, что путь внутри
    `DOCUMENTS_DIR`.
  - `list_documents()` — рекурсивно листает поддерживаемые расширения.
  - `search_documents(query)` — **по имени файла** (не по содержимому);
    название историческое, мы его сохраняем для совместимости.
- **Клиент** (`mcp/client.py`) — простой `subprocess.Popen(...)` + JSON-RPC по
  stdin/stdout. Выполняет `initialize` при старте, держит счётчик `next_id`,
  потокобезопасен через `threading.Lock`.

### 4.7 Конфигурация (`src/config.py`)
Все «магические числа» здесь. Новые ключи:
```
HYBRID_ENABLED, FUSION_STRATEGY, RRF_K, N_VEC, N_BM25, N_HYBRID,
RERANKER_ENABLED, RERANKER_MODEL,
QUERY_EXPANSION_ENABLED, QUERY_EXPANSION_MAX_LEN.
```

---

## 5. Тесты

| Файл | Уровень | Что проверяет |
|---|---|---|
| `tests/unit/test_search_engine.py` | unit | `tokenize`, `BM25Index`, `rrf_fuse`, `HybridSearchEngine` (включая weighted и пустые корпуса) |
| `tests/unit/test_query_expansion.py` | unit | dict-расширение, длинные запросы, LLM-мок и failure-режим |
| `tests/unit/test_reranker.py` | unit | enabled/disabled, top-k truncation, model failure → fallback |
| `tests/integration/test_pipeline.py` | integration | Полный pipeline без FAISS на двух «адверсариальных» запросах |

Все тесты не требуют ни faiss, ни sentence-transformers, поэтому suite
выполняется за ≈0.1 с.

```bash
.venv/bin/pytest tests -q
# 34 passed in 0.09s
```

---

## 6. Точки расширения

- **Persisting BM25** — для огромных корпусов сохранить `bm25.pkl` в
  `build_index.py`, грузить в `_get_hybrid_engine`.
- **Reranker через ONNX** — заменить `sentence_transformers.CrossEncoder` на
  `optimum.onnxruntime.ORTModelForSequenceClassification`, без изменений
  публичного API.
- **Метрики** — добавить middleware, который пишет `score@1, recall@5` для
  каждого запроса в SQLite/Prometheus.
- **A/B сравнение** — флаги в `config.py` плюс лог в JSON для каждого запроса.

---

## 7. Что НЕ изменилось (контракт)

- MCP-инструменты `read_document`, `list_documents`, `search_documents` —
  идентичны legacy-версии.
- Внешний интерфейс `assistant.CompanyKBAssistant.query(user_query)` —
  возвращает `{answer, sources, mcp_used, mcp_tool}`.
- `rag.query.ask(query)`, `rag.query.build_prompt`, `rag.query.ask_llm` —
  без изменений.
- Пути `index.faiss` и `chunks.pkl` — те же.

Это означает: можно ставить новую ветку как drop-in замену старой и проверять
качество A/B-сравнением, без правок у клиентов.
