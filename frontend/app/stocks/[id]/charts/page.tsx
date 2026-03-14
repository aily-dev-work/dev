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

const RESOLUTIONS = ["1d", "1w", "5m", "1m"] as const;
type Resolution = (typeof RESOLUTIONS)[number];

const RESOLUTION_LABELS: Record<Resolution, string> = {
  "5m": "5分足",
  "1d": "日足",
  "1w": "週足",
  "1m": "月足",
};

/** 表示用に足数を制限。forLargeChart=true のときは2倍の期間 */
function limitBarsForDisplay(bars: StockPriceBar[], resolution: Resolution, forLargeChart?: boolean): StockPriceBar[] {
  if (bars.length === 0) return bars;
  const mul = forLargeChart ? 2 : 1;
  if (resolution === "1d") return bars.slice(-60 * mul);
  if (resolution === "5m") {
    const barsPerPeriod = 6 * (60 / 5); // 6時間分
    return bars.slice(-barsPerPeriod * mul);
  }
  if (resolution === "1w") return bars.slice(-80 * mul);
  if (resolution === "1m") return bars.slice(-60 * mul);
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
  const [barsByResolution, setBarsByResolution] = useState<Partial<Record<Resolution, StockPriceBar[]>>>({});
  const [stockLoading, setStockLoading] = useState(true);
  const [barsLoading, setBarsLoading] = useState(true);
  const [fetchingPrices, setFetchingPrices] = useState(false);
  const [fetchMessage, setFetchMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fullScreenResolution, setFullScreenResolution] = useState<Resolution | null>(null);
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

  // 4足を一括取得
  useEffect(() => {
    if (Number.isNaN(id)) return;
    setBarsLoading(true);
    setError(null);
    Promise.all(
      RESOLUTIONS.map((res) =>
        getStockPrices(id, { resolution: res, limit: 500 }).then((r) => ({ res, bars: r.bars })),
      ),
    )
      .then((results) => {
        setBarsByResolution((prev) => {
          const next = { ...prev };
          for (const { res, bars } of results) {
            next[res] = bars;
          }
          return next;
        });
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setBarsLoading(false));
  }, [id]);

  // 表示中の足のデータが空のとき、バックグラウンド取得完了に備えて再取得（1d のみポーリング）
  const bars1d = barsByResolution["1d"] ?? [];
  useEffect(() => {
    if (Number.isNaN(id) || barsLoading || bars1d.length > 0) return;
    const t = window.setInterval(() => {
      getStockPrices(id, { resolution: "1d", limit: 500 })
        .then((res) => {
          if (res.bars.length === 0) return;
          setBarsByResolution((prev) => ({ ...prev, "1d": res.bars }));
        })
        .catch(() => {});
    }, 3000);
    return () => window.clearInterval(t);
  }, [id, barsLoading, bars1d.length]);

  // 日足が無いとき、アクセス時に自動で Yahoo から取得
  useEffect(() => {
    if (
      Number.isNaN(id) ||
      !stock ||
      barsLoading ||
      bars1d.length > 0 ||
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
        return Promise.all(
          RESOLUTIONS.map((r) =>
            getStockPrices(id, { resolution: r, limit: 500 }).then((data) => ({ res: r, bars: data.bars })),
          ),
        );
      })
      .then((results) => {
        setBarsByResolution((prev) => {
          const next = { ...prev };
          for (const { res, bars } of results) {
            next[res] = bars;
          }
          return next;
        });
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setFetchingPrices(false));
  }, [id, stock, barsLoading, bars1d.length]);

  async function handleFetchPrices() {
    setFetchingPrices(true);
    setFetchMessage(null);
    setError(null);
    try {
      const res = await fetchStockPrices(id);
      setFetchMessage(
        `日足 ${res.daily.created} 件、週足 ${res.weekly.created} 件、5分足 ${res["5m"].created} 件、月足 ${res.monthly.created} 件を取得しました。`,
      );
      const results = await Promise.all(
        RESOLUTIONS.map((r) =>
          getStockPrices(id, { resolution: r, limit: 500 }).then((data) => ({ res: r, bars: data.bars })),
        ),
      );
      setBarsByResolution((prev) => {
        const next = { ...prev };
        for (const { res, bars } of results) {
          next[res] = bars;
        }
        return next;
      });
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
        <Link href="/stocks" className="text-blue-600 hover:underline">
          一覧へ戻る
        </Link>
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
        <Link href="/stocks" className="text-blue-600 hover:underline">
          一覧へ戻る
        </Link>
      </div>
    );
  }

  // 全画面表示（1枚のチャート）
  if (fullScreenResolution) {
    const bars = barsByResolution[fullScreenResolution] ?? [];
    const displayedBars = limitBarsForDisplay(bars, fullScreenResolution, true);
    const chartData = barsToChartData(displayedBars, fullScreenResolution);

    return (
      <div
        className="fixed inset-x-8 inset-y-20 z-50 flex flex-col rounded-lg border-2 border-slate-200 bg-white shadow-xl"
        role="button"
        tabIndex={0}
        onClick={() => setFullScreenResolution(null)}
        onKeyDown={(e) => e.key === "Escape" && setFullScreenResolution(null)}
      >
        <div className="flex shrink-0 items-center justify-between rounded-t-lg border-b bg-white px-4 py-2">
          <h2 className="text-lg font-semibold">{RESOLUTION_LABELS[fullScreenResolution]}</h2>
          <button
            type="button"
            className="rounded bg-slate-200 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-300"
            onClick={(e) => {
              e.stopPropagation();
              setFullScreenResolution(null);
            }}
          >
            閉じる
          </button>
        </div>
        <div className="min-h-0 flex-1 p-2" onClick={(e) => e.stopPropagation()}>
          {chartData.length > 0 ? (
            <div className="h-full min-h-0 w-full">
              <StockPriceChart key={fullScreenResolution} data={chartData} />
            </div>
          ) : (
            <p className="p-4 text-slate-500">データがありません。</p>
          )}
        </div>
      </div>
    );
  }

  // 4分割表示
  return (
    <div className="space-y-4">
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
        <button
          type="button"
          onClick={handleFetchPrices}
          disabled={fetchingPrices}
          className="rounded bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-60"
        >
          {fetchingPrices ? "取得中..." : "株価を取得（Yahoo）"}
        </button>
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

      {barsLoading ? (
        <p className="text-sm text-slate-600">読み込み中...</p>
      ) : (
        <div className="relative left-1/2 right-1/2 -ml-[50vw] -mr-[50vw] w-screen">
          <div className="mx-auto max-w-7xl px-4">
            <div className="grid grid-cols-2 grid-rows-2 gap-3">
          {RESOLUTIONS.map((res) => {
            const bars = barsByResolution[res] ?? [];
            const displayedBars = limitBarsForDisplay(bars, res);
            const chartData = barsToChartData(displayedBars, res);

            return (
              <div
                key={res}
                role="button"
                tabIndex={0}
                className="flex cursor-pointer flex-col overflow-hidden rounded-lg border bg-white shadow-sm transition hover:border-slate-400 hover:shadow"
                onClick={() => setFullScreenResolution(res)}
                onKeyDown={(e) => e.key === "Enter" && setFullScreenResolution(res)}
              >
                <div className="shrink-0 border-b bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-700">
                  {RESOLUTION_LABELS[res]}
                </div>
                <div className="h-64 min-h-0 shrink-0">
                  {chartData.length > 0 ? (
                    <StockPriceChart key={res} data={chartData} />
                  ) : (
                    <div className="flex h-full items-center justify-center text-sm text-slate-400">
                      データがありません
                    </div>
                  )}
                </div>
              </div>
            );
          })}
            </div>
          </div>
        </div>
      )}

      {!barsLoading && RESOLUTIONS.every((r) => (barsByResolution[r] ?? []).length === 0) && (
        <p className="text-sm text-slate-500">
          「株価を取得（Yahoo）」でデータを取得するとチャートに表示されます。
        </p>
      )}
    </div>
  );
}
