# Supabase で DB を永続化する（初心者向け）

「データを残したい」ときに、**Supabase** という無料のデータベースサービスを使う方法を、できるだけやさしく説明します。

---

## 時系列でやること一覧（ここで → こうする）

**次の表を、番号 1 から順に 1 つずつ実行してください。** 各行は「いまここにいる状態」と「そこでする対処」だけを書いています。

| # | いまここにいる | する対処 |
|---|----------------|----------|
| 1 | ブラウザを開いた | https://supabase.com を開く |
| 2 | Supabase のトップ | **Sign in** をクリックしてログインする |
| 3 | ログイン後のダッシュボード | **New project** をクリックする |
| 4 | プロジェクト作成画面（Name / Database Password / Region の入力欄がある） | **Name** に `stocks-db` など好きな名前を入力する |
| 5 | 同じ画面 | **Database Password** に自分で決めたパスワードを入力し、**必ずメモ帳にコピーして保存する** |
| 6 | 同じ画面 | **Region** で **Southeast Asia (Singapore)** または **Northeast Asia (Tokyo)** を選ぶ |
| 7 | 同じ画面 | **Create new project** をクリックする |
| 8 | 「Setting up project...」など表示されている | 1〜2 分待つ。完了するまで何もクリックしない |
| 9 | プロジェクトが開いた（左に Table Editor などのメニューがある） | 左メニュー一番下の **Project Settings**（歯車アイコン）をクリックする |
| 10 | Project Settings が開き、右に「General」の内容が出ている | 右側の **Project ID** の欄を確認し、その英数字を**コピー**してメモ帳に貼る（例: `rxseqdafinorcuromehp`） |
| 11 | 同じ Project Settings の左サブメニュー | **Database** をクリックする（無い場合はブラウザで `https://supabase.com/dashboard/project/【10でコピーしたID】/settings/database` を開く） |
| 12 | Database の設定ページ | 画面の「Primary Database」などで**地域**を確認する。**Singapore** ならリージョンは `ap-southeast-1`、**Tokyo** なら `ap-northeast-1` とメモする |
| 13 | メモ帳を開いた状態 | 次の 1 行を書く（【A】に 10 でコピーした Project ID、【B】に 5 で決めたパスワード、【C】に 12 のリージョン（`ap-southeast-1` か `ap-northeast-1`）を入れる）:<br>`postgresql://postgres.【A】:【B】@aws-0-【C】.pooler.supabase.com:5432/postgres` |
| 14 | メモ帳で 1 行が完成した | その 1 行全体をコピーする（あとで 2 回貼り付けるので取っておく） |
| 15 | Render のサイトを開く | https://dashboard.render.com にログインする |
| 16 | Render のダッシュボード | 自分の **Web サービス（例: dev）** をクリックする |
| 17 | サービスの中（左に Environment などがある） | 左の **Environment** をクリックする |
| 18 | Environment のページ（KEY / VALUE の一覧がある） | **Add Environment Variable**（または **Add**）をクリックする |
| 19 | KEY / VALUE を入力する欄が出た | **KEY** に `DATABASE_URL` と入力する |
| 20 | 同じ欄 | **VALUE** に 14 でコピーした **接続文字列 1 行全体**を貼り付ける |
| 21 | 入力し終えた | **Save Changes** をクリックする（Render が再デプロイを始める） |
| 22 | 自分のパソコンのターミナル（PowerShell）を開いた | `cd D:\dev` と入力して Enter（プロジェクトのフォルダに移動） |
| 23 | 同じターミナル | `.\.venv\Scripts\Activate.ps1` と入力して Enter（仮想環境を有効化） |
| 24 | 同じターミナル | `pip install dj-database-url psycopg2-binary` と入力して Enter（パッケージを入れる） |
| 25 | 同じターミナル | `$env:DATABASE_URL="【14で作った1行をそのまま貼る】"` と入力して Enter（引用符も含めて 1 行で。パスワード部分は自分のものに置き換え） |
| 26 | 同じターミナル | `python manage.py migrate --noinput` と入力して Enter |
| 27 | ターミナルに「Applying ... OK」が並んだ | 成功。Supabase の画面に戻り、左の **Table Editor** を開く |
| 28 | Supabase の Table Editor | `auth_user` や `stocks_` で始まるテーブルが並んでいれば完了 |
| 29 | 「FATAL: Tenant or user not found」と出た（pooler の 5432 でも同じ場合） | **直接接続**の 1 行に切り替える: ホストを `db.【プロジェクトID】.supabase.co`、ユーザーを `postgres` のみにし、`postgresql://postgres:【パスワード】@db.【プロジェクトID】.supabase.co:5432/postgres` で 25 と 20（Render）を作り直す |
| 29a | 上記 29 の直接接続でも「Tenant or user not found」 | Project Settings → General で **Project ID** を再確認し、接続文字列の `db.xxxxx.supabase.co` の xxxxx がその ID と完全一致しているか確認する |
| 30 | 「No module named 'dj_database_url'」と出た | 23 の仮想環境を有効化したあと、24 の `pip install` を実行してから 25〜26 をやり直す |
| 31 | 「password authentication failed」と出た | Supabase の Project Settings → Database で **Reset database password** を実行し、新しいパスワードで 13〜14 の 1 行を作り直して 20 と 25 をやり直す |

