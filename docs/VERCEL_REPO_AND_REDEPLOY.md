# Vercel でリポジトリ・ブランチの確認と Redeploy のやり方

---

## 1. どのリポジトリ・ブランチがデプロイされているか確認する

1. **https://vercel.com** にログインする。
2. 対象の **プロジェクト**（例: dev-beta-lake）をクリックして開く。
3. 上か左のメニューから **「Settings」** をクリックする。
4. 左のサブメニューで **「Git」** をクリックする。
5. 次の内容を確認する:
   - **Connected Git Repository** … 接続されているリポジトリ（例: `aily15s-projects/dev`）。
   - **Production Branch** … 本番デプロイに使うブランチ（例: `main` や `master`）。
   - ほかに **Preview Branches** の設定があれば、どのブランチがプレビューされるかもここで分かる。

「どのリポジトリのどのブランチがデプロイされているか」は、この **Settings → Git** で判断できる。

---

## 2. いまデプロイされているコミットを確認する（Redeploy されているか）

1. プロジェクトを開いた状態で、上か左のメニューから **「Deployments」** をクリックする。
2. 一覧の **いちばん上** が「直近のデプロイ」。
3. 各デプロイの行に次のような情報が出る:
   - **Status** … Ready / Building / Error など。
   - **Commit** … どのコミットがデプロイされたか（コミットメッセージの先頭）。
   - **Branch** … どのブランチからデプロイされたか。
   - **Created** … いつデプロイされたか。

「Redeploy されているか」は、**Deployments の一番上の Created が「ルートビューを追加したコミットを push したあと」になっているか**で判断する。  
そのコミットが一覧の一番上にあり、Status が **Ready** なら、その内容で Redeploy 済み。

---

## 3. 手動で Redeploy する

1. **Deployments** を開く。
2. デプロイ一覧の **右端の「…」（三点メニュー）** をクリックする。
3. **「Redeploy」** を選ぶ。
4. 確認ダイアログで **「Redeploy」** を押す。

これで「その時点で Vercel が参照している Git の最新コミット」で再デプロイされる。  
Redeploy 後は、一覧の一番上に新しいデプロイが並び、Status が **Ready** になれば反映完了。

---

## 4. ローカルで「どのブランチで、変更が push されているか」を確認する（Git）

Vercel は「接続したリポジトリの特定ブランチ」の最新コミットをデプロイする。  
そのため、**ルートビューを追加した変更が、そのブランチに push されているか**をローカルで確認するとよい。

1. **ターミナル**でプロジェクトのルート（`D:\dev`）に移動する。
2. 現在のブランチを確認する:
   ```bash
   git branch
   ```
   現在いるブランチの先頭に `*` が付く。
3. 変更がコミットされているか確認する:
   ```bash
   git status
   ```
   `webapp/urls.py` が **Changes not staged** や **Untracked** なら、まだコミットされていない。
4. リモートに push されているか確認する:
   ```bash
   git log origin/main -1
   ```
   （ブランチが `main` でない場合は `origin/マスターブランチ名` に置き換える。）  
   ここに「ルートビューを追加したコミット」が含まれていれば、そのブランチには push 済み。

**まだコミット・push していない場合の例:**

```bash
git add webapp/urls.py
git commit -m "Add root view for /"
git push origin main
```

（実際のブランチ名が `master` なら `git push origin master`。）

---

## 5. まとめ

| 確認したいこと | 見る場所（Vercel） |
|----------------|---------------------|
| どのリポジトリ・ブランチがデプロイされているか | **Settings → Git** |
| いまどのコミットでデプロイされているか / Redeploy されたか | **Deployments** の一覧（一番上のコミット・日時） |
| 手動で再デプロイしたい | **Deployments** → 対象の「…」→ **Redeploy** |

| 確認したいこと | やること（ローカル） |
|----------------|----------------------|
| どのブランチにいるか | `git branch` |
| 変更がコミット・push されているか | `git status`、`git log origin/ブランチ名 -1` |
| まだなら push する | `git add` → `git commit` → `git push origin ブランチ名` |

Vercel の **Settings → Git** に「Git の接続先」の記載が無い場合は、そのプロジェクトは **Git 連携ではなく手動アップロード**で作られている可能性がある。そのときは、Vercel の「Import」で改めてリポジトリを指定し直すか、ドキュメントの「Deploy without Git」を参照する。
