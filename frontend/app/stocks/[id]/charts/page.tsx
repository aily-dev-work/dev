"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { getStock, getStockPrices } from "@/lib/api";
import type { WatchStock } from "@/types/api";
import type { StockPriceBar } from "@/types/api";

const StockPriceChart = dynamic(
  () => import("./StockPriceChart").then((m) => m.StockPriceChart),
  { ssr: false },
);

type Resolution = "5m" | "1d" | "1m";

const RESOLUTION_LABELS: Record<Resolution, string> = {
  "5m": "5分足",
  "1d": "日足",
  "1m": "月足",
};

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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (Number.isNaN(id)) return;
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

  const chartData = barsToChartData(bars, resolution);

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
        {(["1d", "5m", "1m"] as const).map((res) => (
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

      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold">{RESOLUTION_LABELS[resolution]} 終値</h2>
        {barsLoading ? (
          <p className="text-sm text-slate-600">読み込み中...</p>
        ) : chartData.length > 0 ? (
          <div className="h-80">
            <StockPriceChart data={chartData} />
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            データがありません。バックエンドの管理画面や取り込み処理で価格データを登録してください。
          </p>
        )}
      </div>
    </div>
  );
}
