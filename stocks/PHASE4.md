# 株価監視アプリ フェーズ4 進捗まとめ

## 1. フェーズ4の目的

- **目的**: 保存済みの日足データから計算したテクニカルサマリ（フェーズ3）をもとに、  
  **1銘柄単位で「買いスコア」「売りスコア」を計算して API で取得**できるようにする。
- **範囲**:
  - フェーズ3の `/api/v1/stocks/<id>/technical/` を入力として、シンプルなルールベースのスコアリングを行う。
  - スコアは 0〜100 の範囲で、初版として分かりやすい加点方式を採用。
  - 提案文・通知・AI 連携は行わない。
- **前提**:
  - フェーズ1〜3 がすでに実装・動作している。
  - 認証・権限制御は引き続き未実装（AllowAny）で、read-only なスコア API を追加する。

---

## 2. 追加・変更した構成（フェーズ4）

### 2.1 service 層の追加（スコア計算）

- ディレクトリ: `stocks/services/`
- ファイル: `signal_scoring.py`
- 役割:
  - フェーズ3で定義した `TechnicalSummary` を入力として、  
    買いスコア (`buy_score`) / 売りスコア (`sell_score`) と各項目の内訳を計算する。
  - 重み（ウェイト）を定数辞書としてまとめ、後から調整しやすくする。

主な要素:

- `ScoreResult` dataclass
  - `buy_score: float`
  - `sell_score: float`
  - `breakdown_buy: Dict[str, float]`
  - `breakdown_sell: Dict[str, float]`
  - `insufficient_data: bool`
  - `insufficient_reason: Optional[str]`
- 重み定義:
  - `BUY_WEIGHTS` / `SELL_WEIGHTS`（dict）
    - 例: `"trend_long_up": 20.0`, `"trend_mid_up": 15.0`, `"trend_short_up": 10.0`, など
- メイン関数:
  - `score_from_technical(summary: TechnicalSummary) -> ScoreResult`

### 2.2 View の拡張（スコア API）

- `stocks/views.py`
  - `WatchStockViewSet` に新しい detail アクション `score` を追加。
  - URL: `/api/v1/stocks/<id>/score/`
  - 処理の流れ:
    1. `calculate_technical_summary(stock)` を呼び出してテクニカルサマリを取得。
    2. `score_from_technical(summary)` を呼び出してスコアと内訳を計算。
    3. 必要最小限のテクニカル要約とともに JSON で返却。

---

## 3. スコア計算ロジック（概要）

### 3.1 使用するテクニカル情報（フェーズ3のサマリから）

- `latest_close`
- `moving_averages.ma25`
- `moving_averages.ma75`
- `high_low.high_20`
- `high_low.low_20`
- `signals.trend_short`, `signals.trend_mid`, `signals.trend_long`
- `signals.volume_trend`

### 3.2 重み（初版）

```python
BUY_WEIGHTS = {
    "trend_long_up": 20.0,
    "trend_mid_up": 15.0,
    "trend_short_up": 10.0,
    "volume_high": 10.0,
    "above_ma25": 10.0,
    "above_ma75": 10.0,
    "near_high_20": 10.0,
}

SELL_WEIGHTS = {
    "trend_long_down": 20.0,
    "trend_mid_down": 15.0,
    "trend_short_down": 10.0,
    "volume_low": 10.0,
    "below_ma25": 10.0,
    "below_ma75": 10.0,
    "near_low_20": 10.0,
}
```

### 3.3 加点ルール（初版のイメージ）

- **トレンド系**
  - `trend_long == "up"` → `buy.trend_long_up += 20`
  - `trend_mid == "up"` → `buy.trend_mid_up += 15`
  - `trend_short == "up"` → `buy.trend_short_up += 10`
  - `trend_long == "down"` → `sell.trend_long_down += 20`
  - `trend_mid == "down"` → `sell.trend_mid_down += 15`
  - `trend_short == "down"` → `sell.trend_short_down += 10`

- **出来高トレンド**
  - `volume_trend == "high"` → `buy.volume_high += 10`
  - `volume_trend == "low"` → `sell.volume_low += 10`

- **移動平均との位置関係**
  - `latest_close > ma25` → `buy.above_ma25 += 10`
  - `latest_close < ma25` → `sell.below_ma25 += 10`
  - `latest_close > ma75` → `buy.above_ma75 += 10`
  - `latest_close < ma75` → `sell.below_ma75 += 10`

- **20日高値/安値との位置関係**
  - `high_20` / `low_20` が存在し、レンジ幅が正の場合:
    - 正規化位置 `pos = (latest_close - low_20) / (high_20 - low_20)` を 0〜1 にマッピング。
    - `pos >= 0.7` → `buy.near_high_20 += 10`（高値圏に近い：上昇継続の期待）
    - `pos <= 0.3` → `sell.near_low_20 += 10`（安値圏に近い：弱さのシグナル）

- **スコア範囲の制御**
  - `buy_score_raw = sum(breakdown_buy.values())`
  - `sell_score_raw = sum(breakdown_sell.values())`
  - 最終スコアは 0〜100 にクランプ:

    ```python
    buy_score = clamp(buy_score_raw, 0, 100)
    sell_score = clamp(sell_score_raw, 0, 100)
    ```

