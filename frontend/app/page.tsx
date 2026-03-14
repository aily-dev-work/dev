"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getDashboardStats, request } from "@/lib/api";
import type { DashboardStatsResponse } from "@/types/api";

function formatLabel(row: { profile_name: string; profile_version: string; signal_type: string }) {
  return `${row.profile_name} ${row.profile_version} - ${row.signal_type}`;
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rollbackLoading, setRollbackLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await getDashboardStats();
      setData(res);
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

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-slate-600">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      </div>
    );
  }

  const ops = data?.ops_summary;
  const overview = data?.profile_overview;
  const chartData = data?.chart_data;
  const successRateChartData =
    chartData?.profile_success_rate_rows.map((r) => ({
      name: formatLabel(r),
      rate: r.success_rate_h20 != null ? Math.round(r.success_rate_h20 * 100) / 100 : null,
    })) ?? [];
  const avgReturnChartData =
    chartData?.profile_avg_return_rows.map((r) => ({
      name: formatLabel(r),
      return: r.avg_return_h20,
    })) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      {/* Upper cards: current active + counts */}
      <section className="grid gap-4 md:grid-cols-[2fr,1fr]">
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold">Current active profile</h2>
          {data?.current_active_profile ? (
            <div className="space-y-1">
              <div className="text-base font-medium">
                {data.current_active_profile.name}{" "}
                <span className="text-slate-500">({data.current_active_profile.version})</span>
              </div>
              <div className="text-xs text-slate-500">
                id={data.current_active_profile.id}
              </div>
              {data.current_active_profile.description && (
                <p className="mt-1 text-sm text-slate-700">
                  {data.current_active_profile.description}
                </p>
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

        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-700">Ops summary</h2>
          <div className="grid gap-2">
            <div className="rounded border bg-white px-3 py-2 text-sm shadow-sm">
              <div className="text-slate-500">Stale active</div>
              <div className="text-xl font-semibold">{ops?.counts.stale_active_count ?? 0}</div>
            </div>
            <div className="rounded border bg-white px-3 py-2 text-sm shadow-sm">
              <div className="text-slate-500">Underperforming</div>
              <div className="text-xl font-semibold">{ops?.counts.underperforming_count ?? 0}</div>
            </div>
            <div className="rounded border bg-white px-3 py-2 text-sm shadow-sm">
              <div className="text-slate-500">Accepted not activated</div>
              <div className="text-xl font-semibold">
                {ops?.counts.accepted_not_activated_count ?? 0}
              </div>
            </div>
          </div>
          {overview && (
            <div className="rounded border bg-slate-50 px-3 py-2 text-xs text-slate-600">
              Profiles: {overview.total_count} total, {overview.active_count} active,{" "}
              {overview.proposal_derived_count} from proposals
            </div>
          )}
        </div>
      </section>

      {/* Charts */}
      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold">Profile success rate (h20)</h2>
          {successRateChartData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={successRateChartData} margin={{ left: 8, right: 8, bottom: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: unknown) => (v != null && typeof v === "number" ? v.toFixed(2) : "-")} />
                  <Bar dataKey="rate" name="Success rate" fill="#475569" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500">No data.</p>
          )}
        </div>
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold">Profile avg return (h20)</h2>
          {avgReturnChartData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={avgReturnChartData} margin={{ left: 8, right: 8, bottom: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: unknown) => (v != null && typeof v === "number" ? v.toFixed(4) : "-")} />
                  <Bar dataKey="return" name="Avg return" fill="#0f766e" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500">No data.</p>
          )}
        </div>
      </section>

      {/* Activation timeline (list) */}
      {chartData && chartData.activation_timeline_rows.length > 0 && (
        <section className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold">Activation timeline</h2>
          <ul className="space-y-1 text-sm">
            {chartData.activation_timeline_rows.slice(0, 15).map((row, idx) => (
              <li key={idx} className="flex flex-wrap gap-2 border-b border-slate-100 py-1">
                <span className="text-slate-500">{row.activated_at ?? "-"}</span>
                <span className="font-medium">
                  {row.activated_profile_name ?? "?"} ({row.activated_profile_version ?? "?"})
                </span>
                <span className="text-slate-500">{row.activation_reason}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Compare snapshot */}
      {data?.compare_snapshot && (
        <section className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Compare snapshot</h2>
            <Link
              href="/profiles/compare"
              className="text-sm text-blue-600 hover:underline"
            >
              Open Compare →
            </Link>
          </div>
          <div className="grid gap-3 text-sm md:grid-cols-2">
            <div className="rounded border bg-slate-50 p-2">
              <div className="text-xs font-semibold text-slate-500">Base</div>
              {data.compare_snapshot.base_profile.name} ({data.compare_snapshot.base_profile.version})
            </div>
            <div className="rounded border bg-slate-50 p-2">
              <div className="text-xs font-semibold text-slate-500">Candidate</div>
              {data.compare_snapshot.candidate_profile.name} (
              {data.compare_snapshot.candidate_profile.version})
            </div>
          </div>
        </section>
      )}

      {/* Recent activation history table */}
      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">Recent activation history</h2>
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
              {data?.recent_activation_history.map((h) => (
                <tr key={h.id} className="odd:bg-slate-50">
                  <td className="border px-2 py-1">{h.activated_at ?? "-"}</td>
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
              {(!data?.recent_activation_history?.length) && (
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

      {/* message_lines */}
      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">Messages</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-800">
          {ops?.message_lines.map((line, idx) => (
            <li key={idx}>{line}</li>
          )) ?? <li className="text-slate-500">No messages.</li>}
        </ul>
      </section>
    </div>
  );
}
