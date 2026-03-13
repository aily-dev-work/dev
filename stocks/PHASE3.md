# 株価監視アプリ フェーズ3 進捗まとめ

## 1. フェーズ3の目的

- **目的**: 保存済みの日足株価データから、**1銘柄単位で基本的なテクニカル指標を計算し、API で取得**できるようにする。
- **範囲**:
  - 既存の日足データ (`StockPriceDaily`) を利用して、移動平均や高値・安値、出来高トレンドなどの**基本的なテクニカル指標**を計算。
  - 買いスコア / 売りスコア、提案、通知、AI 連携などは行わない。
- **前提**:
  - フェーズ1で `WatchStock` と `/api/v1/stocks/` の CRUD API が実装済み。
  - フェーズ2で `StockPriceDaily` と `/api/v1/stock-prices/` の CRUD API が実装済み。
  - 認証・権限制御は引き続き未実装（AllowAny）で、最小限の read API を追加する。

---

## 2. 追加・変更した構成（フェーズ3）

### 2.1 service 層の追加

- ディレクトリ: `stocks/services/`
- ファイル: `technical_analysis.py`
- 役割:
  - `StockPriceDaily` からテクニカル指標を計算するロジックをまとめる。
  - View に直接計算ロジックを書きすぎないようにし、将来の指標追加やリファクタリングをしやすくする。

主なクラス / 関数（dataclass ベース）:

- `MovingAverages` … `ma5`, `ma25`, `ma75`
- `HighLow` … `high_20`, `low_20`
- `AverageVolume` … `avg_volume_5`, `avg_volume_20`
- `TechnicalSignals` … `trend_short`, `trend_mid`, `trend_long`, `volume_trend`
- `TechnicalSummary` … 上記をまとめた 1 銘柄分の集約結果
- `calculate_technical_summary(stock: WatchStock) -> TechnicalSummary`
  - 指定銘柄の `StockPriceDaily` をもとにテクニカル集計を行う。
  - データ不足の場合は該当指標を `None` として返却する（API 側では `null`）。

### 2.2 View の拡張

- `stocks/views.py`
  - `WatchStockViewSet` に対して、新しいアクション `technical` を追加。
  - URL: `/api/v1/stocks/<id>/technical/`（detail アクション）
  - `calculate_technical_summary` を呼び出して JSON 形式で返却する。

---

## 3. 計算しているテクニカル指標

### 3.1 基本指標

1銘柄 (`WatchStock`) に対して、以下を計算:

- **最新終値**
  - `latest_date`: 最新日付（文字列 `"YYYY-MM-DD"`）
  - `latest_close`: 最新終値（Decimal を文字列化）

- **単純移動平均 (SMA)**
  - `ma5`: 直近 5 営業日の終値平均（5 本未満なら `null`）
  - `ma25`: 直近 25 営業日の終値平均（25 本未満なら `null`）
  - `ma75`: 直近 75 営業日の終値平均（75 本未満なら `null`）

- **直近 20 営業日の高値・安値**
  - `high_20`: 直近 20 本の中の終値の最大値（十分な本数がなければ取得できる範囲で / 0 本なら `null`）
  - `low_20`: 直近 20 本の中の終値の最小値（同上）

- **平均出来高**
  - `avg_volume_5`: 直近 5 本分の出来高平均（`volume` が `null` のレコードは除外。有効データ 0 件なら `null`）
  - `avg_volume_20`: 直近 20 本分の出来高平均（同上）

### 3.2 シンプルな判定値（signals）

- `trend_short`: 短期トレンド
  - 最新終値 vs `ma5` の関係で判定
  - `latest_close > ma5` → `"up"`
  - `latest_close < ma5` → `"down"`
  - それ以外 → `"flat"`
  - `ma5` が `null` の場合 → `null`

- `trend_mid`: 中期トレンド
  - `ma25` を用いて `trend_short` と同様のロジック

- `trend_long`: 長期トレンド
  - `ma75` を用いて `trend_short` と同様のロジック

- `volume_trend`: 出来高のトレンド
  - `avg_volume_5` と `avg_volume_20` の比で判定
  - 両方 `null` または `avg_volume_20 == 0` → `null`
  - `avg_volume_5 / avg_volume_20 >= 1.5` → `"high"`
  - `avg_volume_5 / avg_volume_20 <= 0.5` → `"low"`
  - それ以外 → `"normal"`

---

## 4. 追加した API

### 4.1 エンドポイント

- ベース URL: `/api/v1/stocks/<id>/technical/`
  - `<id>` は `WatchStock` の id（整数）。
  - 例: `/api/v1/stocks/1/technical/`

### 4.2 HTTP メソッド

- `GET` のみ（情報取得専用）。

### 4.3 レスポンス例

