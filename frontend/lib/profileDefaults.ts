/** デフォルト重み（合計100％で配分。新規作成の初期値） */
export const DEFAULT_WEIGHTS: Record<string, unknown> = {
  buy: {
    trend_long_up: 40.0,
    trend_mid_up: 20.0,
    trend_short_up: 10.0,
    volume_high: 10.0,
    above_ma75: 10.0,
    above_ma25: 10.0,
    near_high_20: 0.0,
    near_low_20: 0.0,
  },
  sell: {
    trend_long_down: 40.0,
    trend_mid_down: 20.0,
    trend_short_down: 10.0,
    volume_low: 0.0,
    below_ma75: 10.0,
    below_ma25: 10.0,
    near_low_20: 0.0,
    near_high_20: 0.0,
  },
};

/** バックエンド _default_thresholds と同様のデフォルト閾値（新規作成の初期値） */
export const DEFAULT_THRESHOLDS: Record<string, unknown> = {
  bias: { neutral_abs_diff_lt: 10.0 },
  strength: { weak_abs_diff_lt: 15.0, normal_abs_diff_lt: 30.0 },
};
