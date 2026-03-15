"use client";

/** 一覧用: 買い・売りの重みを積み上げ棒グラフで表示。ホバーで％を表示。 */
const BUY_KEYS = [
  "trend_long_up",
  "trend_mid_up",
  "trend_short_up",
  "volume_high",
  "above_ma25",
  "above_ma75",
  "near_high_20",
  "near_low_20",
] as const;
const SELL_KEYS = [
  "trend_long_down",
  "trend_mid_down",
  "trend_short_down",
  "volume_low",
  "below_ma25",
  "below_ma75",
  "near_low_20",
  "near_high_20",
] as const;

const SEGMENT_LABELS: Record<string, string> = {
  trend_long_up: "長期上",
  trend_mid_up: "中期上",
  trend_short_up: "短期上",
  volume_high: "出来高",
  above_ma25: "MA25上",
  above_ma75: "MA75上",
  near_high_20: "高値20",
  near_low_20: "安値20",
  trend_long_down: "長期下",
  trend_mid_down: "中期下",
  trend_short_down: "短期下",
  volume_low: "出来低",
  below_ma25: "MA25下",
  below_ma75: "MA75下",
};

const SEGMENT_COLORS = [
  "bg-teal-600",
  "bg-teal-700",
  "bg-emerald-600",
  "bg-emerald-700",
  "bg-cyan-600",
  "bg-slate-600",
  "bg-amber-600",
  "bg-amber-700",
];
const SEGMENT_COLORS_SELL = [
  "bg-red-600",
  "bg-red-700",
  "bg-orange-600",
  "bg-orange-700",
  "bg-amber-700",
  "bg-slate-700",
  "bg-rose-600",
  "bg-rose-700",
];

function toPcts(
  raw: Record<string, unknown>,
  keys: readonly string[],
): { key: string; pct: number }[] {
  const values = keys.map((k) => {
    const v = raw[k];
    const n = typeof v === "number" && !Number.isNaN(v) ? v : typeof v === "string" ? parseFloat(v) : 0;
    return Number.isNaN(n) ? 0 : n;
  });
  const sum = values.reduce((a, b) => a + b, 0);
  const scale = sum > 0 ? 100 / sum : 0;
  return keys.map((key, i) => ({
    key,
    pct: Math.round(values[i]! * scale * 10) / 10,
  }));
}

export function ProfileWeightsMiniChart({ weightsJson }: { weightsJson: unknown }) {
  const o = weightsJson && typeof weightsJson === "object" ? (weightsJson as Record<string, unknown>) : {};
  const buyRaw = (o.buy && typeof o.buy === "object" ? o.buy : {}) as Record<string, unknown>;
  const sellRaw = (o.sell && typeof o.sell === "object" ? o.sell : {}) as Record<string, unknown>;

  const buyPcts = toPcts(buyRaw, [...BUY_KEYS]);
  const sellPcts = toPcts(sellRaw, [...SELL_KEYS]);
  const buySum = buyPcts.reduce((a, b) => a + b.pct, 0);
  const sellSum = sellPcts.reduce((a, b) => a + b.pct, 0);
  if (buySum === 0 && sellSum === 0) {
    return <span className="text-xs text-slate-400">-</span>;
  }

  const BarRow = ({
    label,
    pcts,
    colors,
  }: {
    label: string;
    pcts: { key: string; pct: number }[];
    colors: string[];
  }) => (
    <div className="flex items-center gap-1">
      <span className="w-6 shrink-0 text-[10px] text-slate-500">{label}</span>
      <div className="flex h-9 w-[450px] min-w-[450px] overflow-hidden rounded bg-slate-100" title={`${label}の重み（％）`}>
        {pcts.map(({ key, pct }, i) =>
          pct > 0 ? (
            <span
              key={key}
              className={`flex shrink-0 flex-col items-center justify-center ${colors[i] ?? "bg-slate-300"}`}
              style={{ width: `${pct}%`, minWidth: pct >= 6 ? "auto" : "2px" }}
              title={`${SEGMENT_LABELS[key] ?? key}: ${pct}％`}
            >
              {pct >= 6 ? (
                <>
                  <span className="truncate max-w-full text-[9px] leading-tight text-white drop-shadow-[0_0_1px_rgba(0,0,0,0.8)]">
                    {SEGMENT_LABELS[key] ?? key}
                  </span>
                  <span className="text-[10px] font-medium text-white drop-shadow-[0_0_1px_rgba(0,0,0,0.8)]">
                    {pct}%
                  </span>
                </>
              ) : null}
            </span>
          ) : null,
        )}
      </div>
    </div>
  );

  return (
    <div className="w-[450px] min-w-[450px] space-y-1.5">
      <BarRow label="買" pcts={buyPcts} colors={SEGMENT_COLORS} />
      <BarRow label="売" pcts={sellPcts} colors={SEGMENT_COLORS_SELL} />
    </div>
  );
}
