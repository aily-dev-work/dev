# webapp（Django プロジェクト）

個人用 Web アプリの開発基盤。Django 6 + Django REST Framework、SQLite（開発）、将来 MariaDB 対応を想定。

## 必要な環境

- Python 3.12+
- （任意）Docker / Docker Compose

## ローカル開発（仮想環境）

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # 未導入時のみ
python manage.py migrate
python manage.py runserver
```

- 管理画面: http://127.0.0.1:8000/admin/
- 認証 URL: `/accounts/login/`, `/accounts/logout/` など（ログイン後は `/admin/` にリダイレクト）

**初回のみ** 管理者ユーザを作成:

```powershell
python manage.py createsuperuser
```

## Docker で起動

（Docker がインストール済みで PATH に通っている場合）

```powershell
cd d:\dev
docker compose up --build
```

初回は `migrate` が自動実行され、続けて runserver が起動します。  
ブラウザで http://127.0.0.1:8000/admin/ を開き、管理者が未作成ならコンテナ内で:

```powershell
docker compose exec web python manage.py createsuperuser
```

### Docker での stocks 機能の確認

コンテナ起動後、以下をブラウザから確認できます。

- `http://127.0.0.1:8000/api/v1/stocks/` にアクセスし、JSON で一覧が取得できること
- `http://127.0.0.1:8000/admin/` にアクセスし、管理画面のメニューに「監視銘柄 (WatchStock)」が表示されること

## 主な設定

- **言語・タイムゾーン**: `ja` / `Asia/Tokyo`
- **DB**: 開発は SQLite。MariaDB に切り替える場合は環境変数 `DJANGO_DB_ENGINE=mysql` と `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` を設定。
- **認証**: Django 標準の認証。ログイン後のリダイレクト先は `/admin/`。
- **DRF**: 導入済み。API 設計・アプリ分割は今後追加。

## stocks アプリ（株価監視フェーズ1）

**フェーズ1の進捗まとめ（目的・実装内容・手順・API例）**: [stocks/PHASE1.md](stocks/PHASE1.md)

※ 現時点（フェーズ1）では、認証・権限制御は未実装で、最小限の CRUD API のみ提供しています。

- アプリ名: `stocks`
- モデル: `WatchStock`
  - `ticker` (str, 必須, 一意)
  - `name` (str, 必須)
  - `market` (str, 任意)
  - `is_active` (bool, デフォルト True)
  - `memo` (text, 任意)
  - `created_at`, `updated_at`
- 管理画面: Django Admin から「監視銘柄」を一覧・登録・編集可能
  - 一覧: `ticker`, `name`, `market`, `is_active`, `updated_at` を表示
  - 検索: `ticker`, `name`
  - 絞り込み: `is_active`, `market`
- API: Django REST Framework + ViewSet + Router
  - エンドポイント: `/api/v1/stocks/`
  - 提供機能: 一覧取得 / 詳細取得 / 登録 / 更新 / 削除（CRUD）

### マイグレーション手順

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py makemigrations stocks
python manage.py migrate
```

（このリポジトリでは既に `stocks` の初回マイグレーションは実行済み）

### 起動確認手順

1. 仮想環境を有効化し、開発サーバを起動:

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

2. 管理画面で確認:
   - ブラウザで `http://127.0.0.1:8000/admin/` を開く
   - 「監視銘柄 (WatchStock)」メニューから、銘柄の登録・編集・削除ができることを確認

3. API で確認（例: PowerShell / curl）

- 一覧取得:

```powershell
curl http://127.0.0.1:8000/api/v1/stocks/
```

- 登録 (POST):

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/stocks/ `
  -H "Content-Type: application/json" `
  -d "{`"ticker`":`"7203.T`",`"name`":`"トヨタ自動車`",`"market`":`"JP`"}"
```

- 詳細取得 (id=1 の例):

```powershell
curl http://127.0.0.1:8000/api/v1/stocks/1/
```

- 更新 (PUT の例):

```powershell
curl -X PUT http://127.0.0.1:8000/api/v1/stocks/1/ `
  -H "Content-Type: application/json" `
  -d "{`"ticker`":`"7203.T`",`"name`":`"トヨタ自動車`",`"market`":`"TSE`",`"is_active`":true}"
