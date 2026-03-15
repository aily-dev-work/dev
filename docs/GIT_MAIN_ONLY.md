# main だけにする手順（master を削除）

---

## 1. GitHub でデフォルトブランチを main に変更する（必須・先にやる）

1. **https://github.com/aily15/dev** を開く。
2. リポジトリの **Settings** タブをクリックする。
3. 左の **General** を開く。
4. 一番上の **Default branch** の右にある **Switch to another branch** またはブランチ名（master）をクリックする。
5. 一覧から **main** を選び、**Update** をクリックする。
6. 確認が出たら **I understand, update the default branch.** を押す。

これで GitHub のデフォルトが main になる。**このあとでないと、次の「master 削除」はできない。**

---

## 2. リモートの master を削除する

GitHub でデフォルトを main にしたあと、ローカルで実行:

```powershell
git push origin --delete master
```

---

## 3. ローカルの master を削除する

```powershell
git branch -d master
```

（main にマージ済みなら `-d` で消える。消えない場合は `git branch -D master` で強制削除。）

---

## 4. 今後の運用

- 常に **main** で作業する: `git checkout main`
- 変更を送る: `git push origin main`
- Vercel の **Production Branch** を **main** にしておく。

これで main だけの構成になる。
