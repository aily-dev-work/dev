# 株価監視アプリ フェーズ2 進捗まとめ

## 1. フェーズ2の目的

- **目的**: 監視対象銘柄ごとに、**日足の株価履歴（OHLCV）を保存・管理・取得**できる状態を作る。
- **範囲**: 外部 API 取得や分析・通知は行わず、日足株価の CRUD と Admin/API の整備まで。
- **前提**:
  - フェーズ1で `WatchStock` モデルと `/api/v1/stocks/` の CRUD API が実装済み。
  - 既存コードを壊さずに、`WatchStock` を自然に拡張する形で日足モデルを追加する。
  - 認証・権限制御は引き続き未実装（AllowAny）で、最小限の CRUD のみ提供する。

---

## 2. 追加したモデル: `StockPriceDaily`

### 2.1 モデル定義

- モデル名: `StockPriceDaily`
- 所属アプリ: `stocks`
- 関連: `WatchStock` への `ForeignKey` で紐づく

| フィールド       | 型                       | 必須 | 備考                                           |
|------------------|--------------------------|------|----------------------------------------------|
| `stock`          | ForeignKey(WatchStock)   | ○    | 監視対象銘柄。削除時は関連する日足も削除（CASCADE） |
| `date`           | DateField                | ○    | 日付                                          |
| `open_price`     | DecimalField(12, 4)      | ○    | 始値                                          |
| `high_price`     | DecimalField(12, 4)      | ○    | 高値                                          |
| `low_price`      | DecimalField(12, 4)      | ○    | 安値                                          |
| `close_price`    | DecimalField(12, 4)      | ○    | 終値                                          |
| `volume`         | BigIntegerField          | -    | 出来高。任意（null/blank 許可）              |
| `created_at`     | DateTimeField            | -    | レコード作成日時（auto_now_add）             |
| `updated_at`     | DateTimeField            | -    | レコード更新日時（auto_now）                 |

- `stock` には `related_name="daily_prices"` を設定し、`watch_stock.daily_prices.all()` のようにアクセス可能。

### 2.2 制約・並び順

- 複合ユニーク制約: **(stock, date)** の組み合わせが一意になるように制約を追加。
  - `models.UniqueConstraint(fields=["stock", "date"], name="unique_stock_date")`
- 並び順 (`Meta.ordering`):
  - デフォルトは `["-date", "-updated_at"]` とし、**新しい日付が先に来る**ように設定。

---

## 3. Django Admin 拡張

- 対象モデル: `StockPriceDaily`
- Admin クラス: `StockPriceDailyAdmin`

### 3.1 一覧表示

- `list_display`:
  - `stock`, `date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `updated_at`

### 3.2 検索・絞り込み

- `search_fields`:
  - `stock__ticker`, `stock__name`
- `list_filter`:
  - `stock`
- `ordering`:
  - `("-date", "-updated_at")` で **新しい日付から確認しやすい**ように設定。

---

## 4. DRF API 追加

- ViewSet: `StockPriceDailyViewSet`
- Serializer: `StockPriceDailySerializer`
- ルーター登録: `stocks/urls.py` 内で `DefaultRouter` に登録
  - パス: `"stock-prices"`
  - ベース URL: `/api/v1/stock-prices/`

### 4.1 Serializer: `StockPriceDailySerializer`

- 主なフィールド:
  - `id`
  - `stock`（FK の ID）
  - `stock_ticker`（読み取り専用, `stock.ticker`）
  - `stock_name`（読み取り専用, `stock.name`）
  - `date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`
  - `created_at`, `updated_at`
- 読み取り専用:
  - `id`, `created_at`, `updated_at`, `stock_ticker`, `stock_name`

### 4.2 ViewSet: `StockPriceDailyViewSet`

- ベースクラス: `viewsets.ModelViewSet`
- クエリセット:
  - `StockPriceDaily.objects.select_related("stock").all()` を基点にフィルタ。
- フィルタ仕様（**シンプルなクエリパラメータのみ**）:
  - `?stock=<WatchStock の id>` で絞り込み:
    - 例: `/api/v1/stock-prices/?stock=1`
  - `?ticker=<WatchStock.ticker>` で絞り込み:
    - 例: `/api/v1/stock-prices/?ticker=7203.T`
  - 両方指定された場合は AND 条件で適用。
  - いずれも無指定の場合は全件（`Meta.ordering` に基づく新しい日付順）。

### 4.3 提供する API（すべて `/api/v1/stock-prices/` 配下）

- 一覧取得: `GET /api/v1/stock-prices/`
- 詳細取得: `GET /api/v1/stock-prices/<id>/`
- 登録: `POST /api/v1/stock-prices/`
- 更新: `PUT` / `PATCH /api/v1/stock-prices/<id>/`
- 削除: `DELETE /api/v1/stock-prices/<id>/`

※ 認証・権限制御はフェーズ2でも未実装（AllowAny）。

---

## 5. 変更・追加したファイル一覧（フェーズ2）

| 種別 | パス |
|------|------|
| 変更 | `stocks/models.py` … `StockPriceDaily` モデルを追加 |
| 変更 | `stocks/admin.py` … `StockPriceDailyAdmin` を追加 |
| 変更 | `stocks/serializers.py` … `StockPriceDailySerializer` を追加 |
| 変更 | `stocks/views.py` … `StockPriceDailyViewSet` を追加 |
| 変更 | `stocks/urls.py` … `"stock-prices"` ルートを Router に登録 |
| 追加 | `stocks/migrations/0002_stockpricedaily.py` … `StockPriceDaily` 用マイグレーション |
| 変更 | `README.md` … プロジェクト構成にフェーズ2の情報を追記 |
| 追加 | `stocks/PHASE2.md` … 本ドキュメント（フェーズ2まとめ） |

---

## 6. マイグレーション手順

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py makemigrations stocks   # 既に 0002 がある場合はスキップされる
python manage.py migrate
```

