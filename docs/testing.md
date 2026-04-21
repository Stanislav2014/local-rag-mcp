# Testing

Как устроены тесты, как их запускать, какие инварианты они охраняют.

## Фреймворки

| Инструмент | Версия | Роль |
|---|---|---|
| `pytest` | ≥ 8.0 | раннер |
| `pytest-asyncio` | 0.25+ | для будущих async-тестов (пока не используется) |
| `unittest.mock` | stdlib | мокать ollama-клиента и cross-encoder |
| `rank_bm25` | ≥ 0.2.2 | реальный BM25 в тестах (lightweight, ставится) |
| `numpy` | ≥ 1.24 | для векторных моков в conftest |

**Намеренно отсутствуют в тестах:**
- `faiss-cpu` — не нужен, vector-search инжектится через DI.
- `sentence-transformers` — не нужен, CrossEncoder мокается.
- `ollama` — мокается через `MagicMock`.

Это позволяет юнит-тестам бежать за **~100 мс** и работать в любом CI без
скачивания моделей.

## Структура

```
tests/
├── __init__.py
├── conftest.py                  ← sys.path + sample_chunks + fake_vector_search
├── unit/
│   ├── __init__.py
│   ├── test_search_engine.py    ← tokenize, BM25Index, rrf_fuse, HybridSearchEngine (13 тестов)
│   ├── test_query_expansion.py  ← QueryExpander dict/LLM/failure (11 тестов)
│   └── test_reranker.py         ← CrossEncoderReranker enabled/disabled/failure (8 тестов)
└── integration/
    ├── __init__.py
    └── test_pipeline.py         ← полный pipeline через DI, без faiss (2 теста)
```

Всего: **34 теста, ~100 мс**.

## Fixtures (tests/conftest.py)

### `sample_chunks`
Детерминированный корпус из 5 чанков:
- HTTP `403 Forbidden` (для BM25 exact-token теста)
- HTTP `404 Not Found`
- SQL Injection (sqli)
- Cross-Site Scripting (xss)
- Vacation policy

### `fake_vector_search`
Стаб-замена FAISS. Считает релевантность как количество совпадающих токенов
запроса в тексте чанка. Намеренно **слабее** чем настоящий vector search —
чтобы BM25 выигрывал на exact-token запросах и тесты это видели.

## Команды

### Локально

```bash
# Прогнать всё
.venv/bin/pytest tests -q

# Только unit
.venv/bin/pytest tests/unit -q

# Только integration
.venv/bin/pytest tests/integration -q

# Один файл
.venv/bin/pytest tests/unit/test_search_engine.py -v

# Один конкретный тест
.venv/bin/pytest tests/unit/test_search_engine.py::TestRRFFuse::test_score_formula -v
```

### В Docker

```bash
docker compose run --rm app python -m pytest /app/tests -q
```

## Инварианты, которые тесты охраняют

### HybridSearchEngine
1. **Exact-token wins** — запрос `"403 Forbidden"` находит чанк с этим токеном
   первым (BM25 побеждает чисто-векторные кандидаты).
2. **Топ-K обрезается** — `search(query, k=2)` возвращает ≤ 2 элементов.
3. **Все результаты имеют `score` и `rank`**.
4. **Weighted стратегия работает** — не только RRF.
5. **Unknown strategy → ValueError** — нельзя тихо пропустить опечатку в
   `FUSION_STRATEGY`.
6. **Пустой корпус → `[]`** — не падает.

### RRF Fusion
1. **Документ в обоих списках обгоняет документ в одном** — формула
   действительно объединяет ранги.
2. **Формула**: `score = 1 / (k_rrf + rank)` (проверяется с точностью до `math.isclose`).
3. **Пустые входы** → `[]`.
4. **Дедупликация по `(source, text)`** когда `chunk_id` отсутствует.

### BM25Index
1. **Точный токен** находит правильный чанк первым.
2. **Все результаты имеют `text`, `source`, `score`, `rank`**.
3. **Максимум `k` результатов**.
4. **Пустой запрос → `[]`**.

### Tokenizer
1. **`"403 Forbidden"` → `["403", "forbidden"]`** (цифры сохраняются).
2. **`"HTTP/1.1 404 Not-Found!"` → `["http", "1", "1", "404", "not", "found"]`**
   (пунктуация удаляется).
3. **Пустая строка → `[]`**.

### QueryExpander
1. **Известная аббревиатура** (`sqli`) → `"sqli SQL Injection vulnerability"`
   (оригинал сохраняется).
2. **Длинный запрос (>4 токенов)** — без изменений.
3. **LLM failure** — возвращает оригинал.
4. **LLM-rewrite** работает через мок и не ломает интерфейс.

### CrossEncoderReranker
1. **`enabled=False`** — возвращает `candidates[:top_k]` как есть.
2. **`enabled=True`** — сортирует по `rerank_score`, добавляет поле.
3. **Model failure** — fallback к входному порядку.
4. **Пустые кандидаты** — не падает.
5. **`top_k=0`** → `[]`.

### Integration (полный pipeline)
1. **`403 Forbidden`** через expansion → hybrid → rerank находит
   `http-errors.md` первым.
2. **`sqli`** после expansion содержит `"sql injection"` и находит
   `security/sqli.md`.

## Как добавлять новые тесты

1. **Сначала тест** (RED) — писать до кода.
2. **Юнит-тесты не должны требовать faiss/sentence-transformers** — инжектить моки.
3. **Если тест требует реальной модели** — класть в `tests/integration_slow/`
   (пока не создана) и запускать через `pytest -m slow`.
4. **Edge-case → обязательный тест.** Каждая запись в `architecture.md § Edge Cases`
   должна иметь соответствующий тест (или явно помеченная как «проверено e2e»).

## Что не покрыто тестами (осознанно)

- **Сетевое взаимодействие с ollama** — мы проверяем это через e2e smoke в
  Docker при разработке, не через юнит-тесты.
- **Реальный FAISS** — интеграционный slow-suite (D-08 в tasks.md).
- **MCP-клиент ↔ сервер** — работают через stdio subprocess, smoke-тест в Docker.
- **CLI (`main.py`)** — не тестируется, это тонкий wrapper.

## Известные проблемы

- `virtualenv` используется вместо `python3 -m venv` — системный Debian
  не поставляет `python3-venv`.
- На macOS / Windows возможны отличия при работе с `faiss-cpu` (но тесты их
  не требуют, так что на юниты не влияет).
