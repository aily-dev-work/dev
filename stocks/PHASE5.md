# 株価監視アプリ フェーズ5 進捗まとめ

## 1. フェーズ5の目的

- **目的**: フェーズ4までで計算したスコアを「提案（シグナル）」として保存し、  
  将来のバックテストや AI 分析に利用できるようにする。
- **範囲**:
  - 1銘柄・1日単位で `TradingSignal` を保存し、テクニカル状態とスコアをスナップショットとして保持する。
  - 提案文や通知は行わない（データ保存の土台のみ）。

---

## 2. 追加したモデル: TradingSignal

### 2.1 モデル定義

- 所属アプリ: `stocks`
- モデル名: `TradingSignal`
- 役割: シグナル発生時点のスコアとテクニカル状態を保存する。

フィールド:

- `stock`: `ForeignKey(WatchStock, related_name="signals", CASCADE)`
- `signal_date`: `DateField`
  - 通常はテクニカルサマリの `latest_date` を利用。
- `signal_type`: `CharField(max_length=16, choices=["buy", "sell", "neutral"])`
- `buy_score`: `DecimalField(max_digits=5, decimal_places=2)`
- `sell_score`: `DecimalField(max_digits=5, decimal_places=2)`
- `score_bias`: `CharField(max_length=16)`（buy / sell / neutral）
- `score_strength`: `CharField(max_length=16)`（weak / normal / strong）
- `signal_price`: `DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)`
  - シグナル生成時の価格（通常は `latest_close`）。  
    フェーズ6 以降のバックテストで、「提案時点価格」として利用予定。
- `latest_close`: `DecimalField(12, 4, null=True, blank=True)`
- `ma25`: `DecimalField(12, 4, null=True, blank=True)`
- `ma75`: `DecimalField(12, 4, null=True, blank=True)`
- `high_20`: `DecimalField(12, 4, null=True, blank=True)`
- `low_20`: `DecimalField(12, 4, null=True, blank=True)`
- `technical_position`: `DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)`
  - 20日レンジ内での価格位置。  
    `pos = (latest_close - low_20) / (high_20 - low_20)` を 0〜1 に正規化した値。
  - `high_20` / `low_20` / `latest_close` のいずれかが欠損している、もしくはレンジ幅が 0 の場合は `null`。
- `trend_short`: `CharField(max_length=16, null=True, blank=True)`
- `trend_mid`: `CharField(max_length=16, null=True, blank=True)`
- `trend_long`: `CharField(max_length=16, null=True, blank=True)`
- `volume_trend`: `CharField(max_length=16, null=True, blank=True)`
- `created_at`: `DateTimeField(auto_now_add=True)`

Meta:

- `ordering = ["-signal_date", "-created_at"]`
- `UniqueConstraint(fields=["stock", "signal_date"], name="unique_stock_signal_per_day")`

---

## 3. シグナル生成ロジック（service 層）

### 3.1 `stocks/services/signal_generation.py`

関数:

```python
def generate_trading_signal(
    stock: WatchStock,
    summary: TechnicalSummary,
    score: ScoreResult,
) -> TradingSignal:
    ...
```

処理の流れ:

1. `signal_date` を決定
   - 原則として `summary.latest_date`（`YYYY-MM-DD`）を `date.fromisoformat` で日付に変換。
   - `latest_date` がない場合は `date.today()` を使用。
2. `signal_type` を決定
   - `score.bias == "buy"` → `"buy"`
   - `score.bias == "sell"` → `"sell"`
   - それ以外 → `"neutral"`
3. `TradingSignal.objects.update_or_create(...)` により保存
   - キー: `(stock, signal_date)`
   - `defaults` として以下を保存:
     - `signal_type`, `buy_score`, `sell_score`, `score_bias`, `score_strength`
     - `signal_price`（`summary.latest_close`）
     - `latest_close`
     - `ma25`, `ma75`
     - `high_20`, `low_20`
     - `technical_position`（20日レンジ内での価格位置。0〜1、計算不能時は null）
     - `trend_short`, `trend_mid`, `trend_long`, `volume_trend`

これにより、1銘柄・1日あたり最大 1 件のシグナルが保存され、  
同じ日に再度生成した場合は同じレコードが更新される。

---

## 4. API 追加

### 4.1 シグナル生成 API（POST）

