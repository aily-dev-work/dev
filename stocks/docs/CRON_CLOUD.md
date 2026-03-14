# 5 分毎ジョブのクラウド自動実行（Vercel / Supabase / Docker）

5 分足の取得と判定をクラウド上で自動実行する方法。**HTTP エンドポイント** を 5 分毎に呼ぶ方式と、**Docker 内で cron を回す方式** を説明する。

---

## 共通: HTTP エンドポイント

Django に次のエンドポイントを用意している。

- **URL**: `POST /api/v1/cron/run-5m-evaluate/`
- **認証**: `X-Cron-Secret` ヘッダー（またはクエリ `?secret=...`）が環境変数 `RUN_5M_CRON_SECRET` と一致する場合のみ実行。未設定なら 403。
- **取得スキップ**: `?no_fetch=1` で 5 分足取得をスキップし、既存データだけで判定のみ実行。

```bash
# 例（シークレットを環境変数に設定済みとする）
curl -X POST "https://your-api.example.com/api/v1/cron/run-5m-evaluate/" \
  -H "X-Cron-Secret: YOUR_RUN_5M_CRON_SECRET"
```

レスポンス例:

```json
{
  "stocks_count": 6,
  "5m_created": 12,
  "signals_updated": 6,
  "bar_start": "2026-03-14T14:35:00+00:00",
  "errors": []
}
```

---

## 1. Docker でバックエンドを動かす（推奨）

Django を Docker で起動し、**外部の cron サービス** で上記 URL を 5 分毎に POST する形が扱いやすい。

### 1.1 手順

1. **Django を Docker でデプロイ**（Render / Fly.io / Railway / 自前 VPS など）。
2. 環境変数に **`RUN_5M_CRON_SECRET`** を設定（長いランダム文字列推奨）。
3. **cron サービス** で 5 分毎に `POST https://あなたのDjangoのURL/api/v1/cron/run-5m-evaluate/` を呼ぶ（ヘッダー `X-Cron-Secret: <RUN_5M_CRON_SECRET>`）。

### 1.2 利用しやすい cron サービス例

- **[cron-job.org](https://cron-job.org)**（無料）: 5 分間隔で URL を叩ける。Custom headers で `X-Cron-Secret` を設定可能。
- **[EasyCron](https://www.easycron.com)** など: 同様に HTTP で POST + ヘッダー指定。
- **Render**: Render で Django を動かしている場合、[Cron Jobs](https://render.com/docs/cron-jobs) で「5 分毎に curl する」ような別サービスを立てるか、上記の外部 cron で Django の URL を叩く。

### 1.3 Docker 内で cron を回す場合（同一コンテナ）

Django と同じコンテナ内で cron を動かし、5 分毎に `python manage.py run_5m_fetch_and_evaluate` を実行する方法。

- **Dockerfile 例**: `cron` を入れ、`crontab` で `*/5 * * * * cd /app && python manage.py run_5m_fetch_and_evaluate` を登録。エントリポイントで `cron -f` と `gunicorn`（または `runserver`）の両方を起動するには `supervisord` やシェルで並列起動する必要あり。
- 運用が重くなるため、**まずは「Django は Docker で起動 ＋ 外部 cron で HTTP を叩く」を推奨**。

---

## 2. Supabase を使う場合

Supabase は **DB・Auth・Storage** が中心で、Django アプリそのものをホストする機能はない。次のいずれかになる。

### 2.1 Supabase（DB）＋ Django は他でホスト

- **DB**: Supabase の PostgreSQL を Django の `DATABASES` に設定。
- **Django**: Docker や Render / Fly.io などでホスト。
- **5 分毎ジョブ**: 上記 1 と同様に、Django の `POST /api/v1/cron/run-5m-evaluate/` を外部 cron サービスで 5 分毎に呼ぶ。

### 2.2 pg_cron で URL を叩く（Supabase の DB のみ使う場合）

Supabase では **pg_cron** 拡張が使える場合がある。この場合でも「ジョブの中身」は Django が持っているので、**pg_cron からは「Django の URL を叩く」** 形になる。

- 例: `pg_cron` で 5 分毎に `http_request` や外部 HTTP を呼ぶ設定（Supabase のバージョン・プランで可否が異なる）。
- Django は別ホスト（Docker 等）で動かし、その URL を Supabase 側の cron から呼ぶイメージ。

---

## 3. Vercel について

- **Vercel** は Next.js などの **フロント／サーバーレス API** 向け。Django のような長時間・常駐バックエンドの実行には向かない。
- **推奨**: フロントは Vercel、**バックエンド（Django）は Docker など別ホスト**にデプロイし、5 分毎ジョブは「Django の HTTP エンドポイントを外部 cron で叩く」形にする。
- 5 分毎の「重い処理」を Vercel の Serverless Function に載せると、タイムアウトやコールドスタートの影響を受けやすいため避けた方がよい。

---

## 4. 環境変数まとめ（クラウド用）

| 変数名 | 説明 |
|--------|------|
| `RUN_5M_CRON_SECRET` | cron 用エンドポイントの検証用。5 分毎に POST する側（cron サービスや curl）で同じ値を `X-Cron-Secret` に設定する。 |
| `DJANGO_SECRET_KEY` | Django の SECRET_KEY（本番用に必ず変更）。 |
| `DJANGO_DEBUG` | 本番では `False` 推奨。 |
| DB 接続 | Supabase を使う場合は `DJANGO_DB_ENGINE` を `postgres` 相当にし、`DB_*` を Supabase の接続情報に合わせる。 |

---

## 5. ローカルでの動作確認

```bash
# シークレットを設定してエンドポイントを叩く
export RUN_5M_CRON_SECRET=your-secret-here
curl -X POST "http://localhost:8000/api/v1/cron/run-5m-evaluate/" \
  -H "X-Cron-Secret: your-secret-here"
```

`RUN_5M_CRON_SECRET` を設定していないと 403 が返る。
