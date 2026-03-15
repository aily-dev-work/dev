#!/bin/sh
set -e
cd /app
# migrate を先に同期的に実行（完了してから gunicorn を起動する）
python manage.py migrate --noinput
# スーパーユーザー作成はバックグラウンド（gunicorn 起動をブロックしない）
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  (python manage.py createsuperuser --noinput 2>/dev/null || true) &
fi
exec gunicorn webapp.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 2
