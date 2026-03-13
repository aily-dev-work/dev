# 株価監視アプリ フェーズ9: TradingSignal と ScoreProfile のひも付け

## 1. フェーズ9の目的

- **目的**: 各 `TradingSignal` が「どの `ScoreProfile` を使って生成されたか」を後から追跡できるようにする。
- **狙い**:
  - プロファイル変更前後の成績比較やバックテスト比較をしやすくする。
  - 将来の AI 改善フェーズで、「どの重み設定で出したシグナルか」を明示的に扱えるようにする。

フェーズ8でスコア計算は `ScoreProfile` ベースになったが、シグナル側にその情報が保存されていなかったため、
過去のシグナルがどの設定で生成されたかを判別しづらい状態だった。

---

## 2. TradingSignal への ScoreProfile 情報の保存

### 2.1 モデル変更: `TradingSignal`

- パス: `stocks/models.py`

`TradingSignal` に以下の3カラムを追加。

- `score_profile`: `ForeignKey("ScoreProfile", null=True, blank=True, on_delete=SET_NULL, related_name="signals")`
  - このシグナル生成時に使用した `ScoreProfile` への参照。
  - 後から `ScoreProfile` が削除された場合は `NULL` になる（SET_NULL）。
- `score_profile_name`: `CharField(max_length=100, blank=True, default="")`
  - 生成時点の `ScoreProfile.name` のスナップショット。
- `score_profile_version`: `CharField(max_length=32, blank=True, default="")`
  - 生成時点の `ScoreProfile.version` のスナップショット。

### 2.2 設計意図

- **FK + name/version スナップショット**の二段構え:
  - `score_profile` FK で「どのプロファイルか」を直接参照できる。
  - `ScoreProfile` が後から変更/削除されても、
    - `score_profile_name`
    - `score_profile_version`
    はシグナル側に残るため、生成時点の設定名/バージョンを最低限追える。

既存の `TradingSignal` レコードにはこの3カラムは **NULL / 空文字** のまま残し、
データマイグレーションで無理に埋めない方針とした（フェーズ9以降に生成された分から追跡可能にする）。

---

## 3. signal 生成処理の修正: `generate_trading_signal`

- パス: `stocks/services/signal_generation.py`

### 3.1 修正点

シグナル生成時にアクティブな `ScoreProfile` を取得し、`TradingSignal` に保存する。

- 追加インポート:

```python
from .scoring_profile import get_active_score_profile
```

- `generate_trading_signal` 内:

```python
profile = get_active_score_profile()

defaults = {
    ...
    "score_profile": profile,
    "score_profile_name": profile.name,
    "score_profile_version": profile.version,
}
signal, _created = TradingSignal.objects.update_or_create(
    stock=stock,
    signal_date=signal_date,
    defaults=defaults,
)
```

`get_active_score_profile()` はフェーズ8で導入した通り、
`is_active=True` の `ScoreProfile` が 1件のみ存在することを前提にし、

- 0件
- 複数件

の場合は `ImproperlyConfigured` を送出する。

これにより、「壊れた設定状態」でシグナルが生成されるのを防ぐ。

---

## 4. dataset / シグナル履歴 API への ScoreProfile 情報の追加

### 4.1 dataset API: `/api/v1/signals/dataset/`

- service: `stocks/services/signal_dataset.py`
- View: `SignalViewSet.dataset`

1行=1シグナルのフラットデータに、以下3項目を追加:

- `score_profile_id`: `TradingSignal.score_profile_id`
- `score_profile_name`: `TradingSignal.score_profile_name`
- `score_profile_version`: `TradingSignal.score_profile_version`

これにより、

- 「どのプロファイルのシグナルか」でフィルタ/グルーピング
- プロファイル変更前後の成績比較

などがしやすくなる。

`score_profile` が `NULL` の既存シグナルについては、これらの値は `null` / 空文字として返される。

### 4.2 シグナル履歴 API: `/api/v1/stocks/<id>/signals/`

- 実装: `WatchStockViewSet.signals`（`stocks/views.py`）

レスポンスの各要素に以下を追加:

- `stock_id`
- `score_profile_id`
- `score_profile_name`
- `score_profile_version`

簡易な履歴確認の時点で、「どのプロファイル由来のシグナルか」を目視できるようになる。

---

## 5. マイグレーション