---

## なぜ Supabase を使うの？

- Render の**無料プラン**では、再デプロイするたびに**データが消える**ことがあります。
- **Supabase** は「クラウドのデータベース」です。ここにデータを保存しておくと、**Render を再デプロイしてもデータは消えません**。
- このプロジェクトでは、Django が「データをどこに保存するか」を **DATABASE_URL** という 1 つの設定で決めています。Supabase 用のアドレスを入れると、Django が Supabase にデータを保存するようになります。

---

## ステップ 1: Supabase でプロジェクトを作る（詳細）

### 1-1. Supabase にログインする

1. ブラウザで **https://supabase.com** を開く。
2. **Sign in** をクリックし、GitHub やメールでログインする。

### 1-2. 新しいプロジェクトを作る

1. ログインしたあと、**「New project」** をクリックする。
2. 次の 3 つを入力する:
   - **Name（名前）**: なんでもよい（例: `stocks-db`）。自分用のメモです。
   - **Database Password（データベースのパスワード）**:  
     **ここで自分で決めたパスワードを必ずメモする。** あとで何度も使うので、忘れないように。
   - **Region（地域）**: 日本なら **Northeast Asia (Tokyo)** や **Southeast Asia (Singapore)** など、近いものを選ぶ。
3. **「Create new project」** をクリックする。
4. 1〜2 分待つ。緑のチェックなどが出たら「できた」という意味です。

---

## ステップ 2: 「接続のための 1 行」を用意する（詳細・接続文字列）

Django が Supabase のデータベースに「ここにデータを保存します」とつなぐために、**1 行の文字列**が必要です。これを **接続文字列（URI）** といいます。

### 2-1. 接続文字列の「型」を覚える

形はこうです（穴埋めが 2 つあります）:

```
postgresql://postgres.【プロジェクトID】:【パスワード】@aws-0-【リージョン】.pooler.supabase.com:5432/postgres
```

- **【プロジェクトID】** … Supabase があなたのプロジェクトに付けた ID（英数字の並び）
- **【パスワード】** … ステップ 1 で自分で決めた **Database Password**
- **【リージョン】** … プロジェクトを作ったときに選んだ地域（例: Singapore なら `ap-southeast-1`、Tokyo なら `ap-northeast-1`）

### 2-2. プロジェクト ID を確認する

1. Supabase の画面で、左のメニューから **「Project Settings」**（歯車のアイコンのところ）をクリックする。
2. 一番上にある **「General」** のページで、**「Project ID」** という欄を見る。
3. そこに表示されている英数字（例: `rxseqdafinorcuromehp`）をコピーする。これが **【プロジェクトID】** です。

### 2-3. リージョンを確認する

1. 同じく **Project Settings** を開いた状態で、左のサブメニューから **「Database」** をクリックする。  
   （一覧に「Database」が無い場合は、ブラウザのアドレスバーに  
   `https://supabase.com/dashboard/project/【あなたのProject ID】/settings/database`  
   と入力して開く。）
