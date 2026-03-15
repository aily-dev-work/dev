# Render デプロイ後の設定: 5 分ジョブと DB 永続化

Render に Django をデプロイしたあとに行う **5 分ジョブ（cron-job.org）** と **DB 永続化（Disk / Supabase）** の手順です。

---

## 時系列でやること一覧

### 5 分ジョブ（cron-job.org）— ここで → こうする

番号の順に 1 つずつ実行してください。

| # | いまここにいる | する対処 |
|---|----------------|----------|
| 1 | ブラウザを開いた | https://cron-job.org を開く |
| 2 | cron-job.org のトップ | **Sign up** でアカウントを作成し、ログインする |
| 3 | ログイン後のダッシュボード | **Create cron job**（または **Cronjobs → Create cron job**）をクリックする |
| 4 | ジョブ作成画面（Title / Address などの入力欄がある） | **Title** に `stocks 5min evaluate` など任意の名前を入力する |
| 5 | 同じ画面 | **Address (URL)** に `https://【あなたのRenderのサービスURL】/api/v1/cron/run-5m-evaluate/` を入力する（例: `https://dev-3qx3.onrender.com/api/v1/cron/run-5m-evaluate/`） |
| 6 | 同じ画面 | **Request method** で **POST** を選択する |
| 7 | 同じ画面 | **Request headers** または **Advanced → Headers** を開き、**Name** に `X-Cron-Secret`、**Value** に Render の Environment で設定した **RUN_5M_CRON_SECRET** の値（目のアイコンで表示してコピー）を 1 つ追加する |
| 8 | 同じ画面 | **Schedule** で **Every 5 minutes** を選択する（または Custom で `*/5 * * * *`） |
| 9 | 入力し終えた | **Create cron job** または **Save** をクリックする |
| 10 | ジョブ一覧に戻った | **Run now** で 1 回手動実行し、**Last run** や **Log** で HTTP 200 が出ているか確認する |
| 11 | Render がスリープから起動に 50 秒かかってタイムアウトする場合 | cron-job.org のジョブ編集で **Timeout** を 60 秒以上に設定する |

### DB 永続化（Supabase）— 時系列

