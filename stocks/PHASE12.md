# 株価監視アプリ フェーズ12: ScoreProfile AI レビュー API

## 1. フェーズ12の目的

- **目的**: フェーズ11で作成した analysis-package を入力として、
  - 問題点
  - 改善仮説
  - 新しい `weights_json` / `thresholds_json` の案
  を AI に提案させる API を追加する。

- 重要な制約:
  - **このフェーズでは AI の提案を DB に保存しない。**
  - **active な ScoreProfile を自動変更しない。**
  - あくまで「AI レビューの結果を JSON として受け取る」まで。

---

## 2. 追加した service: `ai_profile_review.py`

- パス: `stocks/services/ai_profile_review.py`
- 役割:
  - フェーズ11の `analysis_package` service を利用して analysis-package を生成。
  - それを AI モデル（OpenAI 等）に渡すためのフック関数を提供。
  - AI 応答を JSON として解析し、期待されるキーが揃っているか検証。

### 2.1 期待される AI 応答形式

AI からは最低限以下のキーを持つ JSON オブジェクトを返すことを想定している:

- `target_profile`
- `analysis_summary`
- `issues`
- `improvement_hypotheses`
- `suggested_weights_json`
- `suggested_thresholds_json`
- `cautions`

### 2.2 OpenAI 呼び出し実装: `_call_openai_with_package`

- 実装場所: `stocks/services/ai_profile_review.py`
- 概要:
  - 環境変数から OpenAI クライアントの設定を読み込む。
  - `analysis_package` と `user_note` を JSON にシリアライズして AI に渡す。
  - `response_format={"type": "json_object"}` を指定し、JSON 文字列を受け取る。

#### 必要な環境変数

- `OPENAI_API_KEY`（必須）: OpenAI API キー
- `OPENAI_MODEL`（任意）: 利用するモデル名。未指定時は `"gpt-4.1-mini"`
- `OPENAI_BASE_URL`（任意）: 自前プロキシや互換エンドポイントを利用する場合のベース URL

#### 設定不足時の挙動

- `openai` Python クライアントがインポートできない、または `OPENAI_API_KEY` が未設定の場合:
  - `ImproperlyConfigured` を送出する。
  - View 側で `503 Service Unavailable` にマッピングされる。

### 2.3 応答パース: `_parse_ai_response`

- 役割:
  - AI からの生テキストを `json.loads` でパース。
  - dict であることを確認。
  - `EXPECTED_KEYS`（上記7キー）がすべて存在するか検証。
  - 各フィールドの型を検証。
- 型要件:
  - `target_profile`: object (dict)
  - `analysis_summary`: string
  - `issues`: list
  - `improvement_hypotheses`: list
  - `suggested_weights_json`: object (dict)
  - `suggested_thresholds_json`: object (dict)
  - `cautions`: list
- 不正な場合:
  - JSON パース失敗 → `ValueError("AI response is not valid JSON: ...")`
  - dict 以外 → `ValueError("AI response JSON must be an object.")`
  - 必須キー不足 → `ValueError("AI response is missing expected keys: [...]")`
  - 型不正 → `ValueError("AI response field '<name>' must be ...")`

### 2.4 メイン関数: `build_ai_review_for_profile`

```python
def build_ai_review_for_profile(
    profile: ScoreProfile,
    params: Mapping[str, Any],
    user_note: Optional[str] = None,
) -> Dict[str, Any]:
    analysis_package = build_analysis_package_for_profile(profile, params)
    raw = _call_openai_with_package(analysis_package, user_note=user_note)
    parsed = _parse_ai_response(raw)
    return parsed
```

- まず `build_analysis_package_for_profile` で analysis-package を構築。
- それを `_call_openai_with_package` に渡し、生テキスト応答を取得。
- `_parse_ai_response` で JSON パースとキー検証を行い、dict を返す。

### 2.5 active profile 向けヘルパ: `build_ai_review_for_active_profile`

```python
def build_ai_review_for_active_profile(
    params: Mapping[str, Any],
    user_note: Optional[str] = None,
) -> Dict[str, Any]:
    profile = get_active_score_profile()
    return build_ai_review_for_profile(profile, params, user_note=user_note)
```

- active な `ScoreProfile` を自動的に選び、その Profile 向けのレビューを実行する。

---

## 3. 追加した API: ai-review

- 実装: `ScoreProfileViewSet`（`stocks/views.py`）
- ルーティング: 既存 router により `/api/v1/score-profiles/` 配下。

### 3.1 current profile 向け AI レビュー

```text
POST /api/v1/score-profiles/current/ai-review/
```

#### 入力（body, JSON 推奨）

- 任意:
  - `user_note`: 人間の補足メモ（自由記述）

#### 入力（query params, 任意）

- `ticker`
- `signal_date_from`
- `signal_date_to`
- `signal_type`
- `limit`

