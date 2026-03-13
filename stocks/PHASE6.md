# 株価監視アプリ フェーズ6 進捗まとめ

## 1. フェーズ6の目的

- **目的**: フェーズ5までに保存した `TradingSignal` ごとに、その後の価格推移を検証して  
  **5/10/20 営業日後のリターンと成否を保存できる状態**にする。
- **範囲**:
  - 1シグナル = 1結果 (`SignalOutcome`) という構造で検証データを保存。
  - 集計ダッシュボードや AI 連携は行わず、まずは元データの保存に集中する。

---

## 2. 追加したモデル: SignalOutcome

### 2.1 モデル定義

- 所属アプリ: `stocks`
- モデル名: `SignalOutcome`
- 関連:
  - `signal`: `OneToOneField(TradingSignal, related_name="outcome", on_delete=CASCADE)`

フィールド:

- `base_price`: `DecimalField(12, 4, null=True, blank=True)`
  - 通常は `signal.signal_price`（なければ `signal.latest_close`）をコピー。
- `eval_status`: `CharField(max_length=16, default="pending")`
  - `pending` / `partial` / `completed`

### 2.2 5/10/20 営業日後

- 5 営業日後:
  - `date_5d`: `DateField(null=True, blank=True)`
  - `close_5d`: `DecimalField(12, 4, null=True, blank=True)`
  - `return_5d`: `DecimalField(8, 4, null=True, blank=True)`
  - `success_5d`: `BooleanField(null=True, blank=True)`
- 10 営業日後:
  - `date_10d`
  - `close_10d`
  - `return_10d`
  - `success_10d`
- 20 営業日後:
  - `date_20d`
  - `close_20d`
  - `return_20d`
  - `success_20d`

その他:

- `created_at`: `DateTimeField(auto_now_add=True)`
- `updated_at`: `DateTimeField(auto_now=True)`

---

## 3. 成功判定ルール

- `signal.signal_type == "buy"`:
  - `return_N > 0` → `success_N = True`
  - `return_N <= 0` → `success_N = False`
- `signal.signal_type == "sell"`:
  - `return_N < 0` → `success_N = True`
  - `return_N >= 0` → `success_N = False`
- `signal.signal_type == "neutral"`:
  - `success_N = None`（neutral の成否はまだ判定しない）

---

## 4. 評価ロジック（service 層）

### 4.1 `stocks/services/signal_evaluation.py`

関数:

```python
def evaluate_signal(signal: TradingSignal) -> SignalOutcome:
    ...
```

処理の流れ:

1. **base_price の決定**
   - `base_price = signal.signal_price or signal.latest_close`
2. **対象日足の取得**
   - `StockPriceDaily` を `signal.stock` / `date > signal.signal_date` で絞り、
     `date` 昇順に並べたリスト `days` を作成。
3. **5/10/20 営業日後のレコード取得**
   - `days[4]` → 5 営業日後 (`h5`)
   - `days[9]` → 10 営業日後 (`h10`)
   - `days[19]` → 20 営業日後 (`h20`)
   - 該当 index が存在しない場合、その horizon は未評価（全て `null`）。
4. **リターン計算**
   - `return_N = (close_N - base_price) / base_price`  
     - `base_price` または `close_N` が `null`、あるいは `base_price == 0` の場合は `return_N = None`。
5. **success 判定**
   - 上記「成功判定ルール」に従い、`success_N` を決定。
6. **eval_status 判定**
   - `return_5d`, `return_10d`, `return_20d` の有無で判定:
     - 3つとも `null` → `"pending"`
     - 1つ以上は非 `null` だが、3つすべてではない → `"partial"`
     - 3つとも非 `null` → `"completed"`
7. **保存**
   - `SignalOutcome.objects.update_or_create(signal=signal, defaults={...})` で保存し、`SignalOutcome` を返す。

---

## 5. 「営業日後」の定義

- `signal.signal_date` 当日は含めず、**翌日以降の `StockPriceDaily` から数えて**:
  - 5本目 → 5 営業日後
  - 10本目 → 10 営業日後
  - 20本目 → 20 営業日後
- 同一銘柄の `StockPriceDaily` を `date > signal_date` で昇順に並べて index を参照しています。
- データ不足（例: 10本未満）の場合、その horizon は未評価（`date_N` / `close_N` / `return_N` / `success_N` すべて `null`）。

---

## 6. 追加した API

### 6.1 単体評価 API（POST）

- エンドポイント: `POST /api/v1/signals/<id>/evaluate/`
- 実装: `SignalViewSet.evaluate`
- 挙動:
  1. `TradingSignal` を `<id>` から取得。
  2. `evaluate_signal(signal)` を呼び出して `SignalOutcome` を生成・更新。
  3. 結果を JSON で返却。

レスポンス例:

```json
{
  "signal_id": 12,
  "stock_id": 1,
  "ticker": "7203.T",
  "signal_type": "buy",
  "signal_date": "2026-03-13",
  "base_price": "2520.0000",
  "eval_status": "partial",
  "outcomes": {
    "5d": {
      "date": "2026-03-20",
      "close": "2580.0000",
      "return": "0.0238",
      "success": true
    },
    "10d": {
      "date": null,
      "close": null,
      "return": null,
      "success": null
    },
    "20d": {
      "date": null,
      "close": null,
      "return": null,
      "success": null
    }
  }
}
```

### 6.2 結果取得 API（GET）

- エンドポイント: `GET /api/v1/signals/<id>/outcome/`
- 実装: `SignalViewSet.outcome`
- 挙動:
  - `SignalOutcome` が存在すれば、上記と同じ形式の JSON を返却。
  - 未評価の場合は 404:

```json
{
  "detail": "Outcome not evaluated yet."
}
```

---

## 7. Admin での確認

`stocks/admin.py` に `SignalOutcomeAdmin` を追加:

- 一覧表示 (`list_display`):
  - `signal`, `eval_status`, `base_price`,
    `return_5d`, `success_5d`,
    `return_10d`, `success_10d`,
    `return_20d`, `success_20d`,
    `updated_at`
- 絞り込み (`list_filter`):
  - `eval_status`, `success_5d`, `success_10d`, `success_20d`
- 検索 (`search_fields`):
  - `signal__stock__ticker`, `signal__stock__name`

---

## 8. データ不足時の挙動

- `StockPriceDaily` が少なくて 5/10/20 営業日後のいずれかが存在しない場合:
  - その horizon の `date`, `close`, `return`, `success` はすべて `null`。
  - 他の horizon が埋まっていれば `eval_status = "partial"`。
  - 全て埋まっていなければ `eval_status = "pending"`。
- `base_price` が `null` の場合:
  - すべての `return_N` / `success_N` は `null` のまま。
  - `eval_status` は horizon の埋まり具合に応じて `pending` / `partial`。

---

## 9. 今後の AI 分析へのつながり

- `TradingSignal` + `SignalOutcome` により、1 行で以下が揃う:
  - シグナル発生時のスコア・テクニカル状態
  - 5/10/20 営業日後のリターンと成否
  - 評価ステータス
- これをそのまま表形式データとして AI に渡すことで:
  - スコアロジックの重み調整
  - 成功パターン / 失敗パターンの発見
  - 将来の自動チューニング
などに利用できるようになります。