- エンドポイント: `POST /api/v1/stocks/<id>/generate-signal/`
- 実装場所: `WatchStockViewSet.generate_signal`
- 処理フロー:
  1. `WatchStock` を `pk` から取得。
  2. `calculate_technical_summary(stock)` でテクニカルサマリを取得。
  3. `score_from_technical(summary)` でスコア・バイアス・強度を計算。
  4. `generate_trading_signal(stock, summary, score_result)` で `TradingSignal` を保存。
  5. 保存された `TradingSignal` の内容を JSON で返却（201 Created）。

レスポンス例（要約）:

```json
{
  "id": 10,
  "stock_id": 1,
  "signal_date": "2026-03-13",
  "signal_type": "buy",
  "buy_score": 72.0,
  "sell_score": 28.0,
  "score_bias": "buy",
  "score_strength": "strong",
  "signal_price": "2520.0000",
  "latest_close": "2520.0000",
  "ma25": "2480.1234",
  "ma75": null,
  "high_20": "2550.0000",
  "low_20": "2400.0000",
  "trend_short": "up",
  "trend_mid": "up",
  "trend_long": "up",
  "volume_trend": "normal",
  "created_at": "2026-03-13T12:34:56+09:00"
}
```

### 4.2 シグナル履歴取得 API（GET）

- エンドポイント: `GET /api/v1/stocks/<id>/signals/`
- 実装場所: `WatchStockViewSet.signals`
- 振る舞い:
  - 指定銘柄の `TradingSignal` を `signal_date` / `created_at` の降順で一覧返却。

レスポンス例（要約）:

```json
[
  {
    "id": 10,
    "signal_date": "2026-03-13",
    "signal_type": "buy",
    "buy_score": 72.0,
    "sell_score": 28.0,
    "score_bias": "buy",
    "score_strength": "strong",
    "signal_price": "2520.0000",
    "created_at": "2026-03-13T12:34:56+09:00"
  },
  {
    "id": 7,
    "signal_date": "2026-03-12",
    "signal_type": "neutral",
    "buy_score": 40.0,
    "sell_score": 35.0,
    "score_bias": "neutral",
    "score_strength": "weak",
    "signal_price": "2500.0000",
    "created_at": "2026-03-12T12:34:56+09:00"
  }
]
```

---

## 5. Admin での確認

`stocks/admin.py` に `TradingSignalAdmin` を追加:

- `list_display`:
  - `stock`, `signal_date`, `signal_type`,
    `buy_score`, `sell_score`, `score_bias`, `score_strength`, `created_at`
- `list_filter`:
  - `stock`, `signal_type`, `score_bias`, `score_strength`
- `search_fields`:
  - `stock__ticker`, `stock__name`

管理画面から、銘柄ごとのシグナル履歴を一覧・フィルタ・検索できます。

---

## 6. 保存データのイメージと将来のバックテスト

1 レコード (`TradingSignal`) には、主に次の情報が保存されます。

- **シグナル情報**
  - 銘柄 (`stock`)
  - シグナル日 (`signal_date`)
  - シグナル種別 (`signal_type`)
  - `buy_score`, `sell_score`
  - `score_bias`, `score_strength`
- **価格・テクニカル状態**
  - `signal_price`（提案時点の価格）
  - `latest_close`, `ma25`, `ma75`
  - `high_20`, `low_20`
  - `trend_short`, `trend_mid`, `trend_long`, `volume_trend`

将来的には、ここから:

- `signal_price` → 5日後 / 10日後の `close_price` とのリターン計算
- bias / strength ごとのヒット率集計
- テクニカル状態ごとの勝率やドローダウン分析

などを行い、スコアロジックや重みのチューニングに利用できます。

---

## 7. 変更・追加したファイル一覧（フェーズ5）

- 変更:
  - `stocks/models.py` … `TradingSignal` モデルの追加
  - `stocks/admin.py` … `TradingSignalAdmin` の追加
  - `stocks/views.py` … `generate_signal` / `signals` アクションの追加
- 追加:
  - `stocks/services/signal_generation.py` … シグナル生成ロジック
  - `stocks/migrations/0003_tradingsignal.py` … `TradingSignal` 用マイグレーション
  - `stocks/PHASE5.md` … 本ドキュメント

これで、フェーズ5の目的である「スコア計算結果を提案として保存する土台」が整いました。

