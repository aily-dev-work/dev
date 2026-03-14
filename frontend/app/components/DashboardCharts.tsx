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

type SuccessRatePoint = { name: string; rate: number | null };
type AvgReturnPoint = { name: string; return: number | null };

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
        <h2 className="mb-3 text-lg font-semibold">Profile success rate (h20)</h2>
        {successRateData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={successRateData} margin={{ left: 8, right: 8, bottom: 80 }}>
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
        {avgReturnData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={avgReturnData} margin={{ left: 8, right: 8, bottom: 80 }}>
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
  );
}
