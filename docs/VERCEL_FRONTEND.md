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

---

## フロントと API の接続確認（詳しく）

フロント（Vercel）と API（Django）が「どの URL にリクエストするか」「どのオリジンを許可するか」を両方で揃える手順です。**API が Render の場合**と**API が Vercel（dev-beta-lake など）の場合**のどちらでも、やることは同じです。

### 準備：2 つの URL をメモする

#### API の URL を確認する

- **Django（API）を Vercel にデプロイしている場合**
  1. **https://vercel.com** を開く。
  2. ダッシュボードで **Django が動いているプロジェクト**を開く（ルート `/` を開くと `{"message":"API server. Use /admin/ or /api/v1/."}` のような JSON が返る方。プロジェクト名は例: `dev` など）。
  3. 開いたら **Overview** または **Deployments** を表示する。
  4. いちばん上のデプロイの行に **「Visit」** というリンクがある。そのリンクの URL が **API の URL**（例: `https://dev-beta-lake.vercel.app`）。クリックしてコピーするか、アドレスバーからコピーする。
- **Django（API）を Render にデプロイしている場合**
  1. **https://dashboard.render.com** を開く。
  2. 対象の **Web サービス**をクリックする。
  3. 画面上部に **「Your service is live at …」** と表示されている URL、または左サイドバー付近の **URL** が **API の URL**（例: `https://xxx.onrender.com`）。

#### フロントの URL を確認する

- **Next.js（フロント）を Vercel にデプロイしている場合**
  1. **https://vercel.com** を開く。
  2. ダッシュボードで **フロント用のプロジェクト**を開く（Root Directory が `frontend` のプロジェクト、または Next.js だけをデプロイしている方。プロジェクト名で判別する）。
  3. **Overview** または **Deployments** を表示する。
  4. いちばん上のデプロイの行の **「Visit」** のリンクの URL が **フロントの URL**（例: `https://dev-xxxxx.vercel.app`）。

**どちらが API でどちらがフロントか迷うとき**  
- ブラウザでその URL の **ルート（`/`）** を開く。`{"message":"API server..."}` のような JSON が表示されれば **API**。トップページやアプリの画面が表示されれば **フロント**。

---

### 手順 1：フロント側で「API の URL」を設定する（NEXT_PUBLIC_API_BASE_URL）

1. **https://vercel.com** を開き、ログインする。
2. **フロント用のプロジェクト**（Next.js をデプロイした方）をクリックして開く。
3. 上か左の **Settings** をクリックする。
4. 左の **Environment Variables** をクリックする。
5. **Key** に **`NEXT_PUBLIC_API_BASE_URL`** を入力する（既にあればその行を編集する）。
6. **Value** に **API の URL を 1 つ**入れる。
   - 例: `https://dev-beta-lake.vercel.app` または `https://xxx.onrender.com`
   - **末尾にスラッシュは付けない**（`https://...com` まで）。
7. **Environment** で **Production** にチェックを入れる（Preview / Development も使うならそれらにも入れる）。
8. **Save** をクリックする。
9. **重要**: 環境変数を変えたあとは **再デプロイ**しないと反映されない。  
   → **Deployments** を開き、いちばん上のデプロイの **「…」** → **Redeploy** を実行する。完了するまで待つ。

---

### 手順 2：API 側で「フロントの URL」を許可する（CORS_ORIGINS）

**API が Render で動いている場合**

1. **https://dashboard.render.com** を開き、対象の **Web サービス**をクリックする。
2. 左の **Environment** をクリックする。
3. **CORS_ORIGINS** を探す。無ければ **Add Environment Variable** で追加する。
4. **KEY** を `CORS_ORIGINS`、**VALUE** に **フロントの URL を 1 つ**入れる（例: `https://dev-xxxxx.vercel.app`）。複数ある場合はカンマ区切り。**https:// で始め、末尾に / を付けない**。
5. **Save Changes** をクリックする。Render が再デプロイする。

**API が Vercel で動いている場合（Django を Vercel にデプロイしている場合）**

1. **https://vercel.com** で **API 用のプロジェクト**（Django が動いている方）を開く。
2. **Settings** → **Environment Variables** を開く。
3. **CORS_ORIGINS** を追加または編集する。**Value** に **フロントの URL**（例: `https://dev-xxxxx.vercel.app`）を入れる。
4. **Save** のあと、**Deployments** から **Redeploy** して反映させる。

---

### 手順 3：接続ができているか確認する

1. **ブラウザ**で **フロントの URL** を開く（例: `https://dev-xxxxx.vercel.app`）。
2. トップや **銘柄一覧・ダッシュボード** など、API を呼ぶ画面を開く。
3. **データが表示されれば**接続は成功。表示されない場合は次へ。

