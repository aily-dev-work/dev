# ローカル開発・本番デプロイ兼用
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 本番: migrate 後に gunicorn。PORT は Render/Fly 等が設定（未設定時 8000）
RUN chmod +x /app/scripts/docker_entry.sh
CMD ["/app/scripts/docker_entry.sh"]