```

- 削除:

```powershell
curl -X DELETE http://127.0.0.1:8000/api/v1/stocks/1/
```

## プロジェクト構成

```
d:\dev\
  .venv/              # 仮想環境
  .git/
  .gitignore
  .dockerignore
  Dockerfile
  docker-compose.yml
  manage.py
  requirements.txt
  webapp/             # 設定パッケージ
    settings.py
    urls.py
    wsgi.py
    asgi.py
  stocks/             # 株価監視アプリ（フェーズ1〜22）
    models.py         # WatchStock, StockPriceDaily, TradingSignal, SignalOutcome, ScoreProfile, ScoreProfileProposal, ScoreProfileActivationHistory
    admin.py          # Admin for all models
    views.py          # ViewSets（stocks, stock-prices, signals）
    serializers.py    # WatchStockSerializer, StockPriceDailySerializer
    urls.py           # /api/v1/stocks/, /api/v1/stock-prices/, /api/v1/signals/
    services/
      technical_analysis.py    # テクニカル指標計算ロジック
      signal_scoring.py        # 買い/売りスコア計算ロジック（ScoreProfile を参照）
      signal_generation.py     # TradingSignal 生成
      signal_evaluation.py     # SignalOutcome 評価
      scoring_profile.py       # ScoreProfile からスコア設定を取得
      signal_dataset.py        # TradingSignal + SignalOutcome のフラットデータ
      signal_summary.py        # ScoreProfile / signal_type 別 summary 集計
      analysis_package.py      # AI 分析入力パッケージ構築
      ai_profile_review.py     # ScoreProfile の AI レビュー（提案のみ、OpenAI 連携）
      profile_proposal.py      # AI レビュー結果を ScoreProfileProposal として保存
      profile_apply.py         # accepted proposal から新しい ScoreProfile を生成
      profile_activation.py    # ScoreProfile の active 切替
      profile_rollback.py      # ScoreProfile の手動ロールバック（直前へ戻す）
      profile_review_targets.py  # レビュー対象の抽出（review-targets API 用）
      profile_comparison.py      # active と候補 profile の比較（compare API 用）
    PHASE1.md         # フェーズ1まとめ
    PHASE2.md         # フェーズ2まとめ
    PHASE3.md         # フェーズ3まとめ
    PHASE4.md         # フェーズ4まとめ
    PHASE5.md         # フェーズ5まとめ
    PHASE6.md         # フェーズ6まとめ
    PHASE7.md         # フェーズ7まとめ（シグナル + 結果のフラットデータセット）
    PHASE8.md         # フェーズ8まとめ（スコア設定の外部化）
    PHASE9.md         # フェーズ9まとめ（TradingSignal と ScoreProfile のひも付け）
    PHASE10.md        # フェーズ10まとめ（ScoreProfile 別シグナル集計 API）
    PHASE11.md        # フェーズ11まとめ（AI 分析入力パッケージ API）
    PHASE12.md        # フェーズ12まとめ（ScoreProfile AI レビュー API）
    PHASE13.md        # フェーズ13まとめ（AI 提案の保存 API）
    PHASE14.md        # フェーズ14まとめ（proposal レビュー管理 API）
    PHASE15.md        # フェーズ15まとめ（accepted proposal から ScoreProfile 生成）
    PHASE16.md        # フェーズ16まとめ（ScoreProfile 手動 activation）
    PHASE17.md        # フェーズ17まとめ（ScoreProfile activation 履歴管理）
    PHASE18.md        # フェーズ18まとめ（ScoreProfile 手動ロールバック）
    PHASE19.md        # フェーズ19まとめ（運用補助 API: review-targets / compare）
    PHASE20.md        # フェーズ20まとめ（運用サマリ API: ops-summary）
    PHASE21.md        # フェーズ21まとめ（フロントエンド MVP）
    PHASE22.md        # フェーズ22まとめ（ScoreProfile フル一覧 API とフロント改善）
    migrations/
      0001_initial.py
      0002_stockpricedaily.py
      0003_tradingsignal.py
      0004_tradingsignal_technical_position.py
      0005_signaloutcome.py
      0006_scoreprofile.py
  db.sqlite3          # 開発用 DB（作成後）
```

アプリケーションは後から `python manage.py startapp <app_name>` で追加してください。
