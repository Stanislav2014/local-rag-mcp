# Local RAG / MCP Assistant — Advanced Search Pipeline

Локальный (offline-friendly) ассистент по корпоративной базе знаний: отвечает
на вопросы по документации, используя **RAG** (Retrieval-Augmented Generation)
и **MCP** (Model Context Protocol) для динамического доступа к файлам.

В этой ветке базовый векторный поиск расширен до **Advanced Search Pipeline**:
*Query Expansion → Hybrid Search (BM25 + Vector, RRF) → Cross-Encoder Reranker*.

> Все компоненты работают локально: эмбеддинги — `sentence-transformers`,
> LLM — `ollama`, никаких внешних API.

---

## Описание проекта

| | |
|---|---|
| **Назначение** | Q&A по корпоративной/технической документации (`.md`, `.txt`, `.pdf`, `.docx`) |
| **Кому полезно** | Команды поддержки, инженеры, security-аналитики — все, кому нужен быстрый поиск по большому корпусу документов без отправки данных в облако |
| **Главное преимущество** | Полностью локальный pipeline + улучшенная точность поиска на «технических» запросах (HTTP-коды, аббревиатуры безопасности и т. п.) |

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER (CLI / MCP client)                        │
└──────────────────┬──────────────────────────────────────┬───────────────┘
                   │                                      │
                   ▼                                      ▼
        ┌────────────────────┐                ┌──────────────────────┐
        │ CompanyKBAssistant │                │  MCP Server (stdio)  │
        │   src/assistant.py │                │   src/mcp/server.py  │
        └─────────┬──────────┘                │  read_document       │
                  │                           │  list_documents      │
                  │                           │  search_documents    │
                  │                           └──────────────────────┘
                  ▼
   ┌────────────────────────────────────────┐
   │      Advanced Search Pipeline          │
   │  src/rag/query.retrieve()              │
   │                                        │
   │  ┌──────────────────────────────────┐  │
   │  │ 1. QueryExpander                 │  │
   │  │   src/rag/query_expansion.py     │  │
   │  │   • dict (sqli→SQL Injection…)   │  │
   │  │   • LLM rewrite (ollama)         │  │
   │  └──────────────┬───────────────────┘  │
   │                 ▼                      │
   │  ┌──────────────────────────────────┐  │
   │  │ 2. HybridSearchEngine            │  │
   │  │   src/rag/search_engine.py       │  │
   │  │   • BM25Okapi (rank_bm25)        │  │
   │  │   • FAISS vector search          │  │
   │  │   • RRF / Weighted fusion        │  │
   │  └──────────────┬───────────────────┘  │
   │                 ▼                      │
   │  ┌──────────────────────────────────┐  │
   │  │ 3. CrossEncoderReranker          │  │
   │  │   src/rag/reranker.py            │  │
   │  │   • BAAI/bge-reranker-base       │  │
   │  │   • lazy load + fallback         │  │
   │  └──────────────┬───────────────────┘  │
   │                 ▼                      │
   │       top-K chunks → LLM prompt        │
   └────────────────┬───────────────────────┘
                    ▼
           ┌────────────────┐
           │  Ollama (LLM)  │
           │  qwen3:0.6b    │
           └────────────────┘
