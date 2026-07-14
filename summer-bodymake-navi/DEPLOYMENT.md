# XServer Static への自動デプロイ

本番反映は **XServer Static の GitHub 連携** で行います（FTP は使いません）。

## 設定（管理画面）

| 項目 | 値 |
|------|-----|
| リポジトリ | `aily-dev-work/dev` |
| ブランチ | `main` |
| 公開ディレクトリ | `/summer-bodymake-navi` |

参考: [GitHub自動デプロイ](https://static.xserver.ne.jp/support/manual/man_server_githubautodeploy.php)

## 反映のしかた

1. `summer-bodymake-navi/` を変更する
2. `aily-dev-work/dev` の `main` に push する
3. XServer Static のデプロイ履歴と https://mens-body.com/ で反映を確認する

`dev` リポジトリの他フォルダだけの変更では、公開ディレクトリ外のためサイトには影響しません。
