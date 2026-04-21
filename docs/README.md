# Documentation Index

Навигация по всей документации `local-rag-mcp`. Структура — адаптация
[manbot](https://github.com/larchanka/manbot) `_docs` / `_board` разделения
под одиночное RAG-приложение.

Принцип: **index-level** файлы живут плоско в `docs/`, доменные артефакты
уходят в подпапки только когда их больше одного.

## 0. Индекс / стратегия / доска

| Файл | Назначение |
|---|---|
| [README.md](./README.md) | этот индекс |
| [project.md](./project.md) | обзор проекта на 1 экран — назначение, продукты, стек, карта «где что искать» |
| [instructions.md](./instructions.md) | процесс ведения задач (TDD workflow, branch naming, commit/push/merge, AI-правила) |
| [plan.md](./plan.md) | roadmap по фазам / майлстоуны |
| [ideas.md](./ideas.md) | копилка идей (ещё не задачи) |
| [discuss.md](./discuss.md) | открытые архитектурные/продуктовые вопросы + варианты решений |
| [tasks.md](./tasks.md) | master-каталог задач, нумерация A-/B-/C-/D- |
| [current-sprint.md](./current-sprint.md) | kanban текущей итерации (To Do / In Progress / In Review / Done) |
| [change-request.md](./change-request.md) | **реальные данные** текущей задачи (чистится после merge) |
| [change-request-doc.md](./change-request-doc.md) | **шаблон** change-request |

## 1. Архитектура и технический атлас

| Файл | Назначение |
|---|---|
| [architecture.md](./architecture.md) | архитектурные решения + Edge cases со ссылками на тесты |
| [context-dump.md](./context-dump.md) | карта потоков взаимодействия компонентов |
| [tech-stack.md](./tech-stack.md) | стек, версии, библиотеки |
| [db-schema.md](./db-schema.md) | формат `chunks.pkl`, `index.faiss`, BM25 in-memory, Docker volumes |
| [ui-kit.md](./ui-kit.md) | CLI визуальные соглашения (эмодзи, формат stage-логов) |
| [testing.md](./testing.md) | фреймворки, fixtures, команды прогона |
| [legacy-warning.md](./legacy-warning.md) | каталог тех-долга / костылей с приоритетами |
| [links.md](./links.md) | внутренние и внешние ссылки |

## 2. Контракты

| Файл | Назначение |
|---|---|
| [contracts/mcp-server.md](./contracts/mcp-server.md) | формальный контракт MCP-инструментов (read/list/search_document) — **жёсткий API**, не менять без миграции клиентов |

> Проект пока не имеет REST API и не общается через RMQ, поэтому
> `contracts/api/` и `contracts/events/` сейчас отсутствуют. Появятся при
> первой необходимости.

## 3. История / расследования

| Файл | Назначение |
|---|---|
| [impact-analysis.md](./impact-analysis.md) | legacy data flow + найденные проблемы до введения Advanced Pipeline |
| [search-spec.md](./search-spec.md) | спецификация Advanced Search Pipeline (hybrid + rerank + expansion) |
| [session-prompts.md](./session-prompts.md) | хронологический лог промтов пользователя при внедрении pipeline |
| [docs-setup-prompt.md](./docs-setup-prompt.md) | расширенный промт по методологии ведения docs (этот файл вырос оттуда) |

## Карта потоков (быстрая навигация)

- **Новая задача** → `change-request-doc.md` (шаблон) → заполнить `change-request.md` →
  запись в `tasks.md` → перенести в `current-sprint.md` → (опц.)
  `docs/tasks/{PREFIX}-{NN}*.md` спека.
- **Нашли костыль** → запись в `legacy-warning.md` с приоритетом 🔥/⚠/🧟.
- **Открытый вопрос** → `discuss.md` с 2-3 вариантами решения.
- **Сырая идея** → `ideas.md` (станет задачей позже).
- **Планируется фаза** → `plan.md`.
- **Нужно понять взаимодействие модулей** → `context-dump.md` →
  `architecture.md` (edge cases).
- **Нужно понять формат данных** → `db-schema.md`.
- **Нужно понять UI CLI** → `ui-kit.md`.
