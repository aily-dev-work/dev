# 株価監視アプリ フェーズ13: ScoreProfileProposal による AI 提案の保存

## 1. フェーズ13の目的

- フェーズ12までで実装した ScoreProfile 向け AI レビュー（`ai-review`）の結果を、後から比較・確認・採用判断できるように **DB に保存** する。
- 本フェーズではあくまで「AI の提案を保存するところまで」であり、**active profile の自動切替や自動適用は行わない**。

---

## 2. 追加モデル: `ScoreProfileProposal`

- パス: `stocks/models.py`
- 用途: ある `ScoreProfile` に対する AI レビュー提案を 1件ずつ保存する。

### 2.1 フィールド

- `score_profile`: `ForeignKey(ScoreProfile, on_delete=CASCADE, related_name="proposals")`
- `proposal_name`: `CharField(max_length=255)`
  - 人間が識別しやすい提案名（自動生成名を含む）
- `status`: `CharField(max_length=16, choices=[draft/reviewed/accepted/rejected], default="draft")`
- `score_profile_name_snapshot`: `CharField(max_length=100)`
- `score_profile_version_snapshot`: `CharField(max_length=32)`
  - 提案作成時点の `ScoreProfile` の name / version をスナップショットとして保持
- `source_filters_json`: `JSONField`
  - analysis-package 生成時に利用したフィルタ条件（`ticker`/`signal_date_from`/`signal_date_to`/`signal_type` 等）
- `analysis_summary`: `TextField`
  - AI による全体サマリ
- `issues_json`: `JSONField`
  - AI が指摘した課題一覧
- `improvement_hypotheses_json`: `JSONField`
  - AI が提案する改善仮説一覧
- `suggested_weights_json`: `JSONField`
  - AI が提案する新しい `weights_json`
- `suggested_thresholds_json`: `JSONField`
  - AI が提案する新しい `thresholds_json`
- `cautions_json`: `JSONField`
  - AI が挙げた注意点・リスク
- `raw_ai_response_json`: `JSONField`
  - AI が返した JSON をそのまま保存（将来の再解析用）
- `created_at`: `DateTimeField(auto_now_add=True)`
- `updated_at`: `DateTimeField(auto_now=True)`

### 2.2 Migration

- 追加ファイル: `stocks/migrations/0009_scoreprofileproposal.py`
- 役割: 上記 `ScoreProfileProposal` モデルのテーブルを作成。

---

## 3. 追加 service: `profile_proposal.py`

- パス: `stocks/services/profile_proposal.py`
- 役割: AI レビュー結果を `ScoreProfileProposal` として保存する。

### 3.1 関数: `build_proposal_name(profile)`

- `ScoreProfile` を受け取り、UT C時刻を含んだデフォルト提案名を生成。
- 例: `"Default scoring profile v1 proposal 2026-03-13T12:34:56"`

### 3.2 関数: `save_profile_proposal(profile, filters, ai_result)`

- 引数:
  - `profile`: 対象の `ScoreProfile`
  - `filters`: analysis-package 生成時に利用したフィルタ（`Mapping[str, Any]`）
  - `ai_result`: フェーズ12の AI レビューが返した JSON（最低限、次のキーを含む前提）:
    - `target_profile`
    - `analysis_summary`
    - `issues`
    - `improvement_hypotheses`
    - `suggested_weights_json`
    - `suggested_thresholds_json`
    - `cautions`
- 処理:
  - `ScoreProfileProposal` を `STATUS_DRAFT` で1件作成。
  - `score_profile_name_snapshot` / `score_profile_version_snapshot` に `profile` の name / version をコピー。
  - `source_filters_json` に `filters` を保存。
  - `analysis_summary` / `issues_json` / `improvement_hypotheses_json` / `suggested_weights_json` / `suggested_thresholds_json` / `cautions_json` / `raw_ai_response_json` を `ai_result` から詰め替え。

---

## 4. 追加 API: 提案の生成と取得

### 4.1 ai-review-and-save（current）

- エンドポイント:

```text
POST /api/v1/score-profiles/current/ai-review-and-save/
```

- 実装: `ScoreProfileViewSet.current_ai_review_and_save`
- 挙動:
  1. `get_active_score_profile()` で active な `ScoreProfile` を取得。
  2. フェーズ12の `build_ai_review_for_profile` を利用して AI レビューを実行。
  3. クエリパラメータから `ticker` / `signal_date_from` / `signal_date_to` / `signal_type` を抽出して `filters` とする。
  4. `save_profile_proposal(profile, filters, ai_result)` で `ScoreProfileProposal` を1件保存。
  5. 主要フィールド（`proposal_id` など）を JSON として返す。

- 入力:
  - body(JSON, 任意): `user_note`
  - query params(任意):
    - `ticker`
    - `signal_date_from`
    - `signal_date_to`
    - `signal_type`
    - `limit`（AI レビュー自身は analysis-package 側で利用）

- 出力（一例）:

```json
{
  "proposal_id": 1,
  "score_profile_id": 1,
  "proposal_name": "Default scoring profile v1 proposal 2026-03-13T12:34:56",
  "status": "draft",
  "score_profile_name_snapshot": "Default scoring profile",
  "score_profile_version_snapshot": "v1",
  "created_at": "2026-03-13T12:34:56",
  "analysis_summary": "...",
  "issues": ["..."],
  "improvement_hypotheses": ["..."],
  "suggested_weights_json": { "buy": {...}, "sell": {...} },
  "suggested_thresholds_json": {...},
  "cautions": ["..."]
}
```

