FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir --timeout=200 --retries=10 -r requirements.txt

COPY . .

CMD ["bash", "-c", "set -e && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]