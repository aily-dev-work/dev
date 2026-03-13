# 株価監視アプリ フェーズ17: ScoreProfile activation 履歴管理

## 1. フェーズ17の目的

- ScoreProfile の **active 切替履歴を記録・参照** できるようにし、
  「いつ」「どの profile を」「何由来で」有効化したのかを追跡可能にする。
- 運用時に「なぜ今この ScoreProfile が active なのか」を後から説明できる状態を作る。

このフェーズでは:

- active 切替時に履歴を自動保存する。
- 履歴を API で取得できるようにする。

以下は **今回やらない**:

- 自動ロールバック
- active 切替の通知
- 勝率ベース自動切替
- バッチ
- ダッシュボード
- 認証/ユーザー管理

---

## 2. モデル: ScoreProfileActivationHistory

- パス: `stocks/models.py`
- モデル名: `ScoreProfileActivationHistory`

### 2.1 フィールド構成

- `previous_profile = models.ForeignKey("ScoreProfile", null=True, blank=True, on_delete=models.SET_NULL, related_name="deactivated_histories")`
  - 切り替え前に active だった ScoreProfile
  - 初回 active 化時など、存在しない場合は `NULL` 許可
- `activated_profile = models.ForeignKey("ScoreProfile", on_delete=models.CASCADE, related_name="activated_histories")`
  - この履歴で active にした ScoreProfile
- `source_proposal = models.ForeignKey("ScoreProfileProposal", null=True, blank=True, on_delete=models.SET_NULL, related_name="activation_histories")`
  - 有効化した ScoreProfile の元になった proposal（`applied_score_profile == activated_profile` なものを可能な範囲で逆引き）

- スナップショット項目（FK が削除されても追跡できるようにするための冗長情報）
  - `previous_profile_name_snapshot`
  - `previous_profile_version_snapshot`
  - `activated_profile_name_snapshot`
  - `activated_profile_version_snapshot`
  - `source_proposal_name_snapshot`

- メタ情報
  - `activation_reason = models.CharField(max_length=50, default="manual_activate")`
    - 例: `"manual_activate"`, `"apply_and_activate"` など
  - `note = models.TextField(blank=True, default="")`
    - 運用メモ（「2026年3月の検証用設定」など）
  - `activated_at = models.DateTimeField(auto_now_add=True)`
    - active 化した日時

### 2.2 並び順

- `Meta.ordering = ["-activated_at", "-id"]`
  - デフォルトで **新しい履歴が先頭** に来る。

---

## 3. active 切替 service 拡張

- パス: `stocks/services/profile_activation.py`
- 既存の `activate_score_profile` をフェーズ17用に拡張。

### 3.1 シグネチャ

```python
@transaction.atomic
def activate_score_profile(
    profile: ScoreProfile,
    *,
    note: str = "",
    activation_reason: str = "manual_activate",
) -> ScoreProfile:
    ...
```

### 3.2 処理内容

1. 切り替え前の active プロファイルを取得
   - `previous_active = ScoreProfile.objects.filter(is_active=True).exclude(id=profile.id).order_by("-updated_at").first()`
2. 呼び出し前に `profile.is_active` だったかどうかを記録
3. 既存ロジック通りに、対象以外の active プロファイルをすべて `is_active=False` にする
4. 対象 `profile` が inactive の場合は `is_active=True` に更新
5. 履歴作成ルール:
   - 「すでに active だった profile を再 activate（かつ他に active がいない）」場合
     - **200 で返すが新しい history は作らない**（冪等呼び出しで履歴を汚さない方針）
   - それ以外（初回 active 化 / 別 profile からの切り替えなど）の場合
     - `ScoreProfileActivationHistory` を 1 件作成
6. `source_proposal` の特定:
   - `ScoreProfileProposal.objects.filter(applied_score_profile=profile).order_by("-created_at").first()`
   - 見つかった場合のみ `source_proposal` と `source_proposal_name_snapshot` を設定

### 3.3 履歴保存ルール

- 初回 active 化時:
  - `previous_profile` は `NULL` 可
- 通常切替時:
  - `previous_profile` と `activated_profile` を両方保存
- 同じ profile を再 activate:
  - ステータスは **200 OK**
  - すでにその profile が唯一の active の場合は **履歴を増やさない**
- source_proposal:
  - proposal 由来の profile であれば、`applied_score_profile` から追跡して保存
  - proposal が特定できない profile は `NULL` でよい

---

## 4. API: activation-history 一覧 & profile ごとの履歴

### 4.1 エンドポイント一覧

- 一覧:
  - `GET /api/v1/score-profiles/activation-history/`
- profile ごとの履歴:
  - `GET /api/v1/score-profiles/<id>/activation-history/`

いずれも `ScoreProfileViewSet` の `@action` として実装。

### 4.2 一覧 API: `GET /api/v1/score-profiles/activation-history/`