- エラーハンドリング:
  - active profile が取得できない / AI クライアント未設定:
    - `503 Service Unavailable`
  - AI 応答が不正（JSON でない / 必須キー不足 / 型不正など）:
    - `502 Bad Gateway`

### 4.2 ai-review-and-save（id 指定）

- エンドポイント:

```text
POST /api/v1/score-profiles/<id>/ai-review-and-save/
```

- 実装: `ScoreProfileViewSet.ai_review_and_save`
- 挙動は `current` 版と同様だが、対象 `ScoreProfile` を URL の `<id>` で明示指定する。
- 追加のエラーハンドリング:
  - 指定 id の `ScoreProfile` が存在しない場合:
    - `404 Not Found` + `{"detail": "ScoreProfile not found."}`

### 4.3 proposals 一覧

- エンドポイント:

```text
GET /api/v1/score-profiles/<id>/proposals/
```

- 実装: `ScoreProfileViewSet.proposals`
  - `router.register("score-profiles", ScoreProfileViewSet, ...)` に対する `@action(detail=True, url_path="proposals")` として実装。
- 挙動:
  - 指定 `ScoreProfile` に紐づく `ScoreProfileProposal` を新しい順で一覧返却。
- 出力例:

```json
[
  {
    "id": 1,
    "score_profile_id": 1,
    "proposal_name": "Default scoring profile v1 proposal 2026-03-13T12:34:56",
    "status": "draft",
    "score_profile_name_snapshot": "Default scoring profile",
    "score_profile_version_snapshot": "v1",
    "created_at": "2026-03-13T12:34:56"
  }
]
```

### 4.4 proposal 詳細

- エンドポイント:

```text
GET /api/v1/proposals/<proposal_id>/
```

- 実装: `ProposalViewSet.retrieve`
- 挙動:
  - 単一の `ScoreProfileProposal` の詳細を返す。
- 出力例:

```json
{
  "id": 1,
  "score_profile_id": 1,
  "proposal_name": "Default scoring profile v1 proposal 2026-03-13T12:34:56",
  "status": "draft",
  "score_profile_name_snapshot": "Default scoring profile",
  "score_profile_version_snapshot": "v1",
  "source_filters": {
    "ticker": "TEST",
    "signal_date_from": "2026-03-01"
  },
  "analysis_summary": "...",
  "issues": ["..."],
  "improvement_hypotheses": ["..."],
  "suggested_weights_json": { "buy": {...}, "sell": {...} },
  "suggested_thresholds_json": {...},
  "cautions": ["..."],
  "raw_ai_response_json": { "...": "..." },
  "created_at": "2026-03-13T12:34:56",
  "updated_at": "2026-03-13T12:35:00"
}
```

---

## 5. テスト

- パス: `stocks/tests.py`
- 追加クラス: `ScoreProfileProposalTests`

### 5.1 `save_profile_proposal` の単体テスト

- `test_save_profile_proposal_creates_draft_proposal`
  - ダミーの `ScoreProfile` / `filters` / `ai_result` を用意し、`save_profile_proposal` を呼び出す。
  - 以下を検証:
    - `score_profile_id` が期待どおり
    - `status == "draft"`
    - name/version スナップショットが元の `ScoreProfile` と一致
    - `source_filters_json` にフィルターが保存されている
    - `analysis_summary` / `issues_json` / `improvement_hypotheses_json` / `cautions_json` などが AI 結果から保存されている
    - `raw_ai_response_json` に AI 応答全体が保存されている

（API レベルのエラーハンドリングは、フェーズ12.1 相当の `AIProfileReviewViewTests` に準拠して実装・確認する想定）

---

## 6. 動作確認手順（PowerShell 例）

### 6.1 マイグレーションとテスト

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py test stocks
```

### 6.2 AI フックをモックした状態での手動確認（概要）

実運用では `_call_openai_with_package` を OpenAI API に接続する実装にしておき、  
ここではその前提でのエンドツーエンドの流れだけを確認する。

1. 管理画面で active な `ScoreProfile` が1件存在することを確認。
2. いくつか TradingSignal / SignalOutcome を用意しておく（既存フェーズの確認手順に準拠）。
3. `ai-review-and-save` を叩く:

```powershell
$body = @{ user_note = "テスト提案" } | ConvertTo-Json -Encoding UTF8

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/current/ai-review-and-save/?ticker=TEST&signal_date_from=2026-03-01" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

4. 戻り値の `proposal_id` を使って詳細を取得:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/proposals/1/" `
  -Method Get
```

5. 対象 profile の提案一覧を取得:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/1/proposals/" `
  -Method Get
```

---

## 7. 今回やらないこと

- `ScoreProfileProposal` の `status` を変更する API（`accepted` にした瞬間の自動反映など）
- `ScoreProfileProposal` を元に新しい `ScoreProfile` を自動生成・有効化する処理
- AI 提案の自動適用 / 自動 AB テスト
- 通知機能・定期バッチ・ダッシュボード UI

フェーズ13のゴールは、**AI 提案を安全に保存できる土台を作ること** に限定している。  
実際の採用フローや UI は、以降のフェーズで段階的に追加していく前提。 

