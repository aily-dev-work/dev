import "./globals.css";
import type { ReactNode } from "react";
import Link from "next/link";
import { AutoFetchPrices } from "./components/AutoFetchPrices";

export const metadata = {
  title: "株価スコア管理",
  description: "スコアプロファイル管理ダッシュボード",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body className="min-h-screen flex flex-col">
        <AutoFetchPrices />
        <header className="border-b bg-white">
          <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
            <Link href="/" className="text-lg font-semibold">
              株価スコア管理
            </Link>
            <nav className="flex gap-4 text-sm">
              <Link href="/">ダッシュボード</Link>
              <Link href="/stocks">銘柄ウォッチリスト</Link>
              <Link href="/profiles">プロファイル一覧</Link>
              <Link href="/proposals">AI改善提案</Link>
              <Link href="/history">プロファイル変更履歴</Link>
              <Link href="/help" className="text-slate-500 hover:text-slate-700">使い方</Link>
            </nav>
          </div>
        </header>
        <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}

