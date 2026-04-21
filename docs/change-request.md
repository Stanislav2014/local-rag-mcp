# Change Request — Active

Здесь живут **реальные данные текущей задачи**. Шаблон — в
[change-request-doc.md](./change-request-doc.md). После merge задачи этот
файл очищается (оставляется только placeholder), запись уходит в `tasks.md`
с ✅.

> **Текущее состояние:** нет активной задачи. Ниже оставлена CR-001
> («Advanced Search Pipeline») как *завершённый пример заполнения* до момента
> появления следующей крупной задачи.

---

## CR-001 Advanced Search Pipeline (completed)
- **Дата:** 2026-04-12 – 2026-04-13
- **Автор:** stanislav
- **Задача:** D-01 (`feature/advanced-search-pipeline`)
- **Фаза:** D
- **Оценка:** S (1-2 дня)
- **Статус:** ✅ Merged → push, commit `4efedb9`

### Motivation (Why)

Legacy `retrieve()` в `rag.query` использовал **только** cosine-search по
векторному индексу. Это давало два провала на реальных запросах:

1. Точные технические токены (`403 Forbidden`, `sqli`) теряются среди
   семантически близких чанков.
2. Короткие аббревиатуры (`xss`, `csrf`) имеют слабый эмбеддинг.

Success criteria:
- BM25 + RRF — запрос с точным токеном находит его первым.
- Query expansion — короткие аббревиатуры расшифровываются перед поиском.
- Cross-encoder reranker доступен как опция, но не ломает существующий flow.
- MCP-контракт не меняется.
- 100% новый код покрыт тестами (unit + integration) без зависимости от faiss
  в тестовой среде.

### Затронутые компоненты
- `src/rag/query.py` — `retrieve()` переписан на 3-этапный pipeline
  (expansion → hybrid → rerank). Добавлены кешированные синглтоны
  `_hybrid_engine`, `_query_expander`, `_reranker` и функция `reset_pipeline()`.
- `src/config.py` — новые флаги `HYBRID_ENABLED`, `FUSION_STRATEGY`, `RRF_K`,
  `N_VEC`, `N_BM25`, `N_HYBRID`, `RERANKER_ENABLED`, `RERANKER_MODEL`,
  `QUERY_EXPANSION_ENABLED`, `QUERY_EXPANSION_MAX_LEN`. `OLLAMA_URL` /
  `OLLAMA_MODEL` переведены на `os.getenv`.
- **Новые файлы:**
  - `src/rag/search_engine.py` — `tokenize`, `BM25Index`, `rrf_fuse`,
    `_weighted_fuse`, `HybridSearchEngine`.
  - `src/rag/query_expansion.py` — `QueryExpander` + словарь `ABBREVIATIONS`.
  - `src/rag/reranker.py` — `CrossEncoderReranker` с lazy load.
- `src/rag/ingest.py` — починен мёртвый рекурсивный путь (`TypeError:
  ingest_documents() takes 0 positional arguments but 1 was given`).
