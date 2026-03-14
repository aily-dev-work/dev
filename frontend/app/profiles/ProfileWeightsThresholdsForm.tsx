"use client";

/** API とやりとりする重みの型（買い/売りごとのキー→数値） */
export type WeightsFormValue = {
  buy: Record<string, number>;
  sell: Record<string, number>;
};

/** API とやりとりする閾値の型 */
export type ThresholdsFormValue = {
  bias: Record<string, number>;
  strength: Record<string, number>;
};

const WEIGHT_LABELS: { side: "buy" | "sell"; key: string; label: string; description: string }[] = [
  { side: "buy", key: "trend_long_up", label: "長期トレンドが上向きのとき", description: "重要度（％）" },
  { side: "buy", key: "trend_mid_up", label: "中期トレンドが上向きのとき", description: "重要度（％）" },
  { side: "buy", key: "trend_short_up", label: "短期トレンドが上向きのとき", description: "重要度（％）" },
  { side: "buy", key: "volume_high", label: "出来高が多いとき", description: "重要度（％）" },
  { side: "buy", key: "above_ma25", label: "株価が25日移動平均より上にあるとき", description: "重要度（％）" },
  { side: "buy", key: "above_ma75", label: "株価が75日移動平均より上にあるとき", description: "重要度（％）" },
  { side: "buy", key: "near_high_20", label: "直近20日の高値付近にいるとき", description: "重要度（％）" },
  { side: "buy", key: "near_low_20", label: "直近20日の安値付近にいるとき", description: "重要度（％）" },
  { side: "sell", key: "trend_long_down", label: "長期トレンドが下向きのとき", description: "重要度（％）" },
  { side: "sell", key: "trend_mid_down", label: "中期トレンドが下向きのとき", description: "重要度（％）" },
  { side: "sell", key: "trend_short_down", label: "短期トレンドが下向きのとき", description: "重要度（％）" },
  { side: "sell", key: "volume_low", label: "出来高が少ないとき", description: "重要度（％）" },
  { side: "sell", key: "below_ma25", label: "株価が25日移動平均より下にあるとき", description: "重要度（％）" },
  { side: "sell", key: "below_ma75", label: "株価が75日移動平均より下にあるとき", description: "重要度（％）" },
  { side: "sell", key: "near_low_20", label: "直近20日の安値付近にいるとき", description: "重要度（％）" },
  { side: "sell", key: "near_high_20", label: "直近20日の高値付近にいるとき", description: "重要度（％）" },
];

const THRESHOLD_LABELS: { group: "bias" | "strength"; key: string; label: string; description: string }[] = [
  {
    group: "bias",
    key: "neutral_abs_diff_lt",
    label: "「様子見」と判定する境界",
    description: "買いスコアと売りスコアの差が、このポイント数未満なら「様子見」になります。",
  },
  {
    group: "strength",
    key: "weak_abs_diff_lt",
    label: "シグナル強度「弱」の境界",
    description: "スコア差がこのポイント数未満なら、シグナルは「弱」と表示されます。",
  },
  {
    group: "strength",
    key: "normal_abs_diff_lt",
    label: "シグナル強度「通常」の境界",
    description: "スコア差がこのポイント数未満なら「通常」、以上なら「強」と表示されます。",
  },
];

function toNumber(v: unknown): number {
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  if (typeof v === "string") {
    const n = parseFloat(v);
    if (!Number.isNaN(n)) return n;
  }
  return 0;
}

/** 1辺の重み合計を100に正規化 */
function normalizeSideTo100(side: Record<string, number>): Record<string, number> {
  const sum = Object.values(side).reduce((a, b) => a + b, 0);
  if (sum <= 0) return side;
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(side)) {
    out[k] = Math.round((v / sum) * 1000) / 10;
  }
  return out;
}

/** API の weights_json をフォーム用に正規化（％表示のため合計100になるよう換算） */
export function normalizeWeights(raw: unknown): WeightsFormValue {
  const o = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const buy = (o.buy && typeof o.buy === "object" ? o.buy as Record<string, unknown> : {}) as Record<string, number>;
  const sell = (o.sell && typeof o.sell === "object" ? o.sell as Record<string, unknown> : {}) as Record<string, number>;
  const result: WeightsFormValue = { buy: {}, sell: {} };
  for (const { side, key } of WEIGHT_LABELS) {
    const src = side === "buy" ? buy : sell;
    result[side][key] = toNumber(src[key]);
  }
  result.buy = normalizeSideTo100(result.buy);
  result.sell = normalizeSideTo100(result.sell);
  return result;
}

/** API の thresholds_json をフォーム用に正規化 */
export function normalizeThresholds(raw: unknown): ThresholdsFormValue {
  const o = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const bias = (o.bias && typeof o.bias === "object" ? o.bias as Record<string, unknown> : {}) as Record<string, number>;
  const strength = (o.strength && typeof o.strength === "object" ? o.strength as Record<string, unknown> : {}) as Record<string, number>;
  const result: ThresholdsFormValue = { bias: {}, strength: {} };
  for (const { group, key } of THRESHOLD_LABELS) {
    const src = group === "bias" ? bias : strength;
    result[group][key] = toNumber(src[key]);
  }
  return result;
}

