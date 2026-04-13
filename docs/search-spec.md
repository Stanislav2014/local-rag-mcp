# Advanced Search Pipeline — Спецификация

Документ описывает три уровня обработки запроса, которые превращают legacy
векторный поиск в `Advanced Pipeline`.

```
query
  │
  ▼
[1] Query Expansion          (перефраз / расшифровка аббревиатур)
  │
  ▼
[2] Hybrid Search            (BM25 ⊕ Vector → RRF)
  │   top-N (≈20)
  ▼
[3] Cross-Encoder Reranker   (BAAI/bge-reranker-base или fallback)
  │   top-K (=5) → LLM
  ▼
LLM
```

Все три уровня — **аддитивны** и включаются флагами в `config.py`, чтобы можно
было проводить A/B-сравнение и быстро откатываться.

---

## 1. Hybrid Search (BM25 + Vector)

### Цель
Запрос `403 Forbidden` должен находить чанк с этим **точным токеном**, а не
«что-то про ошибки HTTP». Векторный поиск на коротких запросах с редкими
терминами проигрывает классической лексической метрике.

### Алгоритм

1. **Параллельные кандидаты**:
   - `vec_top  = vector_search(query, k = N_VEC)`   (через FAISS, как сейчас)
   - `bm25_top = bm25_search(query,   k = N_BM25)`  (через `rank_bm25.BM25Okapi`)
   - `N_VEC = N_BM25 = 50` (конфигурируемо)
2. **Объединение через RRF** (Reciprocal Rank Fusion):
   ```
   RRF_score(d) = Σ_q  1 / (k_rrf + rank_q(d))
   ```
   - `k_rrf = 60` (значение по-умолчанию из оригинальной статьи Cormack et al.)
   - `rank_q(d)` — позиция документа `d` в ранжированном списке от источника `q`
     (BM25 или Vector). Если документ отсутствует в списке — слагаемое = 0.
3. **Top-N результат** — отсортированный по убыванию `RRF_score` список из `N_HYBRID = 20` лучших чанков.
4. **Альтернатива (Weighted Sum)** — оставлена как fallback для исследований:
   ```
   score(d) = α · norm(vec_score(d)) + (1-α) · norm(bm25_score(d))
   ```
   `α = 0.5`. Активируется флагом `FUSION_STRATEGY = "weighted"`.

### Структура BM25 индекса
- Корпус для BM25 строится **из тех же чанков**, что и FAISS-индекс.
- Токенизация: lowercase + split по `\W+` (простая, без стемминга — чтобы
  сохранить токены вроде `403` и `xss`).
- Сериализация: `bm25.pkl` рядом с `chunks.pkl`.
- Перестроение: вместе с FAISS в `rag/build_index.py`.

### Контракт
```python
class HybridSearchEngine:
    def __init__(self, chunks, faiss_index, embed_model,
                 k_rrf: int = 60,
                 strategy: str = "rrf"): ...

    def search(self, query: str, k: int = 20) -> list[dict]:
        """Returns chunks with 'score' and 'rank' keys, sorted desc."""
```

Существующий `retrieve(query)` использует `HybridSearchEngine.search(...)`
внутри, **сигнатура и MCP-контракт не меняются**.

### Тесты (TDD)
- `tokenize("403 Forbidden")` → `["403", "forbidden"]`
- BM25 с корпусом из 3 чанков возвращает чанк с точным `"403 Forbidden"` на 1-м месте.
- RRF: при объединении двух списков элемент, попавший в оба, ранжируется выше элемента, попавшего только в один.
- `HybridSearchEngine.search()` возвращает ровно `k` элементов (или меньше, если корпус мал).
- Каждый возвращённый элемент содержит `text`, `source`, `score`.

---

## 2. Reranking (Cross-Encoder)

### Цель
Убрать «семантический шум» из top-20 гибридного поиска и оставить **топ-5
действительно отвечающих** на вопрос чанков для LLM.

### Алгоритм
1. На вход — top-N (≈20) от гибридного поиска.
2. Для каждой пары `(query, chunk.text)` считается релевантность через
   cross-encoder:
   ```
   score = CrossEncoder.predict([(query, chunk.text), ...])
   ```
3. Сортировка по убыванию, возврат top-K (=5).

