# 株価監視アプリ フェーズ7 進捗まとめ

## 1. フェーズ7の目的

- **目的**: `TradingSignal` と `SignalOutcome` を横断し、  
  1シグナル = 1行のフラットなデータセットを API で取得できるようにする。
- **用途**:
  - 将来の AI 分析・重み調整・バックテスト集計の**入力テーブル**として利用。
  - ダッシュボードや BI ツールへの取り込みをしやすくする。

---

## 2. 追加した service: `signal_dataset.py`

- パス: `stocks/services/signal_dataset.py`
- 役割:
  - `TradingSignal` と `SignalOutcome` を結合した QuerySet の構築。
  - 1シグナル=1行の dict へフラット化。

### 2.1 QuerySet 構築: `build_signal_queryset(params)`

- `TradingSignal.objects.select_related("stock", "outcome")` をベースに、  
  以下のクエリパラメータによるフィルタを適用:

| パラメータ           | 条件                                             |
|----------------------|--------------------------------------------------|
| `stock`              | `stock_id` で絞り込み                            |
| `ticker`             | `stock__ticker` で絞り込み                       |
| `signal_type`        | `signal_type` で絞り込み                         |
| `score_bias`         | `score_bias` で絞り込み                          |
| `score_strength`     | `score_strength` で絞り込み                      |
| `eval_status`        | `outcome__eval_status` で絞り込み               |
| `signal_date_from`   | `signal_date__gte`                               |
| `signal_date_to`     | `signal_date__lte`                               |

- 並び順:
  - デフォルトで `signal_date` 降順、次に `created_at` 降順。

### 2.2 フラット化: `signals_to_dataset(signals)`

- 引数: `Iterable[TradingSignal]`
- 戻り値: `List[Dict[str, Any]]`
- 各行のキー（少なくとも以下を含む）:

```text
signal_id
stock_id
ticker
name
signal_date
signal_type
buy_score
sell_score
score_bias
score_strength
signal_price
latest_close
ma25
ma75
high_20
low_20
technical_position
trend_short
trend_mid
trend_long
volume_trend
base_price
eval_status
date_5d
close_5d
return_5d
success_5d
date_10d
close_10d
return_10d
success_10d
date_20d
close_20d
return_20d
success_20d
signal_created_at
outcome_updated_at
```

- `outcome` が存在しない場合:
  - outcome 系の列 (`base_price`, `eval_status`, `date_*`, `close_*`, `return_*`, `success_*`, `outcome_updated_at`) はすべて `null`。

---

## 3. 追加した API: `/api/v1/signals/dataset/`

- 実装: `SignalViewSet.dataset`
- URL: `GET /api/v1/signals/dataset/`
- 振る舞い:
  1. `build_signal_queryset(request.query_params)` で QuerySet を構築。
  2. `signals_to_dataset(qs)` で 1シグナル=1行のデータセットに変換。
  3. JSON 配列として返却。

### 3.1 対応クエリパラメータ

- `stock=<WatchStock id>`
- `ticker=<ticker 文字列>`
- `signal_type=buy|sell|neutral`
- `score_bias=buy|sell|neutral`
- `score_strength=weak|normal|strong`
- `eval_status=pending|partial|completed`
- `signal_date_from=YYYY-MM-DD`
- `signal_date_to=YYYY-MM-DD`

### 3.2 レスポンス例（要約）

```json
[
  {
    "signal_id": 12,
    "stock_id": 1,
    "ticker": "7203.T",
    "name": "トヨタ自動車",
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
    "technical_position": "0.80",
    "trend_short": "up",
    "trend_mid": "up",
    "trend_long": "up",
    "volume_trend": "normal",
    "base_price": "2520.0000",
    "eval_status": "partial",
    "date_5d": "2026-03-20",
    "close_5d": "2580.0000",
    "return_5d": "0.0238",
    "success_5d": true,
    "date_10d": null,
    "close_10d": null,
    "return_10d": null,
    "success_10d": null,
    "date_20d": null,
    "close_20d": null,
    "return_20d": null,
    "success_20d": null,
    "signal_created_at": "2026-03-13T12:34:56+09:00",
    "outcome_updated_at": "2026-03-20T12:34:56+09:00"
  }
]
```

---

## 4. PowerShell での確認例

### 4.1 全件取得

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/signals/dataset/ | ConvertFrom-Json | Select-Object -First 3
```

### 4.2 ticker 絞り込み

```powershell
curl.exe -s "http://127.0.0.1:8000/api/v1/signals/dataset/?ticker=7203.T"
```

### 4.3 `eval_status=completed` のみ

```powershell
curl.exe -s "http://127.0.0.1:8000/api/v1/signals/dataset/?eval_status=completed"
```

### 4.4 日付範囲で絞り込み

```powershell
curl.exe -s "http://127.0.0.1:8000/api/v1/signals/dataset/?signal_date_from=2026-03-01&signal_date_to=2026-03-31"
```

---

## 5. 変更・追加したファイル一覧（フェーズ7）

- 追加:
  - `stocks/services/signal_dataset.py` … QuerySet 構築 & フラット化ロジック。
  - `stocks/PHASE7.md` … 本ドキュメント。
- 変更:
  - `stocks/views.py` … `SignalViewSet.dataset` を追加。
  - `stocks/urls.py` … `SignalViewSet` を router に登録済み（`/api/v1/signals/` 配下）。
  - `README.md` … フェーズ1〜7 までの構成に更新。

---

## 6. 今後の拡張（フェーズ8以降の候補）

- 集計 API:
  - 銘柄別 / 期間別の成功率集計
  - bias / strength 別の勝率
- AI 連携:
  - このデータセットをそのまま AI に渡して、重みやロジックの改善案を得る。
- ダッシュボード:
  - 成功率・リターン分布・ドローダウンなどの可視化。

（本フェーズではあくまで「フラットな行データを取得する API」までを実装し、集計や AI 呼び出しは行っていません。）

