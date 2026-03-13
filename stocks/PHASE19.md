# 株価監視アプリ フェーズ19: 運用補助 API（review-targets / compare）

## 1. フェーズ19の目的

コア機能完成後の運用を助けるため、
「次に何を見直すべきか」「どの profile が良いか」を判断しやすい
**運用補助 API** を追加する。

このフェーズでは:

- **レビュー対象の抽出 API**（review-targets）
- **active profile と候補 profile の比較用サマリ API**（compare）

を追加する。

以下は **今回やらない**:

- 通知
- バッチ
- ダッシュボード画面
- 自動切替
- AI に自動で再レビューさせない

---

## 2. service

### 2.1 profile_review_targets.py

- パス: `stocks/services/profile_review_targets.py`
- 役割: 次にレビュー候補として見るべき profile / proposal を抽出する。

返却観点:

- **現在 active な profile**（いなければ null）
- **stale_active_profiles**: 長く active のままで見直しされていない profile
- **underperforming_profiles**: 直近期間で成績が弱い profile（h20 success_rate が閾値未満）
- **accepted_not_activated_profiles**: accepted 済みだがまだ active にしていない proposal 由来 profile

### 2.2 profile_comparison.py

- パス: `stocks/services/profile_comparison.py`
- 役割: base と candidate の2 profile の比較用サマリを返す。既存の summary / dataset 用 service を再利用。

---

## 3. API 仕様

### 3.1 レビュー対象一覧: `GET /api/v1/score-profiles/review-targets/`

**クエリパラメータ（任意）:**

- `signal_date_from`: シグナル日付の開始（summary の絞り込み）
- `signal_date_to`: シグナル日付の終了
- `threshold_success_rate`: underperforming 判定の閾値（h20.success_rate がこの値未満なら underperforming）。デフォルト 0.5
- `min_evaluated_count`: underperforming 判定に必要な h20 の最低 evaluated_count。この件数未満の signal_type はノイズとして underperforming に含めない。デフォルト 5
- `stale_days`: この日数以上 active のままなら stale。デフォルト 30

**返却内容:**

- `current_active_profile`: 現在 active な profile の簡易情報（id, name, version, is_active）。いなければ null
- `stale_active_profiles`: stale と判定された profile のリスト
- `underperforming_profiles`: underperforming と判定された profile のリスト
- `accepted_not_activated_profiles`: accepted だが未 active の proposal 由来 profile のリスト（source_proposal_id / source_proposal_name 含む）

### 3.2 profile 比較: `GET /api/v1/score-profiles/compare/`

**クエリパラメータ（必須）:**

- `base_profile_id`: 比較基準側の profile id
- `candidate_profile_id`: 比較候補側の profile id

**クエリパラメータ（任意）:**

- `signal_date_from`, `signal_date_to`: シグナル日付範囲

**返却内容:**

- `base_profile`: id, name, version, is_active, source_proposal_id, source_proposal_name
- `candidate_profile`: 同上
- `comparison`: signal_type ごとのリスト。各要素は `signal_type`, `base`, `candidate`。  
  `base` / `candidate` はそれぞれ total_signals と h5 / h10 / h20（evaluated_count, success_count, success_rate, avg_return）を持つ。

**同一 profile 指定:** base と candidate に同じ id を指定しても **200 OK** で同じ構造を返す（冪等）。

**異常時:**

- `base_profile_id` または `candidate_profile_id` 未指定 → 400
- 存在しない profile id → 404

---

## 4. 判定ルール（最小構成）

### 4.1 underperforming

- 指定期間の summary で、その profile の **いずれかの signal_type** について  
  **h20.evaluated_count >= min_evaluated_count** かつ  
  **h20.success_rate < threshold_success_rate** の場合のみ underperforming とする。
- データが無い（evaluated_count=0）、または evaluated_count が min_evaluated_count 未満の場合は underperforming に含めない（評価件数が少なすぎるケースをノイズとして除外する）。

### 4.2 stale

- その profile が **activated_profile** になっている直近の activation history の **activated_at** から、  
  **stale_days 日以上経過** していれば stale。
- 現在 active は1件のみのため、stale_active_profiles には最大1件しか入らない。

---

## 5. 今回やらないこと

- 通知
- バッチ
- 画面ダッシュボード
- 自動切替
- AI による自動再レビュー
- proposal の自動承認

---

## 6. テスト（stocks/tests.py）

### 6.1 ScoreProfileReviewTargetsAPITests

- `test_review_targets_returns_current_active_profile`: current_active_profile に現在 active が返る
- `test_review_targets_accepted_not_activated_profiles`: accepted 済みだが active でない proposal 由来 profile がリストに出る
- `test_review_targets_underperforming_profiles`: h20 success_rate が閾値未満の profile が underperforming_profiles に出る
- `test_review_targets_stale_active_profiles`: 直近 activated_at が stale_days より前の active が stale_active_profiles に出る

### 6.2 ScoreProfileCompareAPITests

- `test_compare_returns_base_and_candidate_summary`: base / candidate と comparison（signal_type ごと）が返る
- `test_compare_same_profile_returns_200`: 同じ profile を base と candidate に指定しても 200
- `test_compare_missing_base_profile_returns_404`: 存在しない base_profile_id で 404
- `test_compare_missing_candidate_profile_returns_404`: 存在しない candidate_profile_id で 404
- `test_compare_missing_params_returns_400`: 必須パラメータ欠落で 400

---

## 7. PowerShell 動作確認例

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py test stocks
```

```powershell
# レビュー対象の取得
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/review-targets/" `
  -Method Get

# パラメータ付き（min_evaluated_count で最低評価件数を指定）
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/review-targets/?stale_days=30&threshold_success_rate=0.5&min_evaluated_count=5" `
  -Method Get

# profile 比較（base=1, candidate=2）
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/compare/?base_profile_id=1&candidate_profile_id=2" `
  -Method Get
```

---

## 8. 実装方針

- 既存の `build_summary_queryset` / `summarize_signals` を再利用し、View は薄く保つ。
- 判定ルールは service 内に分離し、将来の閾値変更や通知・定期抽出に拡張しやすい形にする。
