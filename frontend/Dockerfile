FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends nginx && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates/ templates/
COPY static/ static/
COPY nginx.conf /etc/nginx/nginx.conf
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
# The same container hosts Nginx and Gunicorn. Terminate both on exit.
CMD ["/bin/sh","-c","gunicorn -w 2 -b 127.0.0.1:8000 app:app & pid=$!; trap 'kill $pid 2>/dev/null || true' TERM INT EXIT; nginx -g 'daemon off;' & nginxpid=$!; wait $nginxpid; kill $pid 2>/dev/null || true; wait $pid 2>/dev/null || true"]
