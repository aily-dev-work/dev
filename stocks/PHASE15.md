# 株価監視アプリ フェーズ15: accepted proposal からの ScoreProfile 生成

## 1. フェーズ15の目的

- **accepted 済みの `ScoreProfileProposal`** を元に、新しい `ScoreProfile` を生成できるようにする。
- このフェーズでは:
  - 生成した `ScoreProfile` は **`is_active=False`** のまま。
  - 既存 active profile は自動で変更しない。
  - proposal accepted 時の自動適用もしない。

---

## 2. モデル拡張

- パス: `stocks/models.py`
- モデル: `ScoreProfileProposal`

### 2.1 追加フィールド

```python
applied_score_profile = models.ForeignKey(
    "ScoreProfile",
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="source_proposals",
    help_text="この proposal から生成された ScoreProfile（なければ NULL）",
)
```

- 役割:
  - この proposal から生成された `ScoreProfile` を追跡する。
  - 1 proposal から複数の profile を作ってしまうことを防ぎやすくする。

### 2.2 Migration

- 追加ファイル: `stocks/migrations/0012_scoreprofileproposal_applied_profile.py`
- 依存関係: `0011_alter_scoreprofile_id_alter_signaloutcome_id_and_more`
- 内容:
  - 既存 `ScoreProfileProposal` テーブルに `applied_score_profile` FK カラムを追加。

---

## 3. service 追加: `profile_apply.py`

- パス: `stocks/services/profile_apply.py`
- 役割: accepted proposal から新しい `ScoreProfile` を生成するビジネスロジックをまとめる。

### 3.1 `apply_proposal_to_new_profile(proposal) -> ScoreProfile`

- 前提条件:
  - `proposal.status == "accepted"` であること。
  - `proposal.applied_score_profile is None` であること。
  - `proposal.suggested_weights_json` / `proposal.suggested_thresholds_json` が **dict かつ非空** であること。

- 検証に失敗した場合:
  - `django.core.exceptions.ValidationError` を送出。

- 正常系の処理:
  1. name を組み立てる（例）:
     - `<元profile名> derived from proposal <proposal.id>`
  2. version を組み立てる:
     - `from-proposal-<proposal.id>-<UTC時刻ISO>`
  3. description を組み立てる:
     - source proposal id
     - source profile name/version snapshot
     - AI review 由来であること
  4. `ScoreProfile.objects.create(...)` で新規 profile を生成:
     - `is_active=False`
     - `weights_json = proposal.suggested_weights_json`
     - `thresholds_json = proposal.suggested_thresholds_json`
  5. `proposal.applied_score_profile = profile` を設定し、保存。

---

## 4. API 追加

### 4.1 apply API

- エンドポイント:

```text
POST /api/v1/proposals/<proposal_id>/apply/
```

- 実装: `ProposalViewSet.apply`（`stocks/views.py`）
- 挙動:
  1. `proposal_id` から `ScoreProfileProposal` を取得。
  2. service `apply_proposal_to_new_profile(proposal)` を呼び出す。
  3. 新しく生成された `ScoreProfile` の情報を `201 Created` で返す。

- バリデーション / エラーハンドリング:
  - proposal が存在しない → **404 Not Found**
  - `status != accepted` → **409 Conflict**（状態衝突）
  - すでに `applied_score_profile` が設定済み → **409 Conflict**（再適用の衝突）
  - `suggested_weights_json` / `suggested_thresholds_json` が空 or 不正 → **400 Bad Request**（入力不正）

### 4.2 proposal detail 拡張

- エンドポイント:

```text
GET /api/v1/proposals/<proposal_id>/
```

- 追加フィールド:

```json
{
  "review_note": "...",
  "applied_score_profile_id": 12,
  "applied_score_profile_name": "BaseProfile derived from proposal 5",
  "applied_score_profile_version": "from-proposal-5-2026-03-13T12:34:56"
}
```

- これにより、「どの proposal からどの ScoreProfile が生成されたか」を proposal 側から追える。

---

## 5. テスト

- パス: `stocks/tests.py`
- 追加クラス: `ScoreProfileProposalApplyTests`

### 5.1 正常系

- `test_apply_creates_new_score_profile`
  - `POST /api/v1/proposals/<accepted_id>/apply/` で
    - 新しい `ScoreProfile` が1件生成される。
    - `is_active` は `False`。
    - `weights_json` / `thresholds_json` が proposal の `suggested_*` と一致。
    - `proposal.applied_score_profile_id` が設定される。

- `test_apply_sets_applied_profile_info_visible_in_detail`
  - apply 実行後、`GET /api/v1/proposals/<id>/` で
    - `applied_score_profile_id`
    - `applied_score_profile_name`
    - `applied_score_profile_version`
    が取得できること。

### 5.2 異常系

- `test_apply_not_found_returns_404`
  - 存在しない proposal id に対する `/apply/` は **404**。

- `test_apply_rejects_non_accepted_status`
  - `draft` / `reviewed` / `rejected` status の proposal に対する `/apply/` は **409**。
  - `applied_score_profile` は設定されない。

- `test_apply_rejects_when_already_applied`
  - 同じ proposal に対して2回 `/apply/` すると、2回目は **409**。

- `test_apply_rejects_empty_suggested_payload`
  - `suggested_weights_json` / `suggested_thresholds_json` が空 dict の proposal に対する `/apply/` は **400**（入力不正）。

---

## 6. README / 構成への反映

- `README.md`:
  - `stocks/` 配下に `PHASE15.md` を追加。
  - `services/` 配下に `profile_apply.py` を追加。

---

## 7. 動作確認手順（PowerShell 例）

### 7.1 マイグレーションとテスト

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py test stocks
```

### 7.2 apply API の確認

1. フェーズ13〜14 の手順に従って、`accepted` 状態の `ScoreProfileProposal` を1件用意する。

2. apply 実行:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/proposals/1/apply/" `
  -Method Post `
  -ContentType "application/json" `
  -Body "{}"
```

3. proposal detail で applied profile を確認:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/proposals/1/" `
  -Method Get
```

---

## 8. 注意点

- このフェーズでは、生成された `ScoreProfile` を **active** にする処理は実装していない。
- proposal accepted 時の自動 apply も行っていない。
- TradingSignal / SignalOutcome の再計算や再生成も行わない。
- 通知・バッチ・ダッシュボードなどは次フェーズ以降の検討事項。

フェーズ15のゴールは、
**AI 提案（accepted proposal）をもとに、安全に新しい ScoreProfile の候補を生成できる状態** を作ることに限定している。 

