#1
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --user --no-cache-dir -r requirements.txt

#2
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app app

WORKDIR /app

COPY --from=builder /root/.local /home/app/.local

COPY --chown=app:app . .

ENV PATH=/home/app/.local/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

USER app

CMD ["python", "worker.py"]