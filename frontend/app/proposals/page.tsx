"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { request } from "@/lib/api";
import type { ScoreProfileProposal } from "@/types/api";

const TRADING_STYLE_OPTIONS = [
  { value: "long_term", label: "長期（スイング・ポジション）" },
  { value: "short_term", label: "短期（数日〜数週間）" },
  { value: "day_trade", label: "デイトレ" },
] as const;

type AiReviewSaveResponse = {
  proposal_id: number;
  score_profile_id: number;
  proposal_name: string;
  status: string;
  score_profile_name_snapshot: string;
  score_profile_version_snapshot: string;
  created_at: string | null;
  analysis_summary: string | null;
  issues_json: unknown;
  improvement_hypotheses_json: unknown;
  suggested_weights_json: unknown;
  suggested_thresholds_json: unknown;
  cautions_json: unknown;
};

type ProposalsListItem = Pick<
  ScoreProfileProposal,
  "id" | "proposal_name" | "status" | "score_profile_name_snapshot" | "score_profile_version_snapshot" | "created_at"
> & {
  applied_score_profile_id: number | null;
};

export default function ProposalsPage() {
  const router = useRouter();
  const [items, setItems] = useState<ProposalsListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tradingStyle, setTradingStyle] = useState<string>("short_term");
  const [userNote, setUserNote] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await request<ProposalsListItem[]>("/api/v1/proposals/");
      setItems(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleGenerateAndSave() {
    setGenerateError(null);
    setGenerating(true);
    try {
      const body: { trading_style: string; user_note?: string } = {
        trading_style: tradingStyle,
      };
      if (userNote.trim()) body.user_note = userNote.trim();
      const res = await request<AiReviewSaveResponse>(
        "/api/v1/score-profiles/current/ai-review-and-save/",
        {
          method: "POST",
          body: JSON.stringify(body),
        }
      );
      await load();
      router.push(`/proposals/${res.proposal_id}`);
    } catch (e) {
      setGenerateError((e as Error).message);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">提案</h1>

      <section className="rounded-lg border border-slate-200 bg-slate-50 p-4 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold text-slate-800">AI に提案を生成</h2>
        <p className="mb-3 text-sm text-slate-600">
          現在使用中のプロファイルを対象に、長期視点で改善提案を生成して保存します。トレードスタイルに応じて最適化されます。
        </p>
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-slate-700">トレードスタイル</span>
            <select
              value={tradingStyle}
              onChange={(e) => setTradingStyle(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            >
              {TRADING_STYLE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-slate-700">メモ（任意）</span>
            <input
              type="text"
              value={userNote}
              onChange={(e) => setUserNote(e.target.value)}
              placeholder="AI への補足"
              className="min-w-[200px] rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <button
            type="button"
            onClick={handleGenerateAndSave}
            disabled={generating}
            className="rounded-md bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-60"
          >
            {generating ? "生成中..." : "生成して保存"}
          </button>
        </div>
        {generateError && (
          <p className="mt-2 text-sm text-red-600">{generateError}</p>
        )}
      </section>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {loading && <p className="text-sm text-slate-600">読み込み中...</p>}
      <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="border px-2 py-1 text-center">名前</th>
              <th className="border px-2 py-1 text-center">状態</th>
              <th className="border px-2 py-1 text-center">プロファイル</th>
              <th className="border px-2 py-1 text-center">作成日時</th>
              <th className="border px-2 py-1 text-center">反映</th>
              <th className="border px-2 py-1 text-center">詳細</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id} className="odd:bg-slate-50">
                <td className="border px-2 py-1">{p.proposal_name}</td>
                <td
                  className={`border px-2 py-1 font-medium ${
                    p.status === "accepted"
                      ? "text-emerald-700"
                      : p.status === "rejected"
                      ? "text-red-700"
                      : "text-slate-700"
                  }`}
                >
                  {p.status}
                </td>
                <td className="border px-2 py-1">
                  {p.score_profile_name_snapshot} ({p.score_profile_version_snapshot})
                </td>
                <td className="border px-2 py-1">
                  {p.created_at ? new Date(p.created_at).toLocaleString() : "-"}
                </td>
                <td className="border px-2 py-1">
                  {p.applied_score_profile_id ? `反映済 (id=${p.applied_score_profile_id})` : "-"}
                </td>
                <td className="border px-2 py-1">
                  <Link href={`/proposals/${p.id}`} className="text-blue-600 hover:underline">
                    表示
                  </Link>
                </td>
              </tr>
            ))}
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="border px-2 py-2 text-center text-slate-500">
                  提案がありません。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

