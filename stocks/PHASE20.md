# 株価監視アプリ フェーズ20: 運用サマリ API（ops-summary）

## 1. フェーズ20の目的

review-targets / compare まで完成した運用ループに対して、
運用担当者が「今見るべきもの」をすぐ把握できるようにするため、
**通知・定期レビュー支援向けの運用サマリ API** を追加する。

このフェーズでは:

- review-targets の結果を運用向けに集約した API
- 通知本文に流用しやすい整形結果（message_lines）

を追加する。

以下は **今回やらない**:

- LINE / Slack / Mail など外部通知送信
- 自動通知スケジューラ
- 自動切替
- ダッシュボード画面

---

## 2. service: profile_ops_summary.py

- パス: `stocks/services/profile_ops_summary.py`
- 役割: review-targets の結果を取得し、運用向けの summary と message_lines を構築する。

### 2.1 関数

```python
def build_ops_summary(
    *,
    signal_date_from: str | None = None,
    signal_date_to: str | None = None,
    threshold_success_rate: float,
    stale_days: int,
    min_evaluated_count: int,
) -> Dict[str, Any]:
    ...
```

### 2.2 返却内容

- `generated_at`: サマリ生成日時（`timezone.now().isoformat()`）
- `current_active_profile`: review-targets と同じ形式
- `stale_active_profiles`: 同上
- `underperforming_profiles`: 同上
- `accepted_not_activated_profiles`: 同上
- `counts`:
  - `stale_active_count`
  - `underperforming_count`
  - `accepted_not_activated_count`
- `message_lines`: 通知本文にそのまま流用しやすい短い英語メッセージの配列

### 2.3 message_lines の方針

例:

- `"Active profile: Default v3"`
- `"1 stale active profile found."` / `"2 stale active profiles found."`
- `"1 underperforming profile found."` / `"2 underperforming profiles found."`
- `"1 accepted but not activated proposal-derived profile found."` / `"No accepted but not activated proposal-derived profiles."`

現在の実装では:

- active profile が存在しない場合: `"No active profile configured."`
- count=0 の場合も「No ...」系の行を返し、`message_lines` は常に 1 行以上になる。

---

## 3. API: `GET /api/v1/score-profiles/ops-summary/`

- 実装: `ScoreProfileViewSet.ops_summary`
- エンドポイント: `GET /api/v1/score-profiles/ops-summary/`

### 3.1 クエリパラメータ

review-targets と同じ:

- `signal_date_from`
- `signal_date_to`
- `threshold_success_rate`
- `stale_days`
- `min_evaluated_count`

すべて任意。指定がなければフェーズ19で定義したデフォルト値が利用される。

### 3.2 返却内容

レスポンス例（構造のみ）:

```json
{
  "generated_at": "2026-03-14T12:34:56.789012+09:00",
  "current_active_profile": { "...": "..." } | null,
  "stale_active_profiles": [ { "...": "..." }, ... ],
  "underperforming_profiles": [ { "...": "..." }, ... ],
  "accepted_not_activated_profiles": [ { "...": "..." }, ... ],
  "counts": {
    "stale_active_count": 1,
    "underperforming_count": 2,
    "accepted_not_activated_count": 1
  },
  "message_lines": [
    "Active profile: OpsActive v1",
    "1 stale active profile found.",
    "1 underperforming profile found.",
    "1 accepted but not activated proposal-derived profile found."
  ]
}
```

### 3.3 review-targets との違い

- review-targets:
  - 生のリスト（current / stale / underperforming / accepted-not-activated）を返す API。
  - 自分で counts を計算し、文面を組み立てる前提。
- ops-summary:
  - review-targets の結果をもとに counts と message_lines を追加した **運用サマリ**。
  - 通知本文・定期レビュー用のテキストにそのまま流用しやすい構造を返す。

---

## 4. テスト（stocks/tests.py）

### 4.1 ScoreProfileOpsSummaryAPITests

- `test_ops_summary_returns_current_and_counts_and_messages`
  - current_active_profile が返る
  - stale / underperforming / accepted-not-activated が counts に反映される
  - message_lines が空でなく生成される
- `test_ops_summary_underperforming_respects_min_evaluated_count`
  - min_evaluated_count を変えると underperforming_count が変わる
- `test_ops_summary_aligns_with_review_targets_counts`
  - 同じクエリパラメータで review-targets と ops-summary を呼び、
    stale / underperforming / accepted-not-activated の件数が一致することを確認

---

## 5. PowerShell 動作確認例

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py test stocks
```

```powershell
# ops-summary の取得
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/ops-summary/" `
  -Method Get

# パラメータ付き（review-targets と同じパラメータ）
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/score-profiles/ops-summary/?stale_days=30&threshold_success_rate=0.5&min_evaluated_count=5&signal_date_from=2026-01-01&signal_date_to=2026-12-31" `
  -Method Get
```

---

## 6. 注意点

- ops-summary は **外部通知送信は行わない**。あくまで通知本文に流用しやすい JSON を返すのみ。
- review-targets のロジック（underperforming / stale / accepted-not-activated）は service に集約されており、ops-summary はそれを再利用しているだけなので、判定ルールが一貫する。
- compare API には影響を与えていない。
- フェーズ20では新しいモデルやスケジューラは追加していない。

