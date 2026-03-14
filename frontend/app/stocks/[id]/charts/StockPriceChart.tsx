"use client";

import { useEffect, useRef } from "react";
import { createChart, CandlestickSeries, type IChartApi, type ISeriesApi } from "lightweight-charts";

type ChartPoint = {
  label: string;
  fullLabel: string;
  close: number;
  open?: number;
  high?: number;
  low?: number;
  volume?: number | null;
};

/** 日足・月足は yyyy-mm-dd、5分足など時刻付きは Unix 秒（ライブラリが yyyy-mm-dd のみ受け付けるため） */
function toChartTime(fullLabel: string): string | number {
  const s = fullLabel.trim();
  const hasTime = s.includes("T") || / \d{2}:/.test(s);
  if (hasTime) {
    const date = new Date(s.includes("T") ? s.slice(0, 19) : s.slice(0, 16).replace(" ", "T"));
    if (!Number.isNaN(date.getTime())) return Math.floor(date.getTime() / 1000) as number;
  }
  return s.slice(0, 10);
}

function toCandlestickData(data: ChartPoint[]) {
  return data
    .filter((d) => d.close != null && Number.isFinite(d.close))
    .map((d) => {
      const o = d.open ?? d.close;
      const h = d.high ?? Math.max(o, d.close);
      const l = d.low ?? Math.min(o, d.close);
      const c = d.close;
      return {
        time: toChartTime(d.fullLabel),
        open: round2(o),
        high: round2(h),
        low: round2(l),
        close: round2(c),
      };
    });
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

export default function StockPriceChart({ data }: { data: ChartPoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    if (!chartRef.current) {
      const chart = createChart(containerRef.current, {
        layout: {
          background: { type: "solid", color: "#fff" },
          textColor: "#374151",
        },
        grid: {
          vertLines: { color: "#e5e7eb" },
          horzLines: { color: "#e5e7eb" },
        },
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
          borderColor: "#d1d5db",
        },
        rightPriceScale: {
          borderColor: "#d1d5db",
          scaleMargins: { top: 0.1, bottom: 0.2 },
        },
      });

      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#059669",
        downColor: "#dc2626",
        borderDownColor: "#dc2626",
        borderUpColor: "#059669",
        wickDownColor: "#dc2626",
        wickUpColor: "#059669",
      });

      chartRef.current = chart;
      seriesRef.current = candleSeries;

      window.addEventListener("resize", () => {
        if (containerRef.current && chartRef.current) {
          chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
        }
      });
    }

    const candlestickData = toCandlestickData(data);
    if (candlestickData.length > 0 && seriesRef.current) {
      seriesRef.current.setData(candlestickData);
      chartRef.current?.timeScale().fitContent();
    }
  }, [data]);

  useEffect(() => {
    return () => {
      chartRef.current?.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  if (data.length === 0) return null;

  return (
    <div
      ref={containerRef}
      className="h-full w-full min-h-[200px]"
      style={{ height: "320px" }}
    />
  );
}
