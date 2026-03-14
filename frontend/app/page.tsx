"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { getDashboardStats, getStocksScores, getRecentSignals } from "@/lib/api";
import type { DashboardStatsResponse, RecentSignalItem, StockScoreItem } from "@/types/api";

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
  const [recentSignals, setRecentSignals] = useState<RecentSignalItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [res, scoresRes, signalsRes] = await Promise.all([
        getDashboardStats(),
        getStocksScores().catch(() => ({ stocks: [] as StockScoreItem[] })),
        getRecentSignals(30).catch(() => [] as RecentSignalItem[]),
      ]);
      setData(res);
      setStockScores(Array.isArray(scoresRes?.stocks) ? scoresRes.stocks : []);
      setRecentSignals(Array.isArray(signalsRes) ? signalsRes : []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

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
  const chartData = data?.chart_data;
  const activeId = data?.current_active_profile?.id;
  const isUnderperforming =
    activeId != null &&
    (ops?.underperforming_profiles?.some((p) => p.id === activeId) ?? false);
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

      {/* 使用中プロファイル + 成績 */}
      <section className="flex flex-wrap items-center gap-4 text-sm">
        <span className="font-medium text-slate-700">
          使用中プロファイル:{" "}
          {data?.current_active_profile
            ? displayProfileName(data.current_active_profile.name)
            : "—"}
        </span>
        {data?.current_active_profile && (
          <span
            className={
              isUnderperforming
                ? "rounded bg-amber-100 px-2 py-0.5 font-medium text-amber-800"
                : "rounded bg-slate-100 px-2 py-0.5 text-slate-700"
            }
          >
            成績: {isUnderperforming ? "要見直し" : "良好"}
          </span>
        )}
      </section>

      {/* 直近のシグナル発報（スコアの上に表示） */}
      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold">直近のシグナル発報</h2>
        {recentSignals && recentSignals.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full border text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className="border px-2 py-1 text-center">発報日時</th>
                  <th className="border px-2 py-1 text-left">銘柄</th>
                  <th className="border px-2 py-1 text-center">シグナル</th>
                  <th className="border px-2 py-1 text-center">強さ</th>
                  <th className="border px-2 py-1 text-right">価格</th>
                </tr>
              </thead>
              <tbody>
                {recentSignals.map((sig) => (
                  <tr key={sig.id} className="odd:bg-slate-50">
                    <td className="border px-2 py-1 text-center text-slate-600">
                      {sig.created_at
                        ? new Date(sig.created_at).toLocaleString("ja-JP")
                        : sig.signal_date}
                    </td>
                    <td className="border px-2 py-1">
                      <span className="font-mono">{sig.ticker}</span>
                      <span className="ml-1 text-slate-600">{sig.stock_name}</span>
                    </td>
                    <td className="border px-2 py-1 text-center font-medium">
                      {sig.signal_type === "buy" && <span className="text-emerald-700">買い</span>}
                      {sig.signal_type === "sell" && <span className="text-red-700">売り</span>}
                      {sig.signal_type === "neutral" && <span className="text-slate-600">様子見</span>}
                    </td>
                    <td className="border px-2 py-1 text-center text-xs text-slate-600">
                      {sig.score_strength}
                    </td>
                    <td className="border px-2 py-1 text-right font-mono text-slate-700">
                      {sig.signal_price ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-500">発報されたシグナルはありません。</p>
        )}
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
