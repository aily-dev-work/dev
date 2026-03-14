"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { request } from "@/lib/api";
import type { ScoreProfileProposal } from "@/types/api";

type ReviewBody = {
  status?: string;
  review_note?: string;
};

export default function ProposalDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);

  const [proposal, setProposal] = useState<ScoreProfileProposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingReview, setSavingReview] = useState(false);
  const [applying, setApplying] = useState(false);
  const [reviewStatus, setReviewStatus] = useState<string>("");
  const [reviewNote, setReviewNote] = useState<string>("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const p = await request<ScoreProfileProposal>(`/api/v1/proposals/${id}/`);
      setProposal(p);
      setReviewStatus(p.status);
      setReviewNote(p.review_note ?? "");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!Number.isNaN(id)) {
      void load();
    }
  }, [id]);

  async function handleSaveReview() {
    setSavingReview(true);
    setError(null);
    const body: ReviewBody = {};
    if (reviewStatus && reviewStatus !== proposal?.status) {
      body.status = reviewStatus;
    }
    if (reviewNote !== (proposal?.review_note ?? "")) {
      body.review_note = reviewNote;
    }
    try {
      await request(`/api/v1/proposals/${id}/review/`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingReview(false);
    }
  }

  async function handleApply() {
    if (!proposal || proposal.status !== "accepted") {
      alert("採用（accepted）済みの提案のみ反映できます。");
      return;
    }
    if (!confirm("この提案を反映して新しいプロファイルを作成しますか？")) return;
    setApplying(true);
    setError(null);
    try {
      await request(`/api/v1/proposals/${id}/apply/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setApplying(false);
    }
  }

  if (Number.isNaN(id)) {
    return <p>無効な提案 ID です。</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">提案 #{id}</h1>
        <button
          type="button"
          onClick={() => router.back()}
          className="text-sm text-slate-600 hover:text-slate-900"
        >
          ← 戻る
        </button>
      </div>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {loading && <p className="text-sm text-slate-600">読み込み中...</p>}

      {proposal && (
        <div className="space-y-4">
          <section className="rounded border bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-lg font-semibold">サマリ</h2>
            <div className="space-y-1 text-sm">
              <div>
                <span className="font-medium">名前:</span> {proposal.proposal_name}
              </div>
              <div>
                <span className="font-medium">状態:</span> {proposal.status}
              </div>
              <div>
                <span className="font-medium">対象プロファイル:</span>{" "}
                {proposal.score_profile_name_snapshot} (
                {proposal.score_profile_version_snapshot})
              </div>
              <div>
                <span className="font-medium">反映済みプロファイル:</span>{" "}
                {proposal.applied_score_profile_id
                  ? `${proposal.applied_score_profile_name} (${proposal.applied_score_profile_version}) [id=${proposal.applied_score_profile_id}]`
                  : "-"}
              </div>
            </div>
          </section>

          <section className="rounded border bg-white p-4 shadow-sm space-y-3">
            <h2 className="text-lg font-semibold">レビュー</h2>
            <div className="flex flex-wrap gap-3 text-sm">
              <label className="flex items-center gap-2">
                <span className="w-24">状態</span>
                <select
                  value={reviewStatus}
                  onChange={(e) => setReviewStatus(e.target.value)}
                  className="rounded border px-2 py-1"
                >
                  <option value="draft">draft</option>
                  <option value="reviewed">reviewed</option>
                  <option value="accepted">accepted</option>
                  <option value="rejected">rejected</option>
                </select>
              </label>
            </div>
            <div className="text-sm">
              <div className="mb-1 font-medium">レビューメモ</div>
              <textarea
                value={reviewNote}
                onChange={(e) => setReviewNote(e.target.value)}
                rows={3}
                className="w-full rounded border px-2 py-1"
              />
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleSaveReview}
                disabled={savingReview}
                className="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
              >
                {savingReview ? "保存中..." : "レビューを保存"}
              </button>
              <button
                type="button"
                onClick={handleApply}
                disabled={applying || proposal.status !== "accepted"}
                className="rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
              >
                {applying ? "反映中..." : "提案を反映"}
              </button>
            </div>
          </section>

          <section className="rounded border bg-white p-4 shadow-sm space-y-4">
            <h2 className="text-lg font-semibold">詳細</h2>
            <DetailBlock title="分析サマリ" value={proposal.analysis_summary} />
            <JsonBlock title="元フィルタ" value={proposal.source_filters_json} />
            <JsonBlock title="課題" value={proposal.issues_json} />
            <JsonBlock title="改善仮説" value={proposal.improvement_hypotheses_json} />
            <JsonBlock title="提案重み" value={proposal.suggested_weights_json} />
            <JsonBlock title="提案閾値" value={proposal.suggested_thresholds_json} />
            <JsonBlock title="注意点" value={proposal.cautions_json} />
            <JsonBlock title="AI 生レスポンス" value={proposal.raw_ai_response_json} />
          </section>
        </div>
      )}
    </div>
  );
}

function DetailBlock({ title, value }: { title: string; value: string }) {
  return (
    <div className="text-sm">
      <div className="mb-1 font-medium">{title}</div>
      <div className="whitespace-pre-wrap rounded border bg-slate-50 px-2 py-1 text-slate-800">
        {value || "-"}
      </div>
    </div>
  );
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  let text = "-";
  try {
    if (value != null) {
      text = JSON.stringify(value, null, 2);
    }
  } catch {
    text = String(value);
  }
  return (
    <div className="text-sm">
      <div className="mb-1 font-medium">{title}</div>
      <pre className="max-h-80 overflow-auto rounded border bg-slate-50 px-2 py-1 text-xs text-slate-800">
        {text}
      </pre>
    </div>
  );
}

