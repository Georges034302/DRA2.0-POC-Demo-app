FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 5001
CMD ["sh", "-c", "python init-db.py && exec gunicorn -w 2 -b 0.0.0.0:5001 --timeout 30 app:app"]
