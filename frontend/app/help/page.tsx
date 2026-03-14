export default function HelpPage() {
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">使い方</h1>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold border-b pb-1">このアプリについて</h2>
        <p className="text-sm text-slate-700">
          株価シグナル用の「スコアプロファイル」を管理する画面です。
          ダッシュボードで監視銘柄のスコア（買い・売り・様子見、長期・短期トレンド）やシグナル発報を確認し、
          プロファイル一覧で「今の計算に使うプロファイル」を切り替え、AI改善提案の生成・反映、プロファイル変更履歴の確認ができます。
        </p>
        <p className="text-sm font-medium text-slate-800">
          管理操作はすべて <strong>http://localhost:3000</strong> から行えます。銘柄ウォッチリスト・プロファイル・提案・履歴をこの画面で一覧・追加・編集・削除できます。
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
            <li><strong>使用中プロファイル</strong>で、今のスコア計算に使われているプロファイル名を確認できます。成績が「良好」または「要見直し」で表示されます。</li>
            <li><strong>直近のシグナル発報</strong>で、発報日時・銘柄・シグナル（買い/売り/様子見）・強さ・価格を一覧できます。</li>
            <li><strong>監視銘柄のスコア</strong>で、各銘柄の買い％・売り％・様子見％・現在の判定（買い/売り/様子見と強さ）・長期トレンド・短期トレンドを確認できます。いずれも使用中プロファイルで算出された値です。</li>
            <li><strong>プロファイル成功率</strong>と<strong>プロファイル平均リターン</strong>のグラフで、各プロファイルの成績を比較できます。評価期間はプロファイルのトレードスタイル（デイトレ=5営業日・短期=10営業日・長期=20営業日）に応じて変わります。</li>
          </ul>
        </div>

        <div className="rounded border bg-slate-50 p-4 space-y-2">
          <h3 className="font-semibold">銘柄ウォッチリスト</h3>
          <ul className="list-disc list-inside text-sm text-slate-700 space-y-1">
            <li>監視したい<strong>銘柄</strong>をここで管理します。</li>
            <li>「市場の銘柄を検索」で銘柄コードや銘柄名を入力し、検索結果から<strong>監視リストに追加</strong>できます。</li>
            <li>登録済み銘柄一覧で、銘柄コード・銘柄名・市場・メモを確認できます。</li>
            <li>各行の<strong>チャート</strong>で価格グラフ、<strong>価格</strong>で価格データの一覧・追加、<strong>編集</strong>で銘柄情報の変更、<strong>削除</strong>で監視リストから外せます。</li>
          </ul>
        </div>

        <div className="rounded border bg-slate-50 p-4 space-y-2">
          <h3 className="font-semibold">プロファイル一覧</h3>
          <ul className="list-disc list-inside text-sm text-slate-700 space-y-1">
            <li>登録されている<strong>スコアプロファイル</strong>の一覧です。使用中・名前・説明・設定（重み）・操作が表示されます。</li>
            <li><strong>「使用する」</strong>を押すと、そのプロファイルが「今の計算に使うプロファイル」に切り替わります。使用中は「使用中」バッジで表示されます。</li>
            <li><strong>新規作成</strong>で新しいプロファイルを追加できます。<strong>編集</strong>で名前・説明・重み・閾値・トレードスタイル（長期/短期/デイトレ）を変更できます。使用中でないプロファイルは削除可能です。</li>
          </ul>
        </div>

        <div className="rounded border bg-slate-50 p-4 space-y-2">
          <h3 className="font-semibold">AI改善提案</h3>
          <ul className="list-disc list-inside text-sm text-slate-700 space-y-1">
            <li>現在使用中のプロファイルを対象に、<strong>AI で改善提案を生成して保存</strong>できます。トレードスタイル（長期/短期/デイトレ）を選んでから「生成して保存」を押します。</li>
            <li>保存された提案の一覧で、名前・状態・作成日時・改善対象プロファイル・反映プロファイル・提案内容詳細を確認できます。<strong>「表示」</strong>で詳細を開きます。</li>
            <li>詳細画面で<strong>状態（draft / reviewed / accepted / rejected）</strong>や<strong>レビューメモ</strong>を変更し「レビューを保存」できます。</li>
            <li>状態が<strong>accepted</strong>のとき<strong>「提案を反映」</strong>を押すと、提案内容で新しいスコアプロファイルが作成され、プロファイル一覧に追加されます（この時点では使用中にはなりません）。</li>
          </ul>
        </div>

        <div className="rounded border bg-slate-50 p-4 space-y-2">
          <h3 className="font-semibold">プロファイル変更履歴</h3>
          <ul className="list-disc list-inside text-sm text-slate-700 space-y-1">
            <li>「いつ・どのプロファイルから・どのプロファイルに切り替えたか」の<strong>有効化履歴</strong>です。</li>
            <li>有効化日時・理由・直前プロファイル・有効化後プロファイル・メモを一覧できます。</li>
            <li>プロファイル名で絞り込みができます。不要な履歴は行の<strong>「削除」</strong>で削除できます。</li>
          </ul>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold border-b pb-1">よくある流れ（例）</h2>
        <ol className="list-decimal list-inside space-y-2 text-sm text-slate-700">
          <li>
            <strong>今どれが使われているか確認</strong> → ダッシュボードの「使用中プロファイル」を見る。
          </li>
          <li>
            <strong>別のプロファイルに切り替えたい</strong> → 「プロファイル一覧」で一覧から選び、「使用する」を押す。
          </li>
          <li>
            <strong>提案を採用して新しいプロファイルを作りたい</strong> → 「AI改善提案」で該当提案の詳細を開き、状態を accepted にして「レビューを保存」→「提案を反映」。その後「プロファイル一覧」で新しいプロファイルの「使用する」を押す。
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
