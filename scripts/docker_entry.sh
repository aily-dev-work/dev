#!/bin/sh
set -e
cd /app
# migrate をバックグラウンドで実行し、すぐに gunicorn を起動（Render の起動タイムアウト対策）
python manage.py migrate --noinput &
exec gunicorn webapp.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 2