- 各項目のスコアは `breakdown_buy` / `breakdown_sell` としてそのまま返却するため、  
  「どの条件で何点入っているか」を後から読みやすい構造になっています。

---

## 4. 追加した API

### 4.1 エンドポイント

- ベース URL: `/api/v1/stocks/<id>/score/`
  - `<id>` は `WatchStock` の id（整数）。
  - 例: `/api/v1/stocks/1/score/`

### 4.2 HTTP メソッド

- `GET` のみ。

### 4.3 レスポンス構造（例）

```json
{
  "stock_id": 1,
  "ticker": "7203.T",
  "name": "トヨタ自動車",
  "buy_score": 72.0,
  "sell_score": 28.0,
  "score_breakdown": {
    "buy": {
      "trend_long_up": 20.0,
      "trend_mid_up": 15.0,
      "trend_short_up": 10.0,
      "volume_high": 10.0,
      "above_ma25": 10.0,
      "above_ma75": 7.0,
      "near_high_20": 0.0
    },
    "sell": {
      "trend_long_down": 0.0,
      "trend_mid_down": 0.0,
      "trend_short_down": 0.0,
      "volume_low": 0.0,
      "below_ma25": 0.0,
      "below_ma75": 0.0,
      "near_low_20": 0.0
    }
  },
  "technical_summary": {
    "latest_date": "2026-03-13",
    "latest_close": "2520.0000",
    "moving_averages": {
      "ma25": "2480.1234",
      "ma75": null
    },
    "high_low": {
      "high_20": "2550.0000",
      "low_20": "2400.0000"
    },
    "signals": {
      "trend_short": "up",
      "trend_mid": "up",
      "trend_long": "up",
      "volume_trend": "normal"
    }
  },
  "insufficient_data": false,
  "insufficient_reason": null
}
```

---

## 5. データ不足時の挙動

- **テクニカルサマリ自体がほぼ空（`StockPriceDaily` が 0 件）の場合**
  - 多くの指標が `None` となり、対応するスコア項目は 0 点扱い。
  - `insufficient_data: true`
  - `insufficient_reason` に `"ma25_or_latest_missing"`, `"ma75_or_latest_missing"`, `"high_20_or_low_20_or_latest_missing"` などの理由がカンマ区切りで格納される。
  - API 自体は 200 OK を返し、買い/売りスコアは 0〜100 の範囲（通常は 0）で返却。

- **一部のみ不足している場合**
  - 例: ma75 が未計算だが、ma25 と latest_close はある
    - `above_ma25` / `below_ma25` は評価される。
    - `above_ma75` / `below_ma75` は 0 点扱い。
    - `insufficient_data: true` になり、理由に `"ma75_or_latest_missing"` が含まれる。

- **基本方針**
  - **評価可能な条件だけ加点し、不足している条件は 0 点（未評価）扱い。**
  - API は常に正常レスポンスを返し、`insufficient_data` と `insufficient_reason` で  
    「どの情報が不足しているか」をクライアントが把握できるようにしている。

---

## 6. 起動・確認手順（フェーズ4観点）

### 6.1 サーバ起動

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

### 6.2 スコア API の確認

- `stock id=1` のスコアを取得:

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/stocks/1/score/
```

- テクニカルサマリが十分な場合:
  - `buy_score` / `sell_score` に 0〜100 の値が入り、`score_breakdown` に各項目ごとの点数が入る。
  - `insufficient_data` は `false`、`insufficient_reason` は `null`。

- テクニカルサマリが不十分な場合:
  - `buy_score` / `sell_score` は 0 または低めの値。
  - `insufficient_data` は `true` になり、理由が `insufficient_reason` に文字列で入る。

---

## 7. フェーズ4でできること / まだやっていないこと

### 7.1 フェーズ4でできること

- 各監視銘柄 (`WatchStock`) について:
  - フェーズ3のテクニカルサマリをもとに、
    - **買いスコア (`buy_score`)**
    - **売りスコア (`sell_score`)**
    - 各スコアの内訳 (`score_breakdown`)
  - を `/api/v1/stocks/<id>/score/` から取得できる。
- スコア計算のロジックと重みは `signal_scoring.py` に集中しており、  
  後から検証結果や AI に基づいて重みを調整しやすい構造になっている。

### 7.2 まだやっていないこと（今後のフェーズで検討）

- 買い提案 / 売り提案の文章生成
- 提案履歴の保存・結果検証
- AI 連携（スコアの自動チューニングや説明生成など）
- LINE 通知・メール通知
- フォーメーション分析
- RSI / MACD / ボリンジャーバンドなどのテクニカル指標追加
- 外部 API からの株価自動取得
- バッチ処理（定期的なスコア更新など）
- ユーザー単位の管理（パーソナライズされたスコアやウォッチリスト）

---

フェーズ4では、テクニカルサマリをもとにしたシンプルなスコアリングの仕組みと `/api/v1/stocks/<id>/score/` を整備しました。  
今後はこのスコアと内訳を基盤として、提案ロジックや AI 分析、通知機能などを段階的に追加できます。