4. **開発者ツール**で確認する。
   - **F12** または右クリック → **検証** で開発者ツールを開く。
   - **Console** タブで **CORS** や **Failed to fetch** のエラーが出ていないか見る。
   - **Network** タブを開き、ページを再読み込みする。一覧に **XHR** や **Fetch** のリクエストが出る。
   - そのリクエストの **Request URL** が **API の URL**（例: `https://dev-beta-lake.vercel.app/api/v1/...`）になっているか確認する。
   - **Status** が **200** なら API は成功。** (failed)** や **CORS** と出ている場合は、API 側の **CORS_ORIGINS** にフロントの URL が**完全に一致**で入っているか再確認する（スペース・末尾スラッシュ・http と https の違いに注意）。

5. **よくあるミス**
   - フロントの環境変数を変えたが **Redeploy していない** → 手順 1 の 9 をやり直す。
   - CORS_ORIGINS に **フロントの URL を入れ忘れ**、または **別のドメイン**が入っている → 手順 2 でフロントの URL だけ正確に入れる。
   - NEXT_PUBLIC_API_BASE_URL に **末尾スラッシュ**を付けてしまっている → スラッシュなしの 1 行にする。

---

### 設定の対応（一覧）

| 設定する場所 | 変数名 | 入れる値 |
|--------------|--------|----------|
| **フロント（Vercel）** | `NEXT_PUBLIC_API_BASE_URL` | API の URL（例: `https://dev-beta-lake.vercel.app`） |
| **API（Render または Vercel）** | `CORS_ORIGINS` | フロントの URL（例: `https://dev-xxxxx.vercel.app`） |

両方を設定し、フロントを Redeploy したうえで、ブラウザでフロントの URL を開いてデータが表示されれば接続確認完了です。

---

## 変数を設定する場所（画面の流れ）

### フロント用：NEXT_PUBLIC_API_BASE_URL を入れる場所

1. ブラウザで **https://vercel.com** を開く。
2. ログインしたら、**ダッシュボード**（プロジェクト一覧）が表示される。
3. **フロント用のプロジェクト**（例: dev-frontend-five）の **名前** をクリックして、そのプロジェクトの中に入る。
4. 画面上部または左に **「Settings」** があるのでクリックする。
5. 左のサブメニューで **「Environment Variables」** をクリックする。
6. 画面に **Key** と **Value** の入力欄、および **Add** や既存の変数一覧が出る。
7. **Key** に `NEXT_PUBLIC_API_BASE_URL`、**Value** に API の URL（例: `https://dev-beta-lake.vercel.app` または `https://dev-3qx3.onrender.com`）を入力する。
8. **Environment** で **Production** にチェックを入れる。
9. **Save** または **Add** をクリックする。
10. 変数を追加・変更したあとは、**Deployments** タブを開き、いちばん上のデプロイの **「…」** → **Redeploy** で再デプロイする。

**まとめ**: Vercel → フロント用プロジェクトを開く → **Settings** → **Environment Variables** → ここに `NEXT_PUBLIC_API_BASE_URL` を設定する。

---

### API が Vercel のとき：CORS_ORIGINS を入れる場所

1. **https://vercel.com** を開く。
2. **API 用のプロジェクト**（例: dev-beta-lake。ルート `/` で JSON が返る方）の名前をクリックする。
3. **Settings** をクリックする。
4. 左の **Environment Variables** をクリックする。
5. **Key** に `CORS_ORIGINS`、**Value** にフロントの URL（例: `https://dev-frontend-five.vercel.app`）を入力する。
6. **Save** のあと、**Deployments** から **Redeploy** して反映させる。

**まとめ**: Vercel → API 用プロジェクトを開く → **Settings** → **Environment Variables** → ここに `CORS_ORIGINS` を設定する。

---

### API が Render のとき：CORS_ORIGINS を入れる場所

1. ブラウザで **https://dashboard.render.com** を開く。
2. ログインしたら、**Web サービス**の一覧が出る。**API 用のサービス**（例: dev）の名前をクリックする。
3. サービスの中に入ったら、左サイドバーで **「Environment」** をクリックする。
4. **Environment Variables** の一覧と **「Add Environment Variable」**（または **Add**）ボタンがある。
5. **Key** に `CORS_ORIGINS`、**Value** にフロントの URL（例: `https://dev-frontend-five.vercel.app`）を入力する。
6. **Save Changes** をクリックする。Render が自動で再デプロイする。

**まとめ**: Render ダッシュボード → 対象の Web サービスを開く → 左の **Environment** → ここに `CORS_ORIGINS` を設定する。

---

より詳しいデプロイ全般は [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)、バックエンド・cron・DB は [RENDER_CRON_AND_DB.md](RENDER_CRON_AND_DB.md) を参照してください。
