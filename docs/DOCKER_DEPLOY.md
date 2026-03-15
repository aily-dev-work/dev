# Docker で Django をクラウドにデプロイする

5 分毎ジョブをクラウドで動かすために、Django を Docker でビルドし Render / Railway / Fly.io のいずれかにデプロイする手順。

---

## 前提

- リポジトリルートに `Dockerfile` と `scripts/docker_entry.sh` がある
- 起動時に `migrate --noinput` のあと `gunicorn` で待ち受け
- 環境変数で本番設定を渡す

---

## 1. 必要な環境変数（本番）

| 変数 | 説明 | 例 |
|------|------|-----|
| `DJANGO_SECRET_KEY` | 本番用の秘密鍵（必ず変更） | ランダム文字列 |
| `DJANGO_DEBUG` | 本番では `False` | `0` または `False` |
| `ALLOWED_HOSTS` | 許可するホスト（カンマ区切り） | `.onrender.com` や `xxx.fly.dev` |
| `RUN_5M_CRON_SECRET` | 5 分ジョブ用エンドポイントの認証 | ランダム文字列 |
| `PORT` | 待ち受けポート（Render/Fly が自動設定するので通常は不要） | `8000` |
| `CORS_ORIGINS` | フロントのオリジン（カンマ区切り・任意） | `https://your-app.vercel.app` |

DB はデフォルトで SQLite（`db.sqlite3`）。コンテナ再作成で消えるため、**永続化**が必要なら以下どちらか。

- **Render / Railway**: ボリューム（Persistent Disk）をマウントして `db.sqlite3` を保存
- **本番推奨**: Supabase 等の PostgreSQL を使い、`DJANGO_DB_ENGINE` と `DB_*` を設定（要 `psycopg2` 等の追加と settings の DB 分岐）

---

## 2. Render でデプロイ

1. [Render](https://render.com) にログインし、**New → Web Service**
2. リポジトリを接続（GitHub/GitLab）
3. 設定:
   - **Environment**: Docker
   - **Dockerfile のパス**: リポジトリルートの `Dockerfile` のまま
   - **Instance Type**: Free または有料
4. **Environment Variables** に上記を追加（`ALLOWED_HOSTS` に `.onrender.com` を含める）
5. **Create Web Service** でデプロイ
6. デプロイ後、URL は `https://<サービス名>.onrender.com`。5 分ジョブ用に `RUN_5M_CRON_SECRET` を設定し、cron-job.org 等で `POST https://<サービス名>.onrender.com/api/v1/cron/run-5m-evaluate/` を 5 分毎に呼ぶ

**注意**: Free プランはスリープするため、cron で叩いたときに起動するまで数十秒かかることがある。

---

## 3. Railway でデプロイ

1. [Railway](https://railway.app) にログインし、**New Project**
2. **Deploy from GitHub repo** でリポジトリを選択
3. ルートの `Dockerfile` を検出してビルドされる
4. **Variables** に環境変数を追加。`ALLOWED_HOSTS` に `*.up.railway.app` や発行されたドメインを指定
5. **Settings → Networking** で **Generate Domain** し、発行された URL を控える
6. 5 分ジョブはその URL に対して `POST .../api/v1/cron/run-5m-evaluate/` を cron で呼ぶ

---

## 4. Fly.io でデプロイ

1. [Fly.io](https://fly.io) にログイン（`fly auth login`）
2. リポジトリルートで:
   ```bash
   fly launch
   ```
   - Dockerfile を検出するか聞かれたら Yes
   - App name / Region を設定
3. 環境変数を設定:
   ```bash
   fly secrets set DJANGO_SECRET_KEY=xxx DJANGO_DEBUG=0
   fly secrets set ALLOWED_HOSTS=xxx.fly.dev
   fly secrets set RUN_5M_CRON_SECRET=xxx
   ```
4. デプロイ:
   ```bash
   fly deploy
   ```
5. URL は `https://<app名>.fly.dev`。cron で `POST https://<app名>.fly.dev/api/v1/cron/run-5m-evaluate/` を 5 分毎に呼ぶ

---

## 5. ローカルで Docker イメージを確認する

```bash
# ビルド
docker build -t stocks-web .

# 実行（ポート 8000、環境変数は必要に応じて）
docker run --rm -p 8000:8000 \
  -e DJANGO_DEBUG=0 \
  -e ALLOWED_HOSTS=localhost,127.0.0.1 \
  -e RUN_5M_CRON_SECRET=test-secret \
  stocks-web
```

ブラウザで `http://localhost:8000/admin/` や `http://localhost:8000/api/v1/` にアクセスして確認。

---

## 6. 5 分ジョブの cron 設定

デプロイ後、[cron-job.org](https://cron-job.org) などで:

- **URL**: `https://<あなたのDjangoのURL>/api/v1/cron/run-5m-evaluate/`
- **Method**: POST
- **Interval**: 5 分
- **Custom header**: `X-Cron-Secret: <RUN_5M_CRON_SECRET>`

詳細は [stocks/docs/CRON_CLOUD.md](../stocks/docs/CRON_CLOUD.md) を参照。
