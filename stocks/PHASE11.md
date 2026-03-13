# 株価監視アプリ フェーズ11: AI 分析入力パッケージ API

## 1. フェーズ11の目的

- **目的**: ScoreProfile ごとの成績を AI に改善相談しやすいように、
  - summary 情報
  - dataset 行データ
  - 対象 ScoreProfile の設定
  - 実際に適用したフィルタ
をまとめた「AI 分析入力パッケージ」を 1 回の API で取得できるようにする。

- 背景:
  - フェーズ7: `/api/v1/signals/dataset/`（1シグナル=1行の raw データ）
  - フェーズ8: `ScoreProfile` によるスコア設定外部化
  - フェーズ9: `TradingSignal` に `score_profile_*` 情報を保存
  - フェーズ10: `/api/v1/signals/summary/`（ScoreProfile / signal_type 別の集計）
  - → これらを AI に渡すには、毎回手動で複数の API を叩き、フィルタや Profile 情報を組み合わせる必要があった。

本フェーズでは、AI 実行そのものではなく、「AI に渡すための入力 JSON」を提供することがゴール。

---

## 2. 追加した service: `analysis_package.py`

- パス: `stocks/services/analysis_package.py`
- 役割:
  - 対象 `ScoreProfile` を決定（明示指定 or active）
  - summary 用の QuerySet を構築し、`signal_summary` service で集計
  - dataset 用の QuerySet を構築し、`signal_dataset` service で 1行=1シグナルの行を作成
  - これらを AI に渡しやすい JSON 構造にまとめる

### 2.1 limit の扱い

- 定数:
  - `DEFAULT_DATASET_LIMIT = 100`
  - `MAX_DATASET_LIMIT = 500`
- クエリパラメータ `limit` を整数解釈し、
  - 未指定 or 不正値 → `DEFAULT_DATASET_LIMIT`
  - 0 以下 → `DEFAULT_DATASET_LIMIT`
  - `> MAX_DATASET_LIMIT` → `MAX_DATASET_LIMIT` にクリップ

### 2.2 対応フィルタ

analysis package 内で使用するフィルタは以下:

- `ticker`
- `signal_date_from`
- `signal_date_to`
- `signal_type`
- `limit`

※ `score_profile_name` / `score_profile_version` は API 側では指定不要で、  
対象 Profile によって暗黙的に絞り込みを行う。

### 2.3 関数: `build_analysis_package_for_profile(profile, params)`

```python
def build_analysis_package_for_profile(
    profile: ScoreProfile,
    params: Mapping[str, Any],
) -> Dict[str, Any]:
    ...
```

- 入力:
  - `profile`: 対象 `ScoreProfile`
  - `params`: `request.query_params` 相当のマッピング
- 処理概要:
  1. `limit`・`filters` を正規化。
  2. summary 用:
     - `build_summary_queryset` に渡す `params` に
       - `score_profile_name = profile.name`
       - `score_profile_version = profile.version`
       を追加。
     - `summarize_signals` で集計し、`summary` を構築。
  3. dataset 用:
     - `build_signal_queryset(params)` を呼び、ticker/date/signal_type ベースのフィルタを適用。
     - さらに
       - `score_profile_name = profile.name`
       - `score_profile_version = profile.version`
       で絞り込み。
     - 既に `signal_date` / `created_at` 降順で並んでいるため、そのまま `[:limit]` で件数制限。
     - `signals_to_dataset` でフラットな行データを作成し、`dataset_rows` として返す。
  4. `target_profile` / `config` / `filters` / `notes` を含めた dict を返す。

### 2.4 関数: `build_analysis_package_for_active_profile(params)`

```python
def build_analysis_package_for_active_profile(
    params: Mapping[str, Any],
) -> Dict[str, Any]:
    profile = get_active_score_profile()
    return build_analysis_package_for_profile(profile, params)
```

- active な `ScoreProfile` を `get_active_score_profile()` で取得し、
  そのまま `build_analysis_package_for_profile` に渡すヘルパ。

---

## 3. 追加した API: analysis-package

- 実装: `ScoreProfileViewSet`（`stocks/views.py`）
- ルーティング: `stocks/urls.py`（既存の router により `/api/v1/score-profiles/` 配下）

### 3.1 エンドポイント（current profile 向け）

```text
GET /api/v1/score-profiles/current/analysis-package/
```

- 対象: active な `ScoreProfile`
- クエリパラメータ（任意）:
  - `ticker`
  - `signal_date_from`
  - `signal_date_to`
  - `signal_type`
  - `limit`

### 3.2 エンドポイント（id 指定 profile 向け）

```text
GET /api/v1/score-profiles/<id>/analysis-package/
```

- 対象: `id` で指定した `ScoreProfile`
- クエリパラメータは `current` 版と同じ。

### 3.3 View 実装概要

