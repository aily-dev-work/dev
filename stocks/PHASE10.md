# 株価監視アプリ フェーズ10: ScoreProfile 別シグナル集計 API

## 1. フェーズ10の目的

- **目的**: `TradingSignal` + `SignalOutcome` + `ScoreProfile` 情報を用いて、
  - 「どの ScoreProfile がどれくらい良かったか」
  を比較しやすい summary API を追加する。

- 背景:
  - フェーズ7: 1シグナル=1行の dataset API（`/api/v1/signals/dataset/`）を実装。
  - フェーズ8: `ScoreProfile` によるスコア設定の外部化。
  - フェーズ9: `TradingSignal` に `score_profile` / `score_profile_name` / `score_profile_version` を保存。
  - → raw データ比較は可能になったが、profile 別・期間別の成功率や平均リターンを直接比較するには不便だった。

本フェーズでは、既存 dataset API の上に「サマリ集計レイヤ」を追加するイメージで、
人間が手元で ScoreProfile を比較しやすい集計 API を追加する。

---

## 2. 追加した service: `signal_summary.py`

- パス: `stocks/services/signal_summary.py`
- 役割:
  - `TradingSignal` + `SignalOutcome` をフィルタリングしたうえで、
    - `score_profile_name`
    - `score_profile_version`
    - `signal_type`
    単位で集計サマリを返す。

### 2.1 QuerySet 構築: `build_summary_queryset(params)`

```python
def build_summary_queryset(params) -> Iterable[TradingSignal]:
    """
    TradingSignal + SignalOutcome を対象に、summary 用の QuerySet を構築する。
    対応フィルタ:
    - ticker
    - signal_date_from
    - signal_date_to
    - score_profile_name
    - score_profile_version
    - signal_type
    """
```

- ベース: `TradingSignal.objects.select_related("stock", "outcome").all()`
- フィルタ:
  - `ticker`: `stock__ticker`
  - `signal_date_from`: `signal_date__gte`
  - `signal_date_to`: `signal_date__lte`
  - `score_profile_name`: `score_profile_name`
  - `score_profile_version`: `score_profile_version`
  - `signal_type`: `signal_type`

### 2.2 集計本体: `summarize_signals(signals)`

```python
def summarize_signals(signals: Iterable[TradingSignal]) -> List[Dict[str, Any]]:
    """
    TradingSignal 群を profile_name / profile_version / signal_type ごとに集計し、
    summary のリストとして返す。
    """
```

- グルーピングキー:
  - `(score_profile_name, score_profile_version, signal_type)`
  - `score_profile_name` / `score_profile_version` が空文字列の場合もそのままグループ化。
- 各グループごとに:
  - `total_signals`: シグナル総数（Outcome の有無に関わらず）
  - 5営業日 (`h5`), 10営業日 (`h10`), 20営業日 (`h20`) について、以下を計算:
    - `evaluated_count`: `return_*d` が非 `None` の件数
    - `success_count`: `success_*d` が `True` の件数
    - `success_rate`: `success_count / evaluated_count`（`evaluated_count=0` の場合は `null`）
    - `avg_return`: `return_*d` の平均（`evaluated_count=0` の場合は `null`）

- `SignalOutcome` が存在しない（未評価シグナル）場合:
  - `evaluated_count` に含めない（= `return_*d` が `None` 扱い）。

- 並び順:
  - `score_profile_name`, `score_profile_version`, `signal_type` の昇順でソート。

### 2.3 レスポンスの形

`summarize_signals` の戻り値は以下のような辞書のリスト:

```json
[
  {
    "score_profile_name": "ProfileA",
    "score_profile_version": "v1",
    "signal_type": "buy",
    "total_signals": 10,
    "h5": {
      "evaluated_count": 8,
      "success_count": 5,
      "success_rate": 0.625,
      "avg_return": 0.034
    },
    "h10": {
      "evaluated_count": 7,
      "success_count": 4,
      "success_rate": 0.5714,
      "avg_return": 0.028
    },
    "h20": {
      "evaluated_count": 5,
      "success_count": 3,
      "success_rate": 0.6,
      "avg_return": 0.05
    }
  },
  ...
]
```

---

## 3. 追加した API: `/api/v1/signals/summary/`

- 実装: `SignalViewSet.summary`（`stocks/views.py`）
- URL: `GET /api/v1/signals/summary/`
- フィルタ:
  - `ticker`
  - `signal_date_from`
  - `signal_date_to`
  - `score_profile_name`
  - `score_profile_version`
  - `signal_type`

### 3.1 実装概要

```python
@action(detail=False, methods=["get"], url_path="summary")
def summary(self, request):
    """
    TradingSignal + SignalOutcome を ScoreProfile 単位・signal_type 単位で集計したサマリを返す。
    フィルタ:
    - ticker
    - signal_date_from
    - signal_date_to
    - score_profile_name
    - score_profile_version
    - signal_type
    """
    qs = build_summary_queryset(request.query_params)
    rows = summarize_signals(qs)
    return Response(rows, status=status.HTTP_200_OK)
```

