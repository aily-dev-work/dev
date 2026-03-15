#!/bin/sh
set -e
cd /app
# migrate をバックグラウンドで実行し、すぐに gunicorn を起動（Render の起動タイムアウト対策）
python manage.py migrate --noinput &
# 環境変数があればスーパーユーザーを自動作成（無料枠で Shell が使えない場合の代替）
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  sleep 5
  python manage.py createsuperuser --noinput 2>/dev/null || true
fi
exec gunicorn webapp.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 2
