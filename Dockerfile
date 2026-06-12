FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8001
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV NOTIFY_ERP_AUTO=0

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . .

EXPOSE 8001
CMD ["sh", "scripts/start_server.sh"]
