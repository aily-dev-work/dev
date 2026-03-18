"use client";

import Link from "next/link";
import { useState } from "react";

export function NavBar() {
  const [open, setOpen] = useState(false);

  const toggle = () => setOpen((v) => !v);
  const close = () => setOpen(false);

  return (
    <div className="flex items-center justify-between gap-2">
      <Link href="/" className="text-lg font-semibold">
        株価スコア管理
      </Link>
      {/* デスクトップ: 通常ナビ */}
      <nav className="hidden md:flex gap-4 text-sm">
        <Link href="/" onClick={close}>
          ダッシュボード
        </Link>
        <Link href="/stocks" onClick={close}>
          銘柄ウォッチリスト
        </Link>
        <Link href="/profiles" onClick={close}>
          プロファイル一覧
        </Link>
        <Link href="/proposals" onClick={close}>
          AI改善提案
        </Link>
        <Link href="/history" onClick={close}>
          プロファイル変更履歴
        </Link>
        <Link href="/help" className="text-slate-500 hover:text-slate-700" onClick={close}>
          使い方
        </Link>
      </nav>
      {/* モバイル: ハンバーガー */}
      <div className="md:hidden">
        <button
          type="button"
          onClick={toggle}
          aria-label="メニュー"
          className="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-slate-700 shadow-sm hover:bg-slate-50"
        >
          <span className="sr-only">メニューを開閉</span>
          <span className="flex flex-col gap-0.5">
            <span className="block h-0.5 w-5 rounded bg-slate-700" />
            <span className="block h-0.5 w-5 rounded bg-slate-700" />
            <span className="block h-0.5 w-5 rounded bg-slate-700" />
          </span>
        </button>
      </div>
      {open && (
        <div className="absolute inset-x-0 top-full z-20 mt-2 border-b border-t border-slate-200 bg-white md:hidden">
          <nav className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-2 text-sm">
            <Link href="/" onClick={close} className="rounded px-2 py-1 hover:bg-slate-100">
              ダッシュボード
            </Link>
            <Link href="/stocks" onClick={close} className="rounded px-2 py-1 hover:bg-slate-100">
              銘柄ウォッチリスト
            </Link>
            <Link href="/profiles" onClick={close} className="rounded px-2 py-1 hover:bg-slate-100">
              プロファイル一覧
            </Link>
            <Link href="/proposals" onClick={close} className="rounded px-2 py-1 hover:bg-slate-100">
              AI改善提案
            </Link>
            <Link href="/history" onClick={close} className="rounded px-2 py-1 hover:bg-slate-100">
              プロファイル変更履歴
            </Link>
            <Link
              href="/help"
              onClick={close}
              className="rounded px-2 py-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
            >
              使い方
            </Link>
          </nav>
        </div>
      )}
    </div>
  );
}

