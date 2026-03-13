# Stocks Frontend (Phase 21)

Next.js + TypeScript 製の簡易管理画面です。  
既存 Django REST API (`stocks` アプリ) を利用して、ScoreProfile / Proposal / Activation history の運用をブラウザから行えます。

---

## 1. 起動手順

前提:

- Node.js 18+ / npm or pnpm
- バックエンド Django アプリが `http://127.0.0.1:8000` で起動していること

```bash
cd d:\dev\frontend
npm install
npm run dev
```

ブラウザで `http://localhost:3000` を開きます。

---

## 2. 環境変数

フロントエンドから叩く API のベース URL は `NEXT_PUBLIC_API_BASE_URL` で指定できます。

例: `frontend/.env.local`

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

未指定時は `http://127.0.0.1:8000` を利用します。

---

## 3. 画面一覧と API 対応

### 3.1 ダッシュボード `/`

- 表示:
  - 現在 active な profile
  - ops-summary の counts / message_lines
  - 直近 activation history 数件
- 操作:
  - rollback ボタン（`/api/v1/score-profiles/rollback/`）
- 利用 API:
  - `GET /api/v1/score-profiles/ops-summary/`
  - `GET /api/v1/score-profiles/current/`
  - `GET /api/v1/score-profiles/activation-history/`
  - `POST /api/v1/score-profiles/rollback/`

### 3.2 Proposals 一覧 `/proposals`

- 表示:
  - proposal_name / status
  - score_profile_name_snapshot / version_snapshot
  - created_at
  - applied_score_profile の有無
  - 詳細リンク
- 利用 API:
  - `GET /api/v1/proposals/`

### 3.3 Proposal 詳細 `/proposals/[id]`

- 表示:
  - proposal_name / status / review_note
  - analysis_summary
  - issues / improvement_hypotheses / suggested_weights / suggested_thresholds / cautions / source_filters / raw_ai_response (整形 JSON)
  - applied_score_profile 情報（あれば）
- 操作:
  - review 更新: `PATCH /api/v1/proposals/<id>/review/`
  - apply 実行: `POST /api/v1/proposals/<id>/apply/`
- 利用 API:
  - `GET /api/v1/proposals/<id>/`
  - `PATCH /api/v1/proposals/<id>/review/`
  - `POST /api/v1/proposals/<id>/apply/`

### 3.4 Profiles 一覧（サマリ） `/profiles`

- 表示:
  - id / name / version / is_active
  - kind: current / stale / underperforming / accepted_not_activated
  - source proposal 情報（あれば）
- 操作:
  - activate ボタン（Confirm 付き）
- 利用 API:
  - `GET /api/v1/score-profiles/ops-summary/`
  - `POST /api/v1/score-profiles/<id>/activate/`

※ バックエンドに ScoreProfile 一覧 API が無いため、ops-summary / review-targets ベースで「運用上見るべき profile」のみを表示しています。

### 3.5 Compare 画面 `/profiles/compare`

- 操作:
  - base_profile_id / candidate_profile_id を入力し compare API を実行
  - Swap ボタンで base / candidate を入れ替え
- 表示:
  - base_profile / candidate_profile の基本情報
  - signal_type ごとの summary テーブル
    - total_signals
    - h5 / h10 / h20 の evaluated_count / success_count / success_rate / avg_return
- 利用 API:
  - `GET /api/v1/score-profiles/compare/?base_profile_id=...&candidate_profile_id=...`

### 3.6 History 画面 `/history`

- 表示:
  - activated_at
  - activation_reason
  - previous_profile (name/version/id)
  - activated_profile (name/version/id)
  - source_proposal (name/id)
  - note
- フィルタ:
  - activation_reason
  - activated_profile_id
- 利用 API:
  - `GET /api/v1/score-profiles/activation-history/`

---

## 4. 操作確認手順（例）

1. Django バックエンドを起動し、いくつかの ScoreProfile / Proposal / ActivationHistory を用意。
2. フロントエンド `npm run dev` を起動。
3. ブラウザで `http://localhost:3000` を開く。
4. Dashboard:
   - Active profile / Ops summary / History が表示されること。
   - Rollback ボタン押下 → Confirm 後、active profile と history が更新されること。
5. Proposals:
   - Proposal 一覧が表示され、accepted proposal に対して detail 画面から review / apply が行えること。
6. Profiles:
   - current / stale / underperforming / accepted-not-activated profiles が一覧表示されること。
   - Activate ボタンで profile を切り替えられること。
7. Compare:
   - 2つの profile id を指定して compare できること。
8. History:
   - activation history 一覧が表示され、filter で絞り込みできること。

---

## 5. 注意点

- 認証・権限制御は行っていません（開発用管理画面想定）。
- バックエンド API のレスポンス形式に強く依存しているため、API 仕様を変更する場合は併せてフロントの型 (`types/api.ts`) を更新してください。
- プロファイルの完全な一覧 API は無いため、`/profiles` では ops-summary/ review-targets に出てくる profile だけを表示しています。
- 自動更新・通知 UI・グラフ表示などはフェーズ21では実装していません。

