FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY docs /app/docs
COPY regulations /app/regulations
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