2. ページの上の方に **「Primary Database」** などと書いてあり、**地域名（例: Singapore, Tokyo）** が出ています。
3. 地域に合わせて **【リージョン】** を入れる:
   - **Singapore** → `ap-southeast-1`
   - **Tokyo** → `ap-northeast-1`
   - その他は Supabase の表示やヘルプを参照。

### 2-4. 1 行を自分で作る

メモ帳を開き、次の 1 行を**そのまま**書く（ただし【】の 3 つだけ置き換える）:

```
postgresql://postgres.【プロジェクトID】:【パスワード】@aws-0-【リージョン】.pooler.supabase.com:5432/postgres
```

**置き換え例**（架空の値）:

- プロジェクトID: `rxseqdafinorcuromehp`
- パスワード: `MyPass123`
- リージョン: `ap-southeast-1`

なら、完成形は:

```
postgresql://postgres.rxseqdafinorcuromehp:MyPass123@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
```

**注意**: パスワードに **@** や **#** が含まれていると、この 1 行が壊れることがあります。その場合は、Supabase の Database 設定で **「Reset database password」** から、**@ や # を含まない**新しいパスワードに変更してから、もう一度この 1 行を作り直してください。

この **完成した 1 行** を、次のステップで使います。**人に送ったり、Git にコミットしたりしないでください**（パスワードが含まれています）。

---

## ステップ 3: Render に「Supabase の住所」を教える + テーブルを作る

### 3-1. Render に DATABASE_URL を設定する

1. **Render** のサイト（https://dashboard.render.com）にログインする。
2. あなたの **Web サービス（例: dev）** をクリックして開く。
3. 左のメニューから **「Environment」** をクリックする。
4. **「Add Environment Variable」** または **「Add」** をクリックする。
5. 次のように入力する:
   - **KEY（キー）**: `DATABASE_URL` と**そのまま**打つ。
   - **VALUE（値）**: ステップ 2 で作った **完成した 1 行** を、そのまま貼り付ける。
6. **「Save Changes」** をクリックする。  
   → Render が自動で再デプロイを始めます。これで「Django は Supabase のデータベースを使う」設定になりました。

### 3-2. 自分のパソコンで「テーブルを作る」作業を 1 回だけやる（migrate）

「テーブル」とは、データを整理して入れておくための箱のようなものです。Django が使うテーブルは、**migrate** というコマンドを 1 回実行すると、Supabase の上に自動で作られます。

#### やること（PowerShell の場合）

1. **プロジェクトのフォルダ**（`manage.py` があるフォルダ）を開く。例: `D:\dev`
2. **PowerShell** または **ターミナル** を開き、次のコマンドを **1 行ずつ** 実行する。

まず、仮想環境を使っている場合は有効化する:

```powershell
cd D:\dev
.\.venv\Scripts\Activate.ps1
```

次に、必要なパッケージが入っているか確認して入れる:

```powershell
pip install dj-database-url psycopg2-binary
```

そのあと、**接続文字列を環境変数に設定**して、**migrate** を実行する（次の 1 行の `【ここにステップ2で作った1行全体を貼る】` の部分を、実際の 1 行に置き換える）:

```powershell
$env:DATABASE_URL="【ここにステップ2で作った1行全体を貼る】"
python manage.py migrate --noinput
```

**例**（パスワードは架空）:

```powershell
$env:DATABASE_URL="postgresql://postgres.rxseqdafinorcuromehp:MyPass123@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
python manage.py migrate --noinput
```

3. 成功すると、画面に **「Applying ... OK」** のような行が何行も出ます。  
   失敗した場合は、**「FATAL: Tenant or user not found」** や **「password authentication failed」** などのメッセージが出ます（下の「よくあるエラー」を参照）。

4. **Supabase の画面**で、左の **「Table Editor」** を開く。  
   → `auth_user` や `stocks_watchstock` のような名前のテーブルが並んでいれば、**テーブル作成は成功**しています。

### 3-3. ここまでできたら

