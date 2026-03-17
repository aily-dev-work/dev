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
      const [statsResult, scoresResult, signalsResult] = await Promise.allSettled([
        getDashboardStats(),
        getStocksScores(),
        getRecentSignals(100),
      ]);

      if (statsResult.status === "fulfilled") {
        setData(statsResult.value);
      } else {
        const message =
          statsResult.reason instanceof Error
            ? statsResult.reason.message
            : "ダッシュボード統計の取得に失敗しました。";
        setError(message);
        setData(null);
        setStockScores(null);
        setRecentSignals(null);
        return;
      }

      if (scoresResult.status === "fulfilled") {
        const scoresValue = scoresResult.value as { stocks?: StockScoreItem[] };
        setStockScores(
          Array.isArray(scoresValue?.stocks) ? (scoresValue.stocks as StockScoreItem[]) : [],
        );
      } else {
        setStockScores([]);
      }

      if (signalsResult.status === "fulfilled") {
        const signalsValue = signalsResult.value as RecentSignalItem[];
        const list = Array.isArray(signalsValue) ? signalsValue : [];
        setRecentSignals(list);
      } else {
        setRecentSignals([]);
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

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">ダッシュボード</h1>
        <p className="text-sm text-slate-600">読み込み中...</p>
        <p className="text-xs text-slate-500">
          初回はサーバー起動のため1分ほどかかることがあります。しばらく待っても表示されない場合は「再試行」を押してください。
        </p>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          再試行
        </button>
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

  const chartData = data?.chart_data;
  const performanceLevel = data?.current_active_profile?.performance_level;
  const successRateChartData =
    chartData?.profile_success_rate_rows.map((r) => ({
      name: formatLabel(r),
      rate: r.success_rate_h20 != null ? Math.round(r.success_rate_h20 * 100) / 100 : null,
      horizonDays: r.evaluation_horizon_days ?? 20,
    })) ?? [];
  const avgReturnChartData =
    chartData?.profile_avg_return_rows.map((r) => ({
      name: formatLabel(r),
      return: r.avg_return_h20,
      horizonDays: r.evaluation_horizon_days ?? 20,
    })) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">ダッシュボード</h1>

      {/* 使用中プロファイル + 成績（5段階+未判定） */}
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
              performanceLevel === "excellent"
                ? "rounded bg-emerald-100 px-2 py-0.5 font-medium text-emerald-800"
                : performanceLevel === "good"
                  ? "rounded bg-teal-100 px-2 py-0.5 font-medium text-teal-800"
                  : performanceLevel === "average"
                    ? "rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-700"
                    : performanceLevel === "needs_review"
                      ? "rounded bg-amber-100 px-2 py-0.5 font-medium text-amber-800"
                      : performanceLevel === "poor"
                        ? "rounded bg-red-100 px-2 py-0.5 font-medium text-red-800"
                        : "rounded bg-slate-200 px-2 py-0.5 text-slate-600"
            }
          >
            成績:{" "}
            {performanceLevel === "excellent"
              ? "優秀"
              : performanceLevel === "good"
                ? "良好"
                : performanceLevel === "average"
                  ? "普通"
                  : performanceLevel === "needs_review"
                    ? "要見直し"
                    : performanceLevel === "poor"
                      ? "要改善"
                      : "未判定"}
          </span>
        )}
      </section>

      {/* 直近のシグナル発報（スコアの上に表示） */}
      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold">直近のシグナル発報</h2>
        {recentSignals && recentSignals.length > 0 ? (
          <div className="max-h-80 overflow-y-auto overflow-x-auto">
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
            {data?.current_active_profile ? (
              <>
                上記の<strong>使用中プロファイル</strong>（{displayProfileName(data.current_active_profile.name)}）で算出した
                買い％・売り％・様子見％および<strong>現在の判定</strong>を表示しています。
              </>
            ) : (
              "使用中プロファイルで算出したスコアを％で表示しています。"
            )}
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full table-fixed border text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className="border px-2 py-1 text-left w-24">銘柄コード</th>
                  <th className="border px-2 py-1 text-left min-w-0">銘柄名</th>
                  <th className="border px-2 py-1 text-center w-[10%]">買い％</th>
                  <th className="border px-2 py-1 text-center w-[10%]">売り％</th>
                  <th className="border px-2 py-1 text-center w-[10%]">様子見％</th>
                  <th className="border px-2 py-1 text-center w-[10%]">現在の判定</th>
                  <th className="border px-2 py-1 text-center w-[10%]">長期トレンド</th>
                  <th className="border px-2 py-1 text-center w-[10%]">短期トレンド</th>
                </tr>
              </thead>
              <tbody>
                {stockScores.map((s) => (
                  <tr key={s.stock_id} className="odd:bg-slate-50">
                    <td className="border px-2 py-1 font-mono w-24">{s.ticker}</td>
                    <td className="border px-2 py-1 min-w-0">{s.name || "-"}</td>
                    <td className="border px-2 py-1 text-center w-[10%]">
                      {s.insufficient_data ? (
                        <span className="text-slate-400">-</span>
                      ) : (
                        <span className="font-medium text-emerald-700">{s.buy_pct}%</span>
                      )}
                    </td>
                    <td className="border px-2 py-1 text-center w-[10%]">
                      {s.insufficient_data ? (
                        <span className="text-slate-400">-</span>
                      ) : (
                        <span className="font-medium text-red-700">{s.sell_pct}%</span>
                      )}
                    </td>
                    <td className="border px-2 py-1 text-center w-[10%]">
                      {s.insufficient_data ? (
                        <span className="text-slate-400">-</span>
                      ) : (
                        <span className="text-slate-600">{s.wait_pct}%</span>
                      )}
                    </td>
                    <td className="border px-2 py-1 text-center text-xs w-[10%]">
                      {s.insufficient_data ? (
                        <span className="text-amber-600">データ不足</span>
                      ) : s.bias === "buy" ? (
                        <span>
                          <span className="font-bold text-emerald-700">買い</span>
                          <span className="text-slate-500"> / </span>
                          <span
                            className={
                              s.strength === "weak"
                                ? "text-emerald-500"
                                : s.strength === "strong"
                                  ? "text-emerald-800"
                                  : "text-emerald-600"
                            }
                          >
                            {s.strength}
                          </span>
                        </span>
                      ) : s.bias === "sell" ? (
                        <span>
                          <span className="font-bold text-red-700">売り</span>
                          <span className="text-slate-500"> / </span>
                          <span
                            className={
                              s.strength === "weak"
                                ? "text-red-500"
                                : s.strength === "strong"
                                  ? "text-red-800"
                                  : "text-red-600"
                            }
                          >
                            {s.strength}
                          </span>
                        </span>
                      ) : (
                        <span className="text-slate-600">
                          様子見{s.strength ? ` / ${s.strength}` : ""}
                        </span>
                      )}
                    </td>
                    <td className="border px-2 py-1 text-center text-xs w-[10%]">
                      {s.long_term_trend === "up" && <span className="text-emerald-700">上昇</span>}
                      {s.long_term_trend === "neutral" && <span className="text-slate-600">中立</span>}
                      {s.long_term_trend === "down" && <span className="text-red-700">下降</span>}
                      {(!s.long_term_trend || !["up", "neutral", "down"].includes(s.long_term_trend)) && <span className="text-slate-400">-</span>}
                    </td>
                    <td className="border px-2 py-1 text-center text-xs w-[10%]">
                      {s.short_term_trend === "up" && <span className="text-emerald-700">上昇</span>}
                      {s.short_term_trend === "neutral" && <span className="text-slate-600">中立</span>}
                      {s.short_term_trend === "down" && <span className="text-red-700">下降</span>}
                      {(!s.short_term_trend || !["up", "neutral", "down"].includes(s.short_term_trend)) && <span className="text-slate-400">-</span>}
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

      {/* Charts (client-only to avoid Recharts SSR issues). 評価期間はプロファイルのトレードスタイル別（デイトレ5日・短期10日・長期20日）。 */}
      <DashboardCharts
        successRateData={successRateChartData}
        avgReturnData={avgReturnChartData}
      />
    </div>
  );
}
