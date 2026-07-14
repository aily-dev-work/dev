# XServer Static への自動デプロイ

`main` に push すると、GitHub Actions が `summer-bodymake-navi/` を **XServer Static** へ FTPS でアップロードします。

- ワークフロー: [`.github/workflows/deploy-summer-bodymake-navi.yml`](../.github/workflows/deploy-summer-bodymake-navi.yml)
- 対象リポジトリ: `aily-dev-work/dev`（この monorepo）

## 1. XServer Static で FTP 情報を確認

1. [XServer Static](https://static.xserver.ne.jp/) にログイン
2. 対象サーバーの **サーバー設定** → **FTPアカウント**（または接続情報）を開く
3. 次を控える

| 項目 | 例 |
|------|-----|
| FTPホスト | `svXXXX.xserver.jp` など（管理画面の表記どおり） |
| FTPユーザー | 管理画面に表示されるユーザー名 |
| FTPパスワード | 管理画面で設定したもの |
| 公開ディレクトリ | 通常は `public_html` → Secrets では `/public_html/` |

## 2. GitHub Secrets を登録（必須）

リポジトリ [`aily-dev-work/dev`](https://github.com/aily-dev-work/dev) で:

**Settings → Secrets and variables → Actions → New repository secret**

| Secret 名 | 値 |
|-----------|-----|
| `FTP_HOST` | XServer Static の FTP ホスト名 |
| `FTP_USER` | FTP ユーザー名 |
| `FTP_PASS` | FTP パスワード |
| `FTP_REMOTE_DIR` | （任意）未設定なら `/public_html/`。末尾の `/` 推奨 |

## 3. 動作確認

1. `summer-bodymake-navi/` 配下を少し変更して `main` へ push  
   または Actions タブで **Deploy summer-bodymake-navi to XServer Static** → **Run workflow**
2. Actions が緑色（成功）になることを確認
3. https://mens-body.com/ で反映を確認

Secrets 未設定のときは **ジョブが失敗** します（気づきやすいようにしています）。

## ローカルから手動デプロイする場合

```powershell
cd D:\dev\summer-bodymake-navi
copy .deploy.env.example .deploy.env
# .deploy.env に FTP_HOST / FTP_USER / FTP_PASS を記入
powershell -ExecutionPolicy Bypass -File scripts\deploy-ftp.ps1
```

## 補足: XServer Static の「GitHub自動デプロイ」

管理画面の [GitHub自動デプロイ](https://static.xserver.ne.jp/support/manual/man_server_githubautodeploy.php) も使えます。  
ただしこのサイトは monorepo（`dev`）内の `summer-bodymake-navi/` だけなので、**リポジトリ全体を上げない**ため Actions（上記）を推奨します。
