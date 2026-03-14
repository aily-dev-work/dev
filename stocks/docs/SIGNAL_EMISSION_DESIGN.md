# シグナル発報のリアルタイム化・デイトレ対応（設計メモ）

## 現状

- **ScoreProfile に `trading_style` フィールドあり**（long_term / short_term / day_trade）。プロファイル一覧・詳細・新規・編集で参照・保存できる。リアルタイム監視や発報頻度を分岐するときは、**アクティブプロファイルの trading_style を参照**すればよい。
- **日足シグナル**: **POST /api/v1/stocks/<id>/generate-signal/** を呼んだとき 1 銘柄・1 日 1 件保存（`signal_datetime` は null）。
- **5 分足シグナル（デイトレ）**: **5 分毎の自動ジョブ**で全銘柄の 5 分足を取得し、取得ごとにテクニカル・スコアを計算してシグナルを保存。`TradingSignal.signal_datetime` に 5 分バー開始時刻を設定し、同一日内で複数件可（ユニークは stock + signal_date + signal_datetime）。
- テクニカル: **日足**は `technical_analysis.calculate_technical_summary`（StockPriceDaily）、**5 分足**は `calculate_technical_summary_5m`（StockPrice5Min）。
- 5 分足の取得ロジックは `stocks/services/price_fetcher.fetch_and_save_5m_prices`。自動実行は management コマンド **`run_5m_fetch_and_evaluate`**（cron で 5 分毎に実行する想定）。
- 発報されたシグナルは **GET /api/v1/signals/recent/** で取得し、ダッシュボードの「直近のシグナル発報」に表示される。

## 望ましい姿

1. **リアルタイム監視・閾値超えで発報**
   - 現在の「手動で generate-signal を叩く」ではなく、**監視プロセスが定期的にスコアを計算し、閾値を超えたときだけシグナルを発報**する。
   - 長期・短期プロファイル: 日足ベースで 1 日 1 回程度の評価で十分。
   - デイトレプロファイル: 5 分足を監視し、**発報頻度を 1 日 1 回より増やす**（例: 5 分ごとや 1 分ごとの評価）。

2. **デイトレ時の 5 分足対応**
   - **5 分足**（StockPrice5Min）からテクニカルサマリを計算するロジックが必要。
   - `technical_analysis` を拡張するか、`technical_analysis_5m` のような別モジュールで 5 分足用の MA・高安・トレンド・出来高を算出する。
   - スコア計算（`signal_scoring.score_from_technical`）は日足用の重み・閾値をそのまま使うか、デイトレ用の別閾値を持つかはプロファイル設計次第。
   - TradingSignal は現在 **(stock, signal_date)** でユニーク＝1 銘柄 1 日 1 件。デイトレで 1 日に複数回発報する場合は **signal_datetime** を持つスキーマ拡張か、別テーブル（例: IntradaySignal）の検討が必要。

3. **デイトレの評価期間: 5 分足 N 本後**
   - その日終値で判定するのは不自然（夕方発報なら終値＝発報直後になってしまう）。**シグナル発報から 5 分足 N 本後**の価格で成否・リターンを評価するのが妥当。
   - 例: 発報から **6 本後（30 分）** の終値で return = (close - signal_price) / signal_price、買いなら return > 0 を成功とする。12 本（1 時間）、24 本（2 時間）なども選択肢。
   - 必要な拡張: シグナルに **発報日時（signal_datetime）** を持たせる、5 分足から「N 本後」の足を取得する評価ロジック、SignalOutcome に **return_5m_Nbars / success_5m_Nbars** のようなフィールドを追加。現状の日足 5d/10d/20d とは別軸でデイトレ用の outcome を蓄積する。

4. **運用イメージ**
   - バッチ or スケジューラ（cron / Celery beat 等）で以下を実行:
     - **長期・短期**: 日足で 1 日 1 回、全監視銘柄のスコアを計算し、閾値超えなら TradingSignal を update_or_create。
     - **デイトレ**: 5 分足で N 分ごとに全監視銘柄を評価し、閾値超えなら発報（同一日内で複数回可にする場合はスキーマ変更が必要）。
   - あるいは、フロントや外部システムが **短周期でポーリング**する API（例: GET /api/v1/signals/evaluate-all/ を 5 分ごとに叩く）を用意し、サーバ側で「全銘柄スコア計算 → 閾値超えのみ保存」を行う方法もある。

## 5 分毎の自動実行（cron 設定例）

- コマンド: `python manage.py run_5m_fetch_and_evaluate`
- 5 分毎に実行する例（cron）:
  ```bash
  */5 * * * * cd /path/to/project && python manage.py run_5m_fetch_and_evaluate
  ```
- 取得をスキップして既存 5 分足データだけで判定のみ行う: `--no-fetch`
- **クラウドで自動実行**（Vercel / Supabase / Docker）: HTTP エンドポイント `POST /api/v1/cron/run-5m-evaluate/` を 5 分毎に呼ぶ方式。詳細は [CRON_CLOUD.md](CRON_CLOUD.md) を参照。

## 実装タスク（TODO）

- [x] 5 分足用テクニカルサマリの算出（`technical_analysis.calculate_technical_summary_5m`）。
- [x] デイトレ用の高頻度発報: `TradingSignal.signal_datetime` 追加、同一日内複数シグナル対応（`generate_trading_signal_5m`）。
- [x] 5 分毎の「データ取得 → 判定」ジョブ（`run_5m_fetch_and_evaluate` と `price_fetcher.fetch_and_save_5m_prices`）。
- [ ] 日足ベースの「全銘柄評価し閾値超えで発報」ジョブ（management コマンド or API）の追加。
- [ ] **デイトレの評価**: シグナル発報から 5 分足 N 本後（例: 6 本＝30 分）の価格でリターン・成否を算出。5 分足 outcome（return_5m_Nbars 等）の追加。
- [ ] トレードスタイル（長期/短期/デイトレ）に応じた「どの resolution で・どの頻度で評価するか」の設定またはコード分岐。
