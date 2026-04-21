# Contract — MCP Server (`src/mcp/server.py`)

**Статус:** жёсткий контракт. Ломать без миграции клиентов нельзя.

## Direction

Сервер → клиент: ассистент `CompanyKBAssistant` и любой внешний MCP-клиент
(Claude Code, другие LLM-хосты) вызывают инструменты сервера через stdio.

## Protocol

- **Транспорт:** stdio (stdin/stdout) + JSON-RPC 2.0
- **Рантайм:** `fastmcp.FastMCP("doc-tools", version="1.0.0")`
- **Старт:** `python src/mcp/server.py` (или через `mcp.run()`)

## Инструменты

### 1. `read_document(file_path: str) -> str`

**Назначение:** вернуть полное содержимое документа из knowledge base.

**Аргументы:**
- `file_path: str` — путь к файлу. **Должен быть внутри `DOCUMENTS_DIR`**
  (security check через `path.resolve().startswith(...)`).

**Возврат:** содержимое файла как строка UTF-8.

**Ошибки (возвращаются как строка, не бросаются):**
- `"Error: Access denied. File must be in {DOCUMENTS_DIR}"` — попытка
  выйти за пределы knowledge base.
- `"Error: File not found: {file_path}"` — файла нет.
- `"Error reading file: {e}"` — другие ошибки I/O.

**Код:** `src/mcp/server.py::read_document`.

### 2. `list_documents() -> str`

**Назначение:** вернуть список всех документов в knowledge base.

**Аргументы:** нет.

**Возврат:** multi-line строка в формате `- relative/path/to/file.md`.
Если базы нет или она пуста — возвращается информационная строка
(`"No documents found in the knowledge base."` либо `"Error: ..."`).

**Фильтр:** `.txt`, `.md`, `.pdf`, `.docx`.

**Код:** `src/mcp/server.py::list_documents`.

### 3. `search_documents(query: str) -> str`

**Назначение:** найти документы **по имени файла** (substring, case-insensitive).

> ⚠ **Важно**: несмотря на название, это **НЕ** семантический поиск. Это
> legacy-имя, которое сохраняется для обратной совместимости.
> Для семантического поиска используется `rag.query.retrieve()` — он
> вызывается ассистентом напрямую (`src/assistant.py`), а не через MCP.

**Аргументы:**
- `query: str` — подстрока в имени файла.

**Возврат:**
- Multi-line `- <relative path>` для совпадений.
- `"No documents found matching '{query}'"` если ничего не найдено.
- `"Error: ..."` при проблеме с базой.

**Код:** `src/mcp/server.py::search_documents`.

## Client processing

Ассистент принимает решение о вызове tool через LLM-decision:

```
_llm_decide_mcp_usage(query, contexts) -> (tool_name, tool_args)
    │
    ├── LLM (qwen3:0.6b) получает:
    │     - пользовательский запрос
    │     - топ-3 retrieved чанка
    │     - список инструментов + правила
    │
    └── возвращает JSON {"use_mcp": bool, "tool": str, "args": dict}
```

Если LLM вернул битый JSON — считается, что MCP не нужен (`return None, None`).

## Gotchas

1. **`search_documents` — по имени, не по содержимому.** Новички путаются.
   Документировано в контракте выше и в `legacy-warning.md::LW-001`.
2. **Security check в `read_document`** использует `resolve()` — symlink'и за
   пределы `DOCUMENTS_DIR` будут отклонены.
3. **Recursion в `list_documents`** — через `rglob("*")`, без ограничения
   глубины. Гигантские knowledge base могут тормозить.
4. **stdio-транспорт** означает: сервер нельзя хостить как HTTP endpoint без
   дополнительного wrapper-а. Для локального CLI это ок.
5. **Lifecycle клиента**: `MCPClient` (`src/mcp/client.py`) держит subprocess
   всё время жизни `CompanyKBAssistant`. `.close()` вызывает `terminate()`.

## История изменений

| Дата | Commit | Изменение |
|---|---|---|
| до 2026-04-12 | (pre-`feature/advanced-search-pipeline`) | Начальная реализация трёх инструментов |
| 2026-04-12 → 2026-04-13 | `ed6951e` | Контракт **не менялся** при внедрении Advanced Search Pipeline. Advanced pipeline сделан **рядом** через `rag.query.retrieve()`, не через MCP. |

## Планы (не обещания)

- **LR-0201 / C-01:** добавить `semantic_search_documents(query)` — отдельный
  инструмент, вызывающий `rag.query.retrieve()`. Старый `search_documents`
  пометить deprecated в docstring.
- Формальная схема инструментов в JSON Schema (fastmcp поддерживает).
