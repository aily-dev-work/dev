"use client";

import { useState } from "react";
import { request } from "@/lib/api";
import type { CompareResponse, CompareRow } from "@/types/api";

export default function ProfilesComparePage() {
  const [baseId, setBaseId] = useState<string>("");
  const [candidateId, setCandidateId] = useState<string>("");
  const [data, setData] = useState<CompareResponse | null>(null);
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCompare() {
    setLoading(true);
    setError(null);
    setData(null);
    setRows([]);
    try {
      const res = await request<CompareResponse>(
        `/api/v1/score-profiles/compare/?base_profile_id=${encodeURIComponent(
          baseId,
        )}&candidate_profile_id=${encodeURIComponent(candidateId)}`,
      );
      setData(res);
      setRows(res.comparison);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function swapIds() {
    setBaseId(candidateId);
    setCandidateId(baseId);
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Compare profiles</h1>
      <p className="text-sm text-slate-600">
        Compare two profiles using /score-profiles/compare API. Same profile ids are also
        allowed.
      </p>

      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col">
          <span className="mb-1 font-medium">Base profile id</span>
          <input
            value={baseId}
            onChange={(e) => setBaseId(e.target.value)}
            className="w-32 rounded border px-2 py-1"
            placeholder="e.g. 1"
          />
        </label>
        <label className="flex flex-col">
          <span className="mb-1 font-medium">Candidate profile id</span>
          <input
            value={candidateId}
            onChange={(e) => setCandidateId(e.target.value)}
            className="w-32 rounded border px-2 py-1"
            placeholder="e.g. 2"
          />
        </label>
        <button
          type="button"
          onClick={swapIds}
          className="rounded border px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
        >
          Swap
        </button>
        <button
          type="button"
          onClick={handleCompare}
          disabled={loading || !baseId || !candidateId}
          className="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
        >
          {loading ? "Comparing..." : "Compare"}
        </button>
      </div>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}

      {data && (
        <section className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <ProfileSummaryCard title="Base" profile={data.base_profile} />
            <ProfileSummaryCard title="Candidate" profile={data.candidate_profile} />
          </div>

          <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
            <table className="min-w-full text-xs md:text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className="border px-2 py-1 text-left">Signal type</th>
                  <th className="border px-2 py-1 text-left">Side</th>
                  <th className="border px-2 py-1 text-right">Total</th>
                  <th className="border px-2 py-1 text-right">H5 eval</th>
                  <th className="border px-2 py-1 text-right">H5 succ</th>
                  <th className="border px-2 py-1 text-right">H5 rate</th>
                  <th className="border px-2 py-1 text-right">H5 avg</th>
                  <th className="border px-2 py-1 text-right">H20 eval</th>
                  <th className="border px-2 py-1 text-right">H20 succ</th>
                  <th className="border px-2 py-1 text-right">H20 rate</th>
                  <th className="border px-2 py-1 text-right">H20 avg</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <FragmentedRows key={row.signal_type} row={row} />
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={11} className="border px-2 py-2 text-center text-slate-500">
                      No summary data.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

import type { ReactNode } from "react";
import type { CompareHorizon } from "@/types/api";

function ProfileSummaryCard({
  title,
  profile,
}: {
  title: string;
  profile: CompareResponse["base_profile"];
}) {
  return (
    <div className="rounded border bg-white p-3 text-sm shadow-sm">
      <div className="mb-1 text-xs font-semibold uppercase text-slate-500">{title}</div>
      <div className="font-medium">
        {profile.name} <span className="text-slate-500">({profile.version})</span>
      </div>
      <div className="text-xs text-slate-500">
        id={profile.id} / active={String(profile.is_active)}
      </div>
      {profile.source_proposal_id && (
        <div className="mt-1 text-xs">
          from proposal: {profile.source_proposal_name} (id={profile.source_proposal_id})
        </div>
      )}
    </div>
  );
}

function FragmentedRows({ row }: { row: CompareRow }) {
  const cells = (h: CompareHorizon): ReactNode[] => [
    <td key="eval" className="border px-2 py-1 text-right">
      {h.evaluated_count}
    </td>,
    <td key="succ" className="border px-2 py-1 text-right">
      {h.success_count}
    </td>,
    <td key="rate" className="border px-2 py-1 text-right">
      {h.success_rate != null ? h.success_rate.toFixed(2) : "-"}
    </td>,
    <td key="avg" className="border px-2 py-1 text-right">
      {h.avg_return != null ? h.avg_return.toFixed(4) : "-"}
    </td>,
  ];

  return (
    <>
      <tr className="bg-slate-50">
        <td className="border px-2 py-1" rowSpan={2}>
          {row.signal_type}
        </td>
        <td className="border px-2 py-1 text-right font-medium">Base</td>
        <td className="border px-2 py-1 text-right">{row.base.total_signals}</td>
        {cells(row.base.h5)}
        <td className="border px-2 py-1 text-right">{row.base.h20.evaluated_count}</td>
        <td className="border px-2 py-1 text-right">{row.base.h20.success_count}</td>
        <td className="border px-2 py-1 text-right">
          {row.base.h20.success_rate != null ? row.base.h20.success_rate.toFixed(2) : "-"}
        </td>
        <td className="border px-2 py-1 text-right">
          {row.base.h20.avg_return != null ? row.base.h20.avg_return.toFixed(4) : "-"}
        </td>
      </tr>
      <tr className="odd:bg-white">
        <td className="border px-2 py-1 text-right font-medium">Candidate</td>
        <td className="border px-2 py-1 text-right">{row.candidate.total_signals}</td>
        {cells(row.candidate.h5)}
        <td className="border px-2 py-1 text-right">
          {row.candidate.h20.evaluated_count}
        </td>
        <td className="border px-2 py-1 text-right">
          {row.candidate.h20.success_count}
        </td>
        <td className="border px-2 py-1 text-right">
          {row.candidate.h20.success_rate != null
            ? row.candidate.h20.success_rate.toFixed(2)
            : "-"}
        </td>
        <td className="border px-2 py-1 text-right">
          {row.candidate.h20.avg_return != null
            ? row.candidate.h20.avg_return.toFixed(4)
            : "-"}
        </td>
      </tr>
    </>
  );
}

