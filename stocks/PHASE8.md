# 株価監視アプリ フェーズ8: スコア設定の外部化（ScoreProfile）

## 1. フェーズ8の目的

- **目的**: 買いスコア / 売りスコアの「重み・閾値・判定ルール」をコード直書きではなく、DB 上の **ScoreProfile** として管理できるようにする。
- **狙い**:
  - 将来の AI 改善フェーズで、「コードを書き換えずに」重みや閾値を調整できる土台を作る。
  - 既存のスコア API / シグナル生成の挙動を、初期状態では **完全に互換** に保つ。

---

## 2. 追加したモデル: `ScoreProfile`

- パス: `stocks/models.py`
- モデル名: `ScoreProfile`
- 役割: 買い/売りスコアの重みおよびバイアス・強度の閾値を JSON で保持するプロファイル。

### 2.1 フィールド定義

- `name`: `CharField(max_length=100)`
- `version`: `CharField(max_length=32)`
  - 例: `"v1"`, `"2026-03-13-01"` など。
- `is_active`: `BooleanField(default=False)`
  - 現在のスコア計算に利用するプロファイルかどうか。
- `description`: `TextField(blank=True)`
  - 用途・メモ（任意）。
- `weights_json`: `JSONField`
  - 買い/売りの重み定義。
  - 形式例は後述。
- `thresholds_json`: `JSONField`
  - バイアス（buy/sell/neutral）と強度（weak/normal/strong）の閾値定義。
- `created_at`: `DateTimeField(auto_now_add=True)`
- `updated_at`: `DateTimeField(auto_now=True)`

### 2.2 モデル Meta

- `ordering = ["-is_active", "-updated_at"]`
- `verbose_name = "スコア設定プロファイル"`
- `verbose_name_plural = "スコア設定プロファイル"`

---

## 3. スコア設定 service: `scoring_profile.py`

- パス: `stocks/services/scoring_profile.py`
- 役割:
  - 現在アクティブな `ScoreProfile` を安全に取得する。
  - スコア計算で使いやすい形 (`ScoringConfig`) に整形して渡す。

### 3.1 関数: `get_active_score_profile()`

- 戻り値: `ScoreProfile`
- 挙動:
  - `is_active=True` の `ScoreProfile` を **1件だけ** 取得。
  - 0件の場合:
    - `django.core.exceptions.ImproperlyConfigured` を送出。
  - 複数件の場合:
    - 同じく `ImproperlyConfigured` を送出。
- 方針:
  - 「壊れた設定状態」を黙ってフォールバックせず、**早めに気づけるようにする**。

### 3.2 関数: `get_active_scoring_config()`

- 戻り値: `ScoringConfig` dataclass

```python
@dataclass
class ScoringConfig:
    buy_weights: Dict[str, float]
    sell_weights: Dict[str, float]
    bias_thresholds: Dict[str, Any]
    strength_thresholds: Dict[str, Any]
```

- `get_active_score_profile()` で取得した `ScoreProfile` から:
  - `weights_json["buy"]` → `buy_weights`
  - `weights_json["sell"]` → `sell_weights`
  - `thresholds_json["bias"]` → `bias_thresholds`
  - `thresholds_json["strength"]` → `strength_thresholds`
- 未設定時のデフォルト:
  - `bias.neutral_abs_diff_lt = 10.0`
  - `strength.weak_abs_diff_lt = 15.0`
  - `strength.normal_abs_diff_lt = 30.0`

---

## 4. スコア計算ロジックの変更: `signal_scoring.py`

- パス: `stocks/services/signal_scoring.py`
- 役割: フェーズ4から継続して、テクニカルサマリから買い/売りスコアを計算する。
- 変更点:
  - 旧実装では `BUY_WEIGHTS` / `SELL_WEIGHTS` / 閾値を **ハードコード** していた。
  - 新実装では、**全て ScoreProfile 経由**で取得する。

### 4.1 主な変更点

- 追加インポート:

```python
from .scoring_profile import get_active_scoring_config
```

- 関数 `score_from_technical(summary: TechnicalSummary) -> ScoreResult` の先頭で:

```python
config = get_active_scoring_config()
buy_weights = config.buy_weights
sell_weights = config.sell_weights
bias_thresholds = config.bias_thresholds
strength_thresholds = config.strength_thresholds
```

- 各加点ロジックは `BUY_WEIGHTS[...]` / `SELL_WEIGHTS[...]` ではなく、

```python
breakdown_buy["trend_long_up"] = buy_weights.get("trend_long_up", 0.0)
breakdown_sell["trend_long_down"] = sell_weights.get("trend_long_down", 0.0)
# など
```

と、**Profile 側の重み**を参照する形に変更。

- バイアス判定:

```python
neutral_abs_diff_lt = float(bias_thresholds.get("neutral_abs_diff_lt", 10.0))
if abs_diff < neutral_abs_diff_lt:
    bias = "neutral"
elif diff >= neutral_abs_diff_lt:
    bias = "buy"
else:
    bias = "sell"
```

- 強度判定:

```python
weak_abs_diff_lt = float(strength_thresholds.get("weak_abs_diff_lt", 15.0))
normal_abs_diff_lt = float(strength_thresholds.get("normal_abs_diff_lt", 30.0))

if abs_diff < weak_abs_diff_lt:
    strength = "weak"
elif abs_diff < normal_abs_diff_lt:
    strength = "normal"
else:
    strength = "strong"
```

### 4.2 既存スコアとの互換性

