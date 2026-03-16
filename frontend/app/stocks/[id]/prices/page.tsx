"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getStock,
  getStockPricesDaily,
  getStockPricesWeekly,
  getStockPrices5m,
  getStockPricesMonthly,
  createStockPrice5m,
  createStockPriceMonthly,
} from "@/lib/api";
import type { WatchStock } from "@/types/api";
import type { StockPriceDailyRow, StockPriceWeeklyRow, StockPrice5MinRow, StockPriceMonthlyRow } from "@/types/api";

type Resolution = "1d" | "1w" | "5m" | "1m";
const LABELS: Record<Resolution, string> = { "1d": "日足", "1w": "週足", "5m": "5分足", "1m": "月足" };
const PER_PAGE = 15;

export default function StockPricesPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [stock, setStock] = useState<WatchStock | null>(null);
  const [resolution, setResolution] = useState<Resolution>("1d");
  const [page, setPage] = useState(1);
  const [dailyRows, setDailyRows] = useState<StockPriceDailyRow[]>([]);
  const [weeklyRows, setWeeklyRows] = useState<StockPriceWeeklyRow[]>([]);
  const [rows5m, setRows5m] = useState<StockPrice5MinRow[]>([]);
  const [monthlyRows, setMonthlyRows] = useState<StockPriceMonthlyRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    console.log("[StockPricesPage] mount id", id);
    return () => {
      console.log("[StockPricesPage] unmount id", id);
    };
  }, [id]);

  useEffect(() => {
    if (Number.isNaN(id)) return;
    console.log("[StockPricesPage] fetch stock start", id);
    getStock(id)
      .then((s) => {
        console.log("[StockPricesPage] fetch stock success", id);
        setStock(s);
      })
      .catch((e) => {
        const msg = (e as Error).message;
        console.log("[StockPricesPage] fetch stock error", id, msg);
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (Number.isNaN(id)) return;
    console.log("[StockPricesPage] fetch prices start", id, resolution);
    setError(null);
    if (resolution === "1d") {
      getStockPricesDaily(id)
        .then((rows) => {
          console.log("[StockPricesPage] fetch prices success", id, resolution, rows.length);
          setDailyRows(rows);
        })
        .catch((e) => {
          const msg = (e as Error).message;
          console.log("[StockPricesPage] fetch prices error", id, resolution, msg);
          setError(msg);
        });
    } else if (resolution === "1w") {
      getStockPricesWeekly(id)
        .then((rows) => {
          console.log("[StockPricesPage] fetch prices success", id, resolution, rows.length);
          setWeeklyRows(rows);
        })
        .catch((e) => {
          const msg = (e as Error).message;
          console.log("[StockPricesPage] fetch prices error", id, resolution, msg);
          setError(msg);
        });
    } else if (resolution === "5m") {
      getStockPrices5m(id)
        .then((rows) => {
          console.log("[StockPricesPage] fetch prices success", id, resolution, rows.length);
          setRows5m(rows);
        })
        .catch((e) => {
          const msg = (e as Error).message;
          console.log("[StockPricesPage] fetch prices error", id, resolution, msg);
          setError(msg);
        });
    } else {
      getStockPricesMonthly(id)
        .then((rows) => {
          console.log("[StockPricesPage] fetch prices success", id, resolution, rows.length);
          setMonthlyRows(rows);
        })
        .catch((e) => {
          const msg = (e as Error).message;
          console.log("[StockPricesPage] fetch prices error", id, resolution, msg);
          setError(msg);
        });
    }
  }, [id, resolution]);

  if (Number.isNaN(id)) {
    return (
      <div className="space-y-4">
        <p>無効な銘柄 ID です。</p>
        <Link href="/stocks" className="text-blue-600 hover:underline">一覧へ戻る</Link>
      </div>
    );
  }
  if (loading && !stock) {
    return <p className="text-sm text-slate-600">読み込み中...</p>;
  }
  if (error && !stock) {
    return (
      <div className="space-y-4">
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>
        <Link href="/stocks" className="text-blue-600 hover:underline">一覧へ戻る</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <Link href="/stocks" className="text-sm text-slate-600 hover:text-slate-900">← 銘柄一覧</Link>
        <Link href={`/stocks/${id}/charts`} className="text-sm text-slate-600 hover:text-slate-900">チャート</Link>
        <h1 className="text-2xl font-semibold">価格データ管理: {stock?.ticker} {stock?.name && `- ${stock.name}`}</h1>
      </div>

      <div className="flex gap-2 border-b border-slate-200 pb-2">
        {(["1d", "1w", "5m", "1m"] as const).map((res) => (
          <button
            key={res}
            type="button"
            onClick={() => { setResolution(res); setPage(1); }}
            className={`rounded px-4 py-2 text-sm font-medium ${resolution === res ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}
          >
            {LABELS[res]}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>
      )}

      {resolution === "1d" && (
        <DailySection
          rows={dailyRows}
          page={page}
          perPage={PER_PAGE}
          onPageChange={setPage}
        />
      )}
      {resolution === "1w" && (
        <WeeklySection
          rows={weeklyRows}
          page={page}
          perPage={PER_PAGE}
          onPageChange={setPage}
        />
      )}
      {resolution === "5m" && (
        <FiveMinSection
          stockId={id}
          rows={rows5m}
          setRows={setRows5m}
          page={page}
          perPage={PER_PAGE}
          onPageChange={setPage}
          submitting={submitting}
          setSubmitting={setSubmitting}
          setError={setError}
        />
      )}
      {resolution === "1m" && (
        <MonthlySection
          stockId={id}
          rows={monthlyRows}
          setRows={setMonthlyRows}
          page={page}
          perPage={PER_PAGE}
          onPageChange={setPage}
          submitting={submitting}
          setSubmitting={setSubmitting}
          setError={setError}
        />
      )}
    </div>
  );
}

function DailySection({
  rows,
  page,
  perPage,
  onPageChange,
}: {
  rows: StockPriceDailyRow[];
  page: number;
  perPage: number;
  onPageChange: (p: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(rows.length / perPage));
  const currentPage = Math.min(page, totalPages);
  const displayedRows = rows.slice((currentPage - 1) * perPage, currentPage * perPage);

  return (
    <section className="space-y-4">
      <div className="overflow-x-auto rounded border bg-white">
        <table className="w-full table-fixed text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="w-28 border px-2 py-1 text-left">日付</th>
              <th className="w-24 border px-2 py-1 text-left">始値</th>
              <th className="w-24 border px-2 py-1 text-left">高値</th>
              <th className="w-24 border px-2 py-1 text-left">安値</th>
              <th className="w-24 border px-2 py-1 text-left">終値</th>
              <th className="w-28 border px-2 py-1 text-left">出来高</th>
            </tr>
          </thead>
          <tbody>
            {displayedRows.map((r) => (
              <tr key={r.id}>
                <td className="border px-2 py-1 truncate" title={r.date.slice(0, 10)}>{r.date.slice(0, 10)}</td>
                <td className="border px-2 py-1 truncate" title={String(r.open_price)}>{r.open_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.high_price)}>{r.high_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.low_price)}>{r.low_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.close_price)}>{r.close_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.volume ?? "-")}>{r.volume ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="text-sm text-slate-500">データがありません。</p>}
      {rows.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={rows.length}
          perPage={perPage}
          onPageChange={onPageChange}
        />
      )}
    </section>
  );
}

function Pagination({
  currentPage,
  totalPages,
  totalItems,
  perPage,
  onPageChange,
}: {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  perPage: number;
  onPageChange: (p: number) => void;
}) {
  const start = (currentPage - 1) * perPage + 1;
  const end = Math.min(currentPage * perPage, totalItems);
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <span className="text-slate-600">
        {start}-{end} / 全{totalItems}件
      </span>
      <div className="flex gap-1">
        <button
          type="button"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
          className="rounded border border-slate-300 px-2 py-1 disabled:opacity-50 hover:bg-slate-100"
        >
          前へ
        </button>
        <span className="flex items-center px-2">
          {currentPage} / {totalPages}
        </span>
        <button
          type="button"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
          className="rounded border border-slate-300 px-2 py-1 disabled:opacity-50 hover:bg-slate-100"
        >
          次へ
        </button>
      </div>
    </div>
  );
}

function WeeklySection({
  rows,
  page,
  perPage,
  onPageChange,
}: {
  rows: StockPriceWeeklyRow[];
  page: number;
  perPage: number;
  onPageChange: (p: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(rows.length / perPage));
  const currentPage = Math.min(page, totalPages);
  const displayedRows = rows.slice((currentPage - 1) * perPage, currentPage * perPage);

  return (
    <section className="space-y-4">
      <div className="overflow-x-auto rounded border bg-white">
        <table className="w-full table-fixed text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="w-28 border px-2 py-1 text-left">日付</th>
              <th className="w-24 border px-2 py-1 text-left">始値</th>
              <th className="w-24 border px-2 py-1 text-left">高値</th>
              <th className="w-24 border px-2 py-1 text-left">安値</th>
              <th className="w-24 border px-2 py-1 text-left">終値</th>
              <th className="w-28 border px-2 py-1 text-left">出来高</th>
            </tr>
          </thead>
          <tbody>
            {displayedRows.map((r) => (
              <tr key={r.id}>
                <td className="border px-2 py-1 truncate" title={r.date.slice(0, 10)}>{r.date.slice(0, 10)}</td>
                <td className="border px-2 py-1 truncate" title={String(r.open_price)}>{r.open_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.high_price)}>{r.high_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.low_price)}>{r.low_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.close_price)}>{r.close_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.volume ?? "-")}>{r.volume ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="text-sm text-slate-500">データがありません。</p>}
      {rows.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={rows.length}
          perPage={perPage}
          onPageChange={onPageChange}
        />
      )}
    </section>
  );
}

function FiveMinSection({
  stockId,
  rows,
  setRows,
  page,
  perPage,
  onPageChange,
  submitting,
  setSubmitting,
  setError,
}: {
  stockId: number;
  rows: StockPrice5MinRow[];
  setRows: React.Dispatch<React.SetStateAction<StockPrice5MinRow[]>>;
  page: number;
  perPage: number;
  onPageChange: (p: number) => void;
  submitting: boolean;
  setSubmitting: (v: boolean) => void;
  setError: (v: string | null) => void;
}) {
  const [form, setForm] = useState({ datetime: "", open_price: "", high_price: "", low_price: "", close_price: "", volume: "" });
  const totalPages = Math.max(1, Math.ceil(rows.length / perPage));
  const currentPage = Math.min(page, totalPages);
  const displayedRows = rows.slice((currentPage - 1) * perPage, currentPage * perPage);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const o = parseFloat(form.open_price), h = parseFloat(form.high_price), l = parseFloat(form.low_price), c = parseFloat(form.close_price);
    if (!form.datetime || Number.isNaN(o) || Number.isNaN(h) || Number.isNaN(l) || Number.isNaN(c)) {
      setError("日時とOHLCは必須です。");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await createStockPrice5m({
        stock: stockId,
        datetime: form.datetime ? `${form.datetime}:00` : "",
        open_price: o,
        high_price: h,
        low_price: l,
        close_price: c,
        volume: form.volume ? parseInt(form.volume, 10) : null,
      });
      setRows((prev) => [created, ...prev]);
      setForm({ datetime: "", open_price: "", high_price: "", low_price: "", close_price: "", volume: "" });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">5分足 新規追加</h2>
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3 rounded border bg-slate-50 p-3">
        <label className="text-sm">日時 <input type="datetime-local" value={form.datetime} onChange={(e) => setForm((f) => ({ ...f, datetime: e.target.value }))} className="ml-1 rounded border px-2 py-1" required /></label>
        <label className="text-sm">始値 <input type="number" step="any" value={form.open_price} onChange={(e) => setForm((f) => ({ ...f, open_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">高値 <input type="number" step="any" value={form.high_price} onChange={(e) => setForm((f) => ({ ...f, high_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">安値 <input type="number" step="any" value={form.low_price} onChange={(e) => setForm((f) => ({ ...f, low_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">終値 <input type="number" step="any" value={form.close_price} onChange={(e) => setForm((f) => ({ ...f, close_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">出来高 <input type="number" value={form.volume} onChange={(e) => setForm((f) => ({ ...f, volume: e.target.value }))} className="ml-1 w-28 rounded border px-2 py-1" /></label>
        <button type="submit" disabled={submitting} className="rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-60">追加</button>
      </form>

      <div className="overflow-x-auto rounded border bg-white">
        <table className="w-full table-fixed text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="w-36 border px-2 py-1 text-left">日時</th>
              <th className="w-24 border px-2 py-1 text-left">始値</th>
              <th className="w-24 border px-2 py-1 text-left">高値</th>
              <th className="w-24 border px-2 py-1 text-left">安値</th>
              <th className="w-24 border px-2 py-1 text-left">終値</th>
              <th className="w-28 border px-2 py-1 text-left">出来高</th>
            </tr>
          </thead>
          <tbody>
            {displayedRows.map((r) => (
              <tr key={r.id}>
                <td className="border px-2 py-1 truncate" title={r.datetime.slice(0, 16).replace("T", " ")}>{r.datetime.slice(0, 16).replace("T", " ")}</td>
                <td className="border px-2 py-1 truncate" title={String(r.open_price)}>{r.open_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.high_price)}>{r.high_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.low_price)}>{r.low_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.close_price)}>{r.close_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.volume ?? "-")}>{r.volume ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="text-sm text-slate-500">データがありません。</p>}
      {rows.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={rows.length}
          perPage={perPage}
          onPageChange={onPageChange}
        />
      )}
    </section>
  );
}

function MonthlySection({
  stockId,
  rows,
  setRows,
  page,
  perPage,
  onPageChange,
  submitting,
  setSubmitting,
  setError,
}: {
  stockId: number;
  rows: StockPriceMonthlyRow[];
  setRows: React.Dispatch<React.SetStateAction<StockPriceMonthlyRow[]>>;
  page: number;
  perPage: number;
  onPageChange: (p: number) => void;
  submitting: boolean;
  setSubmitting: (v: boolean) => void;
  setError: (v: string | null) => void;
}) {
  const [form, setForm] = useState({ date: "", open_price: "", high_price: "", low_price: "", close_price: "", volume: "" });
  const totalPages = Math.max(1, Math.ceil(rows.length / perPage));
  const currentPage = Math.min(page, totalPages);
  const displayedRows = rows.slice((currentPage - 1) * perPage, currentPage * perPage);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const o = parseFloat(form.open_price), h = parseFloat(form.high_price), l = parseFloat(form.low_price), c = parseFloat(form.close_price);
    if (!form.date || Number.isNaN(o) || Number.isNaN(h) || Number.isNaN(l) || Number.isNaN(c)) {
      setError("日付とOHLCは必須です。");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await createStockPriceMonthly({
        stock: stockId,
        date: form.date,
        open_price: o,
        high_price: h,
        low_price: l,
        close_price: c,
        volume: form.volume ? parseInt(form.volume, 10) : null,
      });
      setRows((prev) => [created, ...prev]);
      setForm({ date: "", open_price: "", high_price: "", low_price: "", close_price: "", volume: "" });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">月足 新規追加</h2>
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3 rounded border bg-slate-50 p-3">
        <label className="text-sm">日付（月の代表日） <input type="date" value={form.date} onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))} className="ml-1 rounded border px-2 py-1" required /></label>
        <label className="text-sm">始値 <input type="number" step="any" value={form.open_price} onChange={(e) => setForm((f) => ({ ...f, open_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">高値 <input type="number" step="any" value={form.high_price} onChange={(e) => setForm((f) => ({ ...f, high_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">安値 <input type="number" step="any" value={form.low_price} onChange={(e) => setForm((f) => ({ ...f, low_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">終値 <input type="number" step="any" value={form.close_price} onChange={(e) => setForm((f) => ({ ...f, close_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">出来高 <input type="number" value={form.volume} onChange={(e) => setForm((f) => ({ ...f, volume: e.target.value }))} className="ml-1 w-28 rounded border px-2 py-1" /></label>
        <button type="submit" disabled={submitting} className="rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-60">追加</button>
      </form>

      <div className="overflow-x-auto rounded border bg-white">
        <table className="w-full table-fixed text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="w-28 border px-2 py-1 text-left">日付</th>
              <th className="w-24 border px-2 py-1 text-left">始値</th>
              <th className="w-24 border px-2 py-1 text-left">高値</th>
              <th className="w-24 border px-2 py-1 text-left">安値</th>
              <th className="w-24 border px-2 py-1 text-left">終値</th>
              <th className="w-28 border px-2 py-1 text-left">出来高</th>
            </tr>
          </thead>
          <tbody>
            {displayedRows.map((r) => (
              <tr key={r.id}>
                <td className="border px-2 py-1 truncate" title={r.date.slice(0, 10)}>{r.date.slice(0, 10)}</td>
                <td className="border px-2 py-1 truncate" title={String(r.open_price)}>{r.open_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.high_price)}>{r.high_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.low_price)}>{r.low_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.close_price)}>{r.close_price}</td>
                <td className="border px-2 py-1 truncate" title={String(r.volume ?? "-")}>{r.volume ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="text-sm text-slate-500">データがありません。</p>}
      {rows.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={rows.length}
          perPage={perPage}
          onPageChange={onPageChange}
        />
      )}
    </section>
  );
}
