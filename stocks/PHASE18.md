# 株価監視アプリ フェーズ18: ScoreProfile 手動ロールバック

## 1. フェーズ18の目的

- 現在 active な ScoreProfile を、**必要に応じて安全に手動ロールバック**できるようにする。
- 切替後に問題があったときに「直前の profile に戻す」ことを可能にする。

このフェーズでは:

- 現在 active な profile から、**直前の profile に戻せる**。
- ロールバック操作自体も **activation history に残る**（`activation_reason="manual_rollback"`）。

以下は **今回やらない**:

- 自動ロールバック
- 勝率や AI 判断での自動戻し
- 任意 profile への rollback-to
- 通知・バッチ・ダッシュボード
- TradingSignal の再評価・再生成

---

## 2. service: `profile_rollback.py`

- パス: `stocks/services/profile_rollback.py`
- 役割: 現在 active を確認し、直近の activation history から戻し先を決め、その profile を active にする。ロールバックも履歴に記録する。

### 2.1 関数

```python
def rollback_to_previous_profile(note: str = "") -> ScoreProfile
```

### 2.2 戻し先の決定ルール（今回「直前に戻す」のみ）

1. 現在 active な ScoreProfile を取得する。
2. **直近の activation history** を新しい順に見て、  
   現在 active な profile が `activated_profile` になっている **最新の履歴** を探す。
3. その履歴の **`previous_profile`** を戻し先とする。
4. `previous_profile` が **null の場合は戻せない**（初回 active 化のため前がない）。
5. 戻し先 profile が見つからない場合もロールバック不可。

### 2.3 実行内容

- 戻し先 profile を `activate_score_profile(..., activation_reason="manual_rollback")` で active 化する。
- 既存の activate ロジックにより「他の active は inactive」「履歴 1 件追加」が同一トランザクションで行われる。
- 履歴の `activation_reason` は **`"manual_rollback"`** に固定。

### 2.4 例外

- `RollbackNotAllowedError`: ロールバックが許可されない状態。API では **409 Conflict** にマッピングする。
  - 現在 active な profile が存在しない
  - 現在 active に対応する直近履歴が無い
  - その履歴の `previous_profile` が null

---

## 3. API: `POST /api/v1/score-profiles/rollback/`

### 3.1 仕様

- **メソッド**: POST
- **URL**: `/api/v1/score-profiles/rollback/`
- **入力**: 任意で `note`（ロールバック理由などのメモ）

### 3.2 正常時

- **200 OK**
- 戻った profile（現在 active になった ScoreProfile）の情報を返す。  
  （id, name, version, is_active, description, weights_json, thresholds_json, created_at, updated_at など）

### 3.3 異常時（409 Conflict）

- 現在 active な profile が存在しない → `{"detail": "No active ScoreProfile. Cannot rollback."}` など
- 直前に戻す対象が見つからない（履歴が無い、または現在 active が `activated_profile` の履歴が無い）→ 409
- `previous_profile` が null の履歴しか無い（初回 active のため戻せない）→ 409

いずれも `{"detail": "..."}` 形式で分かりやすく返す。

---

## 4. activation history への記録

- 既存の **ScoreProfileActivationHistory** を再利用する。
- ロールバック時は `activate_score_profile` 内で 1 件作成される。
- 内容の目安:
  - **previous_profile**: ロールバック前に active だった profile
  - **activated_profile**: ロールバック後に active になった profile（戻し先）
  - **source_proposal**: 戻し先 profile が proposal 由来なら可能な範囲で設定（`applied_score_profile` から逆引き）
  - **activation_reason**: `"manual_rollback"`
  - **note**: リクエストで渡した任意メモ

---

## 5. source_proposal の扱い

- ロールバック後に active になった profile について、  
  `ScoreProfileProposal.applied_score_profile` から逆引きできる proposal があれば、  
  その proposal を履歴の `source_proposal` に保存する。
- 見つからない場合は null でよい（既存の activate ロジックと同じ）。

---

## 6. 戻れないケースのまとめ

| ケース | レスポンス |
|--------|------------|
| 現在 active な profile が無い | 409 |
| 現在 active を `activated_profile` にした履歴が無い | 409 |
| その履歴の `previous_profile` が null（初回 active のみ） | 409 |

---

## 7. テスト（stocks/tests.py）

### 7.1 正常系

- active が A → B に切り替わった後、rollback で A に戻せる
- rollback 後、A が active / B が inactive、active は 1 件だけ
- rollback で activation history が 1 件追加される
- その履歴の `activation_reason == "manual_rollback"`
- `note` を渡すと history.note に保存される

### 7.2 異常系

- 現在 active が無い → 409
- activation history が無い（現在 active を activated にした履歴が無い）→ 409
- 現在 active に対応する直近履歴の `previous_profile` が null → 409

### 7.3 境界系

- 複数回切替後でも、現在 active に対応する直近履歴から「1つ前」へ戻せる
- rollback 後、`GET /api/v1/score-profiles/current/` で戻った profile が返る
- rollback 後、`GET /api/v1/score-profiles/activation-history/` に `manual_rollback` 履歴が含まれる

---

## 8. PowerShell 動作確認例

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py test stocks
```

```powershell
# いま B が active の状態でロールバック（A に戻る想定）
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/rollback/" `
  -Method Post `
  -ContentType "application/json" `
  -Body "{`"note`":`"reverted due to issue`"}"

# 現在 active を確認
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/score-profiles/current/" -Method Get

# 履歴に manual_rollback が含まれることを確認
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/score-profiles/activation-history/?activation_reason=manual_rollback" -Method Get
```

---

## 9. 既存 API との関係

- フェーズ16の **activate** ロジックは変更しない。
- ロールバックは内部で `activate_score_profile` を `activation_reason="manual_rollback"` で呼ぶだけなので、active は常に 1 件に保たれ、履歴も一貫して記録される。
- `GET /api/v1/score-profiles/activation-history/` の `activation_reason` フィルタで `manual_rollback` を指定すると、ロールバック履歴だけを取得できる。
