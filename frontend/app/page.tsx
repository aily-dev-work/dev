"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { getDashboardStats, request } from "@/lib/api";
import type { DashboardStatsResponse } from "@/types/api";

const DashboardCharts = dynamic(
  () => import("@/app/components/DashboardCharts").then((m) => m.DashboardCharts),
  { ssr: false },
);

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
    if (!confirm("直前のプロファイルにロールバックしますか？")) return;
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
        <h1 className="text-2xl font-semibold">ダッシュボード</h1>
        <p className="text-sm text-slate-600">読み込み中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">ダッシュボード</h1>
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
      <h1 className="text-2xl font-semibold">ダッシュボード</h1>

      {/* Upper cards: current active + counts */}
      <section className="grid gap-4 md:grid-cols-[2fr,1fr]">
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold">現在のアクティブプロファイル</h2>
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
            <p className="text-sm text-slate-600">アクティブなプロファイルがありません。</p>
          )}
          <div className="mt-4">
            <button
              type="button"
              onClick={handleRollback}
              disabled={rollbackLoading}
              className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60"
            >
              {rollbackLoading ? "ロールバック中..." : "直前のプロファイルにロールバック"}
            </button>
          </div>
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-700">運用サマリ</h2>
          <div className="grid gap-2">
            <div className="rounded border bg-white px-3 py-2 text-sm shadow-sm">
              <div className="text-slate-500">古いアクティブ</div>
              <div className="text-xl font-semibold">{ops?.counts.stale_active_count ?? 0}</div>
            </div>
            <div className="rounded border bg-white px-3 py-2 text-sm shadow-sm">
              <div className="text-slate-500">成績不振</div>
              <div className="text-xl font-semibold">{ops?.counts.underperforming_count ?? 0}</div>
            </div>
            <div className="rounded border bg-white px-3 py-2 text-sm shadow-sm">
              <div className="text-slate-500">採用済み・未反映</div>
              <div className="text-xl font-semibold">
                {ops?.counts.accepted_not_activated_count ?? 0}
              </div>
            </div>
          </div>
          {overview && (
            <div className="rounded border bg-slate-50 px-3 py-2 text-xs text-slate-600">
              プロファイル: 合計 {overview.total_count}、アクティブ {overview.active_count}、提案由来 {overview.proposal_derived_count}
            </div>
          )}
        </div>
      </section>

      {/* Charts (client-only to avoid Recharts SSR issues) */}
      <DashboardCharts
        successRateData={successRateChartData}
        avgReturnData={avgReturnChartData}
      />

      {/* Activation timeline (list) */}
      {chartData && chartData.activation_timeline_rows.length > 0 && (
        <section className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold">有効化タイムライン</h2>
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
            <h2 className="text-lg font-semibold">比較スナップショット</h2>
            <Link
              href="/profiles/compare"
              className="text-sm text-blue-600 hover:underline"
            >
              比較画面を開く →
            </Link>
          </div>
          <div className="grid gap-3 text-sm md:grid-cols-2">
            <div className="rounded border bg-slate-50 p-2">
              <div className="text-xs font-semibold text-slate-500">ベース</div>
              {data.compare_snapshot.base_profile.name} ({data.compare_snapshot.base_profile.version})
            </div>
            <div className="rounded border bg-slate-50 p-2">
              <div className="text-xs font-semibold text-slate-500">候補</div>
              {data.compare_snapshot.candidate_profile.name} (
              {data.compare_snapshot.candidate_profile.version})
            </div>
          </div>
        </section>
      )}

      {/* Recent activation history table */}
      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">直近の有効化履歴</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full border text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="border px-2 py-1 text-left">有効化日時</th>
                <th className="border px-2 py-1 text-left">理由</th>
                <th className="border px-2 py-1 text-left">直前</th>
                <th className="border px-2 py-1 text-left">有効化後</th>
                <th className="border px-2 py-1 text-left">メモ</th>
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
                    履歴がありません。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* message_lines */}
      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">メッセージ</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-800">
          {ops?.message_lines.map((line, idx) => (
            <li key={idx}>{line}</li>
          )) ?? <li className="text-slate-500">メッセージはありません。</li>}
        </ul>
      </section>
    </div>
  );
}
