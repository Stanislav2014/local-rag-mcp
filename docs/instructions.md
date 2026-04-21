# Instructions — Workflow ведения задач

Как **работать** с этим проектом: от идеи до merged-PR. Методология — адаптация
manbot `_board/INSTRUCTIONS.md` + karpathy-guidelines + TDD.

## 1. Жизненный цикл задачи

```
   идея ─► ideas.md
           │
           ▼  (прошла фильтр актуальности)
   open question ─► discuss.md  ── вариант выбран ──►
                                                       │
                                                       ▼
                                    change-request-doc.md (шаблон)
                                                       │ копируем
                                                       ▼
                                            change-request.md (реальные данные)
                                                       │
                                                       ▼
                                                   tasks.md  (добавить запись)
                                                       │
                                                       ▼
                                           current-sprint.md (In Progress)
                                                       │
                                                       ▼  [опц. для сложных]
                                       docs/tasks/{PREFIX}-{NN}_*.md (детальная спека)
                                                       │
                                                       ▼
                                  Research → Plan → TDD (RED→GREEN→REFACTOR)
                                                       │
                                                       ▼
                                              PR → code review
                                                       │
                                                       ▼
                                                    merge
                                                       │
                                                       ▼
                                  Done (current-sprint.md) + ✅ в tasks.md
                                                       │
                                                       ▼
                                  Очистить change-request.md (оставить только шаблон
                                  из change-request-doc.md как placeholder)
```

## 2. Конвенции

### 2.1 Префиксы задач (manbot-style)

| Фаза | Префикс | Когда |
|---|---|---|
| A | `A-01`, `A-02`, ... | **Критичные дефекты** (P0/P1): прод упал, данные теряются, security |
| B | `B-01`, `B-02`, ... | **Исправленные баги** (история) |
| C | `C-01`, `C-02`, ... | **Тех-долг** / рефакторинг (связан с записью из `legacy-warning.md`) |
| D | `D-01`, `D-02`, ... | **Фичи** / enhancements |

Нумерация сквозная внутри фазы, **пропуски разрешены** (если задача удалена /
переименована, номер не переиспользуем).

Файл детальной спеки (если есть): `docs/tasks/{PREFIX}-{NN}_{TICKET}_{SLUG}.md`.
Пример: `D-01_LR-2601_ADVANCED_PIPELINE.md`.

### 2.2 Branch naming

У проекта пока нет внешнего tracker-а (Jira/Linear), поэтому используется
свой префикс `LR-NNNN` (Local-Rag).

| Префикс ветки | Когда | Пример |
|---|---|---|
| `bugfix/LR-NNNN` | критичный дефект или исправленный баг (фаза A/B) | `bugfix/LR-0002` |
| `feature/BAU/LR-NNNN` | фича < 20 дней (Business As Usual) | `feature/BAU/LR-0101` |
| `feature/CR/LR-NNNN` | фича > 20 дней (Change Request) | `feature/CR/LR-0001` |
| `feature/TD/LR-NNNN` | тех-долг (фаза C) | `feature/TD/LR-0201` |

Единственная существующая ветка `feature/advanced-search-pipeline` названа
по-старому (до появления этой конвенции); новые ветки — по схеме выше.

### 2.3 Commit message

```
<type>: <imperative, 50 char>

<body, WHY not WHAT, по-русски или по-английски>

Co-Authored-By: <если уместно>
```

Типы: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `build`.

### 2.4 TDD (обязательно)

Каждая строка кода покрывается тестом, написанным **до** неё:

1. **RED** — падающий тест (проверили глазами: именно там и именно так)
2. **GREEN** — минимальный код чтобы тест проходил
3. **REFACTOR** — SOLID/DRY/KISS, без расширения scope

**Не батчить** тесты в конец задачи. Тесты идут параллельно с каждым step-ом.

### 2.5 Karpathy guidelines

