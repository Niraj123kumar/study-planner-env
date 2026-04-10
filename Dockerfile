FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "openenv-core[core]>=0.2.2" \
    uvicorn \
    fastapi \
    httpx \
    pydantic \
    jinja2 \
    aiofiles \
    openai

COPY models.py .
COPY __init__.py .
COPY server/ ./server/
COPY static/ ./static/
COPY templates/ ./templates/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
# v2.1.0
