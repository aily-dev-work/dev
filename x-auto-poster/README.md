# X Auto Poster

指定日時に X（旧Twitter）へテキストを自動投稿する Python アプリです。  
**プロジェクトは必ず `D:\dev\x-auto-poster` に置きます（Cドライブに作らないでください）。**

認証は **OAuth 2.0 Authorization Code Flow with PKCE** で取得済みの  
Client ID / Client Secret / Access Token / Refresh Token を使います。

---

## 1. セットアップ（Dドライブ）

PowerShell:

```powershell
cd D:\dev\x-auto-poster
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

実行ポリシーで止まった場合:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

`setup.ps1` が行うこと:

- `.venv` 作成
- 依存パッケージ安装
- `data` / `logs` 作成
- `.env` が無ければ `.env.example` から作成（既存は上書きしない）
- `oauth_tokens.json` が無ければテンプレート作成（既存は上書きしない）
- DB初期化

---

## 2. 認証情報の置き場所

| 内容 | 置き場所 |
|------|----------|
| Client ID / Client Secret | `.env` |
| Access Token / Refresh Token | `data\oauth_tokens.json` |

`.env` 例:

```
X_CLIENT_ID=...
X_CLIENT_SECRET=...
X_API_BASE_URL=https://api.x.com
APP_TIMEZONE=Asia/Tokyo
DRY_RUN=true
```

`data\oauth_tokens.json` 例:

```json
{
  "access_token": "取得済みAccessToken",
  "refresh_token": "取得済みRefreshToken",
  "token_type": "bearer",
  "expires_at": null,
  "scope": "tweet.read tweet.write users.read offline.access"
}
```

### Access Token と Refresh Token の違い

- **Access Token**: API呼び出しに使う短命トークン
- **Refresh Token**: Access Token 期限切れ時に更新するためのトークン（`offline.access`）

### 絶対に守ること

- `.env` と `oauth_tokens.json` を **GitHub に上げない**
- ログやチャットにトークンを貼らない
- 同じテスト投稿を何度も繰り返して **クレジットを浪費しない**

---

## 3. よく使うコマンド

仮想環境の Python:

```powershell
cd D:\dev\x-auto-poster
.\.venv\Scripts\python.exe -m app.cli <コマンド>
```

### 認証確認

```powershell
.\.venv\Scripts\python.exe -m app.cli verify-auth
```

### DB初期化

```powershell
.\.venv\Scripts\python.exe -m app.cli init-db
```

### 予約投稿の登録

```powershell
.\.venv\Scripts\python.exe -m app.cli add-post `
  --text "make-mensbody-navi API投稿テスト" `
  --scheduled-at "2026-07-15 12:00"
```

### 一覧

```powershell
.\.venv\Scripts\python.exe -m app.cli list-posts
```

### ドライラン（APIを呼ばない）

```powershell
.\.venv\Scripts\python.exe -m app.cli run-once --dry-run
```

既定で `DRY_RUN=true` なので、`.env` のままでも `run-once` は実投稿しません。

### 実投稿モードの run-once

`.env` で `DRY_RUN=false` にしたうえ:

```powershell
.\.venv\Scripts\python.exe -m app.cli run-once --real
```

### 対話式テスト投稿（明示的に POST と入力した場合のみ）

```powershell
.\.venv\Scripts\python.exe .\scripts\test_post.py
```

`y` / `yes` / Enter では投稿されません。正確に `POST` と入力したときだけ投稿します。

### 取消 / 再試行

```powershell
.\.venv\Scripts\python.exe -m app.cli cancel-post --id 1
.\.venv\Scripts\python.exe -m app.cli retry-post --id 1
```

---

## 4. 推奨確認手順（初めて）

1. 構文・テスト: `.\.venv\Scripts\python.exe -m pytest -q`
2. `init-db`
3. `oauth_tokens.json` に本物のトークンを入れる
4. `verify-auth`
5. `run-once --dry-run`
6. 了承後のみ `scripts\test_post.py` で実投稿

---

## 5. タスクスケジューラ（5分ごと）

**勝手には登録しません。** テスト成功後、自分で実行してください。

```powershell
powershell -ExecutionPolicy Bypass -File .\register_task.ps1
```

停止:

```powershell
powershell -ExecutionPolicy Bypass -File .\unregister_task.ps1
```

タスク名: `XAutoPoster`  
実行: `D:\dev\x-auto-poster\.venv\Scripts\python.exe -m app.cli run-once`

ライブ運用時は `.env` の `DRY_RUN=false` を確認してください。

---

## 6. ログ

`logs\x_poster.log`（ローテーションあり）

```powershell
Get-Content D:\dev\x-auto-poster\logs\x_poster.log -Tail 50
```

---

## 7. エラー対処

| コード | 意味 | 対処 |
|--------|------|------|
| 401 | 認証エラー | Refresh Token 更新。`invalid_grant` なら再認可 |
| 402 | クレジット/課金 | Developer Console のクレジットを確認 |
| 403 | 権限不足 | スコープ（tweet.write 等）とアプリ権限を確認 |
| 429 | レート制限 | 待つ（Retry-After / reset を尊重） |
| 5xx | X側障害 | 自動再試行対象。続く場合は時間を空ける |

Refresh Token 無効時は、PKCEで再取得し `oauth_tokens.json` を更新してください。

---

## 8. ユニットテスト

```powershell
cd D:\dev\x-auto-poster
.\.venv\Scripts\python.exe -m pytest -q
```

実APIは呼びません（モック）。

---

## 9. ディレクトリ構成

```
D:\dev\x-auto-poster
├─ .venv\
├─ .env / .env.example
├─ app\
├─ scripts\
├─ data\   (x_poster.db, oauth_tokens.json)
├─ logs\
└─ tests\
```
