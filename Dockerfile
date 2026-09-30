FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

# Seed demo data on first boot if the database is empty, then serve.
EXPOSE 8000
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
