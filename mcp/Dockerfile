FROM python:3.12-slim

WORKDIR /app

# System deps (if needed for embeddings, e.g. libsqlite3)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* requirements.txt* ./

# If using Poetry
# RUN pip install --no-cache-dir poetry && poetry install --no-interaction --no-root
# Or plain requirements
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp ./mcp

ENV PYTHONUNBUFFERED=1
ENV NATS_URL=nats://nats:4222
ENV EMBEDDING_MODEL=openai/text-embedding-3-small

CMD ["python", "-m", "mcp.server.rpc_server"]