- ファイル: `stocks/migrations/0008_tradingsignal_scoreprofile.py`

内容:

- `TradingSignal` に以下3カラムを追加:
  - `score_profile` (FK, `SET_NULL`)
  - `score_profile_name` (CharField, blank / default="")
  - `score_profile_version` (CharField, blank / default="")
- 既存データに対して特別なデータマイグレーションは行わない。

---

## 6. テスト

- パス: `stocks/tests.py`
- 追加クラス: `TradingSignalScoreProfileTests`

### 6.1 テスト1: signal 生成時に profile 情報が保存される

`test_generate_trading_signal_saves_score_profile_info`

- 手順:
  - active な `ScoreProfile` を1件作成。
  - ダミーの `TechnicalSummary` を作成。
  - `score_from_technical` → `generate_trading_signal` を実行。
- 検証:
  - `signal.score_profile_id == profile.id`
  - `signal.score_profile_name == profile.name`
  - `signal.score_profile_version == profile.version`

### 6.2 テスト2: dataset に profile 情報が含まれる

`test_dataset_contains_score_profile_fields`

- 手順:
  - active な `ScoreProfile` を1件作成。
  - `generate_trading_signal` でシグナル生成。
  - `build_signal_queryset({})` → `signals_to_dataset` で dataset 取得。
- 検証:
  - 対応行の
    - `score_profile_id`
    - `score_profile_name`
    - `score_profile_version`
    が `ScoreProfile` と一致。

### 6.3 テスト3: ScoreProfile が削除されてもスナップショットは残る

`test_score_profile_set_null_keeps_snapshot_fields`

- 手順:
  - active `ScoreProfile` でシグナル生成。
  - `ScoreProfile` を `delete()`（FK は `SET_NULL`）。
  - シグナルを `refresh_from_db()`。
- 検証:
  - `signal.score_profile is None`
  - しかし
    - `score_profile_name`
    - `score_profile_version`
    は生成時の値（例: `"Phase9 profile"`, `"v1"`）のまま残っている。

---

## 7. README の更新ポイント

- プロジェクト構成の `stocks/` 説明にフェーズ9を追記:
  - `stocks/` … 株価監視アプリ（フェーズ1〜9）
  - `TradingSignal` の説明に `ScoreProfile` 由来のフィールドが追加されたことを明記。
- `ScoreProfile` の説明に、
  - `TradingSignal` 側に `score_profile` / `score_profile_name` / `score_profile_version` が保存されるため、
    dataset API からプロファイル別の分析が可能になったことを追記。

（実際の README.md 側で反映済み）

---

## 8. 動作確認手順（フェーズ9観点）

### 8.1 マイグレーション

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py migrate
```

### 8.2 シグナル生成と profile 反映確認

1. active な `ScoreProfile` が1件存在することを確認:

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/score-profiles/current/ | ConvertFrom-Json
```

2. 任意の銘柄に対して `generate-signal` を実行:

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/stocks/1/generate-signal/
```

3. シグナル履歴 API で確認:

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/stocks/1/signals/ | ConvertFrom-Json
```

- 各要素に
  - `score_profile_id`
  - `score_profile_name`
  - `score_profile_version`
  が含まれていること。

4. dataset API で確認:

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/signals/dataset/ | ConvertFrom-Json | Select-Object -First 1
```

- 返却行に
  - `score_profile_id`
  - `score_profile_name`
  - `score_profile_version`
  が含まれていること。

### 8.3 テスト

```powershell
python manage.py test stocks
```

---

## 9. 今回やっていないこと

- AI による `ScoreProfile` の自動生成/自動最適化
- `ScoreProfile` の CRUD API や自動有効化
- Profile ごとの成績集計 API
- ダッシュボード
- 通知 / 外部 API 連携 / バッチ処理

---

## 10. フェーズ9完了条件

- `TradingSignal` に `score_profile` / `score_profile_name` / `score_profile_version` が追加されている。
- active な `ScoreProfile` を使ってシグナル生成すると、上記3つが `TradingSignal` に保存される。
- `/api/v1/stocks/<id>/signals/` と `/api/v1/signals/dataset/` から profile 情報を取得できる。
- `ScoreProfile` が削除されても、`score_profile_name` / `score_profile_version` のスナップショットは残る。
- すべてのテスト（特に `TradingSignalScoreProfileTests`）が成功する。

