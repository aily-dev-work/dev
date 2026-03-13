"use client";

import { useEffect, useState } from "react";
import { request } from "@/lib/api";
import type { OpsSummaryResponse, ActivationHistoryItem } from "@/types/api";

type CurrentProfileDetail = {
  id: number;
  name: string;
  version: string;
  is_active: boolean;
  description: string;
};

export default function DashboardPage() {
  const [ops, setOps] = useState<OpsSummaryResponse | null>(null);
  const [currentDetail, setCurrentDetail] = useState<CurrentProfileDetail | null>(null);
  const [history, setHistory] = useState<ActivationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rollbackLoading, setRollbackLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [opsRes, histRes] = await Promise.all([
        request<OpsSummaryResponse>("/api/v1/score-profiles/ops-summary/"),
        request<ActivationHistoryItem[]>("/api/v1/score-profiles/activation-history/"),
      ]);
      setOps(opsRes);
      setHistory(histRes.slice(0, 10));
      if (opsRes.current_active_profile) {
        const current = await request<CurrentProfileDetail>(
          "/api/v1/score-profiles/current/",
        );
        setCurrentDetail(current);
      } else {
        setCurrentDetail(null);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleRollback() {
    if (!confirm("Rollback to previous profile?")) return;
    setRollbackLoading(true);
    setError(null);
    try {
      await request("/api/v1/score-profiles/rollback/", {
        method: "POST",
        body: JSON.stringify({ note: "rollback from dashboard" }),
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRollbackLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {loading && <p className="text-sm text-slate-600">Loading...</p>}

      {/* Active profile card */}
      <section className="grid gap-4 md:grid-cols-[2fr,1fr]">
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold">Current active profile</h2>
          {ops?.current_active_profile && currentDetail ? (
            <div className="space-y-1">
              <div className="text-base font-medium">
                {currentDetail.name}{" "}
                <span className="text-slate-500">({currentDetail.version})</span>
              </div>
              <div className="text-xs text-slate-500">
                id={currentDetail.id} / active={String(currentDetail.is_active)}
              </div>
              {currentDetail.description && (
                <p className="mt-1 text-sm text-slate-700">{currentDetail.description}</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-600">No active profile configured.</p>
          )}
          <div className="mt-4">
            <button
              type="button"
              onClick={handleRollback}
              disabled={rollbackLoading}
              className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60"
            >
              {rollbackLoading ? "Rolling back..." : "Rollback to previous profile"}
            </button>
          </div>
        </div>

        {/* Counts */}
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-700">Ops summary</h2>
          <div className="grid gap-2">
            <div className="rounded border bg-white px-3 py-2 text-sm shadow-sm">
              <div className="text-slate-500">Stale active profiles</div>
              <div className="text-xl font-semibold">
                {ops?.counts.stale_active_count ?? 0}
              </div>
            </div>
            <div className="rounded border bg-white px-3 py-2 text-sm shadow-sm">
              <div className="text-slate-500">Underperforming profiles</div>
              <div className="text-xl font-semibold">
                {ops?.counts.underperforming_count ?? 0}
              </div>
            </div>
            <div className="rounded border bg-white px-3 py-2 text-sm shadow-sm">
              <div className="text-slate-500">Accepted not activated</div>
              <div className="text-xl font-semibold">
                {ops?.counts.accepted_not_activated_count ?? 0}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* message_lines */}
      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">Messages</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-800">
          {ops?.message_lines.map((line, idx) => (
            <li key={idx}>{line}</li>
          )) ?? <li className="text-slate-500">No messages.</li>}
        </ul>
      </section>

      {/* recent activation history */}
      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent activation history</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full border text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="border px-2 py-1 text-left">Activated at</th>
                <th className="border px-2 py-1 text-left">Reason</th>
                <th className="border px-2 py-1 text-left">Previous</th>
                <th className="border px-2 py-1 text-left">Activated</th>
                <th className="border px-2 py-1 text-left">Note</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id} className="odd:bg-slate-50">
                  <td className="border px-2 py-1">
                    {h.activated_at ?? "-"}
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
                  <td className="border px-2 py-1">{h.note}</td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan={5} className="border px-2 py-2 text-center text-slate-500">
                    No history.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

