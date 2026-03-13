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

