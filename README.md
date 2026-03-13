# webapp（Django プロジェクト）

個人用 Web アプリの開発基盤。Django 6 + Django REST Framework、SQLite（開発）、将来 MariaDB 対応を想定。

## 必要な環境

- Python 3.12+
- （任意）Docker / Docker Compose

## ローカル開発（仮想環境）

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # 未導入時のみ
python manage.py migrate
python manage.py runserver
```

- 管理画面: http://127.0.0.1:8000/admin/
- 認証 URL: `/accounts/login/`, `/accounts/logout/` など（ログイン後は `/admin/` にリダイレクト）

**初回のみ** 管理者ユーザを作成:

```powershell
python manage.py createsuperuser
```

## Docker で起動

（Docker がインストール済みで PATH に通っている場合）

```powershell
cd d:\dev
docker compose up --build
```

初回は `migrate` が自動実行され、続けて runserver が起動します。  
ブラウザで http://127.0.0.1:8000/admin/ を開き、管理者が未作成ならコンテナ内で:

```powershell
docker compose exec web python manage.py createsuperuser
```

## 主な設定

- **言語・タイムゾーン**: `ja` / `Asia/Tokyo`
- **DB**: 開発は SQLite。MariaDB に切り替える場合は環境変数 `DJANGO_DB_ENGINE=mysql` と `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` を設定。
- **認証**: Django 標準の認証。ログイン後のリダイレクト先は `/admin/`。
- **DRF**: 導入済み。API 設計・アプリ分割は今後追加。

## プロジェクト構成

```
d:\dev\
  .venv/              # 仮想環境
  .git/
  .gitignore
  .dockerignore
  Dockerfile
  docker-compose.yml
  manage.py
  requirements.txt
  webapp/             # 設定パッケージ
    settings.py
    urls.py
    wsgi.py
    asgi.py
  db.sqlite3          # 開発用 DB（作成後）
```

アプリケーションは後から `python manage.py startapp <app_name>` で追加してください。
