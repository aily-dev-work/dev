/** 市場検索 1件（Yahoo Finance 等） */
export type MarketSearchResult = {
  symbol: string;
  name: string;
  /** 東証銘柄などで日本語企業名がある場合 */
  name_ja?: string | null;
  exchange: string | null;
  quote_type: string | null;
};

/** GET /api/v1/market-search/?q= の返却 */
export type MarketSearchResponse = {
  results: MarketSearchResult[];
};

/** 監視銘柄（WatchStock） */
export type WatchStock = {
  id: number;
  ticker: string;
  name: string;
  market: string;
  is_active: boolean;
  memo: string;
  created_at?: string | null;
  updated_at?: string | null;
};

/** 価格足（5分/日/月）1本 */
export type StockPriceBar = {
  date?: string;
  datetime?: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
};

/** GET /api/v1/stocks/:id/prices/ の返却 */
export type StockPricesResponse = {
  resolution: string;
  stock_id: number;
  ticker: string;
  bars: StockPriceBar[];
};

/** 日足株価 1件（CRUD API） */
export type StockPriceDailyRow = {
  id: number;
  stock: number;
  stock_ticker: string;
  stock_name: string;
  date: string;
  open_price: string;
  high_price: string;
  low_price: string;
  close_price: string;
  volume: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

/** 5分足株価 1件（CRUD API） */
export type StockPrice5MinRow = {
  id: number;
  stock: number;
  stock_ticker: string;
  stock_name: string;
  datetime: string;
  open_price: string;
  high_price: string;
  low_price: string;
  close_price: string;
  volume: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

/** 週足株価 1件（CRUD API） */
export type StockPriceWeeklyRow = {
  id: number;
  stock: number;
  stock_ticker: string;
  stock_name: string;
  date: string;
  open_price: string;
  high_price: string;
  low_price: string;
  close_price: string;
  volume: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

/** 月足株価 1件（CRUD API） */
export type StockPriceMonthlyRow = {
  id: number;
  stock: number;
  stock_ticker: string;
  stock_name: string;
  date: string;
  open_price: string;
  high_price: string;
  low_price: string;
  close_price: string;
  volume: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ScoreProfile = {
  id: number;
  name: string;
  version: string;
  is_active: boolean;
  description: string;
  weights_json?: unknown;
  thresholds_json?: unknown;
  created_at?: string | null;
  updated_at?: string | null;
};

/** フェーズ22: ScoreProfile 一覧 API の返却型 */
export type ScoreProfileListItem = {
  id: number;
  name: string;
  version: string;
  is_active: boolean;
  description: string;
  trading_style: string;
  weights_json?: unknown;
  thresholds_json?: unknown;
  created_at?: string | null;
  updated_at?: string | null;
  source_proposal_id: number | null;
  source_proposal_name: string | null;
  source_proposal_status: string | null;
};

/** フェーズ22: ScoreProfile 詳細 API の返却型 */
export type ScoreProfileDetail = ScoreProfileListItem;

/** GET /api/v1/stocks/scores/ の1銘柄分（買い/売り/様子見％＋長期・短期トレンド） */
export type StockScoreItem = {
  stock_id: number;
  ticker: string;
  name: string;
  buy_score: number | null;
  sell_score: number | null;
  bias: string | null;
  strength: string | null;
  buy_pct: number | null;
  sell_pct: number | null;
  wait_pct: number | null;
  /** 長期トレンド: up=上昇, neutral=中立, down=下降（75日ベース） */
  long_term_trend: string | null;
  /** 短期トレンド: up=上昇, neutral=中立, down=下降（25日ベース） */
  short_term_trend: string | null;
  insufficient_data: boolean;
  insufficient_reason?: string | null;
  error?: string;
};

export type StockScoresResponse = { stocks: StockScoreItem[] };

/** GET /api/v1/signals/recent/ の1件（直近シグナル発報） */
export type RecentSignalItem = {
  id: number;
  stock_id: number;
  ticker: string;
  stock_name: string;
  signal_date: string;
  signal_type: string;
  score_bias: string;
  score_strength: string;
  buy_score: number;
  sell_score: number;
  signal_price: string | null;
  created_at: string | null;
};

export type ScoreProfileProposal = {
  id: number;
  score_profile_id: number;
  proposal_name: string;
  status: string;
  score_profile_name_snapshot: string;
  score_profile_version_snapshot: string;
  source_filters_json: unknown;
  analysis_summary: string;
  issues_json: unknown;
  improvement_hypotheses_json: unknown;
  suggested_weights_json: unknown;
  suggested_thresholds_json: unknown;
  cautions_json: unknown;
  raw_ai_response_json: unknown;
  review_note: string;
  applied_score_profile_id: number | null;
  applied_score_profile_name: string | null;
  applied_score_profile_version: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type OpsSummaryResponse = {
  generated_at: string;
  current_active_profile: {
    id: number;
    name: string;
    version: string;
    is_active: boolean;
  } | null;
  stale_active_profiles: Array<{ id: number; name: string; version: string; is_active: boolean }>;
  underperforming_profiles: Array<{ id: number; name: string; version: string; is_active: boolean }>;
  accepted_not_activated_profiles: Array<{
    id: number;
    name: string;
    version: string;
    is_active: boolean;
    source_proposal_id: number;
    source_proposal_name: string;
  }>;
  counts: {
    stale_active_count: number;
    underperforming_count: number;
    accepted_not_activated_count: number;
  };
  message_lines: string[];
};

export type ActivationHistoryItem = {
  id: number;
  previous_profile_id: number | null;
  previous_profile_name: string | null;
  previous_profile_version: string | null;
  activated_profile_id: number;
  activated_profile_name: string | null;
  activated_profile_version: string | null;
  source_proposal_id: number | null;
  source_proposal_name: string | null;
  activation_reason: string;
  note: string;
  activated_at: string | null;
};

export type CompareHorizon = {
  evaluated_count: number;
  success_count: number;
  success_rate: number | null;
  avg_return: number | null;
};

export type CompareRow = {
  signal_type: string;
  base: {
    total_signals: number;
    h5: CompareHorizon;
    h10: CompareHorizon;
    h20: CompareHorizon;
  };
  candidate: {
    total_signals: number;
    h5: CompareHorizon;
    h10: CompareHorizon;
    h20: CompareHorizon;
  };
};

export type CompareResponse = {
  base_profile: {
    id: number;
    name: string;
    version: string;
    is_active: boolean;
    source_proposal_id: number | null;
    source_proposal_name: string | null;
  };
  candidate_profile: {
    id: number;
    name: string;
    version: string;
    is_active: boolean;
    source_proposal_id: number | null;
    source_proposal_name: string | null;
  };
  comparison: CompareRow[];
};

/** フェーズ23: ダッシュボード統計 API */
export type DashboardProfileOverview = {
  total_count: number;
  active_count: number;
  inactive_count: number;
  proposal_derived_count: number;
};

export type DashboardChartSuccessRateRow = {
  profile_id: number;
  profile_name: string;
  profile_version: string;
  signal_type: string;
  success_rate_h20: number | null;
  /** トレードスタイルに応じた評価期間（営業日）。デイトレ=5・短期=10・長期=20 */
  evaluation_horizon_days?: number;
};

export type DashboardChartAvgReturnRow = {
  profile_id: number;
  profile_name: string;
  profile_version: string;
  signal_type: string;
  avg_return_h20: number | null;
  /** トレードスタイルに応じた評価期間（営業日） */
  evaluation_horizon_days?: number;
};

export type DashboardActivationTimelineRow = {
  activated_at: string | null;
  activated_profile_name: string | null;
  activated_profile_version: string | null;
  activation_reason: string;
};

export type DashboardChartData = {
  profile_success_rate_rows: DashboardChartSuccessRateRow[];
  profile_avg_return_rows: DashboardChartAvgReturnRow[];
  activation_timeline_rows: DashboardActivationTimelineRow[];
};

export type DashboardStatsResponse = {
  current_active_profile: {
    id: number;
    name: string;
    version: string;
    is_active: boolean;
    description: string;
  } | null;
  ops_summary: OpsSummaryResponse;
  recent_activation_history: ActivationHistoryItem[];
  profile_overview: DashboardProfileOverview;
  compare_snapshot: CompareResponse | null;
  chart_data: DashboardChartData;
};

