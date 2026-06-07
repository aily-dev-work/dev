# premium_monitor

ローカル環境で動作する「プレ値前兆検知システム」のテスト版です。  
RSS または通常の HTML ページを巡回し、以下のキーワードを検知してスコア化します。

- 限定
- 受注終了
- 生産終了
- 再販なし
- 再販未定
- 抽選販売
- 完売
- 在庫切れ
- 販売終了
- 予約終了

`total_score >= 50` でアラート、`80以上` で強い警告として表示します。

## ファイル構成

```text
premium_monitor/
├─ manage.py
├─ premium_monitor/
│  ├─ settings.py
│  ├─ urls.py
│  ├─ asgi.py
│  └─ wsgi.py
├─ signals/
│  ├─ models.py
│  ├─ views.py
│  ├─ services.py
│  ├─ forms.py
│  ├─ admin.py
│  ├─ urls.py
│  ├─ templates/signals/
│  └─ management/commands/
├─ templates/
│  └─ base.html
└─ requirements.txt
```

## 概要

- 監視サイトを登録できます
- RSS / HTML を巡回できます
- 登録済みキーワードを検知してスコアを計算します
- Django の画面で一覧・詳細・登録画面を確認できます
- 管理画面からもデータを管理できます

## セットアップ手順

### 1. 仮想環境を作成

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. 依存パッケージをインストール

```powershell
pip install -r requirements.txt
```

### 3. マイグレーションを適用

```powershell
python manage.py makemigrations signals
python manage.py migrate
```

### 4. 管理ユーザーを作成

```powershell
python manage.py createsuperuser
```

### 5. 初期キーワードを投入

```powershell
python manage.py seed_keywords
```

### 6. サーバーを起動

```powershell
python manage.py runserver
```

## 使い方

### 1. 監視サイトを登録

- `http://127.0.0.1:8000/sources/new/`
- `name`
- `url`
- `source_type` (`rss` または `html`)
- `is_active`

### 2. キーワードを確認

- `http://127.0.0.1:8000/keywords/`

### 3. 巡回を実行

```powershell
python manage.py fetch_signals
```

- 有効な監視サイトだけを巡回します
- RSS は `feedparser`
- HTML は `requests + BeautifulSoup`
- キーワードが見つかった記事だけ `DetectedItem` に保存します
- 同じ URL は重複登録しません

### 4. 検知結果を見る

- `http://127.0.0.1:8000/`
- タイトル
- サイト名
- 検知キーワード
- スコア
- アラート判定
- 詳細リンク

### 5. 詳細を見る

- `http://127.0.0.1:8000/items/<id>/`

### 6. 管理画面

- `http://127.0.0.1:8000/admin/`
- `WatchSource`
- `SignalKeyword`
- `DetectedItem`

## 動作確認手順

1. `python manage.py seed_keywords` を実行する
2. `/sources/new/` から RSS または HTML の URL を登録する
3. `python manage.py fetch_signals` を実行する
4. `/` を開き、検知記事が表示されることを確認する
5. `total_score >= 50` の記事がアラート表示になることを確認する

## 今後の拡張案

- ページネーション対応
- キーワードの重み付けルール拡張
- 巡回履歴の保存
- robots.txt とアクセス間隔の制御
- メール通知や Slack 通知
- キーワードのグルーピング
- 管理画面での一括編集
