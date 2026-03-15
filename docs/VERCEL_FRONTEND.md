# フロントを Vercel にデプロイする（詳細）

Render に Django（API）をデプロイしたあと、**Next.js フロント**を **Vercel** に載せて、ブラウザから本番 API を叩く手順です。

---

## 全体像

| 役割 | サービス | URL の例 | 説明 |
|------|----------|----------|------|
| **API（バックエンド）** | Render | `https://xxx.onrender.com` | Django。認証・DB・cron エンドポイント。すでにデプロイ済み。 |
| **フロント** | Vercel | `https://yyy.vercel.app` | Next.js。ブラウザで開く画面。ここでデプロイする。 |

- ブラウザが **Vercel のページ** を開く → そのページの JavaScript が **Render の API** に `fetch` でリクエストする。
- 別オリジン（Vercel → Render）なので、**Render 側で CORS** を設定し、**フロント側で API のベース URL** を Render の URL にしておく必要がある。

---

## 前提

- Render の Web サービスが **Live** で、URL が分かっている（例: `https://dev-3qx3.onrender.com`）。
- フロントのコードが **Git リポジトリ**（GitHub / GitLab）に push されている。  
  - このプロジェクトでは **frontend** が Next.js。リポジトリが「ルートに frontend がある」か「frontend だけの別リポジトリ」かで、Vercel の Root Directory 設定が変わる（後述）。

---

## 時系列でやること一覧（ここで → こうする）

### A. Render 側（CORS を開ける）

| # | いまここにいる | する対処 |
|---|----------------|----------|
| A1 | まだ Vercel の URL が無い | いったん A2 は飛ばし、B で Vercel デプロイまで進み、表示された Vercel の URL（例: `https://stocks-xxx.vercel.app`）をメモする。その後ここに戻り A2 を実行。 |
| A2 | Render のダッシュボード | 対象の Web サービスを開き、左の **Environment** をクリックする。 |
| A3 | Environment のページ | **CORS_ORIGINS** というキーがあるか確認する。無ければ **Add Environment Variable** で追加する。 |
| A4 | KEY / VALUE の欄 | **KEY** に `CORS_ORIGINS`、**VALUE** に **Vercel の URL を 1 つ**入れる（例: `https://stocks-xxx.vercel.app`）。複数ある場合はカンマ区切り（例: `https://a.vercel.app,https://b.vercel.app`）。**http:// または https:// で始める**こと。 |
| A5 | 入力し終えた | **Save Changes** をクリックする。再デプロイが走る。 |

### B. Vercel 側（フロントをデプロイ）

| # | いまここにいる | する対処 |
|---|----------------|----------|
| B1 | ブラウザを開いた | https://vercel.com を開き、GitHub 等でログインする。 |
| B2 | Vercel のダッシュボード | **Add New…** → **Project** をクリックする。 |
| B3 | リポジトリを選択する画面 | **Import** で、フロントのコードがある **Git リポジトリ**を選ぶ（同じリポジトリで backend と frontend が同居している場合は、そのリポジトリを選ぶ）。 |
| B4 | Configure Project 画面（Framework Preset / Root Directory など） | **Root Directory** を **`frontend`** に設定する（ルートに `frontend` フォルダがある場合）。フロントだけのリポジトリなら **Leave empty** のまま。 |
| B5 | 同じ画面 | **Environment Variables** で **Key** に `NEXT_PUBLIC_API_BASE_URL`、**Value** に **Render の API の URL**（末尾スラッシュなし、例: `https://dev-3qx3.onrender.com`）を入力する。**Production / Preview / Development** のどれに効かせるか選ぶ（通常は **Production** だけでよい）。 |
| B6 | 入力し終えた | **Deploy** をクリックする。 |
| B7 | デプロイが完了した | 表示された **URL**（例: `https://stocks-frontend-xxx.vercel.app`）をコピーする。 |
| B8 | Render の CORS をまだ設定していない場合 | A1 のあとで、この **Vercel の URL** を Render の **CORS_ORIGINS** の値に追加し、Save Changes する。 |

### C. 動作確認

| # | いまここにいる | する対処 |
|---|----------------|----------|
| C1 | ブラウザで Vercel の URL を開いた | トップやダッシュボードが表示されるか確認する。 |
| C2 | 同じ画面で API を使う操作（銘柄一覧・ダッシュボードなど）を試した | データが表示されない／CORS エラーが出る場合は、Render の **CORS_ORIGINS** に **Vercel の URL が正確に**入っているか（`https://` から始まり、余計なスペースやスラッシュ末尾がないか）確認する。 |
| C3 | ログインが必要な画面がある場合 | バックエンドが Cookie 認証なら、Render の **CSRF_TRUSTED_ORIGINS** に Vercel の URL を追加する必要がある（このプロジェクトでは ALLOWED_HOSTS から自動で設定される場合あり。問題があれば別途対応）。 |

---

## 設定の対応関係（まとめ）

| どこ | 変数名 | 入れる値 | 意味 |
|------|--------|----------|------|
| **Vercel** | `NEXT_PUBLIC_API_BASE_URL` | Render の URL（例: `https://dev-3qx3.onrender.com`） | フロントの `fetch` がこの URL に API リクエストを送る。 |
| **Render** | `CORS_ORIGINS` | Vercel の URL（例: `https://stocks-xxx.vercel.app`） | ブラウザからの「どのオリジンからアクセスを許可するか」。ここに Vercel を入れないと CORS エラーになる。 |

---

## フロント側のコード（参照）

- API のベース URL は **frontend/lib/api.ts** で次のように読んでいる。
  - `const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";`
- なので、**Vercel の環境変数**で `NEXT_PUBLIC_API_BASE_URL` を設定すれば、本番では Render の URL にリクエストが飛ぶ。

---

## よくあること

- **CORS エラー**  
  - Render の **CORS_ORIGINS** に、ブラウザのアドレスバーに表示している **Vercel の URL と完全に同じ**を入れる（`https://` から始め、末尾に `/` を付けない）。
- **デプロイ後に 404**  
  - Next.js のルーティングや Root Directory（`frontend`）が正しいか確認する。
- **データが表示されない**  
  - ブラウザの開発者ツールの Network タブで、リクエストが **Render の URL** に向いているか、ステータスが 200 か確認する。

---

より詳しいデプロイ全般は [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)、バックエンド・cron・DB は [RENDER_CRON_AND_DB.md](RENDER_CRON_AND_DB.md) を参照してください。
