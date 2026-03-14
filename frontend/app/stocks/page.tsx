"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getStocks, createStock, deleteStock } from "@/lib/api";
import type { WatchStock } from "@/types/api";

export default function StocksPage() {
  const [rows, setRows] = useState<WatchStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
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
      const list = await getStocks();
      setRows(list);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.ticker.trim() || !form.name.trim()) {
      setError("ティッカーと銘柄名は必須です。");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createStock({
        ticker: form.ticker.trim(),
        name: form.name.trim(),
        market: form.market.trim() || undefined,
        is_active: form.is_active,
        memo: form.memo.trim() || undefined,
      });
      setForm({ ticker: "", name: "", market: "", is_active: true, memo: "" });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number, ticker: string) {
    if (!confirm(`「${ticker}」を監視リストから削除しますか？`)) return;
    setDeletingId(id);
    setError(null);
    try {
      await deleteStock(id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">監視銘柄</h1>
      <p className="text-sm text-slate-600">
        監視したい企業（銘柄）をここで追加・編集・削除できます。
      </p>
      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}

      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">新規追加</h2>
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span>ティッカー *</span>
            <input
              type="text"
              value={form.ticker}
              onChange={(e) => setForm((f) => ({ ...f, ticker: e.target.value }))}
              placeholder="例: 7203.T"
              className="rounded border border-slate-300 px-2 py-1.5 w-28"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span>銘柄名 *</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="例: トヨタ自動車"
              className="rounded border border-slate-300 px-2 py-1.5 w-40"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span>市場</span>
            <input
              type="text"
              value={form.market}
              onChange={(e) => setForm((f) => ({ ...f, market: e.target.value }))}
              placeholder="例: JP, TSE"
              className="rounded border border-slate-300 px-2 py-1.5 w-24"
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
            />
            <span>監視中</span>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span>メモ</span>
            <input
              type="text"
              value={form.memo}
              onChange={(e) => setForm((f) => ({ ...f, memo: e.target.value }))}
              placeholder="任意"
              className="rounded border border-slate-300 px-2 py-1.5 w-48"
            />
          </label>
          <button
            type="submit"
            disabled={submitting}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
          >
            {submitting ? "追加中..." : "追加"}
          </button>
        </form>
      </section>

      {loading && <p className="text-sm text-slate-600">読み込み中...</p>}
      <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="border px-2 py-1 text-left">ティッカー</th>
              <th className="border px-2 py-1 text-left">銘柄名</th>
              <th className="border px-2 py-1 text-left">市場</th>
              <th className="border px-2 py-1 text-left">監視中</th>
              <th className="border px-2 py-1 text-left">メモ</th>
              <th className="border px-2 py-1 text-left">更新日</th>
              <th className="border px-2 py-1 text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr
                key={s.id}
                className={s.is_active ? "bg-emerald-50" : "odd:bg-slate-50"}
              >
                <td className="border px-2 py-1 font-mono">{s.ticker}</td>
                <td className="border px-2 py-1 font-medium">{s.name}</td>
                <td className="border px-2 py-1">{s.market || "-"}</td>
                <td className="border px-2 py-1">{s.is_active ? "はい" : "いいえ"}</td>
                <td className="max-w-[180px] truncate border px-2 py-1 text-slate-600">
                  {s.memo || "-"}
                </td>
                <td className="border px-2 py-1 text-xs text-slate-500">
                  {s.updated_at ? new Date(s.updated_at).toLocaleDateString() : "-"}
                </td>
                <td className="border px-2 py-1">
                  <span className="flex flex-wrap gap-1">
                    <Link
                      href={`/stocks/${s.id}/charts`}
                      className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
                    >
                      チャート
                    </Link>
                    <Link
                      href={`/stocks/${s.id}/prices`}
                      className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
                    >
                      価格
                    </Link>
                    <Link
                      href={`/stocks/${s.id}`}
                      className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
                    >
                      編集
                    </Link>
                    <button
                      type="button"
                      onClick={() => handleDelete(s.id, s.ticker)}
                      disabled={deletingId === s.id}
                      className="rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-60"
                    >
                      {deletingId === s.id ? "削除中..." : "削除"}
                    </button>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!loading && rows.length === 0 && (
        <p className="text-sm text-slate-500">監視銘柄がありません。上から追加してください。</p>
      )}
    </div>
  );
}