- **Render** は、すでに **DATABASE_URL** で Supabase を見に行く設定になっているので、**再デプロイ後はそのまま** Supabase にデータが保存されます。
- 管理画面（`https://あなたのサービス名.onrender.com/admin/`）にログインできるか確認してください。ログインできれば、Supabase に正しくつながっています。
- スーパーユーザー（管理者）は、Render の環境変数 **DJANGO_SUPERUSER_USERNAME** と **DJANGO_SUPERUSER_PASSWORD** を設定しておくと、起動時に自動作成されます（別のドキュメントを参照）。

---

## よくあるエラーと対処

### 「No module named 'dj_database_url'」

- **意味**: パソコン側に、接続文字列を読むためのパッケージが入っていない。
- **対処**: プロジェクトの**仮想環境を有効化**したうえで、`pip install dj-database-url psycopg2-binary` を実行してから、もう一度 `$env:DATABASE_URL="..."` と `python manage.py migrate --noinput` を実行する。

### 「FATAL: Tenant or user not found」

- **意味**: 接続の「住所」か「ユーザー名」が Supabase と合っていない（pooler 経由で出ることがある）。
- **対処 1**: 接続文字列の **`:6543/` を `:5432/`** に変えて pooler の Session モードで試す。
- **対処 2**: それでも同じなら **直接接続** に切り替える。形式は次の 1 行（【プロジェクトID】と【パスワード】だけ置き換え）:
  ```
  postgresql://postgres:【パスワード】@db.【プロジェクトID】.supabase.co:5432/postgres
  ```
  例: プロジェクト ID が `rxseqdafinorcuromehp`、パスワードが `MyPass123` なら  
  `postgresql://postgres:MyPass123@db.rxseqdafinorcuromehp.supabase.co:5432/postgres`  
  Project Settings → General で **Project ID** を再確認し、`db.xxxxx.supabase.co` の xxxxx がその ID と完全一致しているか確認する。

### 「Network is unreachable」（Render で DATABASE_URL を直接接続にしているとき）

- **意味**: Render のネットワークは **IPv4 のみ**。Supabase の **直接接続**（`db.xxx.supabase.co`）は **IPv6** のため届かない。
- **対処**: Render の **DATABASE_URL** を **プーラー（Session mode）** の 1 行に切り替える。形式（【プロジェクトID】【パスワード】【リージョン】を置き換え）:
  ```
  postgresql://postgres.【プロジェクトID】:【パスワード】@aws-0-【リージョン】.pooler.supabase.com:5432/postgres
  ```
  例: プロジェクト ID `rxseqdafinorcuromehp`、リージョン `ap-southeast-1` なら  
  `postgresql://postgres.rxseqdafinorcuromehp:【あなたのパスワード】@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres`  
  Render の **Environment** でこの 1 行に更新し、**Save Changes** して再デプロイする。ローカルでの migrate は従来どおり直接接続（`db.xxx.supabase.co`）でよい。

### 「password authentication failed」

- **意味**: パスワードが違う。
- **対処**: Supabase の **Project Settings → Database** で **「Reset database password」** を実行して新しいパスワードを決め、接続文字列の **【パスワード】** の部分を、その新しいパスワードに書き換える。Render の **DATABASE_URL** も同じ 1 行に更新する。

---

## 用語の簡単な説明

- **DATABASE_URL** … 「データベースの住所と鍵が書かれた 1 行」。Django はこれを見て、どこにデータを保存するか決めます。
- **migrate（マイグレート）** … Django が「テーブル」をデータベース上に作る・更新する作業。初回は「テーブルを作る」ために 1 回実行します。
- **接続文字列（URI）** … 上の「DATABASE_URL に貼る 1 行」のこと。`postgresql://...` で始まります。
- **プロジェクト ID** … Supabase があなたのプロジェクトに付けた英数字の ID。Project Settings の General で確認できます。
- **ポート 5432 / 6543** … 接続の「入口」の番号。この説明では **5432** を使うと「Tenant or user not found」を避けやすいです。

---

より詳しい技術的な説明は [RENDER_CRON_AND_DB.md](RENDER_CRON_AND_DB.md) を参照してください。