**Supabase で DB を永続化する**場合は、**[SUPABASE_SETUP_SIMPLE.md の「時系列でやること一覧」](SUPABASE_SETUP_SIMPLE.md#時系列でやること一覧ここで--こうする)** を **1 番から順に** 実行してください。同じ「いまここにいる → する対処」の表形式で、Render への環境変数追加やローカルでの migrate まで番号で並んでいます。

---

## 1. 5 分ジョブの設定（cron-job.org）— 詳細

5 分ごとに「5 分足取得＋判定」を実行するために、cron-job.org で HTTP を叩くジョブを作成します。

### 1.1 事前に確認すること

- Render の **Environment** に **`RUN_5M_CRON_SECRET`** が設定されていること（値は長いランダム文字列。Render の「目のアイコン」で表示して控えておく）。
- あなたのサービスの URL（例: `https://dev-3qx3.onrender.com`）。

### 1.2 cron-job.org での手順

1. **アカウント作成・ログイン**
   - https://cron-job.org にアクセス
   - **Sign up** でアカウントを作成し、ログインする

2. **新規 cron ジョブを作成**
   - ダッシュボードで **Create cron job**（または **Cronjobs → Create cron job**）をクリック

3. **基本設定**
   - **Title**: 任意（例: `stocks 5min evaluate`）
   - **Address (URL)**:
     ```
     https://dev-3qx3.onrender.com/api/v1/cron/run-5m-evaluate/
     ```
     （あなたの Render の URL に合わせて変更）

4. **リクエスト方法**
   - **Request method**: **POST** を選択
   - **Request headers** または **Advanced → Headers** を開き、次のヘッダーを 1 つ追加する:
     - **Name**: `X-Cron-Secret`
     - **Value**: Render の環境変数 **RUN_5M_CRON_SECRET** に設定した値（そのままコピー＆ペースト）

5. **実行間隔**
   - **Schedule** で **Every 5 minutes**（5 分ごと）を選択  
   - または **Custom** で `*/5 * * * *`（5 分毎）を指定

6. **保存**
   - **Create cron job** または **Save** で保存する

### 1.3 動作確認

- cron-job.org のジョブ一覧で、該当ジョブの **Last run** や **Log** を開く
- 成功していれば HTTP 200 と JSON レスポンスが記録される
- 手動で **Run now** を押して、すぐに 1 回実行して確認してもよい

### 1.4 注意

- Render の **Free プラン**では、しばらくアクセスがないとサービスがスリープします。cron で叩いたときに起動するまで **50 秒程度**かかることがあります。ジョブのタイムアウトは 60 秒以上にしておくと安全です。

---

## 2. DB の永続化

無料枠のままでは、**再デプロイやコンテナの作り直しで SQLite の内容が消える**ことがあります。データを残したい場合は、次のどちらかを行います。

| 方法 | 料金 | 手軽さ |
|------|------|--------|
| **A: Render Disk** | 有料プランが必要 | 環境変数 1 つで済む |
| **B: Supabase** | 無料枠あり | プロジェクト作成＋環境変数 1 つ |

---

### 2.1 方法 A: Render の Disk をマウントする（SQLite のまま）

Render の **Persistent Disk** を 1 つ追加し、その中に `db.sqlite3` を保存する方法です。**有料プラン**で利用できます。

#### 手順（画面の流れ）

1. **Render にログイン**し、https://dashboard.render.com を開く。
2. 左の **Dashboard** から、対象の **Web Service**（例: **dev**）をクリックして開く。
3. 左サイドバーで **「Environment」の下** にある **「Disk」**（または **Storage**）をクリック。
   - 見つからない場合は、同じサイドバーの **Settings** の近くに **Disk** がある場合もある。
4. **「Add Disk」**（または **Connect Disk**）ボタンをクリック。
5. フォームに入力する:
   - **Name**: 任意の名前（例: `data`）。
   - **Mount Path**: 必ず **`/data`** と入力する（スラッシュ付き）。
   - **Size**: 最小でよい（例: 1 GB）。料金ページで確認。
6. **「Save」** または **「Add Disk」** で保存する。
7. 左サイドバーの **「Environment」** を開く。
8. **「Add Environment Variable」** で次の 1 つを追加する:
   - **KEY**: `DATABASE_SQLITE_PATH`
   - **VALUE**: `/data/db.sqlite3`
9. **「Save Changes」** をクリックする。Render が自動で再デプロイを開始する。
10. デプロイが **Live** になったら完了。以降、再デプロイしても DB は `/data/db.sqlite3` に残ります。

#### 注意

- **Persistent Disk** は Render の **有料プラン**（Starter 以上）で利用できます。無料枠では「Add Disk」が表示されない、または利用できない場合は **方法 B（Supabase）** を使ってください。

---

### 2.2 方法 B: Supabase（PostgreSQL）に切り替える【無料枠で利用可】

Django の DB を Supabase の PostgreSQL に接続する方法です。**無料枠**でも利用でき、データは Supabase 側に永続化されます。

#### 2.2.1 Supabase でプロジェクトを作る

1. https://supabase.com にアクセスし、**Sign in**（GitHub 等でログイン可）。
2. ダッシュボードで **「New project」** をクリック。
3. 次のように入力する:
   - **Name**: 任意（例: `stocks-db`）。
   - **Database Password**: **必ず自分で決めたパスワードを入力**し、**メモまたはパスワードマネージャに保存**する（あとで接続文字列に使う）。
   - **Region**: 近いリージョン（例: Northeast Asia (Tokyo)）。
4. **「Create new project」** をクリックし、プロジェクトができるまで 1〜2 分待つ。

#### 2.2.2 接続文字列（URI）をコピーする

1. 左メニュー（Project Overview, Table Editor, … の一覧）の **「Project Settings」** をクリックする。
2. Project Settings が開いたら、**左のサブメニュー**（General, API Keys など）のなかから **「Database」** をクリックする。
   - 「Database」が見つからない場合は、ブラウザで次の URL を開く（`rxseqdafinorcuromehp` は自分の Project ID に置き換える）:
     `https://supabase.com/dashboard/project/rxseqdafinorcuromehp/settings/database`
3. ページ内の **「Connection string」** というセクションまで下にスクロールする。
4. **「URI」** タブを選択し、**Session mode**（ポート **5432**）の URI を使う。**Transaction mode（6543）だと「Tenant or user not found」が出る場合があるので 5432 を使う。**
   - 例: `postgresql://postgres.[プロジェクト参照]:[YOUR-PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres`
5. 表示されている URI の **「Copy」** ボタンでコピーする。
6. コピーした文字列の中の **`[YOUR-PASSWORD]`** を、**2.2.1 で設定した Database Password** に**置き換える**。
   - メモ帳などに貼り付けて、`[YOUR-PASSWORD]` だけを実際のパスワードに書き換え、完成した 1 行を再度コピーする。
   - パスワードに `@` や `#` などが含まれる場合は、URL エンコード（`@` → `%40` など）が必要な場合がある。Supabase の画面でパスワードを入力して表示される形式を使うと安全。

**パスワードを忘れた場合**  
- **Project Settings → Database** の **「Reset database password」** で再設定できる。再設定後、上記の URI の `[YOUR-PASSWORD]` を新しいパスワードに置き換える。

#### 2.2.3 Render に環境変数を 1 つ追加する

1. **Render** のダッシュボードで、対象の Web サービス（例: **dev**）を開く。
2. 左サイドバーで **「Environment」** をクリック。
3. **「Add Environment Variable」** をクリック。
4. 次のように入力する:
   - **KEY**: `DATABASE_URL`
   - **VALUE**: 2.2.2 で用意した **パスワードを置き換えた後の URI 全体**を貼り付ける。  
     例: `postgresql://postgres.abcdefghij:MyPass123@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres`
5. **「Save Changes」** をクリックする。Render が自動で再デプロイする。

#### 2.2.4 コードとデプロイの確認

- このプロジェクトでは、**環境変数 `DATABASE_URL` が存在すると PostgreSQL を使う**ようになっています（`requirements.txt` に `psycopg2-binary` と `dj-database-url` を追加済み）。
- 再デプロイ時にコンテナ内で `migrate` が実行され、**Supabase 上にテーブルが自動作成**されます。
- デプロイが **Live** になり、管理画面（`https://dev-3qx3.onrender.com/admin/`）にログインできれば、Supabase への接続は成功しています。

#### 2.2.5 Supabase にテーブルができない場合（ローカルで migrate を実行する）

Render の起動時に migrate がバックグラウンドで動き、接続エラーが出てもログに残りにくいことがあります。**ローカル**で Supabase 向けに migrate を 1 回実行すると、確実にテーブルが作成されます。

1. **ターミナル**でプロジェクトのルート（`manage.py` があるディレクトリ）に移動する。
2. **DATABASE_URL** を Supabase の接続 URI に設定して migrate を実行する。

   **PowerShell の例:**
   ```powershell
   $env:DATABASE_URL="postgresql://postgres.rxseqdafinorcuromehp:あなたのパスワード@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
   python manage.py migrate --noinput
   ```

   **bash の例:**
   ```bash
   export DATABASE_URL="postgresql://postgres.rxseqdafinorcuromehp:あなたのパスワード@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
   python manage.py migrate --noinput
   ```

3. 成功すると「Applying ... OK」が並び、Supabase の **Table Editor** に `auth_user` や `stocks_*` などのテーブルができる。
4. その後は Render の再デプロイや通常運用で、Django はその Supabase のテーブルを使う。

**注意**: パスワードに `@` や `#` が含まれる場合は URL エンコード（`@` → `%40`、`#` → `%23`）する。

#### 2.2.6 既存の SQLite データがある場合

- いま Render の SQLite にだけあるデータを Supabase に移したい場合は、**データのエクスポート／インポート**や **Django の dumpdata / loaddata** など、別途データ移行が必要です。
- 「これから本番は Supabase だけ使う」場合は、上記のとおり `DATABASE_URL` を設定するだけでよく、初回は空の DB に migrate がかかります。スーパーユーザーは環境変数（`DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD`）で自動作成されるか、移行後に手動で 1 人作成し直す形になります。

---

## 3. まとめ

| やりたいこと | やること |
|--------------|----------|
| 5 分ごとに 5 分足取得・判定を回す | cron-job.org で POST ジョブを 5 分間隔で作成し、`X-Cron-Secret` に `RUN_5M_CRON_SECRET` を設定する（本文「1. 5 分ジョブ」参照） |
| DB を残したい（有料 OK） | **方法 A**: Render の Disk をマウントし、環境変数 `DATABASE_SQLITE_PATH=/data/db.sqlite3` を追加する（本文「2.1 方法 A」参照） |
| DB を残したい（無料で） | **方法 B**: Supabase でプロジェクト作成 → 接続 URI をコピー → Render に `DATABASE_URL` を 1 つ追加する（本文「2.2 方法 B」参照） |

5 分ジョブのエンドポイント仕様は [stocks/docs/CRON_CLOUD.md](../stocks/docs/CRON_CLOUD.md)、デプロイ全般は [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md) も参照してください。