/** フォーム値を API 用のオブジェクトに変換（合計が100でない場合は100に正規化して送る） */
export function weightsToApi(v: WeightsFormValue): Record<string, unknown> {
  const buy = normalizeSideTo100(v.buy);
  const sell = normalizeSideTo100(v.sell);
  return { buy: { ...buy }, sell: { ...sell } };
}

export function thresholdsToApi(v: ThresholdsFormValue): Record<string, unknown> {
  return { bias: { ...v.bias }, strength: { ...v.strength } };
}

export function ProfileWeightsForm({
  value,
  onChange,
}: {
  value: WeightsFormValue;
  onChange: (v: WeightsFormValue) => void;
}) {
  const update = (side: "buy" | "sell", key: string, num: number) => {
    onChange({
      ...value,
      [side]: { ...value[side], [key]: num },
    });
  };

  const buyItems = WEIGHT_LABELS.filter((x) => x.side === "buy");
  const sellItems = WEIGHT_LABELS.filter((x) => x.side === "sell");
  const sumBuy = Math.round(Object.values(value.buy).reduce((a, b) => a + b, 0) * 10) / 10;
  const sumSell = Math.round(Object.values(value.sell).reduce((a, b) => a + b, 0) * 10) / 10;

  return (
    <div className="space-y-4">
      <p className="rounded bg-slate-100 px-3 py-2 text-xs text-slate-600">
        <strong>割合で配分：</strong>
        各条件の<strong>重要度を％で配分</strong>します。買い・売りそれぞれ<strong>合計100％</strong>になるように入力してください。当てはまった条件の割合を足したものがスコア（0〜100）になり、％の大きい条件ほどその方向のシグナルに効きます。保存時に合計が100％でない場合は自動で按分します。
      </p>
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">買いスコアの重み</h3>
          <span className={`text-sm tabular-nums ${sumBuy === 100 ? "text-slate-600" : "text-amber-600"}`}>
            合計: {sumBuy}％
          </span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
          {buyItems.map(({ key, label, description }) => (
            <label key={key} className="flex flex-col gap-0.5 rounded border border-slate-200 bg-slate-50/50 px-3 py-2">
              <span className="text-sm font-medium text-slate-700">{label}</span>
              <span className="text-xs text-slate-500">{description}</span>
              <div className="mt-1 flex items-center justify-end gap-1">
                <input
                  type="number"
                  step="0.5"
                  min={0}
                  max={100}
                  value={value.buy[key] ?? 0}
                  onChange={(e) => update("buy", key, parseFloat(e.target.value) || 0)}
                  className="w-20 rounded border border-slate-300 px-2 py-1 text-right text-sm tabular-nums"
                />
                <span className="text-xs text-slate-500">％</span>
              </div>
            </label>
          ))}
        </div>
      </div>
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">売りスコアの重み</h3>
          <span className={`text-sm tabular-nums ${sumSell === 100 ? "text-slate-600" : "text-amber-600"}`}>
            合計: {sumSell}％
          </span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
          {sellItems.map(({ key, label, description }) => (
            <label key={key} className="flex flex-col gap-0.5 rounded border border-slate-200 bg-slate-50/50 px-3 py-2">
              <span className="text-sm font-medium text-slate-700">{label}</span>
              <span className="text-xs text-slate-500">{description}</span>
              <div className="mt-1 flex items-center justify-end gap-1">
                <input
                  type="number"
                  step="0.5"
                  min={0}
                  max={100}
                  value={value.sell[key] ?? 0}
                  onChange={(e) => update("sell", key, parseFloat(e.target.value) || 0)}
                  className="w-20 rounded border border-slate-300 px-2 py-1 text-right text-sm tabular-nums"
                />
                <span className="text-xs text-slate-500">％</span>
              </div>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ProfileThresholdsForm({
  value,
  onChange,
}: {
  value: ThresholdsFormValue;
  onChange: (v: ThresholdsFormValue) => void;
}) {
  const update = (group: "bias" | "strength", key: string, num: number) => {
    onChange({
      ...value,
      [group]: { ...value[group], [key]: num },
    });
  };

  return (
    <div className="space-y-3">
      <p className="rounded bg-slate-100 px-3 py-2 text-xs text-slate-600">
        <strong>単位について：</strong>
        ここで設定する値はすべて<strong>スコア差のポイント数</strong>です（％や金額ではありません）。
        買いスコアと売りスコアの「差」が何ポイントかで、様子見か・買いか売りか、以及びシグナルの強さ（弱・通常・強）を判定します。
      </p>
      {THRESHOLD_LABELS.map(({ group, key, label, description }) => (
        <label key={`${group}-${key}`} className="flex flex-col gap-0.5 rounded border border-slate-200 bg-slate-50/50 px-3 py-2">
          <span className="text-sm font-medium text-slate-700">{label}</span>
          <span className="text-xs text-slate-500">{description}</span>
          <div className="mt-1 flex items-center justify-end gap-1">
            <input
              type="number"
              step="0.5"
              min={0}
              value={value[group][key] ?? 0}
              onChange={(e) => update(group, key, parseFloat(e.target.value) || 0)}
              className="w-24 rounded border border-slate-300 px-2 py-1 text-right text-sm tabular-nums"
            />
            <span className="text-xs text-slate-500">pt</span>
          </div>
        </label>
      ))}
    </div>
  );
}
