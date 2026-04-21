# Links & References

Внешняя документация, на которой основаны решения и реализации в проекте.

## Алгоритмы

| Тема | Ссылка |
|---|---|
| Reciprocal Rank Fusion (Cormack, Clarke, Buettcher 2009) | https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf |
| BM25 Okapi — оригинальная статья (Robertson et al.) | https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf |
| RAG — оригинальная статья (Lewis et al. 2020, Meta AI) | https://arxiv.org/abs/2005.11401 |

## Библиотеки

| Библиотека | Docs |
|---|---|
| `rank_bm25` | https://github.com/dorianbrown/rank_bm25 |
| `sentence-transformers` | https://www.sbert.net/ |
| `faiss` | https://github.com/facebookresearch/faiss/wiki |
| `CrossEncoder` (sentence-transformers) | https://www.sbert.net/examples/applications/cross-encoder/README.html |
| `tiktoken` | https://github.com/openai/tiktoken |
| `fastmcp` | https://github.com/jlowin/fastmcp |
| `pypdf` | https://pypdf.readthedocs.io |
| `python-docx` | https://python-docx.readthedocs.io |
| `rich` | https://rich.readthedocs.io |
| `pytest` | https://docs.pytest.org |

## Модели

| Модель | Ссылка | Назначение |
|---|---|---|
| `all-MiniLM-L6-v2` | https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 | Эмбеддинги (384-dim) |
| `BAAI/bge-reranker-base` | https://huggingface.co/BAAI/bge-reranker-base | Cross-encoder reranker |
| `qwen3:0.6b` | https://ollama.com/library/qwen3 | Основной локальный LLM |
| `qwen2.5:7b` | https://ollama.com/library/qwen2.5 | Альтернатива (лучше с русским) |

## Сервисы / инструменты

| Сервис | Ссылка |
|---|---|
| Ollama | https://ollama.com/ |
| Docker | https://docs.docker.com/ |
| Docker Compose | https://docs.docker.com/compose/ |
| FastMCP — протокол MCP | https://modelcontextprotocol.io/ |

## Внутренние документы проекта

| Документ | Описание |
|---|---|
| [`../README.md`](../README.md) | Корневой README (описание + запуск) |
| [`tech-stack.md`](./tech-stack.md) | Тех. стек |
| [`architecture.md`](./architecture.md) | Архитектурные решения + edge-cases |
| [`db-schema.md`](./db-schema.md) | Формат `chunks.pkl` и `index.faiss` |
| [`ui-kit.md`](./ui-kit.md) | UI-kit CLI |
| [`current-sprint.md`](./current-sprint.md) | Задачи текущей итерации |
| [`context-dump.md`](./context-dump.md) | Runtime-дамп взаимодействий компонентов |
| [`change-request.md`](./change-request.md) | Журнал «что ломает какая задача» |
| [`legacy-warning.md`](./legacy-warning.md) | Тех.долг и костыли |
| [`impact-analysis.md`](./impact-analysis.md) | Legacy data-flow + найденные проблемы |
| [`search-spec.md`](./search-spec.md) | Спецификация Advanced Search Pipeline |
| [`session-prompts.md`](./session-prompts.md) | Промпты пользователя из сессии внедрения pipeline |

## Вдохновение для структуры документации

| Источник | Что взято |
|---|---|
| [larchanka/manbot](https://github.com/larchanka/manbot) | Разделение `_docs` (стабильная документация) и `_board` (текущее состояние проекта, спринты, аудиты) |
| [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) | Принципы: Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution |
