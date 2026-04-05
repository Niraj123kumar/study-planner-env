FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . /app/server/
COPY ../models.py /app/models.py
COPY ../__init__.py /app/__init__.py

WORKDIR /app

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
