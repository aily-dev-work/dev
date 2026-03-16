"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { getStocks, createStock, deleteStock, searchMarket } from "@/lib/api";
import type { WatchStock } from "@/types/api";
import type { MarketSearchResult } from "@/types/api";

const DEBOUNCE_MS = 400;

export default function StocksPage() {
  const [rows, setRows] = useState<WatchStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [marketQuery, setMarketQuery] = useState("");
  const [marketResults, setMarketResults] = useState<MarketSearchResult[]>([]);
  const [marketSearching, setMarketSearching] = useState(false);
  const [marketError, setMarketError] = useState<string | null>(null);
  const [addingSymbol, setAddingSymbol] = useState<string | null>(null);

  async function load() {
    console.log("[StocksPage] load start");
    setLoading(true);
    setError(null);
    try {
      const list = await getStocks();
      setRows(list);
      console.log("[StocksPage] load success rows", list.length);
    } catch (e) {
      setError((e as Error).message);
      console.log("[StocksPage] load error", (e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    console.log("[StocksPage] mount");
    void load();
    return () => {
      console.log("[StocksPage] unmount");
    };
  }, []);

  useEffect(() => {
    const q = marketQuery.trim();
    if (!q) {
      setMarketResults([]);
      setMarketError(null);
      return;
    }
    const t = setTimeout(() => {
      setMarketSearching(true);
      setMarketError(null);
      searchMarket(q)
        .then((res) => {
          setMarketResults(res.results || []);
        })
        .catch((e) => {
          setMarketError((e as Error).message);
          setMarketResults([]);
        })
        .finally(() => setMarketSearching(false));
    }, DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [marketQuery]);

  const handleAddFromMarket = useCallback(
    async (item: MarketSearchResult) => {
      setAddingSymbol(item.symbol);
      setError(null);
      try {
        await createStock({
          ticker: item.symbol,
          name: (item.name_ja ?? item.name) || item.symbol,
          market: item.exchange || undefined,
          is_active: true,
        });
        await load();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setAddingSymbol(null);
      }
    },
    [],
  );

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
        市場の銘柄を検索して監視リストに追加できます。登録済み銘柄は下の一覧で編集・チャート・価格・削除ができます。
      </p>

      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-2 text-sm font-semibold text-slate-700">市場の銘柄を検索</h2>
        <p className="mb-2 text-xs text-slate-500">
          銘柄コード（例: 7203.T）や銘柄名（例: トヨタ）で検索し、結果から選択して監視リストに追加します。
        </p>
        <input
          type="search"
          value={marketQuery}
          onChange={(e) => setMarketQuery(e.target.value)}
          placeholder="例: 7203 / トヨタ / IHI株式会社"
          className="w-full max-w-md rounded border border-slate-300 px-3 py-2 text-sm"
          aria-label="市場の銘柄を検索"
        />
        {marketSearching && <p className="mt-2 text-xs text-slate-500">検索中...</p>}
        {marketError && (
          <p className="mt-2 text-xs text-red-600">{marketError}</p>
        )}
        {marketResults.length > 0 && (
          <ul className="mt-3 max-h-60 overflow-y-auto rounded border border-slate-200 bg-slate-50">
            {marketResults.map((item) => {
              const isRegistered = rows.some(
                (r) => r.ticker.toUpperCase() === item.symbol.toUpperCase(),
              );
              return (
                <li
                  key={item.symbol}
                  className="flex items-center justify-between gap-2 border-b border-slate-200 px-3 py-2 last:border-b-0"
                >
                  <span className="min-w-0 flex-1 text-sm">
                    <span className="font-mono text-slate-800">{item.symbol}</span>
                    <span className="ml-2 text-slate-600">
                      {item.name_ja ?? item.name}
                    </span>
                    {item.exchange && (
                      <span className="ml-2 text-xs text-slate-400">
                        {item.exchange}
                      </span>
                    )}
                  </span>
                  <button
                    type="button"
                    disabled={isRegistered || addingSymbol === item.symbol}
                    onClick={() => handleAddFromMarket(item)}
                    className="shrink-0 rounded bg-slate-900 px-3 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:bg-slate-400 disabled:opacity-70"
                  >
                    {isRegistered
                      ? "登録済み"
                      : addingSymbol === item.symbol
                        ? "追加中..."
                        : "監視リストに追加"}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {marketQuery.trim() && !marketSearching && marketResults.length === 0 && !marketError && (
          <p className="mt-2 text-xs text-slate-500">該当する銘柄がありません。</p>
        )}
      </section>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}

      <h2 className="text-lg font-semibold">登録済み銘柄一覧</h2>
      {loading && <p className="text-sm text-slate-600">読み込み中...</p>}
      <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="border px-2 py-1 text-center">銘柄コード</th>
              <th className="border px-2 py-1 text-center">銘柄名</th>
              <th className="border px-2 py-1 text-center">市場</th>
              <th className="border px-2 py-1 text-center">メモ</th>
              <th className="border px-2 py-1 text-center">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id} className="odd:bg-slate-50">
                <td className="border px-2 py-1 font-mono">{s.ticker}</td>
                <td className="border px-2 py-1 font-medium">{s.name}</td>
                <td className="border px-2 py-1 text-center">{s.market || "-"}</td>
                <td className="max-w-[180px] truncate border px-2 py-1 text-slate-600">
                  {s.memo || "-"}
                </td>
                <td className="border px-2 py-1 text-center">
                  <span className="flex flex-wrap gap-2 justify-center">
                    <Link
                      href={`/stocks/${s.id}/charts`}
                      className="inline-flex items-center rounded-md bg-teal-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-teal-700"
                    >
                      チャート
                    </Link>
                    <Link
                      href={`/stocks/${s.id}/prices`}
                      className="inline-flex items-center rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50"
                    >
                      価格
                    </Link>
                    <Link
                      href={`/stocks/${s.id}`}
                      className="inline-flex items-center rounded-md border border-slate-400 bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-200"
                    >
                      編集
                    </Link>
                    <button
                      type="button"
                      onClick={() => handleDelete(s.id, s.ticker)}
                      disabled={deletingId === s.id}
                      className="inline-flex items-center rounded-md border border-red-400 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-60"
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
        <p className="text-sm text-slate-500">監視銘柄がありません。上の検索から追加してください。</p>
      )}
    </div>
  );
}
