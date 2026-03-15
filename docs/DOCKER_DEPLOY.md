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
| `CORS_ORIGINS` | フロントのオリジン（カンマ区切り）。Vercel 等から API を呼ぶ場合は**必須**（未設定だとブラウザが CORS でブロックする） | `https://dev-frontend-five.vercel.app` |
| `DJANGO_SUPERUSER_USERNAME` | 起動時に自動作成するスーパーユーザーのユーザー名（任意・Shell が使えない無料枠で便利） | `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | 上記スーパーユーザーのパスワード（上記とセットで設定すること） | 強めのパスワード |
| `DJANGO_SUPERUSER_EMAIL` | 上記のメール（任意・空でも可） | `admin@example.com` |

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
   - **Start Command**: 空のまま（Dockerfile の `CMD` = `scripts/docker_entry.sh` を使う）
   - **Release Command** / **Pre-Deploy Command**（画面によって表記が異なる）: **空のまま**にする。ここに `migrate` などを書くと、サービスが「live」になったあとにメインプロセスに TERM が送られ、Gunicorn が落ちることがある。migrate は `docker_entry.sh` 内で起動前に実行される。
   - **Docker Command**: 空のまま（Dockerfile の `CMD` を使う）。上書きする場合は `migrate` を先に実行してから gunicorn を起動する内容にする。
4. **Environment Variables** に上記を追加（`ALLOWED_HOSTS` に `.onrender.com` を含める）
5. **Create Web Service** でデプロイ
6. デプロイ後、URL は `https://<サービス名>.onrender.com`。5 分ジョブ用に `RUN_5M_CRON_SECRET` を設定し、cron-job.org 等で `POST https://<サービス名>.onrender.com/api/v1/cron/run-5m-evaluate/` を 5 分毎に呼ぶ

**注意**: Free プランはスリープするため、cron で叩いたときに起動するまで数十秒かかることがある。

### 「Your service is live」の直後に Shutting down になる場合

ログで `Your service is live` のあとすぐ `Shutting down: Master` が出る場合は、デプロイ前／起動前コマンドがメインプロセスに影響していることがあります。

- **Settings** → **Build & Deploy** のあたりで次を確認する:
  - **Pre-Deploy Command**: 何か入っていれば**空にする**。migrate は `docker_entry.sh` 内で実行されるため不要です。
  - **Docker Command**: 空のまま（Dockerfile の `CMD` = `scripts/docker_entry.sh` を使う）。ここでコマンドを上書きしている場合は、migrate 実行後に gunicorn がずっと動く形になっているか確認する。
- 変更したら **Save** して再デプロイする。

**補足**: ログで `Handling signal: term` → `Worker exiting` → `Shutting down: Master` の直後に `Detected service running on port 8000` が出ることがある。このとき TERM は**前のインスタンス（古いデプロイ）**に送られており、`Detected service running` は**新しいインスタンス**の起動検知である場合がある。数分後に URL にアクセスしてサービスが応答するか確認するとよい。

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
