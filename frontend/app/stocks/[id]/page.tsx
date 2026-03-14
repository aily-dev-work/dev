"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getStock, updateStock } from "@/lib/api";
import type { WatchStock } from "@/types/api";

export default function StockEditPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);

  const [stock, setStock] = useState<WatchStock | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    ticker: "",
    name: "",
    market: "",
    is_active: true,
    memo: "",
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const s = await getStock(id);
      setStock(s);
      setForm({
        ticker: s.ticker,
        name: s.name,
        market: s.market ?? "",
        is_active: s.is_active,
        memo: s.memo ?? "",
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!Number.isNaN(id)) {
      void load();
    }
  }, [id]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.ticker.trim() || !form.name.trim()) {
      setError("ティッカーと銘柄名は必須です。");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateStock(id, {
        ticker: form.ticker.trim(),
        name: form.name.trim(),
        market: form.market.trim(),
        is_active: form.is_active,
        memo: form.memo.trim(),
      });
      router.push("/stocks");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (Number.isNaN(id)) {
    return (
      <div className="space-y-4">
        <p>無効な銘柄 ID です。</p>
        <Link href="/stocks" className="text-blue-600 hover:underline">一覧へ戻る</Link>
      </div>
    );
  }

  if (loading) {
    return <p className="text-sm text-slate-600">読み込み中...</p>;
  }

  if (!stock) {
    return (
      <div className="space-y-4">
        <p>銘柄が見つかりません。</p>
        <Link href="/stocks" className="text-blue-600 hover:underline">一覧へ戻る</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/stocks" className="text-sm text-slate-600 hover:text-slate-900">
          ← 一覧へ
        </Link>
        <h1 className="text-2xl font-semibold">銘柄の編集: {stock.ticker}</h1>
      </div>
      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="max-w-lg space-y-4 rounded-lg border bg-white p-4 shadow-sm">
        <label className="block">
          <span className="text-sm font-medium text-slate-700">ティッカー *</span>
          <input
            type="text"
            value={form.ticker}
            onChange={(e) => setForm((f) => ({ ...f, ticker: e.target.value }))}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">銘柄名 *</span>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">市場</span>
          <input
            type="text"
            value={form.market}
            onChange={(e) => setForm((f) => ({ ...f, market: e.target.value }))}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5"
          />
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
          />
          <span className="text-sm font-medium text-slate-700">監視中</span>
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">メモ</span>
          <textarea
            value={form.memo}
            onChange={(e) => setForm((f) => ({ ...f, memo: e.target.value }))}
            rows={3}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5"
          />
        </label>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
          >
            {saving ? "保存中..." : "保存"}
          </button>
          <Link
            href="/stocks"
            className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            キャンセル
          </Link>
        </div>
      </form>
    </div>
  );
}
