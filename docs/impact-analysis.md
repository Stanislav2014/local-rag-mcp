# Impact Analysis: текущий путь данных от запроса до выдачи

Документ описывает, **как именно** запрос пользователя превращается в ответ
ассистента в текущей (legacy) реализации — до внедрения Advanced Pipeline.

> Цель: зафиксировать «как было», чтобы потом рассуждать про «как стало».

## 1. Точки входа

| Источник запроса | Файл | Функция |
|---|---|---|
| Интерактивный CLI | `src/main.py` | `main()` → `assistant.query(q)` |
| Прямой запуск ассистента | `src/assistant.py` | `CompanyKBAssistant.query()` |
| Прямой RAG (без MCP) | `src/rag/query.py` | `ask(q)` |
| MCP сервер (для внешних клиентов) | `src/mcp/server.py` | `read_document` / `list_documents` / `search_documents` |

## 2. Поток данных (legacy)

```
            ┌──────────────┐
            │ user query   │
            └──────┬───────┘
                   │
                   ▼
   ┌────────────────────────────┐
   │ CompanyKBAssistant.query() │
   │  src/assistant.py          │
   └──────┬─────────────────────┘
          │
          │  1) retrieve(query)
          ▼
   ┌────────────────────────────┐
   │ rag/query.retrieve()       │
   │  - SentenceTransformer     │
   │    .encode([query])        │
   │  - faiss.normalize_L2      │
   │  - index.search(q, TOP_K)  │
   └──────┬─────────────────────┘
          │  list[chunk]   (top-K = 5)
          ▼
   ┌────────────────────────────┐
   │ _llm_decide_mcp_usage()    │
   │  Ollama (qwen3:0.6b)       │
   │  → JSON {use_mcp,tool,args}│
   └──────┬─────────────────────┘
          │
          │   ┌── if use_mcp ────────┐
          │   ▼                       │
          │  MCPClient.call_tool()   │
          │  src/mcp/client.py       │
          │  → JSON-RPC stdio        │
          │  → mcp/server.py tool    │
          │   │                       │
          │   ▼                       │
          │  mcp_result (str)        │
          │   └───────────┬───────────┘
          │               │
          ▼               ▼
   ┌────────────────────────────┐
   │ build_prompt(query, ctx)   │
   │  + <additional_info_from_  │
   │     mcp_tool> блок          │
   └──────┬─────────────────────┘
          │
          ▼
   ┌────────────────────────────┐
   │ ask_llm(prompt)            │
   │  POST OLLAMA_URL           │
   │  model = qwen3:0.6b        │
   └──────┬─────────────────────┘
          │
          ▼
   ┌────────────────────────────┐
   │ {answer, sources,          │
   │  mcp_used, mcp_tool}       │
   └────────────────────────────┘
```

## 3. Разбор по шагам

### 3.1 Индексация (offline, до запросов)
1. `rag/ingest.ingest_documents()` — обходит `DOCUMENTS_DIR`, читает `.txt/.md/.pdf/.docx`.
2. `rag/chunk.chunk_documents()` — токенизация cl100k_base, окно `CHUNK_SIZE=700`, overlap `100`.
3. `rag/embed.embed_chunks()` — `SentenceTransformer("all-MiniLM-L6-v2")`, 384-dim.
4. `rag/build_index.build_index()` — `faiss.IndexFlatIP` + `normalize_L2` (= cosine), сохраняет `index.faiss` и `chunks.pkl`.

### 3.2 Поиск (online)
1. Запрос пользователя пришёл в `CompanyKBAssistant.query()`.
2. `retrieve(query)` (`rag/query.py`):
   - `SentenceTransformer.encode([query])` → 1×384 вектор.
   - `faiss.normalize_L2(q_emb)`.
   - `index.search(q_emb, TOP_K=5)` → `(scores, ids)`.
   - Возвращает `[chunks[i] for i in ids[0]]` — **score теряется** (legacy bug, исправлено: теперь логируется).
3. `_llm_decide_mcp_usage()` спрашивает LLM, нужно ли вызывать MCP-инструмент. JSON-разбор. Если ошибка — без MCP.
4. (Опционально) `MCPClient.call_tool()` шлёт JSON-RPC через stdio в `mcp/server.py`.
5. `build_prompt()` собирает шаблон с `<context>`. При наличии MCP результата дописывает `<additional_info_from_mcp_tool>`.
6. `ask_llm()` POST в `http://localhost:11434/api/generate`.
7. Ответ + список источников возвращаются вызывающему.

## 4. Найденные проблемы

| # | Проблема | Влияние |
|---|---|---|
| 1 | `retrieve()` теряет `scores` после поиска — невозможно понять «уверенность» | Нет наблюдаемости качества |
| 2 | Поиск **только** векторный (cosine) | Точные коды/токены типа `403 Forbidden`, `sqli` теряются среди семантически близких чанков |
| 3 | Нет реранкера — top-5 могут содержать нерелевантный «семантический шум» | LLM получает отвлекающий контекст |
| 4 | Короткие/абревиатурные запросы (`sqli`, `xss`) встраиваются как есть | Эмбеддинг такого токена слабо коррелирует с полезным контекстом |
| 5 | `mcp/server.py:search_documents` ищет **по имени файла**, а не по содержимому | Имя инструмента вводит в заблуждение, но MCP-контракт не ломаем |
| 6 | `ingest.py` имеет «ленивую» рекурсию через `else` (`ingest_documents(path)` без аргумента) — потенциально мёртвый код | Низкий приоритет |

Проблемы №2-4 — основа для Advanced Pipeline (см. `docs/search-spec.md`).

## 5. Что зафиксировано до изменений

- Контракт MCP-инструментов (`read_document`, `list_documents`, `search_documents`) — **не меняется**.
- Сигнатура `retrieve(query)` остаётся обратно-совместимой: добавлены опциональные `k` и `with_scores`.
- Legacy путь продолжает работать, новый pipeline собирается рядом и подключается через `query.retrieve()`.
