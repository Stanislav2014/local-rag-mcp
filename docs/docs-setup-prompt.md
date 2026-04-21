# DOCS Setup Prompt — расширенная версия

Исторический документ: на каком промте выросла текущая структура `docs/` и какие правила/конвенции в неё упакованы. Полезно для будущих сессий / новых проектов / ревью структуры.

## Исходный промт (2026-04-14)

Первое сообщение сессии от юзера (сохранено дословно):

```
0. Установи скилл отсюда https://github.com/forrestchang/andrej-karpathy-skills
0.1 Посмотри структуру _docs и _board
    Посмотри как ведуться задачи и какие процессы по ведению документации и прогрессу используются в проекте
    https://github.com/larchanka/manbot/tree/main

1. Создай нужную структура и заполни файлы данными
   docs/
       tech-stack.md
       architecture.md - edgecases
       db-schema.md
       links.md - documentation
       ui-kit.md
       current-sprint.md (задачи которые делаются в текущий итерации, на момент создания может быть пустой)

2. Создай файлы
   docs/context-dump.md       - тут должно быть описано все про то как взаимодействуют структуры между собой
   docs/change-request.md     - сюда записывается то на что повлияет данная задача
   docs/legacy-warning.md     - сюда записываются тех долг, костыли
```

## Расширенный промт (канонический, на основе того как реально выросла структура)

Ниже — промт который можно использовать **с нуля** в новом проекте или пересоздать структуру с пониманием всех нюансов. Это не просто «создать файлы», а **полная методология ведения docs + задач + архитектурной документации**.

---

### PROMPT:

