# 株価監視アプリ フェーズ22: ScoreProfile フル一覧 API とフロント改善

## 1. フェーズ22の目的

フロントエンド MVP（フェーズ21）を、より実用的な運用画面にするために、
ScoreProfile のフル一覧取得 API を追加し、
profiles 画面と compare 画面の使い勝手を改善する。

### 背景

フェーズ21で Next.js のフロントエンド MVP を実装済み。
ただし現状の `/profiles` は、バックエンドに ScoreProfile のフル一覧 API が無いため、
ops-summary / review-targets ベースの「運用上重要な profile のみ表示」になっていた。

このため、

- 全 profile を確認しづらい
- compare 画面で profile 選択が不便
- current / candidate / derived profile を一覧的に扱いにくい

という課題があった。

---

## 2. バックエンド API

### 2.1 ScoreProfile 一覧

- エンドポイント: `GET /api/v1/score-profiles/`
- 実装: `ScoreProfileViewSet.list`

#### 返却項目

必須:

- `id`
- `name`
- `version`
- `is_active`
- `description`
- `weights_json`
- `thresholds_json`
- `created_at`
- `updated_at`

追加（proposal 由来 profile の逆引き）:

- `source_proposal_id`: この profile を生成した proposal の id（なければ null）
- `source_proposal_name`: 同上 proposal の proposal_name
- `source_proposal_status`: 同上 proposal の status

#### 並び順

`-is_active`（active を先頭）、`-updated_at`。

### 2.2 ScoreProfile 詳細

- エンドポイント: `GET /api/v1/score-profiles/<id>/`
- 実装: `ScoreProfileViewSet.retrieve`
- 一覧と同じ項目を単一オブジェクトで返す。404 は存在しない id の場合。

---

## 3. フロントエンド改善

### 3.1 `/profiles` 画面

- **変更前**: ops-summary ベースのサマリ画面（current / stale / underperforming / accepted-not-activated のみ）
- **変更後**: ScoreProfile フル一覧画面

列:

- id
- name
- version
- is_active
- description
- source proposal（リンク付き）
- created_at
- actions（Activate / Compare リンク）

- Activate ボタン: 既存と同様 `POST /api/v1/score-profiles/<id>/activate/`
- Compare リンク: `/profiles/compare?base=<id>` へ遷移

### 3.2 `/profiles/compare` 画面

- **変更前**: id 手入力
- **変更後**: profile 一覧 API を使ってプルダウン選択

- Base profile / Candidate profile を `<select>` で選択
- 各オプションに `name (version) [id=N]` と `[ACTIVE]` 表示
- Swap ボタンは維持
- Active profile を画面上部に分かりやすく表示（緑背景バッジ）
- URL クエリ `?base=<id>` で compare 画面に遷移した場合、base を事前選択

---

## 4. 型定義・API ラッパ

### 4.1 frontend/types/api.ts

- `ScoreProfileListItem`: 一覧 API の返却型
- `ScoreProfileDetail`: 詳細 API の返却型（一覧と同じ構造）

### 4.2 frontend/lib/api.ts

- `getScoreProfiles()`: `GET /api/v1/score-profiles/`
- `getScoreProfile(id)`: `GET /api/v1/score-profiles/<id>/`

---

## 5. 起動手順

1. バックエンド起動:

```powershell
cd d:\dev
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

2. フロントエンド起動:

```bash
cd d:\dev\frontend
npm install
npm run dev
```

3. ブラウザで `http://localhost:3000` を開く。

---

## 6. 動作確認手順

1. `GET /api/v1/score-profiles/` が 200 で一覧を返すこと。
2. フロント `/profiles` で全 profile が表示されること。
3. compare 画面でプルダウンから base / candidate を選択できること。
4. Activate 実行後、一覧表示が更新されること（active が切り替わる）。
5. `/profiles` の Compare リンクから `/profiles/compare?base=<id>` に遷移し、base が事前選択されていること。

---

## 7. テスト

### 7.1 ScoreProfileListAPITests

- `test_list_returns_200_and_all_profiles`: 一覧が 200 で全件返る
- `test_list_profile_from_proposal_has_source_proposal_info`: proposal 由来 profile に source_proposal_* が入る
- `test_list_profile_without_source_proposal_has_null_source_fields`: 非 proposal 由来は null
- `test_retrieve_returns_200_and_profile_detail`: 詳細が 200 で返る
- `test_retrieve_not_found_returns_404`: 存在しない id で 404

---

## 8. 注意点

- 既存 API（ops-summary, review-targets, compare, activate など）は変更していない。
- 認証・通知・グラフ・自動更新は今回追加していない。
- proposal / signal / outcome の API は変更していない。