dataset API (`/api/v1/signals/dataset/`) と同様に `SignalViewSet` 配下に追加しつつ、
ロジックはすべて `signal_summary.py` に寄せている。

---

## 4. dataset API との違い

- `/api/v1/signals/dataset/`:
  - 1シグナル=1行。
  - `TradingSignal` + `SignalOutcome` の **生データ**（基礎テーブル）。
  - 詳細分析や AI 入力用。

- `/api/v1/signals/summary/`（本フェーズで追加）:
  - 1行=1 `(ScoreProfile.name, ScoreProfile.version, signal_type)` グループ。
  - 成功率・平均リターンなどの **集計サマリ**。
  - 人間が profile ごとの成績をざっくり比較する用途に向く。

どちらも既存のモデル/カラムを使っており、新たなモデル追加は行っていない。

---

## 5. テスト

- パス: `stocks/tests.py`
- 追加クラス: `SignalSummaryTests`

### 5.1 プロファイル・signal_type ごとのグルーピング

`test_summary_groups_by_profile_and_signal_type`

- 2つの `ScoreProfile`（ProfileA, ProfileB）と、
  - ProfileA, `signal_type="buy"` のシグナル3件
  - ProfileB, `signal_type="sell"` のシグナル1件
  を用意。
- 検証:
  - ProfileA / buy のグループで `total_signals == 3`
  - ProfileB / sell のグループで `total_signals == 1`

### 5.2 success_rate と avg_return の検証

`test_success_rate_and_avg_return_are_computed_correctly`

- ProfileA / buy のシグナル3件について、
  - 5d:
    - sig1: `return_5d=+0.10`, `success_5d=True`
    - sig2: `return_5d=0.00`, `success_5d=False`
    - sig3: 未評価
  - 10d:
    - sig1: `return_10d=-0.05`, `success_10d=False`
    - sig2/sig3: 未評価
  - 20d:
    - sig2: `return_20d=+0.20`, `success_20d=True`
    - sig1/sig3: 未評価
- 検証:
  - 5d:
    - `evaluated_count = 2`
    - `success_count = 1`
    - `success_rate = 0.5`
    - `avg_return = (0.10 + 0.00) / 2`
  - 10d:
    - `evaluated_count = 1`
    - `success_count = 0`
    - `success_rate = 0.0`
    - `avg_return = -0.05`
  - 20d:
    - `evaluated_count = 1`
    - `success_count = 1`
    - `success_rate = 1.0`
    - `avg_return = 0.20`

### 5.3 未評価データが evaluated_count に含まれないこと

`test_un_evaluated_signals_are_not_counted_as_evaluated`

- ProfileB / sell のシグナル1件だけを用意し、5d のみ評価済み、10d/20d は未評価。
- 検証:
  - `h5.evaluated_count == 1`, `success_rate == 1.0`
  - `h10.evaluated_count == 0`, `success_rate == None`, `avg_return == None`
  - `h20.evaluated_count == 0`, 同上

### 5.4 フィルタが効くこと

`test_filters_work`

- `score_profile_name=ProfileA` で絞り込み → すべての行の `score_profile_name` が ProfileA。
- `signal_type=sell` で絞り込み → すべての行の `signal_type` が sell。

---

## 6. 動作確認手順

### 6.1 マイグレーション

フェーズ10では新しいモデルやフィールドは追加していないため、
既にフェーズ9まで適用済みなら追加の migration は不要。

念のため:

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py migrate
```

### 6.2 summary API の確認

1. いくつかの銘柄・ScoreProfile でシグナルと Outcome を作成した後、

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/signals/summary/ | ConvertFrom-Json
```

2. フィルタ付きの確認:

```powershell
# ProfileA の buy シグナルだけを対象にする例
curl.exe -s "http://127.0.0.1:8000/api/v1/signals/summary/?score_profile_name=ProfileA&signal_type=buy" | ConvertFrom-Json
```

- レスポンスの `total_signals` / `h5` / `h10` / `h20` の値が、手計算と一致することを確認。

### 6.3 テスト

```powershell
python manage.py test stocks
```

- `SignalSummaryTests` を含む全テストが OK になること。

---

## 7. まだやらないこと

- AI による ScoreProfile の自動最適化
- ScoreProfile の自動切替
- Profile ごとの成績を可視化するダッシュボード
- 通知機能
- 外部API連携
- バッチ処理（定期集計など）

---

## 8. フェーズ10完了条件

- `stocks/services/signal_summary.py` が実装されている。
- `GET /api/v1/signals/summary/` で、ScoreProfile / signal_type 単位のサマリが取得できる。
- フィルタ (`ticker`, `signal_date_from`, `signal_date_to`, `score_profile_name`, `score_profile_version`, `signal_type`) が効く。
- success_rate / avg_return が正しく計算されている。
- 未評価シグナルが evaluated_count に含まれていない。
- すべてのテスト（特に `SignalSummaryTests`）が成功している。

