# Current Sprint

> **Спринт:** стабилизация `feature/advanced-search-pipeline` + документация по манбот-методологии.
> **Старт:** 2026-04-12
> **Текущая дата:** 2026-04-14

Kanban текущей итерации. Master-каталог задач — в [tasks.md](./tasks.md).

## To Do

| ID | Задача | Приоритет |
|---|---|---|
| D-02 | Append-JSONL лог запросов | high (запрос пользователя) |
| D-03 | Persisted BM25 | medium |
| D-09 | CI GitHub Actions | medium |

## In Progress

_пусто_

## In Review

_пусто_

## Done

### D-01 Advanced Search Pipeline
- **Ветка:** `feature/advanced-search-pipeline`
- **Commits:** `ed6951e` (initial), `4efedb9` (qwen2.5:7b switch + rollback)
- **Дата:** 2026-04-13
- **Итог:** полный 3-этапный pipeline (expansion → hybrid RRF → rerank),
  MCP-контракт сохранён, 34 теста зелёные, Docker обёртка работает,
  e2e smoke через реальную ollama успешен.
- **Документация:** `search-spec.md`, `impact-analysis.md`, `context-dump.md`,
  `architecture.md § Edge Cases`.

### B-01 Починка мёртвой рекурсии в `rag.ingest.ingest_documents`
- **Commit:** `ed6951e`
- **Дата:** 2026-04-13
- **Итог:** `TypeError: ingest_documents() takes 0 positional arguments but 1
  was given` больше не воспроизводится, `rglob("*")` обходит всё без явной
  рекурсии.

### B-02 `.gitignore` блокировал `docs/*.md` и корневой README
- **Commit:** `ed6951e`
- **Дата:** 2026-04-13
- **Итог:** удалены правила `docs/*.md`, `/**.md`, оставлены `src/docs/*.md*`
  (для knowledge-base).

### DOCS-01 Методология docs по manbot-style
- **Дата:** 2026-04-14
- **Итог:** добавлены `README.md` (индекс), `project.md`, `instructions.md`,
  `plan.md`, `ideas.md`, `discuss.md`, `tasks.md`, `testing.md`,
  `change-request-doc.md` (шаблон отделён от данных), `docs-setup-prompt.md`
  (расширенный канонический промпт), `contracts/mcp-server.md`. Записи в
  `legacy-warning.md` помечены приоритетами 🔥 / ⚠ / 🧟. Плагин
  `andrej-karpathy-skills` установлен в `~/.claude/plugins/`.

## Notes

- Ветка `feature/advanced-search-pipeline` запушена в origin, PR ещё не создан.
- Модель по умолчанию — `qwen3:0.6b` (откатилась после эксперимента с
  `qwen2.5:7b` по запросу пользователя; см. Q-02 в `discuss.md`).
- Плагин `andrej-karpathy-skills` активируется при следующем старте
  Claude Code (скиллы загружаются на старте сессии).
