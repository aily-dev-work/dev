# 株価監視アプリ フェーズ1 進捗まとめ

## 1. フェーズ1の位置づけ

- **目的**: 株価監視アプリの最小構成として、**監視対象銘柄の登録・管理・取得**ができる状態にする。
- **範囲**: 分析・通知は行わず、銘柄マスタの CRUD と Admin/API の整備まで。
- **前提**: 既存の Django プロジェクト土台（webapp）は作成済み。既存コードを壊さずに `stocks` アプリを追加。
- **認証**: 現時点（フェーズ1）では認証・権限制御は未実装で、最小限の CRUD API のみ提供する。

---

## 2. フェーズ1で実装した内容

### 2.1 アプリ追加

| 項目 | 内容 |
|------|------|
| アプリ名 | `stocks` |
| 役割 | 監視対象銘柄の管理（フェーズ1はマスタのみ） |

### 2.2 モデル: `WatchStock`

| フィールド | 型 | 必須 | 備考 |
|------------|-----|------|------|
| `ticker` | CharField(32) | ○ | 一意・インデックス。銘柄コード（例: 7203.T, AAPL） |
| `name` | CharField(255) | ○ | 銘柄名 |
| `market` | CharField(32) | - | 市場区分（例: JP, US, TSE）。任意 |
| `is_active` | BooleanField | - | 監視中フラグ。デフォルト True |
| `memo` | TextField | - | メモ。任意 |
| `created_at` | DateTimeField | - | 自動作成 |
| `updated_at` | DateTimeField | - | 自動更新 |

- 表示名: 管理画面では「監視銘柄」。
- 並び順: `updated_at` 降順 → `ticker` 昇順。

### 2.3 Django Admin

- **対象**: `WatchStock`
- **一覧表示**: `ticker`, `name`, `market`, `is_active`, `updated_at`
- **検索**: `ticker`, `name`
- **絞り込み**: `is_active`, `market`

### 2.4 DRF API

- **ベースURL**: `/api/v1/stocks/`
- **実装**: ViewSet + DefaultRouter（`stocks/views.py`, `stocks/urls.py`）
- **提供メソッド**:
  - 一覧取得: `GET /api/v1/stocks/`
  - 詳細取得: `GET /api/v1/stocks/<id>/`
  - 登録: `POST /api/v1/stocks/`
  - 更新: `PUT` / `PATCH /api/v1/stocks/<id>/`
  - 削除: `DELETE /api/v1/stocks/<id>/`
- **認証**: フェーズ1では未実装（AllowAny）。

### 2.5 コード構成（拡張しやすい分離）

- `stocks/models.py` … `WatchStock` モデル
- `stocks/serializers.py` … `WatchStockSerializer`
- `stocks/views.py` … `WatchStockViewSet`
- `stocks/urls.py` … Router 登録と `urlpatterns`
- `stocks/admin.py` … `WatchStockAdmin` 登録
- プロジェクト側 `webapp/urls.py` で `path("api/v1/", include("stocks.urls"))` を追加

---

## 3. 変更・追加したファイル一覧

| 種別 | パス |
|------|------|
| 新規 | `stocks/` アプリ一式（`apps.py`, `models.py`, `admin.py`, `views.py`, `serializers.py`, `urls.py`, `migrations/0001_initial.py`, `tests.py` はそのまま） |
| 変更 | `webapp/settings.py` … `INSTALLED_APPS` に `stocks` 追加 |
| 変更 | `webapp/urls.py` … `path("api/", include("stocks.urls"))` 追加 |
| 変更 | `README.md` … stocks フェーズ1の説明・手順・API例を追記 |
| 新規 | `stocks/PHASE1.md` … 本ドキュメント（フェーズ1まとめ） |

---

## 4. マイグレーション手順

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py makemigrations stocks
python manage.py migrate
```

- 初回は `stocks/migrations/0001_initial.py` が適用され、`WatchStock` テーブルが作成される。
- 既に適用済みの環境では `No migrations to apply.` となる。

---

## 5. 起動・確認手順

### 5.1 開発サーバ起動

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

### 5.2 管理画面での確認

1. ブラウザで http://127.0.0.1:8000/admin/ を開く。
2. 必要なら `python manage.py createsuperuser` で管理者を作成。
3. 「監視銘柄」から一覧・検索・絞り込み・登録・編集・削除ができることを確認。

### 5.3 API での確認（PowerShell）

- **一覧取得**
  ```powershell
  curl.exe -s http://127.0.0.1:8000/api/v1/stocks/
  ```

- **登録（POST）**  
  ※PowerShell では JSON を変数で渡すとエンコーディングで壊れやすいため、一時ファイル経由を推奨。
  ```powershell
  $body = '{"ticker":"AAPL","name":"Apple Inc.","market":"US"}'
  [System.IO.File]::WriteAllText("$env:TEMP\body.json", $body, [System.Text.UTF8Encoding]::new($false))
  curl.exe -s -X POST http://127.0.0.1:8000/api/v1/stocks/ -H "Content-Type: application/json" -d "@$env:TEMP\body.json"
  ```

- **詳細取得**
  ```powershell
  curl.exe -s http://127.0.0.1:8000/api/v1/stocks/1/
  ```

- **更新（PUT）**
  ```powershell
  $body = '{"ticker":"7203.T","name":"トヨタ自動車","market":"TSE","is_active":true,"memo":""}'
  [System.IO.File]::WriteAllText("$env:TEMP\body.json", $body, [System.Text.UTF8Encoding]::new($false))
  curl.exe -s -X PUT http://127.0.0.1:8000/api/v1/stocks/1/ -H "Content-Type: application/json" -d "@$env:TEMP\body.json"
  ```

- **削除**
  ```powershell
  curl.exe -s -X DELETE http://127.0.0.1:8000/api/v1/stocks/1/
  ```

---

## 6. フェーズ1では行っていないこと（今後のフェーズで検討）

- 株価の外部 API 取得
- テクニカル分析・ファンダメンタル分析
- 買いスコア／売りスコア
- AI 連携
- LINE 通知
- バッチ処理
- フォーメーション分析
- API 認証・権限制御（現状は AllowAny）

---

## 7. 次のフェーズへの接続ポイント

- **モデル**: `WatchStock` にカラム追加や関連モデル（例: 株価履歴）を追加しやすい。
- **API**: 同じ `stocks` アプリの `urls.py` に別の ViewSet を `router.register(...)` で追加可能。
- **設定**: `webapp/settings.py` の `REST_FRAMEWORK` や認証設定を後から変更可能。

以上がフェーズ1の進捗まとめです。
