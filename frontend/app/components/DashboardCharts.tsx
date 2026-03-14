"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type SuccessRatePoint = { name: string; rate: number | null; horizonDays?: number };
type AvgReturnPoint = { name: string; return: number | null; horizonDays?: number };

export function DashboardCharts({
  successRateData,
  avgReturnData,
}: {
  successRateData: SuccessRatePoint[];
  avgReturnData: AvgReturnPoint[];
}) {
  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-1 text-lg font-semibold">プロファイル成功率</h2>
        <p className="mb-3 text-xs text-slate-500">
          評価期間はプロファイルのトレードスタイル別（デイトレ=5営業日・短期=10営業日・長期=20営業日）
        </p>
        {successRateData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={successRateData} margin={{ left: 8, right: 8, bottom: 80 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                <Tooltip
                  content={({ active, payload }) =>
                    active && payload?.[0] ? (
                      <div className="rounded border border-slate-200 bg-white px-2 py-1.5 text-sm shadow">
                        <div>{payload[0].payload.name}</div>
                        <div>成功率: {payload[0].value != null ? Number(payload[0].value).toFixed(2) : "-"}</div>
                        {payload[0].payload.horizonDays != null && (
                          <div className="text-slate-500">評価: {payload[0].payload.horizonDays}営業日</div>
                        )}
                      </div>
                    ) : null
                  }
                />
                <Bar dataKey="rate" name="成功率" fill="#475569" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-sm text-slate-500">データがありません。</p>
        )}
      </div>
      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="mb-1 text-lg font-semibold">プロファイル平均リターン</h2>
        <p className="mb-3 text-xs text-slate-500">
          評価期間はプロファイルのトレードスタイル別（デイトレ=5営業日・短期=10営業日・長期=20営業日）
        </p>
        {avgReturnData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={avgReturnData} margin={{ left: 8, right: 8, bottom: 80 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  content={({ active, payload }) =>
                    active && payload?.[0] ? (
                      <div className="rounded border border-slate-200 bg-white px-2 py-1.5 text-sm shadow">
                        <div>{payload[0].payload.name}</div>
                        <div>
                          平均リターン:{" "}
                          {payload[0].value != null ? Number(payload[0].value).toFixed(4) : "-"}
                        </div>
                        {payload[0].payload.horizonDays != null && (
                          <div className="text-slate-500">評価: {payload[0].payload.horizonDays}営業日</div>
                        )}
                      </div>
                    ) : null
                  }
                />
                <Bar dataKey="return" name="平均リターン" fill="#0f766e" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-sm text-slate-500">データがありません。</p>
        )}
      </div>
    </section>
  );
}
