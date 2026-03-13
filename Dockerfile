# 最小構成: ローカル開発・起動確認用
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 初回は migrate してから runserver（docker-compose で上書き可能）
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