- 初期 `ScoreProfile` の `weights_json` / `thresholds_json` を **旧ハードコード値と完全一致** させているため、
  - 同じ `TechnicalSummary` 入力に対して、
    - `buy_score`
    - `sell_score`
    - `score_bias`
    - `score_strength`
    - `score_breakdown`（buy / sell）
  - は **完全に同じ結果** になる。
- テスト `ScoreCalculationCompatibilityTests` で、代表ケースについて旧ロジックをテスト内で再現し、新ロジックとの一致を確認済み。

---

## 5. 初期 ScoreProfile（データマイグレーション）

- ファイル: `stocks/migrations/0006_scoreprofile.py`
- 内容:
  - `ScoreProfile` モデル作成。
  - `RunPython(create_initial_score_profile)` による初期データ投入。

### 5.1 初期 `weights_json`

```json
{
  "buy": {
    "trend_long_up": 20.0,
    "trend_mid_up": 15.0,
    "trend_short_up": 10.0,
    "volume_high": 10.0,
    "above_ma25": 10.0,
    "above_ma75": 10.0,
    "near_high_20": 10.0,
    "near_low_20": 10.0
  },
  "sell": {
    "trend_long_down": 20.0,
    "trend_mid_down": 15.0,
    "trend_short_down": 10.0,
    "volume_low": 10.0,
    "below_ma25": 10.0,
    "below_ma75": 10.0,
    "near_low_20": 10.0,
    "near_high_20": 10.0
  }
}
```

### 5.2 初期 `thresholds_json`

```json
{
  "bias": {
    "neutral_abs_diff_lt": 10.0
  },
  "strength": {
    "weak_abs_diff_lt": 15.0,
    "normal_abs_diff_lt": 30.0
  }
}
```

### 5.3 初期レコード

- `name`: `"Default scoring profile"`
- `version`: `"v1"`
- `is_active`: `True`
- `description`: `"Initial profile migrated from hardcoded signal_scoring.py (Phase 4)."`

これにより、フェーズ8適用直後もスコア結果はフェーズ4〜7と互換になります。

---

## 6. API: 現在のスコア設定プロファイル取得

- 実装: `ScoreProfileViewSet`（`stocks/views.py`）
- ルーティング: `stocks/urls.py`
- エンドポイント:

```text
GET /api/v1/score-profiles/current/
```

### 6.1 レスポンス項目

```json
{
  "id": 1,
  "name": "Default scoring profile",
  "version": "v1",
  "is_active": true,
  "description": "Initial profile migrated from hardcoded signal_scoring.py (Phase 4).",
  "weights_json": { ... 上記と同じ ... },
  "thresholds_json": { ... 上記と同じ ... },
  "created_at": "2026-03-13T12:34:56+09:00",
  "updated_at": "2026-03-13T12:34:56+09:00"
}
```

- 現時点では **read-only**。CRUD 画面や編集 API は未実装。

---

## 7. テスト追加

- パス: `stocks/tests.py`

### 7.1 ScoreProfile 関連テスト

- `ScoreProfileServiceTests`
  - `get_active_score_profile` が:
    - active 0件 → `ImproperlyConfigured` を送出
    - active 複数件 → `ImproperlyConfigured` を送出
    - active 1件 → そのプロファイルを返す

### 7.2 旧ロジック互換テスト

- `ScoreCalculationCompatibilityTests`
  - セットアップで migration と同じ内容の `ScoreProfile` を1件 `is_active=True` で作成。
  - テスト内で旧 `signal_scoring.py` のロジックを再現する `_old_logic_score` を実装。
  - 代表的な1ケースの `TechnicalSummary` を組み立て、
    - 旧ロジック (`_old_logic_score`) の結果
    - 新ロジック (`score_from_technical`)
    を比較し、以下の一致を確認:
    - `buy_score`
    - `sell_score`
    - `bias`
    - `strength`
    - `breakdown_buy`
    - `breakdown_sell`

---

## 8. 動作確認手順（フェーズ8観点）

### 8.1 マイグレーション

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py makemigrations stocks   # 変更がある場合
python manage.py migrate
```

### 8.2 スコアプロファイル API の確認

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/score-profiles/current/ | ConvertFrom-Json
```

- 初期状態では、`Default scoring profile` が 1件返る。

### 8.3 スコア API の互換確認（スポットチェック）

1. 任意の銘柄に対して十分な日足データを登録。
2. フェーズ4以前の状態で `/api/v1/stocks/<id>/score/` を叩いた結果をメモ。
3. フェーズ8適用後に同じ銘柄・同じデータで `/api/v1/stocks/<id>/score/` を再度叩き、
   - `buy_score` / `sell_score`
   - `score_bias` / `score_strength`
   - `score_breakdown`
   が一致することを確認。

### 8.4 テスト実行

```powershell
python manage.py test stocks
```

---

## 9. フェーズ8でやっていないこと

- AI によるスコア設定の自動最適化
- AI 提案の自動採用
- 新テクニカル指標の追加
- スコアプロファイルの CRUD API / 管理画面での編集
- ダッシュボード表示
- 通知 / 外部 API 連携 / バッチ処理

---

## 10. フェーズ8完了条件

- `ScoreProfile` モデルが migration で作成されている。
- 初期プロファイル（フェーズ4互換）が 1件 `is_active=True` で投入される。
- `signal_scoring.py` が **アクティブな ScoreProfile 経由**で動作する。
- 代表ケースにおいて、旧ロジックと新ロジックのスコア結果が完全一致するテストが通る。
- `GET /api/v1/score-profiles/current/` で現在有効な設定が確認できる。
- README / `stocks/PHASE8.md` に本仕様が反映されている。