### Модель
- **Основная**: `BAAI/bge-reranker-base` через `sentence_transformers.CrossEncoder`.
- **Fallback**: при отсутствии модели или флаге `RERANKER_ENABLED=False` —
  результаты гибридного поиска возвращаются как есть, top-K берётся по
  RRF-скору. Это позволяет тестам и Docker-сборке работать без скачивания
  тяжёлой модели.

### Контракт
```python
class CrossEncoderReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base",
                 enabled: bool = True): ...

    def rerank(self, query: str, candidates: list[dict],
               top_k: int = 5) -> list[dict]: ...
```

`rerank()` дописывает каждому возвращённому чанку поле `rerank_score`.

### Тесты (TDD)
- При `enabled=False` `rerank` — это срез `candidates[:top_k]`.
- При замоканном `CrossEncoder.predict` (фиктивные скоры) `rerank` сортирует кандидатов по убыванию.
- `rerank(query, [], top_k=5)` → `[]`.
- Возвращаемые чанки содержат `rerank_score: float`.

---

## 3. Query Expansion (LLM Rewrite)

### Цель
Короткие/абревиатурные запросы (`sqli`, `xss`, `csrf`) расширить до полной
формы, чтобы эмбеддинг отражал смысл, а BM25 матчил больше токенов.

### Алгоритм
1. Если `len(query.split()) > MAX_LEN_FOR_EXPANSION (=4)` — пропускаем расширение.
2. Сначала проверяем встроенный **словарь известных аббревиатур**
   (быстрый и оффлайн-friendly путь):
   ```python
   ABBREVIATIONS = {
       "sqli":  "SQL Injection vulnerability",
       "xss":   "Cross-Site Scripting vulnerability",
       "csrf":  "Cross-Site Request Forgery",
       "ssrf":  "Server-Side Request Forgery",
       "rce":   "Remote Code Execution",
       "lfi":   "Local File Inclusion",
       "rfi":   "Remote File Inclusion",
       "idor":  "Insecure Direct Object Reference",
       "xxe":   "XML External Entity",
       "mfa":   "Multi-Factor Authentication",
       "sso":   "Single Sign On",
   }
   ```
   Расширенный запрос = `"{abbr} {expansion}"` (старый + новый,
   чтобы не потерять оригинальный токен для BM25).
3. Если в словаре нет, но запрос всё ещё «короткий» — идём к LLM
   (`ollama` / тот же `OLLAMA_MODEL`):
   ```
   System: You are a query rewriter. Rewrite the user query into a longer,
   more descriptive search query. Keep all original technical terms.
   Reply with ONLY the rewritten query, no explanation.

   User: <query>
   ```
   Результат: `original + " " + llm_rewrite`.
4. Если LLM недоступен/ошибка — возвращаем исходный запрос (graceful degrade).

### Контракт
```python
class QueryExpander:
    def __init__(self, llm_client=None,
                 model: str = OLLAMA_MODEL,
                 max_len: int = 4,
                 abbreviations: dict | None = None): ...

    def expand(self, query: str) -> str: ...
```

### Тесты (TDD)
- `expand("sqli")` → содержит `"SQL Injection"` и оригинальное `"sqli"`.
- `expand("how do I configure backups in production environment")` → возвращает запрос **без изменений** (длинный).
- `expand("xss")` без LLM-клиента — берёт из словаря.
- `expand("zzz")` без LLM-клиента и без словаря — возвращает оригинал.
- LLM-ветка тестируется через мок (`MagicMock` ollama client).

---

## 4. Конфиг (новые ключи в `src/config.py`)

```python
# === Advanced search pipeline ===
HYBRID_ENABLED      = True
FUSION_STRATEGY     = "rrf"          # "rrf" | "weighted"
RRF_K               = 60
N_VEC               = 50
N_BM25              = 50
N_HYBRID            = 20             # top-N после fusion (вход реранкера)

RERANKER_ENABLED    = True
RERANKER_MODEL      = "BAAI/bge-reranker-base"

QUERY_EXPANSION_ENABLED = True
QUERY_EXPANSION_MAX_LEN = 4
```

Любой флаг = `False` отключает соответствующий слой и pipeline деградирует
к предыдущему уровню.

## 5. Сохранность контрактов

- `mcp/server.py` (`read_document`, `list_documents`, `search_documents`) —
  **не модифицируется**.
- `rag/query.retrieve(query)` — сигнатура совместима, поведение «больше / лучше».
- `assistant.CompanyKBAssistant.query()` — без изменений снаружи.
- Старый `chunks.pkl` / `index.faiss` остаются. Появляется `bm25.pkl`.