- 実装: `ScoreProfileViewSet.activation_history_list`
- 返却内容（各要素のキー）:
  - `id`
  - `previous_profile_id`
  - `previous_profile_name`
  - `previous_profile_version`
  - `activated_profile_id`
  - `activated_profile_name`
  - `activated_profile_version`
  - `source_proposal_id`
  - `source_proposal_name`
  - `activation_reason`
  - `note`
  - `activated_at`

- 名前やバージョンは、可能なら FK 先の最新値を参照し、そうでない場合はスナップショットを利用:
  - 例: `previous_profile` が `NULL` でも `previous_profile_name_snapshot` が空でなければそれを返す。

### 4.3 フィルタ

クエリパラメータ:

- `activated_profile_id`
  - `activated_profile_id` で絞り込み
- `source_proposal_id`
  - `source_proposal_id` で絞り込み
- `activated_from=YYYY-MM-DD`
  - `activated_at__date__gte` で絞り込み
- `activated_to=YYYY-MM-DD`
  - `activated_at__date__lte` で絞り込み
- `activation_reason`
  - `activation_reason` で絞り込み

フォーマット不正（例: `activated_from` が日付になっていない）の場合は **400 Bad Request** を返す。

### 4.4 profile ごとの履歴: `GET /api/v1/score-profiles/<id>/activation-history/`

- 実装: `ScoreProfileViewSet.activation_history_for_profile`
- 対象 profile が:
  - `activated_profile` として登場した履歴
  - `previous_profile` として登場した履歴
  の **両方** を含めて返す。
- レスポンスの各要素は一覧 API と同じキー構成。

---

## 5. 動作仕様のまとめ

- 既存の activation ロジックはそのまま活かしつつ、
  1回の activate 操作で
  - ScoreProfile の `is_active` 更新
  - 既存 active の `is_active` 無効化
  - ActivationHistory への履歴保存
  を同一トランザクションで行う。

- 履歴の並び順:
  - デフォルトは `activated_at` 降順（新しいものが先頭）。

---

## 6. テスト

- パス: `stocks/tests.py`

### 6.1 ScoreProfileActivationTests の拡張

- `test_activation_creates_history_with_previous_and_activated_profiles`
  - inactive な候補 profile を `/activate/` すると:
    - `ScoreProfileActivationHistory` が 1 件作成される
    - `previous_profile_id` / `activated_profile_id` / `activation_reason` / `note` が期待通り
- `test_activation_history_handles_initial_activation_with_null_previous`
  - すべての profile を `is_active=False` にした状態から初回 active 化:
    - `previous_profile` が `NULL`
    - `activated_profile` が対象 profile
- `test_reactivate_already_active_profile_does_not_create_additional_history`
  - すでに active な profile に対して `/activate/` を 2 回実行:
    - 2 回目では history 件数が増えない

### 6.2 ScoreProfileActivationHistoryAPITests

- `test_activation_history_list_returns_entries_in_desc_order`
  - `GET /api/v1/score-profiles/activation-history/` が 200 で、
    `activated_at` 降順になっていることを確認
- `test_activation_history_list_filters_by_activated_profile_id`
  - `activated_profile_id` フィルタで該当 profile の履歴だけが返る
- `test_activation_history_list_filters_by_source_proposal_id`
  - `source_proposal_id` フィルタで該当 proposal 由来の履歴だけが返る
- `test_activation_history_list_filters_by_date_range`
  - `activated_from` / `activated_to` を指定しても 200 で JSON リストが返る
- `test_activation_history_list_returns_empty_for_nonexistent_profile_filter`
  - 存在しない `activated_profile_id` で空配列が返る
- `test_activation_history_profile_endpoint_returns_related_entries`
  - `GET /api/v1/score-profiles/<id>/activation-history/` で、
    その profile が `activated_profile` or `previous_profile` として含まれる履歴のみ返る

---

## 7. PowerShell 動作確認例

### 7.1 マイグレーションとテスト

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py makemigrations stocks
python manage.py migrate
python manage.py test stocks
```

### 7.2 activate ＋ 履歴確認

```powershell
# 例: id=2 の候補 ScoreProfile を active 化する
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/2/activate/" `
  -Method Post `
  -ContentType "application/json" `
  -Body "{`"note`":`"switch to candidate`"}"

# activation-history 一覧を取得
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/activation-history/" `
  -Method Get

# 特定 profile の履歴を取得
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/2/activation-history/" `
  -Method Get

# activated_profile_id でフィルタ
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/activation-history/?activated_profile_id=2" `
  -Method Get
```

---

## 8. まとめ

- `ScoreProfileActivationHistory` モデルにより、ScoreProfile の active 切替履歴を永続化。
- `activate_score_profile` service 拡張により、active 切替と履歴保存を 1 トランザクションで実行。
- `activation-history` API により、一覧・profile ごとの履歴を取得可能。
- proposal 由来の ScoreProfile であれば、`source_proposal` により「どの proposal 由来か」を追跡可能。

