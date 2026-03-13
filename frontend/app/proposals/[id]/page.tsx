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
      alert("Only accepted proposals can be applied.");
      return;
    }
    if (!confirm("Apply this proposal to create a new profile?")) return;
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
    return <p>Invalid proposal id.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Proposal #{id}</h1>
        <button
          type="button"
          onClick={() => router.back()}
          className="text-sm text-slate-600 hover:text-slate-900"
        >
          ← Back
        </button>
      </div>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {loading && <p className="text-sm text-slate-600">Loading...</p>}

      {proposal && (
        <div className="space-y-4">
          <section className="rounded border bg-white p-4 shadow-sm">
            <h2 className="mb-2 text-lg font-semibold">Summary</h2>
            <div className="space-y-1 text-sm">
              <div>
                <span className="font-medium">Name:</span> {proposal.proposal_name}
              </div>
              <div>
                <span className="font-medium">Status:</span> {proposal.status}
              </div>
              <div>
                <span className="font-medium">Target profile:</span>{" "}
                {proposal.score_profile_name_snapshot} (
                {proposal.score_profile_version_snapshot})
              </div>
              <div>
                <span className="font-medium">Applied profile:</span>{" "}
                {proposal.applied_score_profile_id
                  ? `${proposal.applied_score_profile_name} (${proposal.applied_score_profile_version}) [id=${proposal.applied_score_profile_id}]`
                  : "-"}
              </div>
            </div>
          </section>

          <section className="rounded border bg-white p-4 shadow-sm space-y-3">
            <h2 className="text-lg font-semibold">Review</h2>
            <div className="flex flex-wrap gap-3 text-sm">
              <label className="flex items-center gap-2">
                <span className="w-24">Status</span>
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
              <div className="mb-1 font-medium">Review note</div>
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
                {savingReview ? "Saving..." : "Save review"}
              </button>
              <button
                type="button"
                onClick={handleApply}
                disabled={applying || proposal.status !== "accepted"}
                className="rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
              >
                {applying ? "Applying..." : "Apply proposal"}
              </button>
            </div>
          </section>

          <section className="rounded border bg-white p-4 shadow-sm space-y-4">
            <h2 className="text-lg font-semibold">Details</h2>
            <DetailBlock title="Analysis summary" value={proposal.analysis_summary} />
            <JsonBlock title="Source filters" value={proposal.source_filters_json} />
            <JsonBlock title="Issues" value={proposal.issues_json} />
            <JsonBlock title="Improvement hypotheses" value={proposal.improvement_hypotheses_json} />
            <JsonBlock title="Suggested weights" value={proposal.suggested_weights_json} />
            <JsonBlock title="Suggested thresholds" value={proposal.suggested_thresholds_json} />
            <JsonBlock title="Cautions" value={proposal.cautions_json} />
            <JsonBlock title="Raw AI response" value={proposal.raw_ai_response_json} />
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

