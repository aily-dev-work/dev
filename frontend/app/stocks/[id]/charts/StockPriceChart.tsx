"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type ChartPoint = {
  label: string;
  fullLabel: string;
  close: number;
  open?: number;
  high?: number;
  low?: number;
  volume?: number | null;
};

export default function StockPriceChart({ data }: { data: ChartPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ left: 8, right: 8, bottom: 24 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="label"
          angle={-45}
          textAnchor="end"
          height={56}
          tick={{ fontSize: 10 }}
          interval="preserveStartEnd"
        />
        <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value: unknown) =>
            typeof value === "number" ? value.toFixed(2) : value
          }
          labelFormatter={(_, payload) =>
            payload?.[0]?.payload?.fullLabel ?? ""
          }
        />
        <Line
          type="monotone"
          dataKey="close"
          name="終値"
          stroke="#0f766e"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
