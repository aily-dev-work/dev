export default function HelpPage() {
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">使い方</h1>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold border-b pb-1">このアプリについて</h2>
        <p className="text-sm text-slate-700">
          株価シグナル用の「スコアプロファイル」を管理する画面です。
          どのプロファイルを「今の計算に使うか」の切り替え、提案の確認・反映、有効化の履歴確認ができます。
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold border-b pb-1">起動のしかた</h2>
        <ol className="list-decimal list-inside space-y-1 text-sm text-slate-700">
          <li>
            <strong>バックエンド</strong>（Django）を起動する。
            <pre className="mt-1 rounded bg-slate-100 p-2 text-xs overflow-x-auto">
              cd d:\\dev{"\n"}
              .\\.venv\\Scripts\\Activate.ps1{"\n"}
              python manage.py runserver
            </pre>
          </li>
          <li>
            <strong>フロント</strong>（この画面）を起動する。
            <pre className="mt-1 rounded bg-slate-100 p-2 text-xs overflow-x-auto">
              cd d:\\dev\\frontend{"\n"}
              npm run dev
            </pre>
          </li>
          <li>
            ブラウザで <strong>http://localhost:3000</strong> を開く。
          </li>
        </ol>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold border-b pb-1">画面ごとの使い方</h2>

        <div className="rounded border bg-slate-50 p-4 space-y-2">
          <h3 className="font-semibold">ダッシュボード（トップ）</h3>
          <ul className="list-disc list-inside text-sm text-slate-700 space-y-1">
            <li>「現在のアクティブプロファイル」が、今の計算に使われているプロファイルです。</li>
            <li>「直前のプロファイルにロールバック」で、ひとつ前のプロファイルに戻せます。</li>
            <li>運用サマリ（古いアクティブ・成績不振・採用済み未反映の件数）とグラフで状況を確認できます。</li>
            <li>直近の有効化履歴のテーブルで、いつ誰が（何が）切り替えたかを見られます。</li>
          </ul>
        </div>

        <div className="rounded border bg-slate-50 p-4 space-y-2">
          <h3 className="font-semibold">プロファイル</h3>
          <ul className="list-disc list-inside text-sm text-slate-700 space-y-1">
            <li>登録されているスコアプロファイルの<strong>一覧</strong>です。</li>
            <li><strong>「アクティブにする」</strong>を押すと、そのプロファイルが「今の計算に使うプロファイル」に切り替わります。</li>
            <li><strong>「比較」</strong>を押すと、比較画面に飛び、そのプロファイルをベースに別のプロファイルと比較できます。</li>
          </ul>
        </div>

        <div className="rounded border bg-slate-50 p-4 space-y-2">
          <h3 className="font-semibold">比較</h3>
          <ul className="list-disc list-inside text-sm text-slate-700 space-y-1">
            <li><strong>ベース</strong>と<strong>候補</strong>の2つのプロファイルをプルダウンで選び、「比較する」を押します。</li>
            <li>シグナル種別ごとの件数・成功率・平均リターン（H5/H10/H20）の違いが表とグラフで出ます。</li>
            <li>どちらをアクティブにするか判断するときの参考にしてください。</li>
          </ul>
        </div>

        <div className="rounded border bg-slate-50 p-4 space-y-2">
          <h3 className="font-semibold">提案</h3>
          <ul className="list-disc list-inside text-sm text-slate-700 space-y-1">
            <li>AI などから保存された「スコア改善提案」の一覧です。</li>
            <li>一覧の<strong>「表示」</strong>で詳細を開きます。</li>
            <li>詳細で<strong>状態（draft / reviewed / accepted / rejected）</strong>や<strong>レビューメモ</strong>を変えられます。「レビューを保存」で保存。</li>
            <li>状態が<strong>accepted</strong>のときだけ<strong>「提案を反映」</strong>が押せます。押すと、その提案内容で新しいスコアプロファイルが1件作成され、一覧に増えます（この時点ではアクティブにはなりません）。</li>
          </ul>
        </div>

        <div className="rounded border bg-slate-50 p-4 space-y-2">
          <h3 className="font-semibold">履歴</h3>
          <ul className="list-disc list-inside text-sm text-slate-700 space-y-1">
            <li>「いつ・どのプロファイルから・どのプロファイルに切り替えたか」の一覧です。</li>
            <li>理由（manual_activate / manual_rollback など）や、有効化したプロファイル ID で絞り込めます。</li>
          </ul>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold border-b pb-1">よくある流れ（例）</h2>
        <ol className="list-decimal list-inside space-y-2 text-sm text-slate-700">
          <li>
            <strong>今どれが使われているか確認</strong> → ダッシュボードの「現在のアクティブプロファイル」を見る。
          </li>
          <li>
            <strong>別のプロファイルに切り替えたい</strong> → 「プロファイル」で一覧から選び、「アクティブにする」を押す。
          </li>
          <li>
            <strong>切り替えをやめて戻したい</strong> → ダッシュボードの「直前のプロファイルにロールバック」を押す。
          </li>
          <li>
            <strong>2つのプロファイルの成績を比べたい</strong> → 「比較」でベースと候補を選んで「比較する」。
          </li>
          <li>
            <strong>提案を採用して新しいプロファイルを作りたい</strong> → 「提案」で該当提案の詳細を開き、状態を accepted にして「レビューを保存」→「提案を反映」。その後「プロファイル」一覧で新しいプロファイルに「アクティブにする」。
          </li>
        </ol>
      </section>

      <section className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-600">
        <p>
          バックエンドが止まっていると「読み込み中」のままになったりエラーになります。そのときは Django の <code className="rounded bg-slate-100 px-1">runserver</code> が動いているか確認してください。
        </p>
      </section>
    </div>
  );
}
