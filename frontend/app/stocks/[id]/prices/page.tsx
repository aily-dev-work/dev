"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getStock,
  getStockPricesDaily,
  getStockPrices5m,
  getStockPricesMonthly,
  createStockPriceDaily,
  createStockPrice5m,
  createStockPriceMonthly,
  updateStockPriceDaily,
  updateStockPrice5m,
  updateStockPriceMonthly,
  deleteStockPriceDaily,
  deleteStockPrice5m,
  deleteStockPriceMonthly,
} from "@/lib/api";
import type { WatchStock } from "@/types/api";
import type { StockPriceDailyRow, StockPrice5MinRow, StockPriceMonthlyRow } from "@/types/api";

type Resolution = "1d" | "5m" | "1m";
const LABELS: Record<Resolution, string> = { "1d": "日足", "5m": "5分足", "1m": "月足" };

export default function StockPricesPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [stock, setStock] = useState<WatchStock | null>(null);
  const [resolution, setResolution] = useState<Resolution>("1d");
  const [dailyRows, setDailyRows] = useState<StockPriceDailyRow[]>([]);
  const [rows5m, setRows5m] = useState<StockPrice5MinRow[]>([]);
  const [monthlyRows, setMonthlyRows] = useState<StockPriceMonthlyRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    if (Number.isNaN(id)) return;
    getStock(id)
      .then(setStock)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (Number.isNaN(id)) return;
    setError(null);
    if (resolution === "1d") {
      getStockPricesDaily(id).then(setDailyRows).catch((e) => setError((e as Error).message));
    } else if (resolution === "5m") {
      getStockPrices5m(id).then(setRows5m).catch((e) => setError((e as Error).message));
    } else {
      getStockPricesMonthly(id).then(setMonthlyRows).catch((e) => setError((e as Error).message));
    }
  }, [id, resolution]);

  async function handleDeleteDaily(rowId: number) {
    if (!confirm("この日足を削除しますか？")) return;
    setDeletingId(rowId);
    setError(null);
    try {
      await deleteStockPriceDaily(rowId);
      setDailyRows((prev) => prev.filter((r) => r.id !== rowId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeletingId(null);
    }
  }
  async function handleDelete5m(rowId: number) {
    if (!confirm("この5分足を削除しますか？")) return;
    setDeletingId(rowId);
    setError(null);
    try {
      await deleteStockPrice5m(rowId);
      setRows5m((prev) => prev.filter((r) => r.id !== rowId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeletingId(null);
    }
  }
  async function handleDeleteMonthly(rowId: number) {
    if (!confirm("この月足を削除しますか？")) return;
    setDeletingId(rowId);
    setError(null);
    try {
      await deleteStockPriceMonthly(rowId);
      setMonthlyRows((prev) => prev.filter((r) => r.id !== rowId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeletingId(null);
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
        <Link href={`/stocks/${id}`} className="text-sm text-slate-600 hover:text-slate-900">編集</Link>
        <Link href={`/stocks/${id}/charts`} className="text-sm text-slate-600 hover:text-slate-900">チャート</Link>
        <h1 className="text-2xl font-semibold">価格データ管理: {stock?.ticker} {stock?.name && `- ${stock.name}`}</h1>
      </div>

      <div className="flex gap-2 border-b border-slate-200 pb-2">
        {(["1d", "5m", "1m"] as const).map((res) => (
          <button
            key={res}
            type="button"
            onClick={() => { setResolution(res); setEditingId(null); }}
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
          stockId={id}
          rows={dailyRows}
          setRows={setDailyRows}
          submitting={submitting}
          setSubmitting={setSubmitting}
          setError={setError}
          deletingId={deletingId}
          onDelete={handleDeleteDaily}
          editingId={editingId}
          setEditingId={setEditingId}
        />
      )}
      {resolution === "5m" && (
        <FiveMinSection
          stockId={id}
          rows={rows5m}
          setRows={setRows5m}
          submitting={submitting}
          setSubmitting={setSubmitting}
          setError={setError}
          deletingId={deletingId}
          onDelete={handleDelete5m}
          editingId={editingId}
          setEditingId={setEditingId}
        />
      )}
      {resolution === "1m" && (
        <MonthlySection
          stockId={id}
          rows={monthlyRows}
          setRows={setMonthlyRows}
          submitting={submitting}
          setSubmitting={setSubmitting}
          setError={setError}
          deletingId={deletingId}
          onDelete={handleDeleteMonthly}
          editingId={editingId}
          setEditingId={setEditingId}
        />
      )}
    </div>
  );
}

function DailySection({
  stockId,
  rows,
  setRows,
  submitting,
  setSubmitting,
  setError,
  deletingId,
  onDelete,
  editingId,
  setEditingId,
}: {
  stockId: number;
  rows: StockPriceDailyRow[];
  setRows: React.Dispatch<React.SetStateAction<StockPriceDailyRow[]>>;
  submitting: boolean;
  setSubmitting: (v: boolean) => void;
  setError: (v: string | null) => void;
  deletingId: number | null;
  onDelete: (id: number) => void;
  editingId: number | null;
  setEditingId: (v: number | null) => void;
}) {
  const [form, setForm] = useState({ date: "", open_price: "", high_price: "", low_price: "", close_price: "", volume: "" });
  const [editForm, setEditForm] = useState({ date: "", open_price: "", high_price: "", low_price: "", close_price: "", volume: "" });

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
      const created = await createStockPriceDaily({
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

  async function handleSaveEdit() {
    if (editingId == null) return;
    const o = parseFloat(editForm.open_price), h = parseFloat(editForm.high_price), l = parseFloat(editForm.low_price), c = parseFloat(editForm.close_price);
    if (!editForm.date || Number.isNaN(o) || Number.isNaN(h) || Number.isNaN(l) || Number.isNaN(c)) {
      setError("日付とOHLCは必須です。");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const updated = await updateStockPriceDaily(editingId, {
        date: editForm.date,
        open_price: o,
        high_price: h,
        low_price: l,
        close_price: c,
        volume: editForm.volume ? parseInt(editForm.volume, 10) : null,
      });
      setRows((prev) => prev.map((r) => (r.id === editingId ? updated : r)));
      setEditingId(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  const startEdit = (r: StockPriceDailyRow) => {
    setEditingId(r.id);
    setEditForm({
      date: r.date.slice(0, 10),
      open_price: r.open_price,
      high_price: r.high_price,
      low_price: r.low_price,
      close_price: r.close_price,
      volume: r.volume != null ? String(r.volume) : "",
    });
  };

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">日足 新規追加</h2>
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3 rounded border bg-slate-50 p-3">
        <label className="text-sm">日付 <input type="date" value={form.date} onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))} className="ml-1 rounded border px-2 py-1" required /></label>
        <label className="text-sm">始値 <input type="number" step="any" value={form.open_price} onChange={(e) => setForm((f) => ({ ...f, open_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">高値 <input type="number" step="any" value={form.high_price} onChange={(e) => setForm((f) => ({ ...f, high_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">安値 <input type="number" step="any" value={form.low_price} onChange={(e) => setForm((f) => ({ ...f, low_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">終値 <input type="number" step="any" value={form.close_price} onChange={(e) => setForm((f) => ({ ...f, close_price: e.target.value }))} className="ml-1 w-24 rounded border px-2 py-1" required /></label>
        <label className="text-sm">出来高 <input type="number" value={form.volume} onChange={(e) => setForm((f) => ({ ...f, volume: e.target.value }))} className="ml-1 w-28 rounded border px-2 py-1" /></label>
        <button type="submit" disabled={submitting} className="rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-60">追加</button>
      </form>

      <h2 className="text-lg font-semibold">一覧</h2>
      <div className="overflow-x-auto rounded border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="border px-2 py-1 text-left">日付</th>
              <th className="border px-2 py-1 text-left">始値</th>
              <th className="border px-2 py-1 text-left">高値</th>
              <th className="border px-2 py-1 text-left">安値</th>
              <th className="border px-2 py-1 text-left">終値</th>
              <th className="border px-2 py-1 text-left">出来高</th>
              <th className="border px-2 py-1 text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                {editingId === r.id ? (
                  <>
                    <td className="border px-2 py-1"><input type="date" value={editForm.date} onChange={(e) => setEditForm((f) => ({ ...f, date: e.target.value }))} className="w-32 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.open_price} onChange={(e) => setEditForm((f) => ({ ...f, open_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.high_price} onChange={(e) => setEditForm((f) => ({ ...f, high_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.low_price} onChange={(e) => setEditForm((f) => ({ ...f, low_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.close_price} onChange={(e) => setEditForm((f) => ({ ...f, close_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" value={editForm.volume} onChange={(e) => setEditForm((f) => ({ ...f, volume: e.target.value }))} className="w-24 rounded border px-1" /></td>
                    <td className="border px-2 py-1">
                      <button type="button" onClick={handleSaveEdit} disabled={submitting} className="mr-1 rounded bg-teal-600 px-2 py-0.5 text-xs text-white">保存</button>
                      <button type="button" onClick={() => setEditingId(null)} className="rounded border px-2 py-0.5 text-xs">キャンセル</button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="border px-2 py-1">{r.date.slice(0, 10)}</td>
                    <td className="border px-2 py-1">{r.open_price}</td>
                    <td className="border px-2 py-1">{r.high_price}</td>
                    <td className="border px-2 py-1">{r.low_price}</td>
                    <td className="border px-2 py-1">{r.close_price}</td>
                    <td className="border px-2 py-1">{r.volume ?? "-"}</td>
                    <td className="border px-2 py-1">
                      <button type="button" onClick={() => startEdit(r)} className="mr-1 rounded border px-2 py-0.5 text-xs">編集</button>
                      <button type="button" onClick={() => onDelete(r.id)} disabled={deletingId === r.id} className="rounded border border-red-300 px-2 py-0.5 text-xs text-red-700">削除</button>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="text-sm text-slate-500">データがありません。</p>}
    </section>
  );
}

function FiveMinSection({
  stockId,
  rows,
  setRows,
  submitting,
  setSubmitting,
  setError,
  deletingId,
  onDelete,
  editingId,
  setEditingId,
}: {
  stockId: number;
  rows: StockPrice5MinRow[];
  setRows: React.Dispatch<React.SetStateAction<StockPrice5MinRow[]>>;
  submitting: boolean;
  setSubmitting: (v: boolean) => void;
  setError: (v: string | null) => void;
  deletingId: number | null;
  onDelete: (id: number) => void;
  editingId: number | null;
  setEditingId: (v: number | null) => void;
}) {
  const [form, setForm] = useState({ datetime: "", open_price: "", high_price: "", low_price: "", close_price: "", volume: "" });
  const [editForm, setEditForm] = useState({ datetime: "", open_price: "", high_price: "", low_price: "", close_price: "", volume: "" });

  function toDatetimeLocal(iso: string) {
    if (!iso) return "";
    const d = new Date(iso);
    const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, "0"), day = String(d.getDate()).padStart(2, "0");
    const h = String(d.getHours()).padStart(2, "0"), min = String(d.getMinutes()).padStart(2, "0");
    return `${y}-${m}-${day}T${h}:${min}`;
  }

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

  async function handleSaveEdit() {
    if (editingId == null) return;
    const o = parseFloat(editForm.open_price), h = parseFloat(editForm.high_price), l = parseFloat(editForm.low_price), c = parseFloat(editForm.close_price);
    if (!editForm.datetime || Number.isNaN(o) || Number.isNaN(h) || Number.isNaN(l) || Number.isNaN(c)) {
      setError("日時とOHLCは必須です。");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const updated = await updateStockPrice5m(editingId, {
        datetime: editForm.datetime ? `${editForm.datetime}:00` : "",
        open_price: o,
        high_price: h,
        low_price: l,
        close_price: c,
        volume: editForm.volume ? parseInt(editForm.volume, 10) : null,
      });
      setRows((prev) => prev.map((r) => (r.id === editingId ? updated : r)));
      setEditingId(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  const startEdit = (r: StockPrice5MinRow) => {
    setEditingId(r.id);
    setEditForm({
      datetime: toDatetimeLocal(r.datetime),
      open_price: r.open_price,
      high_price: r.high_price,
      low_price: r.low_price,
      close_price: r.close_price,
      volume: r.volume != null ? String(r.volume) : "",
    });
  };

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

      <h2 className="text-lg font-semibold">一覧</h2>
      <div className="overflow-x-auto rounded border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="border px-2 py-1 text-left">日時</th>
              <th className="border px-2 py-1 text-left">始値</th>
              <th className="border px-2 py-1 text-left">高値</th>
              <th className="border px-2 py-1 text-left">安値</th>
              <th className="border px-2 py-1 text-left">終値</th>
              <th className="border px-2 py-1 text-left">出来高</th>
              <th className="border px-2 py-1 text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                {editingId === r.id ? (
                  <>
                    <td className="border px-2 py-1"><input type="datetime-local" value={editForm.datetime} onChange={(e) => setEditForm((f) => ({ ...f, datetime: e.target.value }))} className="rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.open_price} onChange={(e) => setEditForm((f) => ({ ...f, open_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.high_price} onChange={(e) => setEditForm((f) => ({ ...f, high_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.low_price} onChange={(e) => setEditForm((f) => ({ ...f, low_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.close_price} onChange={(e) => setEditForm((f) => ({ ...f, close_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" value={editForm.volume} onChange={(e) => setEditForm((f) => ({ ...f, volume: e.target.value }))} className="w-24 rounded border px-1" /></td>
                    <td className="border px-2 py-1">
                      <button type="button" onClick={handleSaveEdit} disabled={submitting} className="mr-1 rounded bg-teal-600 px-2 py-0.5 text-xs text-white">保存</button>
                      <button type="button" onClick={() => setEditingId(null)} className="rounded border px-2 py-0.5 text-xs">キャンセル</button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="border px-2 py-1">{r.datetime.slice(0, 16).replace("T", " ")}</td>
                    <td className="border px-2 py-1">{r.open_price}</td>
                    <td className="border px-2 py-1">{r.high_price}</td>
                    <td className="border px-2 py-1">{r.low_price}</td>
                    <td className="border px-2 py-1">{r.close_price}</td>
                    <td className="border px-2 py-1">{r.volume ?? "-"}</td>
                    <td className="border px-2 py-1">
                      <button type="button" onClick={() => startEdit(r)} className="mr-1 rounded border px-2 py-0.5 text-xs">編集</button>
                      <button type="button" onClick={() => onDelete(r.id)} disabled={deletingId === r.id} className="rounded border border-red-300 px-2 py-0.5 text-xs text-red-700">削除</button>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="text-sm text-slate-500">データがありません。</p>}
    </section>
  );
}

function MonthlySection({
  stockId,
  rows,
  setRows,
  submitting,
  setSubmitting,
  setError,
  deletingId,
  onDelete,
  editingId,
  setEditingId,
}: {
  stockId: number;
  rows: StockPriceMonthlyRow[];
  setRows: React.Dispatch<React.SetStateAction<StockPriceMonthlyRow[]>>;
  submitting: boolean;
  setSubmitting: (v: boolean) => void;
  setError: (v: string | null) => void;
  deletingId: number | null;
  onDelete: (id: number) => void;
  editingId: number | null;
  setEditingId: (v: number | null) => void;
}) {
  const [form, setForm] = useState({ date: "", open_price: "", high_price: "", low_price: "", close_price: "", volume: "" });
  const [editForm, setEditForm] = useState({ date: "", open_price: "", high_price: "", low_price: "", close_price: "", volume: "" });

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

  async function handleSaveEdit() {
    if (editingId == null) return;
    const o = parseFloat(editForm.open_price), h = parseFloat(editForm.high_price), l = parseFloat(editForm.low_price), c = parseFloat(editForm.close_price);
    if (!editForm.date || Number.isNaN(o) || Number.isNaN(h) || Number.isNaN(l) || Number.isNaN(c)) {
      setError("日付とOHLCは必須です。");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const updated = await updateStockPriceMonthly(editingId, {
        date: editForm.date,
        open_price: o,
        high_price: h,
        low_price: l,
        close_price: c,
        volume: editForm.volume ? parseInt(editForm.volume, 10) : null,
      });
      setRows((prev) => prev.map((r) => (r.id === editingId ? updated : r)));
      setEditingId(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  const startEdit = (r: StockPriceMonthlyRow) => {
    setEditingId(r.id);
    setEditForm({
      date: r.date.slice(0, 10),
      open_price: r.open_price,
      high_price: r.high_price,
      low_price: r.low_price,
      close_price: r.close_price,
      volume: r.volume != null ? String(r.volume) : "",
    });
  };

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

      <h2 className="text-lg font-semibold">一覧</h2>
      <div className="overflow-x-auto rounded border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="border px-2 py-1 text-left">日付</th>
              <th className="border px-2 py-1 text-left">始値</th>
              <th className="border px-2 py-1 text-left">高値</th>
              <th className="border px-2 py-1 text-left">安値</th>
              <th className="border px-2 py-1 text-left">終値</th>
              <th className="border px-2 py-1 text-left">出来高</th>
              <th className="border px-2 py-1 text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                {editingId === r.id ? (
                  <>
                    <td className="border px-2 py-1"><input type="date" value={editForm.date} onChange={(e) => setEditForm((f) => ({ ...f, date: e.target.value }))} className="w-32 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.open_price} onChange={(e) => setEditForm((f) => ({ ...f, open_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.high_price} onChange={(e) => setEditForm((f) => ({ ...f, high_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.low_price} onChange={(e) => setEditForm((f) => ({ ...f, low_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" step="any" value={editForm.close_price} onChange={(e) => setEditForm((f) => ({ ...f, close_price: e.target.value }))} className="w-20 rounded border px-1" /></td>
                    <td className="border px-2 py-1"><input type="number" value={editForm.volume} onChange={(e) => setEditForm((f) => ({ ...f, volume: e.target.value }))} className="w-24 rounded border px-1" /></td>
                    <td className="border px-2 py-1">
                      <button type="button" onClick={handleSaveEdit} disabled={submitting} className="mr-1 rounded bg-teal-600 px-2 py-0.5 text-xs text-white">保存</button>
                      <button type="button" onClick={() => setEditingId(null)} className="rounded border px-2 py-0.5 text-xs">キャンセル</button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="border px-2 py-1">{r.date.slice(0, 10)}</td>
                    <td className="border px-2 py-1">{r.open_price}</td>
                    <td className="border px-2 py-1">{r.high_price}</td>
                    <td className="border px-2 py-1">{r.low_price}</td>
                    <td className="border px-2 py-1">{r.close_price}</td>
                    <td className="border px-2 py-1">{r.volume ?? "-"}</td>
                    <td className="border px-2 py-1">
                      <button type="button" onClick={() => startEdit(r)} className="mr-1 rounded border px-2 py-0.5 text-xs">編集</button>
                      <button type="button" onClick={() => onDelete(r.id)} disabled={deletingId === r.id} className="rounded border border-red-300 px-2 py-0.5 text-xs text-red-700">削除</button>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="text-sm text-slate-500">データがありません。</p>}
    </section>
  );
}
