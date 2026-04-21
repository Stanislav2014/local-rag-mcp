# Data Schema

У проекта **нет реляционной БД**. Вся долговременная память — это два файла
на диске плюс исходные документы. Этот документ фиксирует их формат, чтобы
смена формата не сломала потребителей молча.

## 1. Исходные документы

**Где**: `src/docs/<...>`

**Поддерживаемые форматы**: `.txt`, `.md`, `.pdf`, `.docx` (см.
`src/rag/ingest.py::SUPPORTED_EXTENSIONS`).

**Обход**: `Path.rglob("*")` — читаются все файлы с поддерживаемым расширением,
любой вложенности.

## 2. `src/chunks.pkl`

Python pickle со списком чанков. Создаётся `src/rag/build_index.build_index()`.

```python
list[Chunk]  # всегда того же порядка, что и векторы в index.faiss

Chunk = {
    "text":     str,   # текст чанка (после tiktoken encode+decode)
    "source":   str,   # относительный путь документа (см. ingest_documents)
    "chunk_id": int,   # индекс чанка внутри документа, начиная с 0
}
```

Дополнительные поля, которые **добавляются в runtime** и НЕ пишутся в pickle:

| Поле | Кто добавляет | Значение |
|---|---|---|
| `score` | `HybridSearchEngine.search`, `_vector_search` | Скор RRF / cosine / BM25 (зависит от стадии) |
| `rank` | то же | Позиция в ранжированном списке, 1-based |
| `rerank_score` | `CrossEncoderReranker.rerank` | Сырой output cross-encoder |

Выходной `retrieve()` **чистит** служебные поля перед возвратом, поэтому
потребители (`assistant.py`, `ask()`) видят только `text`, `source`, `chunk_id`.

## 3. `src/index.faiss`

Двоичный FAISS-индекс. Создаётся `build_index()`.

| Параметр | Значение |
|---|---|
| Тип | `faiss.IndexFlatIP` |
| Нормализация | `faiss.normalize_L2` до `add()` и до `search()` (= cosine similarity) |
| Размерность | 384 (`all-MiniLM-L6-v2`) |
| Количество векторов | = `len(chunks.pkl)` |
| Порядок | Строго такой же, как `chunks.pkl` — позиция `i` в индексе ↔ `chunks[i]` |

Инвариант: **порядок `index.faiss` и `chunks.pkl` всегда синхронизирован**.
Если пересобираете индекс вручную — пересобирайте оба файла сразу.

## 4. BM25 (in-memory)

Индекс `BM25Okapi` из `rank_bm25` **не сериализуется** на диск. Он строится в
памяти при первом `_get_hybrid_engine()` из текущего `chunks.pkl`.

Это сознательный trade-off:
- **За**: нет риска рассинхронизации c `chunks.pkl`, не надо думать про
  версию формата BM25.
- **Против**: первый запрос после старта тратит O(N) на построение. Для
  корпусов > 50K чанков имеет смысл сохранять `bm25.pkl` рядом.

## 5. Что НЕ сохраняется

| Сущность | Где живёт | Переживает рестарт? |
|---|---|---|
| Сессионные диалоги | память процесса | Нет |
| Запросы пользователя | stdout-лог | Нет (надо дописать append-JSONL — см. `change-request.md`) |
| Решения LLM по MCP | память процесса | Нет |
| Scores каждого чанка | stdout-лог | Нет |
| История вызовов MCP | память MCP-клиента | Нет |

## 6. Volume layout в Docker

```
docker-compose.yml:
  ollama.volumes:
    - ollama_data:/root/.ollama      # модели ollama (скачиваются один раз)
  app.volumes:
    - ./src:/app/src                 # код + docs + index.faiss + chunks.pkl
    - hf_cache:/root/.cache/huggingface  # кэш HF моделей (sentence-transformers)
```

Bind-mount `./src:/app/src` означает, что `index.faiss` / `chunks.pkl`,
собранные внутри контейнера, остаются на хосте.
