"use client";

import { useEffect, useState } from "react";
import { request } from "@/lib/api";
import type { ActivationHistoryItem } from "@/types/api";

export default function HistoryPage() {
  const [items, setItems] = useState<ActivationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState<string>("");
  const [activatedId, setActivatedId] = useState<string>("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (reason) params.set("activation_reason", reason);
      if (activatedId) params.set("activated_profile_id", activatedId);
      const path =
        "/api/v1/score-profiles/activation-history/" +
        (params.toString() ? `?${params.toString()}` : "");
      const res = await request<ActivationHistoryItem[]>(path);
      setItems(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilterSubmit(e: React.FormEvent) {
    e.preventDefault();
    void load();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Activation history</h1>
      <form
        onSubmit={handleFilterSubmit}
        className="flex flex-wrap items-end gap-3 rounded border bg-white p-3 text-sm shadow-sm"
      >
        <label className="flex flex-col">
          <span className="mb-1 font-medium">Reason</span>
          <select
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="rounded border px-2 py-1"
          >
            <option value="">(all)</option>
            <option value="manual_activate">manual_activate</option>
            <option value="manual_rollback">manual_rollback</option>
          </select>
        </label>
        <label className="flex flex-col">
          <span className="mb-1 font-medium">Activated profile id</span>
          <input
            value={activatedId}
            onChange={(e) => setActivatedId(e.target.value)}
            className="w-32 rounded border px-2 py-1"
            placeholder="e.g. 1"
          />
        </label>
        <button
          type="submit"
          className="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
        >
          Apply filters
        </button>
      </form>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {loading && <p className="text-sm text-slate-600">Loading...</p>}

      <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
        <table className="min-w-full text-xs md:text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="border px-2 py-1 text-left">Activated at</th>
              <th className="border px-2 py-1 text-left">Reason</th>
              <th className="border px-2 py-1 text-left">Previous</th>
              <th className="border px-2 py-1 text-left">Activated</th>
              <th className="border px-2 py-1 text-left">Source proposal</th>
              <th className="border px-2 py-1 text-left">Note</th>
            </tr>
          </thead>
          <tbody>
            {items.map((h) => (
              <tr key={h.id} className="odd:bg-slate-50">
                <td className="border px-2 py-1">
                  {h.activated_at ? new Date(h.activated_at).toLocaleString() : "-"}
                </td>
                <td className="border px-2 py-1">{h.activation_reason}</td>
                <td className="border px-2 py-1">
                  {h.previous_profile_id
                    ? `${h.previous_profile_name} (${h.previous_profile_version}) [id=${h.previous_profile_id}]`
                    : "-"}
                </td>
                <td className="border px-2 py-1">
                  {`${h.activated_profile_name} (${h.activated_profile_version}) [id=${h.activated_profile_id}]`}
                </td>
                <td className="border px-2 py-1">
                  {h.source_proposal_id
                    ? `${h.source_proposal_name} [id=${h.source_proposal_id}]`
                    : "-"}
                </td>
                <td className="border px-2 py-1">{h.note}</td>
              </tr>
            ))}
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="border px-2 py-2 text-center text-slate-500">
                  No history.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