```json
{
  "stock_id": 1,
  "ticker": "7203.T",
  "name": "トヨタ自動車",
  "latest_date": "2026-03-13",
  "latest_close": "2520.0000",
  "moving_averages": {
    "ma5": "2505.0000",
    "ma25": "2480.1234",
    "ma75": null
  },
  "high_low": {
    "high_20": "2550.0000",
    "low_20": "2400.0000"
  },
  "average_volume": {
    "avg_volume_5": 12345678.0,
    "avg_volume_20": 9876543.0
  },
  "signals": {
    "trend_short": "up",
    "trend_mid": "up",
    "trend_long": null,
    "volume_trend": "normal"
  }
}
```

- 数値系:
  - 価格系は Decimal を文字列化して返却（AI やフロント側での扱いを簡単にするため）。
  - 出来高は `float` として返却。
- `null`:
  - データ不足、または指標が計算できない場合は `null` を返す。

---

## 5. データ不足時の挙動

- `StockPriceDaily` が 1 件もない場合:
  - `latest_date`, `latest_close`, すべての移動平均・高値・安値・平均出来高・signals → `null`
  - API 自体は 200 OK で空のサマリに近い形を返却（エラーにしない）。

- 本数不足のとき:
  - 5 本未満 … `ma5` は `null`
  - 25 本未満 … `ma25` は `null`
  - 75 本未満 … `ma75` は `null`
  - 出来高平均:
    - 有効な `volume` が 1 件以上あれば、その範囲で平均を計算。
    - 有効な `volume` が 0 件なら対応する平均は `null`。
  - `trend_*`:
    - 対応する移動平均が `null` の場合は `null`。
  - `volume_trend`:
    - `avg_volume_5` または `avg_volume_20` が `null` / 0 の場合は `null`。

このように、**指標ごとに計算可能なものだけ値を返し、不足分は `null` にする**方針としています。  
API は常に正常レスポンスを返し、クライアント側で「どの指標が使えるか」を判定しやすい構造です。

---

## 6. 変更・追加したファイル一覧（フェーズ3）

| 種別 | パス |
|------|------|
| 追加 | `stocks/services/technical_analysis.py` … テクニカル計算ロジック |
| 変更 | `stocks/views.py` … `WatchStockViewSet` に `technical` アクションを追加 |
| 変更 | `README.md` … プロジェクト構成に service 層と PHASE3 を追記 |
| 追加 | `stocks/PHASE3.md` … 本ドキュメント（フェーズ3まとめ） |

※ モデル・マイグレーションはフェーズ3では追加していません（フェーズ2までの構造をそのまま利用）。

---

## 7. 起動・確認手順

### 7.1 前提

- すでにフェーズ1/2 までのマイグレーションが適用済み。
- `WatchStock` と `StockPriceDaily` にテスト用のデータが入っていること（例: `stock id=1` に複数日分）。

### 7.2 サーバ起動

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

### 7.3 API 確認（テクニカルサマリ）

- `stock id=1` のテクニカル指標を取得:

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/stocks/1/technical/
```

- 日足データが十分にある場合は、`moving_averages` や `high_low`, `average_volume`, `signals` に値が入っていることを確認。
- ほとんどデータがない場合でも、API が 200 OK を返し、該当しない指標が `null` で返ってくることを確認。

---

## 8. フェーズ3でできること / まだやっていないこと

### 8.1 フェーズ3でできること

- 各監視銘柄 (`WatchStock`) について:
  - 保存済みの日足株価 (`StockPriceDaily`) をもとに、
    - 最新終値
    - 5/25/75 日単純移動平均
    - 直近 20 営業日の高値・安値
    - 直近 5/20 営業日の平均出来高
    - シンプルなトレンド判定（短期/中期/長期、出来高トレンド）
  - を **1銘柄単位で API から取得**できる。
- レスポンス構造は、今後のスコア計算や AI 分析の入力として扱いやすい形式（数値・ラベル・期間が分離）になっている。

### 8.2 まだやっていないこと（今後のフェーズで検討）

- RSI / MACD / ボリンジャーバンド
- フォーメーション分析
- 買いスコア / 売りスコア
- 提案結果の保存や履歴管理
- AI 連携
- LINE 通知
- 外部 API からの株価自動取得
- バッチ処理（定期的な指標計算など）
- API 認証・ユーザー単位の権限制御

---

フェーズ3では、`stocks/services/technical_analysis.py` にテクニカル計算ロジックを集約し、View を薄く保ちながら `/api/v1/stocks/<id>/technical/` で 1銘柄分のテクニカルサマリを取得できるようにしました。  
今後のフェーズでは、このサマリをもとにスコアリングや AI 分析、通知ロジックなどを段階的に追加できます。