```

Полный разбор в [docs/impact-analysis.md](docs/impact-analysis.md),
спецификация — в [docs/search-spec.md](docs/search-spec.md),
дамп взаимодействий — в [docs/context-dump.md](docs/context-dump.md).

---

## Подход

### 1. Проверяемость («observability over magic»)
Каждый этап pipeline **логирует score** для каждого чанка. Когда LLM ошибается,
можно сразу увидеть: дал ли retrieval мусор, перепутал ли реранкер, или модель
проигнорировала контекст.

### 2. Постепенная деградация (graceful fallback)
- Если cross-encoder не скачался → берём top-K по RRF.
- Если ollama не поднята → query expansion возвращает оригинальный запрос.
- Если BM25 / FAISS отдали 0 — pipeline возвращает что есть, не падает.

Каждый этап включается/выключается флагом в `src/config.py`, поэтому A/B-сравнение
делается без правки кода.

### 3. TDD
Сначала тесты, потом реализация. Юнит-тесты для каждого модуля (тесты не зависят
от FAISS / sentence-transformers — vector search инжектится как callable),
плюс интеграционный тест на полный pipeline без тяжёлых зависимостей.

### 4. Сохранение контракта MCP
`src/mcp/server.py` (`read_document`, `list_documents`, `search_documents`)
**не модифицируется**. Внешние клиенты MCP продолжают работать как раньше.

---

## Структура проекта

```
local-rag-mcp/
├── README.md                       ← этот файл
├── Dockerfile                      ← образ приложения
├── docker-compose.yml              ← приложение + ollama
├── docs/
│   ├── impact-analysis.md          ← legacy data flow + найденные проблемы
│   ├── search-spec.md              ← спецификация Advanced Pipeline
│   └── context-dump.md             ← как компоненты взаимодействуют
├── src/
│   ├── README.md                   ← старая инструкция по запуску
│   ├── config.py                   ← вся конфигурация (флаги pipeline)
│   ├── main.py                     ← интерактивный CLI
│   ├── assistant.py                ← оркестрация RAG + MCP
│   ├── rag/
│   │   ├── ingest.py               ← загрузка txt/md/pdf/docx
│   │   ├── chunk.py                ← токенизация + окно/overlap
│   │   ├── embed.py                ← sentence-transformers
│   │   ├── build_index.py          ← FAISS индексирование
│   │   ├── query.py                ← retrieve() = pipeline + ask_llm()
│   │   ├── search_engine.py        ← BM25 + RRF + HybridSearchEngine
│   │   ├── query_expansion.py      ← QueryExpander (dict + LLM)
│   │   └── reranker.py             ← CrossEncoderReranker
│   ├── mcp/
│   │   ├── server.py               ← FastMCP tools (НЕ менять)
│   │   └── client.py               ← stdio JSON-RPC клиент
│   ├── docs/                       ← база знаний (документы)
│   └── requirements.txt
└── tests/
    ├── conftest.py                 ← фикстуры + sys.path
    ├── unit/
    │   ├── test_search_engine.py   ← BM25 / RRF / HybridSearchEngine
    │   ├── test_query_expansion.py ← QueryExpander
    │   └── test_reranker.py        ← CrossEncoderReranker
    └── integration/
        └── test_pipeline.py        ← полный pipeline без FAISS (моки)
```

---

## Тех. стек

| Слой | Технология |
|---|---|
| Язык | Python 3.12 |
| Эмбеддинги | `sentence-transformers` / `all-MiniLM-L6-v2` (384-dim) |
| Векторный индекс | `faiss-cpu` (`IndexFlatIP` + `normalize_L2` ≡ cosine) |
| Лексический поиск | `rank_bm25` (`BM25Okapi`) |
| Fusion | RRF (Reciprocal Rank Fusion), Weighted Sum (опционально) |
| Reranker | `BAAI/bge-reranker-base` через `sentence_transformers.CrossEncoder` |
| LLM | Ollama, по умолчанию `qwen3:0.6b` (можно любой) |
| MCP | `fastmcp` (stdio JSON-RPC) |
| Документы | `pypdf`, `python-docx` |
| CLI / pretty-print | `rich` |
| Тесты | `pytest`, `pytest-asyncio`, `unittest.mock` |
| Контейнеризация | Docker + Docker Compose (приложение + сервис ollama) |

---

## Быстрый старт

### Локально

```bash
# Виртуальное окружение
virtualenv .venv && source .venv/bin/activate
pip install -r src/requirements.txt

# Тесты
pytest tests -q

# Запуск (требует поднятой ollama: см. ниже)
cd src && python main.py
```

### Docker (рекомендуемый путь)

```bash
docker compose up --build
# приложение поднимется в контейнере app, ollama — в контейнере ollama
# затем войти в контейнер для интерактива:
docker compose exec app python main.py
```

При первом запуске необходимо сделать `docker compose exec ollama ollama pull qwen3:0.6b`.

См. [docs/context-dump.md](docs/context-dump.md) — там подробно про взаимодействия.

---

## Конфигурация Pipeline

Все ключи живут в `src/config.py`:

```python
HYBRID_ENABLED          = True       # включить/выключить гибрид
FUSION_STRATEGY         = "rrf"      # "rrf" | "weighted"
RRF_K                   = 60
N_VEC                   = 50         # сколько кандидатов от FAISS
N_BM25                  = 50         # сколько кандидатов от BM25
N_HYBRID                = 20         # вход реранкера

RERANKER_ENABLED        = False      # True когда модель скачана
RERANKER_MODEL          = "BAAI/bge-reranker-base"

QUERY_EXPANSION_ENABLED = True
QUERY_EXPANSION_MAX_LEN = 4
```

Любой флаг `False` — соответствующий уровень отключается, pipeline деградирует
до предыдущего поведения.
