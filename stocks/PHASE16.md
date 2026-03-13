# 株価監視アプリ フェーズ16: ScoreProfile の手動 activation

## 1. フェーズ16の目的

- フェーズ15で生成した `is_active=False` の候補 `ScoreProfile` を、
  人間の明示操作で **active に切り替えられるようにする**。
- このフェーズでは:
  - 手動で active プロファイルを切り替える。
  - 既存 active プロファイルを inactive にする。
  - 自動切替や AI 判断による active 変更は行わない。

---

## 2. service 追加: `profile_activation.py`

- パス: `stocks/services/profile_activation.py`
- 役割: `ScoreProfile` の active 切替ロジックを集約する。

### 2.1 `activate_score_profile(profile: ScoreProfile) -> ScoreProfile`

- 実装概要:

```python
@transaction.atomic
def activate_score_profile(profile: ScoreProfile) -> ScoreProfile:
    # 他の active プロファイルをすべて off にする
    ScoreProfile.objects.filter(is_active=True).exclude(id=profile.id).update(is_active=False)

    if not profile.is_active:
        profile.is_active = True
        profile.save(update_fields=["is_active", "updated_at"])

    return profile
```

- 特徴:
  - `transaction.atomic` で一連の更新をトランザクション化。
  - すでに `profile.is_active=True` の場合でも冪等に動作し、  
    最終的に active な `ScoreProfile` はこの1件だけになる。
  - 複数 active な異常状態が事前に存在していても、  
    実行後には対象 profile だけが active になるよう正規化される。

---

## 3. API 追加: activate

- 実装: `ScoreProfileViewSet.activate`（`stocks/views.py`）

### 3.1 エンドポイント

```text
POST /api/v1/score-profiles/<profile_id>/activate/
```

### 3.2 挙動

1. `profile_id` から `ScoreProfile` を取得。
2. service `activate_score_profile(profile)` を呼び出し、active 切替を実行。
3. 更新後の `ScoreProfile` 情報を **200 OK** で返す。

### 3.3 エラーハンドリング

- profile が存在しない:
  - **404 Not Found**

### 3.4 冪等性

- すでに対象 profile が `is_active=True` の場合に再度 `/activate/` を叩いても:
  - ステータスは **200 OK**。
  - active プロファイルはその profile 1件だけ、という状態が保たれる。

---

## 4. proposal 由来との関係

- フェーズ15で `ScoreProfileProposal.applied_score_profile` により
  「どの proposal から生成された ScoreProfile か」は追跡可能になっている。
- フェーズ16では、`ScoreProfile` 自体の `is_active` を切り替えるのみであり、
  `applied_score_profile` のリンクは変更しない。
- active 化された profile が proposal 由来かどうかは、
  - proposal detail (`GET /api/v1/proposals/<id>/`)
    - `applied_score_profile_id` / `applied_score_profile_name` / `applied_score_profile_version`
  から追跡可能。

---

## 5. 読み取り API

- すでにフェーズ8 で `GET /api/v1/score-profiles/current/` が存在しており、
  `get_active_score_profile()` を使って「現在 active な ScoreProfile」を返す。
- フェーズ16の activate API を通じて active を切り替えたあとも、
  `current` API からは常に最新の active profile が取得できる。

---

## 6. テスト

- パス: `stocks/tests.py`
- 追加クラス: `ScoreProfileActivationTests`

### 6.1 正常系

- `test_activate_inactive_profile_switches_active_and_deactivates_others`
  - inactive な候補 profile に対して `/activate/` を実行すると:
    - 対象 profile の `is_active=True`。
    - それまで active だった別 profile の `is_active=False`。
    - `ScoreProfile.objects.filter(is_active=True).count() == 1`。

- `test_activate_already_active_profile_is_idempotent`
  - すでに active な profile に対して `/activate/` を実行しても:
    - ステータスは **200**。
    - active な profile は 1件だけ（同じ profile）のまま。

### 6.2 異常系

- `test_activate_not_found_returns_404`
  - 存在しない profile id に対する `/activate/` は **404**。

- `test_activate_normalizes_when_multiple_active_exist`
  - 擬似的に複数 active な `ScoreProfile` を作った状態で、
    `/activate/` を実行すると:
    - 対象 profile だけが `is_active=True`。
    - それ以外の profile は `is_active=False`。
    - `ScoreProfile.objects.filter(is_active=True).count() == 1`。

---

## 7. 動作確認手順（PowerShell 例）

### 7.1 マイグレーションとテスト

フェーズ16ではモデル変更はないため、追加マイグレーションは不要。  

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py test stocks
```

### 7.2 activate API の確認

```powershell
# 例: id=2 の候補 ScoreProfile を active 化する
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/2/activate/" `
  -Method Post `
  -ContentType "application/json" `
  -Body "{}"
```

```powershell
# 現在 active な profile を確認
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/current/" `
  -Method Get
```
