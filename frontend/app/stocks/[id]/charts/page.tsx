"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { getStock, getStockPrices, fetchStockPrices } from "@/lib/api";
import type { WatchStock } from "@/types/api";
import type { StockPriceBar } from "@/types/api";

const StockPriceChart = dynamic(
  () => import("./StockPriceChart").then((m) => m.default),
  { ssr: false },
);

type Resolution = "5m" | "1d" | "1w" | "1m";

const RESOLUTION_LABELS: Record<Resolution, string> = {
  "5m": "5分足",
  "1d": "日足",
  "1w": "週足",
  "1m": "月足",
};

/** 表示用に足数を制限: 日足60日、5分足6時間、週足2年、月足5年 */
function limitBarsForDisplay(bars: StockPriceBar[], resolution: Resolution): StockPriceBar[] {
  if (bars.length === 0) return bars;
  if (resolution === "1d") return bars.slice(-60);
  if (resolution === "5m") {
    const bars6h = 6 * (60 / 5);
    return bars.slice(-bars6h);
  }
  if (resolution === "1w") return bars.slice(-104);
  if (resolution === "1m") return bars.slice(-60);
  return bars;
}

function barsToChartData(bars: StockPriceBar[], resolution: Resolution) {
  return bars.map((b) => {
    const label = resolution === "5m" ? (b.datetime ?? b.date ?? "") : (b.date ?? b.datetime ?? "");
    return {
      label: label.slice(0, resolution === "5m" ? 16 : 10),
      fullLabel: label,
      close: b.close,
      open: b.open,
      high: b.high,
      low: b.low,
      volume: b.volume,
    };
  });
}

export default function StockChartsPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [stock, setStock] = useState<WatchStock | null>(null);
  const [resolution, setResolution] = useState<Resolution>("1d");
  const [bars, setBars] = useState<StockPriceBar[]>([]);
  const [stockLoading, setStockLoading] = useState(true);
  const [barsLoading, setBarsLoading] = useState(true);
  const [fetchingPrices, setFetchingPrices] = useState(false);
  const [fetchMessage, setFetchMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasAutoFetchedRef = useRef(false);

  useEffect(() => {
    if (Number.isNaN(id)) return;
    hasAutoFetchedRef.current = false;
    let ok = true;
    setStockLoading(true);
    setError(null);
    getStock(id)
      .then((s) => {
        if (ok) setStock(s);
      })
      .catch((e) => {
        if (ok) setError((e as Error).message);
      })
      .finally(() => {
        if (ok) setStockLoading(false);
      });
    return () => {
      ok = false;
    };
  }, [id]);

  useEffect(() => {
    if (Number.isNaN(id)) return;
    let ok = true;
    setBarsLoading(true);
    setError(null);
    getStockPrices(id, { resolution, limit: 500 })
      .then((res) => {
        if (ok) setBars(res.bars);
      })
      .catch((e) => {
        if (ok) setError((e as Error).message);
      })
      .finally(() => {
        if (ok) setBarsLoading(false);
      });
    return () => {
      ok = false;
    };
  }, [id, resolution]);

  // 日足でデータが無いとき、アクセス時に自動で Yahoo から取得
  useEffect(() => {
    if (
      Number.isNaN(id) ||
      !stock ||
      barsLoading ||
      resolution !== "1d" ||
      bars.length > 0 ||
      hasAutoFetchedRef.current
    ) {
      return;
    }
    hasAutoFetchedRef.current = true;
    setFetchingPrices(true);
    setError(null);
    fetchStockPrices(id)
      .then((res) => {
        setFetchMessage(
          `日足 ${res.daily.created} 件、週足 ${res.weekly.created} 件、5分足 ${res["5m"].created} 件、月足 ${res.monthly.created} 件を取得しました。`,
        );
        return getStockPrices(id, { resolution: "1d", limit: 500 });
      })
      .then((r) => setBars(r.bars))
      .catch((e) => setError((e as Error).message))
      .finally(() => setFetchingPrices(false));
  }, [id, stock, barsLoading, resolution, bars.length]);

  async function handleFetchPrices() {
    setFetchingPrices(true);
    setFetchMessage(null);
    setError(null);
    try {
      const res = await fetchStockPrices(id);
      setFetchMessage(
          `日足 ${res.daily.created} 件、週足 ${res.weekly.created} 件、5分足 ${res["5m"].created} 件、月足 ${res.monthly.created} 件を取得しました。`,
        );
      getStockPrices(id, { resolution: "1d", limit: 500 }).then((r) => setBars(r.bars));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setFetchingPrices(false);
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

  if (stockLoading && !stock) {
    return <p className="text-sm text-slate-600">読み込み中...</p>;
  }

  if (error && !stock) {
    return (
      <div className="space-y-4">
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
        <Link href="/stocks" className="text-blue-600 hover:underline">一覧へ戻る</Link>
      </div>
    );
  }

  const displayedBars = limitBarsForDisplay(bars, resolution);
  const chartData = barsToChartData(displayedBars, resolution);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <Link href="/stocks" className="text-sm text-slate-600 hover:text-slate-900">
          ← 銘柄一覧
        </Link>
        <Link href={`/stocks/${id}`} className="text-sm text-slate-600 hover:text-slate-900">
          編集
        </Link>
        <Link href={`/stocks/${id}/prices`} className="text-sm text-slate-600 hover:text-slate-900">
          価格データ
        </Link>
        <h1 className="text-2xl font-semibold">
          {stock?.ticker} {stock?.name && `- ${stock.name}`}
        </h1>
      </div>

      <div className="flex gap-2 border-b border-slate-200 pb-2">
        {(["1d", "1w", "5m", "1m"] as const).map((res) => (
          <button
            key={res}
            type="button"
            onClick={() => setResolution(res)}
            className={`rounded px-4 py-2 text-sm font-medium ${
              resolution === res
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {RESOLUTION_LABELS[res]}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {fetchMessage && (
        <div className="rounded border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
          {fetchMessage}
        </div>
      )}

      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">{RESOLUTION_LABELS[resolution]} 終値</h2>
          <button
            type="button"
            onClick={handleFetchPrices}
            disabled={fetchingPrices}
            className="rounded bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-60"
          >
            {fetchingPrices ? "取得中..." : "株価を取得（Yahoo・日足）"}
          </button>
        </div>
        {barsLoading ? (
          <p className="text-sm text-slate-600">読み込み中...</p>
        ) : chartData.length > 0 ? (
          <div className="h-80">
            <StockPriceChart data={chartData} />
          </div>
        ) : (
          <div className="space-y-2 text-sm text-slate-500">
            <p>データがありません。</p>
            <p>
              <strong>「株価を取得（Yahoo・日足）」</strong>
              を押すと、Yahoo Finance から直近約2年分の日足を取得して保存できます。取得後はチャートに表示されます。
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