- `src/requirements.txt` — добавлены `rank_bm25>=0.2.2`, `pytest>=8.0.0`.
- **Новые инфра-файлы:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`.
- `.gitignore` — удалены правила `docs/*.md`, `/**.md`, которые блокировали
  новые `docs/` и корневой README.
- `README.md` (корень) — переписан с нуля.
- **Новые docs:** `docs/impact-analysis.md`, `docs/search-spec.md`,
  `docs/context-dump.md`, `docs/session-prompts.md`, `docs/tech-stack.md`,
  `docs/architecture.md`, `docs/db-schema.md`, `docs/links.md`, `docs/ui-kit.md`,
  `docs/current-sprint.md`, `docs/change-request.md`, `docs/legacy-warning.md`,
  + позже расширенная методология: `docs/README.md` (индекс), `docs/project.md`,
  `docs/instructions.md`, `docs/plan.md`, `docs/ideas.md`, `docs/discuss.md`,
  `docs/tasks.md`, `docs/testing.md`, `docs/change-request-doc.md`,
  `docs/docs-setup-prompt.md`, `docs/contracts/mcp-server.md`.
- **Новый каталог** `tests/` — `conftest.py`, `unit/*`, `integration/*`.

### Публичный API
- `rag.query.retrieve(query: str, k: int = TOP_K, with_scores: bool = False)`
  — сигнатура расширена (были только `query`). Старый вызов `retrieve(query)`
  продолжает работать — аргументы со значениями по умолчанию.
- `rag.query.reset_pipeline()` — **новая функция**, инвалидирует кэшированные
  компоненты после пересборки индекса.
- **MCP-инструменты** `read_document`, `list_documents`, `search_documents` —
  **без изменений**. Это жёсткий контракт. См.
  [contracts/mcp-server.md](./contracts/mcp-server.md).
- `assistant.CompanyKBAssistant.query(user_query, verbose=False)` — без
  изменений снаружи.
- `rag.query.build_prompt(query, contexts)` — **поменялось содержание промпта**
  (раньше английский, теперь русский + инструкция отвечать на языке вопроса).
  Вызывающий код не изменился.
- `rag.query.ask(query)`, `rag.query.ask_llm(prompt)` — без изменений.

### Риски
1. **Пересборка индекса:** после pull ветки обязателен
   `python main.py build-index`. Старые `index.faiss` + `chunks.pkl`
   совместимы (тот же формат), но при смене `EMBEDDING_MODEL` надо
   пересобирать.
2. **Скачивание модели cross-encoder:** при `RERANKER_ENABLED=True` первый
   запрос тянет ~400 MB. По умолчанию флаг `False`.
3. **Регресс качества на русском:** LLM-расширение отключено для не-ASCII.
   См. Q-05 в [discuss.md](./discuss.md).
4. **Bind-mount `./src:/app/src` в Docker:** COPY в Dockerfile становится
   no-op. Для production-образа (без dev bind mount) COPY нужен.
5. **BM25 строится в памяти** на каждом cold-start процесса. Для >50K чанков
   медленно. См. D-03 в [tasks.md](./tasks.md).

### Pending action items
_Все закрыты в рамках D-01._

- [x] **A1** — implement `tokenize` + `BM25Index` (RED→GREEN→REFACTOR).
- [x] **A2** — implement `rrf_fuse` с формулой `1/(k+rank)`.
- [x] **A3** — implement `HybridSearchEngine` с DI vector-search.
- [x] **A4** — implement `QueryExpander` (dict + LLM).
- [x] **A5** — implement `CrossEncoderReranker` (lazy load).
- [x] **A6** — wire everything в `rag.query.retrieve()`.
- [x] **A7** — Dockerfile + docker-compose.yml (app + ollama).
- [x] **A8** — починить legacy bug в `ingest.py`.
- [x] **A9** — локализация промпта + графический гейт non-ASCII в expander.

### Uncertainty
_Все вопросы разрешены в процессе работы._

- ✅ `qwen3:0.6b` vs `qwen2.5:7b` → см. Q-02 в `discuss.md` (resolved).
- ✅ Как именно расширять аббревиатуры → dict first + LLM fallback.

### Тесты
- 27 unit (`test_search_engine` 13, `test_query_expansion` 11, `test_reranker` 8)
- 2 integration (`test_pipeline`)
- Suite umyшленно не требует faiss/sentence-transformers (~100 ms)
- **Regression gates:** любые изменения `retrieve()`, `HybridSearchEngine`,
  `QueryExpander`, `CrossEncoderReranker` должны проходить существующий
  suite без ослабления.

### Документация
- [x] `architecture.md § Edge Cases` обновлён (18 cases)
- [x] `context-dump.md` описывает поток pipeline
- [x] `search-spec.md` формальная спецификация
- [x] `legacy-warning.md` — добавлены LW-001..LW-010
- [x] `tasks.md` — добавлена D-01, B-01, B-02, C-01..C-10
- [x] `current-sprint.md` — Done секция заполнена
- [x] `contracts/mcp-server.md` — явный контракт, что MCP не тронут