- **Simplicity first** — минимум кода, ноль speculative features
- **Surgical changes** — менять только то, что нужно для задачи
- **Think before coding** — surface assumptions, спроси если неясно
- **Goal-driven** — verifiable success criteria

### 2.6 Комментарии в коде

- **Дефолт — не писать комментариев.** Имена переменных объясняют WHAT.
- Только если WHY non-obvious: hidden constraint, workaround, subtle invariant.
- **НЕ писать** в коде: tracker-id (LR-NNNN), описания «used by X», даты —
  это живёт в commit message / PR / task spec и гниёт в коде.
- **Пример допустимого:**
  ```python
  # LLM-rewrite отключён для non-ASCII: маленькие модели переводят запрос
  # в английский, ломая и BM25, и эмбеддинги
  if self.llm is not None and q.isascii():
      ...
  ```

### 2.7 Action items

Если задача имеет pending sub-items, которые точно нужно сделать:

- Создать **concrete action items** (не uncertainty!) в task spec / в
  `change-request.md § Pending action items` как checkbox-лист.
- Каждый item: уникальный ID (A1, A2…), текущее состояние, 2-3 варианта
  реализации (если применимо), verify-критерии.

Путать с **uncertainty** (что неясно и нужно сначала разобраться) нельзя:
uncertainty идёт в `discuss.md`, action items — в план задачи.

## 3. Workflow одной задачи (чек-лист)

```
[ ] 1. Скопировать шаблон change-request-doc.md → change-request.md
[ ] 2. Заполнить change-request.md: затронутые файлы, API, риски, тесты
[ ] 3. Добавить запись в tasks.md (в нужную фазу)
[ ] 4. Перенести в current-sprint.md → In Progress
[ ] 5. (опц.) docs/tasks/{PREFIX}-{NN}_*.md для больших задач
[ ] 6. Research (parallel grep, git log, смежные задачи)
[ ] 7. Uncertainty list → discuss.md, Action items → change-request.md
[ ] 8. TDD: RED → GREEN → REFACTOR, step by step
[ ] 9. Прогнать pytest (локально) + e2e smoke если надо
[ ] 10. Создать PR (или push в feature-ветку если без PR)
[ ] 11. Code review → фиксы → merge
[ ] 12. Обновить current-sprint.md → Done, tasks.md → ✅
[ ] 13. Очистить change-request.md (оставить placeholder)
[ ] 14. Если нашли новый костыль — запись в legacy-warning.md
```

## 4. AI / LLM rules

Правила для Claude Code / других LLM-агентов при работе в этом репо:

1. **Skills first.** Перед любым действием проверить `/plugin` skills
   (`karpathy-guidelines`, `superpowers:*`) — если применимы, использовать.
2. **Verification before completion.** Никогда не объявлять «готово» без
   свежего вывода команды верификации (pytest, docker build и т. п.).
3. **TDD.** Для любых правок кода — сначала тест. Агент должен показать RED
   фазу (падающий тест) до зелёной.
4. **Не трогать контракты.** `src/mcp/server.py` — жёсткий контракт, любое
   изменение = отдельная задача с миграцией клиентов.
5. **Не удалять файлы молча.** Обсудить с пользователем перед деструктивными
   операциями (git reset --hard, удаление файлов, rm -rf).
6. **Не лгать про результат.** Если верификация провалена — сказать явно.
7. **Логи на русском / ответы на русском.** Модель по умолчанию — `qwen3:0.6b`,
   промпт локализован (`src/rag/query.build_prompt`).

## 5. Post-merge

После merge ветки в `main`:

1. Удалить merged-ветку (`git branch -d`, `git push origin --delete`).
2. Обновить `current-sprint.md` — перенести задачу в Done.
3. Обновить `tasks.md` — пометить ✅ + дописать commit SHA и дату.
4. Если задача открыла новый тех-долг — запись в `legacy-warning.md`.
5. Очистить `change-request.md` (подготовить для следующей задачи).
6. Если методология была улучшена — дописать в `docs-setup-prompt.md`.