- 初回は `stocks/migrations/0002_stockpricedaily.py` が適用され、`StockPriceDaily` テーブルが作成される。
- すでに適用済みの環境では `No migrations to apply.` となる。

---

## 7. 起動確認手順

### 7.1 サーバ起動

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

### 7.2 管理画面での確認

1. ブラウザで http://127.0.0.1:8000/admin/ を開く。
2. 「監視銘柄 (WatchStock)」に加えて、**「日足株価 (StockPriceDaily)」** が表示されていることを確認。
3. 既存の `WatchStock` を選んだ上で、日足データを手動で登録・編集できることを確認。

---

## 8. API 確認例（PowerShell）

※ 事前に `WatchStock` に対象銘柄（例: id=1, ticker=7203.T）が存在している前提です。

### 8.1 一覧取得

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/stock-prices/
```

### 8.2 stock で絞り込み（stock id=1 の例）

```powershell
curl.exe -s "http://127.0.0.1:8000/api/v1/stock-prices/?stock=1"
```

### 8.3 ticker で絞り込み（ticker=7203.T の例）

```powershell
curl.exe -s "http://127.0.0.1:8000/api/v1/stock-prices/?ticker=7203.T"
```

### 8.4 登録（POST）

```powershell
$body = '{
  "stock": 1,
  "date": "2026-03-13",
  "open_price": "2500.0",
  "high_price": "2550.0",
  "low_price": "2480.0",
  "close_price": "2520.0",
  "volume": 12345678
}'
[System.IO.File]::WriteAllText("$env:TEMP\stock_price.json", $body, [System.Text.UTF8Encoding]::new($false))
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/stock-prices/ -H "Content-Type: application/json" -d "@$env:TEMP\stock_price.json"
```

### 8.5 詳細取得（id=1 の例）

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/stock-prices/1/
```

### 8.6 更新（PUT の例）

```powershell
$body = '{
  "stock": 1,
  "date": "2026-03-13",
  "open_price": "2500.0",
  "high_price": "2560.0",
  "low_price": "2480.0",
  "close_price": "2530.0",
  "volume": 22345678
}'
[System.IO.File]::WriteAllText("$env:TEMP\stock_price.json", $body, [System.Text.UTF8Encoding]::new($false))
curl.exe -s -X PUT http://127.0.0.1:8000/api/v1/stock-prices/1/ -H "Content-Type: application/json" -d "@$env:TEMP\stock_price.json"
```

### 8.7 削除

```powershell
curl.exe -s -X DELETE http://127.0.0.1:8000/api/v1/stock-prices/1/
```

---

## 9. フェーズ2でできること / まだやっていないこと

### 9.1 フェーズ2でできること

- 監視銘柄 (`WatchStock`) ごとに、日足株価 (`StockPriceDaily`) を
  - 管理画面から登録・編集・削除
  - REST API 経由で CRUD
  - `stock`（id）または `ticker`（文字列）で絞り込んで一覧取得
- 日足株価の履歴を、将来の分析やシグナル生成のための**基礎データとして蓄積**できる。

### 9.2 まだやっていないこと（今後のフェーズで検討）

- 外部 API からの株価自動取得
- ダミーデータ投入コマンド
- テクニカル分析・ファンダメンタル分析
- 買いスコア / 売りスコア
- シグナル判定
- AI 連携
- LINE 通知
- バッチ処理
- フォーメーション分析
- API 認証・ユーザー単位の権限制御

---

フェーズ2では、`WatchStock` を自然に拡張する形で `StockPriceDaily` を追加し、日足株価の CRUD とシンプルな絞り込み API を提供するところまでを行いました。分析・通知・自動取得などは次フェーズ以降で段階的に追加できます。