```python
class ScoreProfileViewSet(viewsets.ViewSet):
    ...

    @action(detail=False, methods=["get"], url_path="current/analysis-package")
    def current_analysis_package(self, request):
        package = build_analysis_package_for_active_profile(request.query_params)
        return Response(package, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="analysis-package")
    def analysis_package(self, request, pk=None):
        profile = ScoreProfile.objects.get(pk=pk)
        package = build_analysis_package_for_profile(profile, request.query_params)
        return Response(package, status=status.HTTP_200_OK)
```

---

## 4. analysis-package レスポンス構造

### 4.1 フィールド一覧

- `target_profile`
  - `id`
  - `name`
  - `version`
  - `is_active`
- `config`
  - `weights_json`
  - `thresholds_json`
- `filters`
  - 実際に適用した `ticker` / `signal_date_from` / `signal_date_to` / `signal_type`
  - `limit`（正規化後の値）
- `summary`
  - フェーズ10の summary API と同じ形の集計結果（`score_profile_name` / `version` / `signal_type` ごと）
- `dataset_rows`
  - フェーズ7の dataset API と同じ列構成の行データ
  - 件数は `limit` で制御（デフォルト 100、最大 500）
- `notes`
  - 「AI 分析入力用であり、AI 実行結果は含まない」旨の固定文。

### 4.2 用途例

- そのまま JSON 全体を AI モデル（ChatGPT 等）に渡し、
  - 「ProfileA / v1 の重みは妥当か？」
  - 「どの signal_type / horizon で改善余地があるか？」
  - 「他の重み案を提案してほしい」
  といった指示を行う前提の入力パッケージ。

本フェーズでは **AI 呼び出し自体は行わない** ことに注意。

---

## 5. summary / dataset API との違い

- `/api/v1/signals/dataset/`:
  - **raw データ専用**。
  - 1シグナル=1行で、フィルタも ScoreProfile 無関係に使える汎用 API。

- `/api/v1/signals/summary/`:
  - **集計専用**。
  - ScoreProfile / signal_type 単位の summary のみ。

- `/api/v1/score-profiles/.../analysis-package/`（本フェーズ）:
  - **「AI入力用の1パッケージ」にまとめた API**。
  - summary + dataset_rows + profile config + filters + notes を一括で返す。
  - 1つの ScoreProfile にフォーカスして分析したいときに便利。

---

## 6. テスト

- パス: `stocks/tests.py`
- 追加クラス: `AnalysisPackageTests`

### 6.1 target_profile が返ること

`test_build_analysis_package_for_profile_basic_structure`

- `ScoreProfile` を1件作成し、対象 Profile として `build_analysis_package_for_profile` を呼ぶ。
- 検証:
  - `package["target_profile"]["id"] == profile.id`
  - `name` / `version` / `is_active` が正しく含まれる。
  - `config.weights_json` / `config.thresholds_json` が Profile と一致。

### 6.2 summary / dataset_rows が同じフィルタ条件で生成されること

同テスト内で:

- `ticker="ANL"` でフィルタし、別 ticker のシグナルが `dataset_rows` に入らないことを確認。
- `summary` についても、対象 Profile / ticker のシグナルだけを対象に集計されていることを（少なくとも profile name/version で）確認。

### 6.3 limit が効くこと

`test_limit_is_applied`

- `limit=1` で `build_analysis_package_for_profile` を呼び、
  - `len(package["dataset_rows"]) == 1` であることを確認。

### 6.4 active profile 向け helper が動作すること

`test_active_profile_helper_uses_active_profile`

- active な `ScoreProfile` を1件作成し、
  - `build_analysis_package_for_active_profile(params)` を呼ぶ。
- 検証:
  - `package["target_profile"]["id"] == active_profile.id`

---

## 7. 動作確認手順

### 7.1 current profile 向け analysis-package

1. active な `ScoreProfile` が1件存在することを確認:

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/score-profiles/current/ | ConvertFrom-Json
```

2. current profile 向け analysis-package を取得:

```powershell
curl.exe -s "http://127.0.0.1:8000/api/v1/score-profiles/current/analysis-package/?ticker=ANL&signal_date_from=2026-03-01&signal_date_to=2026-03-31&signal_type=buy&limit=50" `
  | ConvertFrom-Json
```

### 7.2 特定 id profile 向け analysis-package

```powershell
$p = curl.exe -s http://127.0.0.1:8000/api/v1/score-profiles/current/ | ConvertFrom-Json
$id = $p.id
curl.exe -s "http://127.0.0.1:8000/api/v1/score-profiles/$id/analysis-package/?ticker=ANL&limit=20" `
  | ConvertFrom-Json
```

### 7.3 テスト

```powershell
python manage.py test stocks
```

---

## 8. 注意点

- 本フェーズでは **AI 呼び出し自体は行わない**。  
  analysis-package はあくまで「AI に渡すための入力 JSON」を提供するだけ。
- limit のデフォルト/上限はコード側で固定（100/500）しているため、
  非常に大きなデータセットを1回で取得したい場合は、別途 dataset API を直接利用すること。
- analysis-package は 1 ScoreProfile にフォーカスした構造になっているため、
  複数 Profile を並列比較したい場合は、Profile ごとに API を複数回呼び出す想定。

