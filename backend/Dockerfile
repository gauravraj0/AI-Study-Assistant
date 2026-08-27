FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY assets ./assets
COPY tools ./tools

ENV DATA_DIR=/data
ENV VECTOR_STORE_PATH=/data/vectors
ENV SEED_DEMO=true

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
