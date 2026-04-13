FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src/requirements.txt /app/src/requirements.txt
RUN pip install -r /app/src/requirements.txt

COPY src /app/src
COPY tests /app/tests
COPY docs /app/docs

ENV PYTHONPATH=/app/src \
    OLLAMA_URL=http://ollama:11434/api/generate

WORKDIR /app/src

CMD ["python", "main.py"]