```
Нужно организовать документацию проекта по manbot-вдохновлённой структуре
+ DocHub integration + TDD методология. Все артефакты в `docs/`.

## 0. Установка skills

Установить в .claude/skills/:
- karpathy-guidelines — behavioural rules (simplicity, surgical changes,
  goal-driven execution). Source: https://github.com/forrestchang/andrej-karpathy-skills

Изучить manbot как образец ведения задач:
https://github.com/larchanka/manbot/tree/main (разделы _docs и _board)

## 1. Базовая структура docs/

### Уровень — индекс / стратегия / доска

docs/
├── README.md           — индекс всех документов + навигация
├── project.md          — обзор проекта на 1 экран (назначение, продукты, стек,
│                        карта «где что искать»)
├── instructions.md     — процесс ведения задач (workflow TDD, branch naming,
│                        commit/push/merge, post-merge, AI-правила)
├── plan.md             — roadmap по фазам / майлстоуны
├── ideas.md            — копилка идей (ещё не задачи)
├── discuss.md          — открытые архитектурные / продуктовые вопросы с
│                        вариантами решений
├── tasks.md            — master-каталог задач по фазам, нумерация A-/B-/C-/D-
├── current-sprint.md   — kanban текущей итерации (To Do / In Progress /
│                        In Review / Done)
├── change-request.md   — **реальные данные** текущей задачи (заполняется при
│                        старте, очищается после merge)
├── change-request-doc.md — **шаблон** для change-request (образец оформления)
└── tasks/              — детальные спеки задач (файлы по наименованию
                          {PREFIX}-{NN}_{TICKET}_{SLUG}.md, см. ниже)

### Уровень — архитектура

docs/
├── architecture.md     — архитектурные паттерны + **Edge cases** секция
│                        (hidden constraints, двойные gating, race conditions)
├── context-dump.md     — **карта всех потоков взаимодействия** компонентов
│                        (flows с конкретными file:line). Это главный
│                        технический атлас — обновлять после каждого
│                        значимого исследования
├── tech-stack.md       — стек (backend + frontend + infra), версии, dev-ports
├── api-routing.md      — API routing narrative (endpoints, field mapping,
│                        controller hierarchy)
├── external-systems.md — RMQ narrative (очереди, handler-ы, статусные переходы)
├── ui-kit.md           — UI компоненты, composables, стилизация, gotchas
├── testing.md          — тестовые фреймворки, fixtures, команды
├── legacy-warning.md   — каталог тех-долга / костылей / known issues
│                        (приоритеты 🔥 критичные / ⚠ архитектурные / 🧟 стиль)
└── links.md            — внутренние и внешние ссылки, официальные доки стека,
                          ссылки на team tools (wiki, DocHub, tracker)

### Уровень — split по доменам

docs/db-schema/              ← схема БД по доменам (не монолит)
├── README.md               индекс + как регенерировать DDL
├── request.md              центральный домен
├── auth.md                 users, tokens, sessions
├── contracts.md            контракты
├── auto.md                 auto справочники
├── ab-test.md              A/B тесты
├── references.md           справочники (важно: помечать source — LK vs SMDS)
└── payment.md              платежи

docs/contracts/              ← формальные контракты API / Events / External
├── README.md
├── api/                    REST endpoints (по файлу на endpoint)
│   ├── get-request.md
│   ├── verification.md
│   ├── file-upload.md
│   ├── auth.md
│   └── ...
├── events/                 RMQ events (по файлу на event)
│   ├── event-NNNN-*.md
│   └── ...
└── external/               внешние системы (по файлу на систему)
    ├── <system>.md         — главный markdown с описанием
    ├── <system>/           — (опционально) sub-folder с синхронизированными
    │   └── *.yaml          YAML-исходниками из arch/DocHub
    └── ...

### Уровень — setup / workflows / knowledge

docs/setup/
├── getting-started.md      онбординг разработчика
├── configuration.md        конфиги
└── ssl-carm-corp-setup.md  ssl / certs setup

docs/workflows/              ← продуктовые workflow
├── pdl-workflow.md
├── installment-workflow.md
├── biginstallment-workflow.md
└── pts-workflow.md

docs/duty-knowledge/         ← kb инцидентов (по дате)
├── README.md
└── YYYY-MM-DD_slug.md

docs/archive/                ← устаревшие документы
└── README.md               — каталог что когда архивировали, почему

## 2. Конвенции (критично!)

### 2.1 Task prefixes — нумерация
В `tasks.md` и именах файлов `docs/tasks/*.md` используй manbot-style префикс:
- **A-** — Phase A: критичные дефекты (P0/P1)
- **B-** — Phase B: баги исправленные (история)
- **C-** — Phase C: технический долг (связан с TD-XXX)
- **D-** — Phase D: фичи / enhancements

Формат файла: `{PREFIX}-{NN}_{TICKET}_{SHORT_SLUG}.md`
Примеры: `A-01_LK-2642_FEDOR_CANCEL_NO_COPY.md`, `D-01_LK-2618_SBER_AUTO_PILOT.md`

Нумерация сквозная внутри фазы, гапы разрешены.

### 2.2 Branch naming
| Префикс | Когда |
|---------|-------|
| `bugfix/LK-XXXX` | дефекты |
| `feature/BAU/LK-XXXX` | фичи < 20 рабочих дней (BAU = Business As Usual) |
| `feature/CR/LK-XXXX` | фичи > 20 дней (CR = Change Request) |
| `feature/TD/LK-XXXX` | тех-долг (всегда `LK-` префикс, не `TD-`) |

### 2.3 TDD mandatory
Каждая строка кода покрывается тестом, написанным ДО неё:
1. **RED** — падающий тест
2. **GREEN** — минимальный код чтобы тест проходил
3. **REFACTOR** — SOLID/DRY/KISS, без расширения scope

НЕ батчить тесты в конец задачи — они идут параллельно с каждым step-ом.

### 2.4 Karpathy guidelines
- Simplicity first — минимум кода, ноль speculative features
- Surgical changes — менять только то что нужно для задачи
- Think before coding — surface assumptions, ask if unclear
- Goal-driven — verifiable success criteria

### 2.5 Комментарии в коде
- **Дефолт — не писать комментариев.** Имена переменных объясняют WHAT
- Только если WHY non-obvious: hidden constraint, workaround, subtle invariant
- **НЕ писать** в коде: tracker-id (LK-XXXX), описания «used by X», даты
  — это живёт в commit message / PR / task spec и гниёт в коде
- **Пример допустимого комментария:**
  `// mixin не подключён — SVG иконки не экспортированы` (hidden constraint)

### 2.6 Action items tracking
Если задача имеет pending sub-items, которые точно нужно сделать — создавать
**concrete action items** (не uncertainty!) в task spec с:
- Уникальным ID (A1, A2, ...)
- Описанием текущего состояния
- 2-3 вариантами реализации (если применимо)
- Verify-критериями
- Владельцем
- Зависимостями

Дубликат в `change-request.md § Pending action items` как checkbox-лист.

## 3. Workflow задачи (TDD + process)

```
1. Новая задача → скопировать структуру из change-request-doc.md в
   change-request.md, заполнить
2. Добавить запись в tasks.md (в нужную фазу) → перенести в current-sprint.md
3. Создать спеку docs/tasks/{PREFIX}-{NN}_{TICKET}_*.md (если сложная)
4. Research (параллельные агенты если need): grep codebase, git log,
   смежные задачи, внешние зависимости
5. Составить Uncertainty list (что неясно) + Action items (что точно делать)
6. Phase 0 Research → Phase 1 Backend foundation → Phase 2 Frontend theme
   → Phase 3 UX gating → Phase 4 Backend gating → Phase 5 Testing →
   Phase 6 Review & docs
7. Каждое изменение: RED → GREEN → REFACTOR
8. В конце каждой фазы — checkpoint (что работает, что не работает)
9. После merge: обновить changelog/history в task spec + tasks.md ✅ + memory
```

## 4. Память между сессиями

Файлы в `memory/MEMORY.md` (индекс) + `memory/<category>_<name>.md` (детали).
Категории: `user` / `feedback` / `project` / `reference`.

После значимой задачи: добавить запись про её итог + root cause + решение.

## 5. DocHub / Architecture as Code integration

Если команда ведёт отдельный arch-репозиторий (AaC в стиле DocHub) — это
**canonical source** для внешних систем, интеграций, C4-схем.

LKP2 docs-правило:
- **НЕ дублировать** бизнес-описание — ссылаться на arch
- **Копировать YAML-исходники** релевантные для проекта в
  `docs/contracts/external/<system>/` с sync-header:

```yaml
# ─────────────────────────────────────────────────────────
# SYNCED from: /path/in/arch/...
# Source: DocHub AaC — https://gitlab.../arch/aac
# Last synced: YYYY-MM-DD
# ⚠ Do NOT edit here — update in arch repo и re-sync.
# ─────────────────────────────────────────────────────────
```

Это предотвращает зависимость от наличия arch checkout у каждого разработчика.

## 6. Контракты — формальные описания

Каждый внешний interface должен иметь файл в `docs/contracts/`:

### API endpoint:
Direction, protocol, endpoint, request/response shape, error codes,
server processing (file:line), client processing, gotchas,
related code, history.

### RMQ event:
Direction, consumer worker (supervisor .ini), listener class,
handler class, payload shape, side effects, related code.

### External system:
Direction, protocol, SDK/library, use cases, configuration,
auth mechanism, gotchas (security, rate limits, etc.), related code.

## 7. Что НЕ делать (anti-patterns)

- **НЕ дублировать** source of truth (arch/DocHub → копировать YAML с sync-header,
  а не переписывать своими словами)
- **НЕ создавать** документацию для процессов которые не практикуются
  (например, audit.md если audit-ы никогда не проводятся)
- **НЕ смешивать** template и реальные данные (поэтому change-request.md
  ↔ change-request-doc.md разделены)
- **НЕ батчить** тесты в конец задачи (TDD = test-first parallel)
- **НЕ писать** в коде tracker-id / даты / описания задач
- **НЕ хардкодить** magic numbers без комментария-объяснения WHY
- **НЕ делать** разом большие PR — surgical changes
- **НЕ забывать** про regression на соседних продуктах/sub-types

## 8. Процесс обновления этого файла

Если при работе находится новый паттерн/анти-паттерн/конвенция — дополнять
этот промт. Цель: чтобы следующая сессия (или новый проект) мог использовать
его как стартовую точку без необходимости переизобретать структуру.
```

---

## Что изменилось с исходного промта

| Аспект | Исходный | Финальный |
|--------|----------|-----------|
| **Файлов в docs/** | 9 | ~60 (с учётом tasks/, db-schema/, contracts/, setup/, workflows/, archive/) |
| **Структура** | плоский список | 6 уровней + subfolder split |
| **Нумерация задач** | — | A-01/B-01/C-01/D-01 префиксы |
| **Branch naming** | — | bugfix/BAU/CR/TD конвенция |
| **TDD** | — | mandatory, test-first |
| **Karpathy rules** | только skill install | explicit rules про комментарии/simplicity |
| **change-request split** | один файл | `change-request.md` (данные) + `change-request-doc.md` (шаблон) |
| **Task specs** | — | `docs/tasks/*.md` с детализацией |
| **Master task catalog** | только current-sprint | `tasks.md` (всё) + `current-sprint.md` (только итерация) |
| **Контракты** | — | `contracts/api,events,external` |
| **DB schema** | один файл | split по доменам |
| **DocHub integration** | — | YAML копии с sync-header |
| **Memory system** | — | `memory/MEMORY.md` + persistence |
| **Action items** | — | concrete TODO vs uncertainty разделены |
| **Action items trackability** | — | discoverable из 3 мест (comment / task spec / change-request) |

## Источники вдохновения

- **manbot** (https://github.com/larchanka/manbot/tree/main): `_docs/` + `_board/` с task spec файлами, `_BOARD.md` канбан, `INSTRUCTIONS.md` workflow
- **karpathy-guidelines** (https://github.com/forrestchang/andrej-karpathy-skills): поведенческие правила
- **DocHub AaC**: Architecture as Code — canonical source для внешних систем

## См. также

- [docs/README.md](./README.md) — финальный индекс docs
- [docs/instructions.md](./instructions.md) — task workflow в живом виде
- [docs/change-request-doc.md](./change-request-doc.md) — образец change-request
- [docs/tasks.md](./tasks.md) — пример master-каталога задач с префиксами
