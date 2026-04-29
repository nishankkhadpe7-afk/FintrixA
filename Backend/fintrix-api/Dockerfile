FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY Backend/fintrix-api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY Backend/fintrix-api/backend /app/backend
COPY Backend/fintrix-api/docs /app/docs
COPY Backend/fintrix-api/regulations /app/regulations
COPY Backend/fintrix-api/alembic /app/alembic
COPY Backend/fintrix-api/alembic.ini /app/alembic.ini

EXPOSE 8000

COPY Backend/fintrix-api/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
