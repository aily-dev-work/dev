# 株価監視アプリ フェーズ23: 統計ダッシュボード

## 1. フェーズ23の目的

既存の review-targets / compare / ops-summary / activation-history を土台にして、
運用担当者が profile の状態や比較結果を視覚的に把握しやすい
**統計ダッシュボード**を追加する。

このフェーズでは、

- ダッシュボード用の統計 API（dashboard-stats）
- Next.js フロントでのグラフ / 集計表示（Recharts）

を追加する。

### 今回やらないこと

- 通知送信
- AI 自動改善
- 自動切替
- 本格認証
- モバイル最適化
- 高度なグラフ分析
- リアルタイム更新

---

## 2. バックエンド API: `GET /api/v1/score-profiles/dashboard-stats/`

### 2.1 クエリパラメータ（任意）

- `signal_date_from`
- `signal_date_to`
- `base_profile_id`
- `candidate_profile_id`
- `threshold_success_rate`
- `stale_days`
- `min_evaluated_count`

base_profile_id と candidate_profile_id を両方指定した場合のみ `compare_snapshot` を返す。
存在しない profile id を指定した場合は **404** を返す。

### 2.2 返却内容

- `current_active_profile`: 現在 active な profile の基本情報（いなければ null）
- `ops_summary`: 既存 build_ops_summary の返却（current_active_profile, counts, message_lines 等）
- `recent_activation_history`: 直近 N 件（デフォルト 10）の activation history
- `profile_overview`: 全 profile 件数 / active / inactive / proposal_derived_count
- `compare_snapshot`: base_profile_id と candidate_profile_id を両方指定した場合のみ。compare_profiles の返却と同じ構造。未指定時は null
- `chart_data`:
  - `profile_success_rate_rows`: profile_id, profile_name, profile_version, signal_type, success_rate_h20
  - `profile_avg_return_rows`: profile_id, profile_name, profile_version, signal_type, avg_return_h20
  - `activation_timeline_rows`: activated_at, activated_profile_name, activated_profile_version, activation_reason

---

## 3. service: profile_dashboard_stats.py

- パス: `stocks/services/profile_dashboard_stats.py`
- 役割: current active / ops_summary / activation history / profile_overview / compare_snapshot / chart_data を 1 レスポンスにまとめる。
- 方針: ops_summary は build_ops_summary を再利用。compare_snapshot は compare_profiles を再利用。activation history は同サービス内で直近 N 件取得。chart_data は全 profile に対して signal_summary の build_summary_queryset + summarize_signals で h20 の success_rate / avg_return を集め、activation 履歴から timeline 行を構築。

---

## 4. フロントエンド改善

### 4.1 ダッシュボード `/`

- **上部カード**: current active profile / stale count / underperforming count / accepted_not_activated count / profile overview（total, active, proposal-derived）
- **グラフ**: Profile success rate (h20) の棒グラフ、Profile avg return (h20) の棒グラフ（Recharts BarChart）
- **Activation timeline**: activation_timeline_rows の一覧表示
- **Compare snapshot**: base/candidate が指定されている場合のみ表示。Compare 画面へのリンク
- **Recent activation history**: 既存と同様のテーブル
- **Messages**: ops_summary.message_lines

### 4.2 Compare 画面 `/profiles/compare`

- 既存のテーブルに加え、signal_type ごとに Base vs Candidate の **H20 Success rate** と **H20 Avg return** を棒グラフで並べて表示。

---

## 5. 型定義・API ラッパ

- `frontend/types/api.ts`: DashboardStatsResponse, DashboardProfileOverview, DashboardChartData, DashboardChartSuccessRateRow, DashboardChartAvgReturnRow, DashboardActivationTimelineRow
- `frontend/lib/api.ts`: `getDashboardStats(params?)`

---

## 6. 起動手順

1. バックエンド: `python manage.py runserver`
2. フロントエンド: `cd frontend && npm install && npm run dev`
3. ブラウザ: `http://localhost:3000`

---

## 7. 動作確認手順

1. `GET /api/v1/score-profiles/dashboard-stats/` が 200 を返す。
2. レスポンスに ops_summary.counts / recent_activation_history / profile_overview / chart_data が含まれる。
3. 存在しない base_profile_id & candidate_profile_id を指定すると 404。
4. ダッシュボードでカード・グラフ・Recent activation history が表示される。
5. API エラー時は画面が壊れずエラーメッセージが表示される。
6. Compare 画面で H20 の比較棒グラフが表示される。

---

## 8. テスト

### ScoreProfileDashboardStatsAPITests

- test_dashboard_stats_returns_200
- test_dashboard_stats_has_ops_summary_and_counts
- test_dashboard_stats_has_recent_activation_history
- test_dashboard_stats_has_profile_overview
- test_dashboard_stats_has_chart_data_structure
- test_dashboard_stats_invalid_base_candidate_returns_404

---

## 9. 注意点

- 既存 API は変更していない。
- View は薄く、集計ロジックは service に集約。
- グラフは Recharts を使用。色・装飾は最小限。
- 認証・通知・自動切替は追加していない。