これらは内部で analysis-package を構築する際のフィルタとしてそのまま利用される。

#### 出力

- AI からの JSON をそのまま返す（`build_ai_review_for_active_profile` の戻り値）。

#### エラーハンドリング

- AI 応答が不正な JSON / 必須キー不足など → `502 Bad Gateway`
  - body: `{"detail": "<エラーメッセージ>"}`
- AI クライアント未設定（デフォルト実装のまま） → `503 Service Unavailable`
  - body: `{"detail": "<ImproperlyConfigured メッセージ>"}`

### 3.2 id 指定 profile 向け AI レビュー

```text
POST /api/v1/score-profiles/<id>/ai-review/
```

- `current` 版とほぼ同じだが、対象 Profile を `id` で明示指定する。
- 入力/出力/エラーハンドリングは `current` 版と同様。

---

## 4. analysis-package との関係

- フェーズ11で実装した `/api/v1/score-profiles/.../analysis-package/` は、
  - summary
  - dataset_rows
  - target_profile
  - config
  - filters
  を 1 パッケージで返す API。

- フェーズ12の ai-review API は、
  - **まず内部で analysis-package を構築し**、
  - それを AI に渡し、
  - AI 応答を JSON として返す。

つまり、フェーズ11の API を手動で叩いて AI に渡していた作業を、
サーバ側で代行する形になっている（ただし保存や自動適用は行わない）。

---

## 5. 今回やらないこと

- `ScoreProfileProposal` などのモデルに AI 提案を保存すること
- active profile の自動切替
- AI 提案の自動適用 / 自動 AB テスト
- 通知
- 定期バッチ
- ダッシュボード

API はあくまで「この入力で AI に聞いたらどう返ってくるか」を返すだけの役割。

---

## 6. テスト

- パス: `stocks/tests.py`
- 追加クラス: `AIProfileReviewTests`

### 6.1 analysis-package を元に AI service が呼ばれること

`test_ai_review_for_profile_uses_analysis_package_and_returns_expected_keys`

- `_call_openai_with_package` を fake 実装に monkeypatch し、
  - 渡された `analysis_package["target_profile"]["id"]` が対象 Profile の id と一致していることを確認。
  - 期待キーをすべて含む JSON を文字列で返す。
- `build_ai_review_for_profile` 呼び出し後、
  - `target_profile.id` が期待通り
  - `analysis_summary` / `issues` / `improvement_hypotheses` / `suggested_weights_json` / `suggested_thresholds_json` / `cautions`
    が存在することを検証。

### 6.2 不正な AI 応答時に適切にエラーになること

`test_ai_review_invalid_json_raises`

- `_call_openai_with_package` を `"not-json"` を返す fake に差し替え。
- `build_ai_review_for_profile` が `ValueError` を送出することを確認。

（View 側ではこの `ValueError` を `502 Bad Gateway` にマッピングしている。）

### 6.3 current / id 指定の両方が正しく対象 profile を選ぶこと

`test_ai_review_for_active_profile_uses_active_profile`

- active な `ScoreProfile` を1件作成。
- `_call_openai_with_package` を fake に差し替え、
  渡された `package["target_profile"]["id"]` を記録。
- `build_ai_review_for_active_profile` を実行し、
  - `called_ids[0] == active_profile.id`
  - 戻り値の `target_profile.id` も同じ
  であることを確認。

（id 指定版は `build_ai_review_for_profile` が直接利用されるため、
  上記プロファイル指定テストで十分と判断。）

---

## 7. 動作確認手順

### 7.1 AI フック未設定時の挙動

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py runserver

curl.exe -s -X POST http://127.0.0.1:8000/api/v1/score-profiles/current/ai-review/ `
  -H "Content-Type: application/json" `
  -d "{`"user_note`":`"テスト`"}"
```

- デフォルトでは `_call_openai_with_package` が `ImproperlyConfigured` を送出するため、
  - ステータスコード: `503`
  - body: `{"detail": "...AI client is not configured..."}`  
  となることを確認。

### 7.2 テストでの擬似 AI 応答確認

- 既に `AIProfileReviewTests` で fake AI を用いたテストを行っており、

```powershell
python manage.py test stocks
```

- とすることで、AI 応答パースロジックや expected keys 判定がすべて通っていることを確認できる。

---

## 8. 注意点

- 実際に OpenAI API などと連携する際は、
  - `_call_openai_with_package` の中でクライアント初期化と API 呼び出しを実装し、
  - プロンプトには「**必ず JSON だけを返すこと**」という指示を強く含めることが推奨される。
- 本フェーズでは、AI 連携の「窓口」とエラーハンドリング・パース部分のみを実装し、
  それ以上の自動化（保存・適用・AB テストなど）は次フェーズ以降の課題として残している。 

