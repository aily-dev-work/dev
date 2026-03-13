# 株価監視アプリ フェーズ14: ScoreProfileProposal のレビュー管理（status / review_note / 削除）

## 1. フェーズ14の目的

- フェーズ13で保存できるようになった `ScoreProfileProposal` に対して、
  - **status**
  - **review_note**
  を人間が管理できるようにする。
- このフェーズでは、AI 提案の「中身」（`analysis_summary` や `suggested_weights_json` など）は編集せず、
  レビュー用メタ情報だけを変更・削除できるようにする。

---

## 2. モデル更新

- パス: `stocks/models.py`
- モデル: `ScoreProfileProposal`

### 2.1 追加フィールド

- `review_note = models.TextField(blank=True, default="", help_text="人間によるレビューコメントやメモ")`

### 2.2 Migration

- 追加ファイル: `stocks/migrations/0010_scoreprofileproposal_review_note.py`
- 内容:
  - 既存テーブル `ScoreProfileProposal` に `review_note` カラムを追加。

---

## 3. service 追加: `profile_proposal_review.py`

- パス: `stocks/services/profile_proposal_review.py`
- 役割: proposal のレビューに関するビジネスルールを集約。

### 3.1 `validate_status(value: str) -> None`

- 有効な status:
  - `draft`
  - `reviewed`
  - `accepted`
  - `rejected`
- 上記以外の値が渡された場合:
  - `django.core.exceptions.ValidationError` を送出。

### 3.2 `can_delete(proposal: ScoreProfileProposal) -> bool`

- 削除ルール:
  - `draft`: 削除可
  - `rejected`: 削除可
  - `reviewed`: 削除不可
  - `accepted`: 削除不可

### 3.3 `update_review_fields(proposal, *, status=None, review_note=None) -> ScoreProfileProposal`

- 更新対象フィールド:
  - `status`（オプション）
  - `review_note`（オプション）
- 処理:
  - `status` が指定されていれば `validate_status` で検証し、問題なければ `proposal.status` を更新。
  - `review_note` が指定されていれば `proposal.review_note` を更新。
  - その他フィールドは一切更新しない。
  - `proposal.save(update_fields=["status", "review_note", "updated_at"])` で永続化。

---

## 4. 追加 / 更新した API

### 4.1 review API（status / review_note 更新）

- エンドポイント:

```text
PATCH /api/v1/proposals/<proposal_id>/review/
```

- 実装: `ProposalViewSet.review`（`stocks/views.py`）

#### 入力（JSON body）

- `status`（任意）
  - 有効値: `draft` / `reviewed` / `accepted` / `rejected`
- `review_note`（任意）

- ただし、**少なくともどちらか1つは指定必須**。

#### バリデーション

- `status` が指定されている場合:
  - `validate_status` で検証し、不正なら **400** を返す。
- body に `status` / `review_note` 以外のキーが含まれている場合:
  - 例: `analysis_summary` など
  - **400 Bad Request** + `{"detail": "Unsupported fields for review: [...]"}` を返し、proposal は変更しない。
- `status` も `review_note` も指定されていない場合:
  - **400 Bad Request** + メッセージを返す。
- 指定 id の proposal が存在しない場合:
  - **404 Not Found**

#### 出力

```json
{
  "id": 1,
  "score_profile_id": 1,
  "status": "reviewed",
  "review_note": "Reviewed and ready"
}
```

### 4.2 delete API（proposal 削除）

- エンドポイント:

```text
DELETE /api/v1/proposals/<proposal_id>/
```

- 実装: `ProposalViewSet.destroy`
- 挙動:
  - `can_delete(proposal)` が `True` の場合のみ削除。
  - `False` の場合は削除せず、**409 Conflict** を返す。

#### ステータス別挙動

- `draft`: **204 No Content**（削除成功）
- `rejected`: **204 No Content**（削除成功）
- `reviewed`: **409 Conflict**
- `accepted`: **409 Conflict**
- 存在しない id:
  - **404 Not Found**

---

## 5. proposal の不変条件

このフェーズでは、以下のフィールドは **API 経由では更新不可** とする。

- `proposal_name`
- `source_filters_json`
- `analysis_summary`
- `issues_json`
- `improvement_hypotheses_json`
- `suggested_weights_json`
- `suggested_thresholds_json`
- `cautions_json`
- `raw_ai_response_json`

`/review/` API は `status` / `review_note` 以外のキーを受け取った場合に **400** を返すことで、  
これらのフィールドが誤って変更されないようにしている。

---

## 6. テスト

- パス: `stocks/tests.py`

### 6.1 既存: `ScoreProfileProposalAPITests`

- フェーズ13.1 までの「作成・一覧・詳細・異常系（404 / 502）」をカバー。

### 6.2 追加: `ScoreProfileProposalReviewAPITests`

#### 正常系

- `test_review_updates_status`
  - `PATCH /api/v1/proposals/<id>/review/` で `status` を `reviewed` に更新できること。
- `test_review_updates_review_note`
  - 同じく `review_note` のみ更新できること。
- `test_review_updates_status_and_review_note`
  - `status` と `review_note` を同時に更新できること。
- `test_delete_draft_proposal`
  - `DELETE /api/v1/proposals/<id>/` で `draft` proposal を削除できること。
- `test_delete_rejected_proposal`
  - 同じく `rejected` proposal を削除できること。

#### 異常系

- `test_review_rejects_invalid_status`
  - 不正な `status` 値の場合、**400** となり、元の status は変化しない。
- `test_review_rejects_unsupported_fields`
  - `analysis_summary` などのサポート外フィールドを含めた PATCH は **400**。
  - この場合も proposal は変更されない。
- `test_delete_reviewed_proposal_forbidden`
  - `reviewed` proposal の DELETE は **409 Conflict** で、proposal は残る。
- `test_delete_accepted_proposal_forbidden`
  - `accepted` proposal の DELETE も同様に **409 Conflict**。
- `test_review_not_found_returns_404`
  - 存在しない proposal id に対する `/review/` は **404**。
- `test_delete_not_found_returns_404`
  - 存在しない proposal id に対する DELETE も **404**。

---

## 7. 動作確認手順（PowerShell 例）

### 7.1 マイグレーションとテスト

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py test stocks
```

### 7.2 review API の確認例

事前にフェーズ13 までの手順で `ScoreProfileProposal` を1件以上作成しておく。

```powershell
# status と review_note の更新
$body = @{
  status      = "reviewed"
  review_note = "人間レビュー済み"
} | ConvertTo-Json -Encoding UTF8

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/proposals/1/review/" `
  -Method Patch `
  -ContentType "application/json" `
  -Body $body
```

### 7.3 delete API の確認例

```powershell
# draft または rejected の proposal を削除
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/proposals/1/" `
  -Method Delete `
  -ContentType "application/json"
```

`reviewed` / `accepted` 状態で同様に DELETE を試すと、**409 Conflict** が返ることを確認できる。

---

## 8. 注意点

- このフェーズでは、あくまで **レビュー用メタ情報の管理（status / review_note / 削除）** のみを扱う。
- `accepted` proposal から `ScoreProfile` を生成したり、active profile を自動切り替えたりする処理は含めていない。
- また、複数ステップの承認フローや通知・バッチ・ダッシュボードも範囲外。

フェーズ14のゴールは、
**AI 提案（proposal）を「人間がレビューして採否を判断できる状態」にする土台を整えること** に限定している。 

