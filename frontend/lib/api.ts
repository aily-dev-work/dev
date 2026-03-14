const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
    ...init,
  });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const data = (await res.json()) as { detail?: string };
      if (data.detail) {
        detail = data.detail;
      }
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (res.status === 204) {
    // @ts-expect-error allow void
    return null;
  }

  return (await res.json()) as T;
}

export { request, API_BASE_URL };

/** 監視銘柄一覧取得 */
export async function getStocks() {
  return request<import("@/types/api").WatchStock[]>("/api/v1/stocks/");
}

/** 監視銘柄詳細取得 */
export async function getStock(id: number) {
  return request<import("@/types/api").WatchStock>(`/api/v1/stocks/${id}/`);
}

/** 監視銘柄作成 */
export async function createStock(body: {
  ticker: string;
  name: string;
  market?: string;
  is_active?: boolean;
  memo?: string;
}) {
  return request<import("@/types/api").WatchStock>("/api/v1/stocks/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** 監視銘柄更新 */
export async function updateStock(
  id: number,
  body: Partial<{
    ticker: string;
    name: string;
    market: string;
    is_active: boolean;
    memo: string;
  }>,
) {
  return request<import("@/types/api").WatchStock>(`/api/v1/stocks/${id}/`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

/** 監視銘柄削除 */
export async function deleteStock(id: number) {
  return request<null>(`/api/v1/stocks/${id}/`, { method: "DELETE" });
}

/** フェーズ22: ScoreProfile 一覧取得 */
export async function getScoreProfiles() {
  return request<import("@/types/api").ScoreProfileListItem[]>("/api/v1/score-profiles/");
}

/** フェーズ22: ScoreProfile 詳細取得 */
export async function getScoreProfile(id: number) {
  return request<import("@/types/api").ScoreProfileDetail>(`/api/v1/score-profiles/${id}/`);
}

/** フェーズ23: ダッシュボード統計取得 */
export async function getDashboardStats(params?: {
  signal_date_from?: string;
  signal_date_to?: string;
  base_profile_id?: number;
  candidate_profile_id?: number;
}) {
  const search = new URLSearchParams();
  if (params?.signal_date_from) search.set("signal_date_from", params.signal_date_from);
  if (params?.signal_date_to) search.set("signal_date_to", params.signal_date_to);
  if (params?.base_profile_id != null) search.set("base_profile_id", String(params.base_profile_id));
  if (params?.candidate_profile_id != null) search.set("candidate_profile_id", String(params.candidate_profile_id));
  const qs = search.toString();
  return request<import("@/types/api").DashboardStatsResponse>(
    `/api/v1/score-profiles/dashboard-stats/${qs ? `?${qs}` : ""}`,
  );
}

