"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { getDashboardStats, getStocksScores, request } from "@/lib/api";
import type { DashboardStatsResponse, StockScoreItem } from "@/types/api";

const DashboardCharts = dynamic(
  () => import("@/app/components/DashboardCharts").then((m) => m.DashboardCharts),
  { ssr: false },
);

/** API のプロファイル名・説明を表示用に日本語化（よくある初期値のみ） */
function displayProfileName(name: string): string {
  if (name === "Default scoring profile") return "デフォルトスコアプロファイル";
  return name;
}
function displayProfileDescription(desc: string): string {
  if (desc.includes("Initial profile migrated from hardcoded signal_scoring.py")) {
    return "フェーズ4の signal_scoring.py から移行した初期プロファイル。";
  }
  return desc;
}

function formatLabel(row: { profile_name: string; profile_version: string; signal_type: string }) {
  return `${row.profile_name} ${row.profile_version} - ${row.signal_type}`;
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardStatsResponse | null>(null);
  const [stockScores, setStockScores] = useState<StockScoreItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rollbackLoading, setRollbackLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [res, scoresRes] = await Promise.all([
        getDashboardStats(),
        getStocksScores().catch(() => ({ stocks: [] as StockScoreItem[] })),
      ]);
      setData(res);
      setStockScores(Array.isArray(scoresRes?.stocks) ? scoresRes.stocks : []);
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
                {displayProfileName(data.current_active_profile.name)}{" "}
                <span className="text-slate-500">({data.current_active_profile.version})</span>
              </div>
              <div className="text-xs text-slate-500">
                id={data.current_active_profile.id}
              </div>
              {data.current_active_profile.description && (
                <p className="mt-1 text-sm text-slate-700">
                  {displayProfileDescription(data.current_active_profile.description)}
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

      {/* 監視銘柄のスコア（買い・売り・様子見 ％） */}
      {stockScores && stockScores.length > 0 && (
        <section className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold">監視銘柄のスコア（買い・売り・様子見）</h2>
          <p className="mb-3 text-xs text-slate-500">
            現在のアクティブプロファイルで算出したスコアを％で表示しています。
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full border text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className="border px-2 py-1 text-left">銘柄コード</th>
                  <th className="border px-2 py-1 text-left">銘柄名</th>
                  <th className="border px-2 py-1 text-center">買い％</th>
                  <th className="border px-2 py-1 text-center">売り％</th>
                  <th className="border px-2 py-1 text-center">様子見％</th>
                  <th className="border px-2 py-1 text-center">判定</th>
                </tr>
              </thead>
              <tbody>
                {stockScores.map((s) => (
                  <tr key={s.stock_id} className="odd:bg-slate-50">
                    <td className="border px-2 py-1 font-mono">{s.ticker}</td>
                    <td className="border px-2 py-1">{s.name || "-"}</td>
                    <td className="border px-2 py-1 text-center">
                      {s.insufficient_data ? (
                        <span className="text-slate-400">-</span>
                      ) : (
                        <span className="font-medium text-emerald-700">{s.buy_pct}%</span>
                      )}
                    </td>
                    <td className="border px-2 py-1 text-center">
                      {s.insufficient_data ? (
                        <span className="text-slate-400">-</span>
                      ) : (
                        <span className="font-medium text-red-700">{s.sell_pct}%</span>
                      )}
                    </td>
                    <td className="border px-2 py-1 text-center">
                      {s.insufficient_data ? (
                        <span className="text-slate-400">-</span>
                      ) : (
                        <span className="text-slate-600">{s.wait_pct}%</span>
                      )}
                    </td>
                    <td className="border px-2 py-1 text-center text-xs">
                      {s.insufficient_data ? (
                        <span className="text-amber-600">データ不足</span>
                      ) : (
                        <span>
                          {s.bias === "buy" && "買い"}
                          {s.bias === "sell" && "売り"}
                          {s.bias === "neutral" && "様子見"} / {s.strength}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {stockScores && stockScores.length === 0 && data?.current_active_profile && (
        <section className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          <h2 className="mb-1 font-semibold text-slate-700">監視銘柄のスコア</h2>
          <p>監視銘柄がありません。銘柄を追加すると、ここに買い・売り・様子見の％が表示されます。</p>
        </section>
      )}

      {stockScores && stockScores.length === 0 && !data?.current_active_profile && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <h2 className="mb-1 font-semibold">監視銘柄のスコア</h2>
          <p>アクティブなプロファイルを設定すると、監視銘柄の買い・売り・様子見の％がここに表示されます。</p>
          <Link href="/profiles" className="mt-2 inline-block text-amber-700 underline hover:no-underline">
            プロファイルを設定 →
          </Link>
        </section>
      )}

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
