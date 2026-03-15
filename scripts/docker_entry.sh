#!/bin/sh
set -e
cd /app
# migrate をバックグラウンドで実行
python manage.py migrate --noinput &
# スーパーユーザー作成もバックグラウンド（migrate 完了待ちのあと実行）。gunicorn は待たない
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  (sleep 15; python manage.py createsuperuser --noinput 2>/dev/null || true) &
fi
# すぐに gunicorn を起動（Render のヘルスチェックが早く通るようにする）
exec gunicorn webapp.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 2
