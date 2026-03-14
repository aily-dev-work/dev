"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { getScoreProfiles, request } from "@/lib/api";
import type {
  CompareResponse,
  CompareRow,
  ScoreProfileListItem,
} from "@/types/api";

function ComparePageContent() {
  const searchParams = useSearchParams();
  const initialBase = searchParams.get("base") ?? "";

  const [profiles, setProfiles] = useState<ScoreProfileListItem[]>([]);
  const [baseId, setBaseId] = useState<string>(initialBase);
  const [candidateId, setCandidateId] = useState<string>("");
  const [activeProfileId, setActiveProfileId] = useState<number | null>(null);
  const [data, setData] = useState<CompareResponse | null>(null);
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [profilesLoading, setProfilesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadProfiles() {
      setProfilesLoading(true);
      try {
        const list = await getScoreProfiles();
        setProfiles(list);
        const active = list.find((p) => p.is_active);
        setActiveProfileId(active?.id ?? null);

        const baseParam = searchParams.get("base");
        if (baseParam) {
          setBaseId(baseParam);
          const candidate = list.find((p) => String(p.id) !== baseParam);
          if (candidate) setCandidateId(String(candidate.id));
        } else {
          if (active) setBaseId(String(active.id));
          const firstNonActive = list.find((p) => !p.is_active);
          if (firstNonActive) setCandidateId(String(firstNonActive.id));
        }
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setProfilesLoading(false);
      }
    }
    void loadProfiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount, base from URL
  }, []);

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
        Select two profiles to compare using the dropdowns below.
      </p>

      {activeProfileId !== null && (
        <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm">
          <span className="font-medium text-emerald-800">
            Active profile: id={activeProfileId}
          </span>
          {profiles.find((p) => p.id === activeProfileId) && (
            <span className="ml-2 text-emerald-700">
              ({profiles.find((p) => p.id === activeProfileId)?.name}{" "}
              {profiles.find((p) => p.id === activeProfileId)?.version})
            </span>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col">
          <span className="mb-1 font-medium">Base profile</span>
          <select
            value={baseId}
            onChange={(e) => setBaseId(e.target.value)}
            className="min-w-[220px] rounded border px-2 py-1.5"
          >
            <option value="">-- Select --</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.version}) [id={p.id}]
                {p.is_active ? " [ACTIVE]" : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col">
          <span className="mb-1 font-medium">Candidate profile</span>
          <select
            value={candidateId}
            onChange={(e) => setCandidateId(e.target.value)}
            className="min-w-[220px] rounded border px-2 py-1.5"
          >
            <option value="">-- Select --</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.version}) [id={p.id}]
                {p.is_active ? " [ACTIVE]" : ""}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={swapIds}
          className="rounded border px-2 py-1.5 text-slate-700 hover:bg-slate-100"
        >
          Swap
        </button>
        <button
          type="button"
          onClick={handleCompare}
          disabled={
            loading ||
            profilesLoading ||
            !baseId ||
            !candidateId ||
            baseId === candidateId
          }
          className="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60"
        >
          {loading ? "Comparing..." : "Compare"}
        </button>
      </div>

      {baseId === candidateId && baseId && (
        <p className="text-sm text-amber-600">
          Base and candidate are the same. Select different profiles to compare.
        </p>
      )}

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}

      {data && (
        <section className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <ProfileSummaryCard
              title="Base"
              profile={data.base_profile}
              isActive={data.base_profile.id === activeProfileId}
            />
            <ProfileSummaryCard
              title="Candidate"
              profile={data.candidate_profile}
              isActive={data.candidate_profile.id === activeProfileId}
            />
          </div>

          {/* H20 comparison bar charts */}
          {rows.length > 0 && (
            <div className="grid gap-4 rounded-lg border bg-white p-3 shadow-sm md:grid-cols-2">
              <div>
                <h3 className="mb-2 text-sm font-semibold">H20 Success rate (Base vs Candidate)</h3>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={rows.map((r) => ({
                        name: r.signal_type,
                        base: r.base.h20.success_rate ?? 0,
                        candidate: r.candidate.h20.success_rate ?? 0,
                      }))}
                      margin={{ top: 4, right: 8, left: 8, bottom: 4 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 1]} tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="base" name="Base" fill="#475569" />
                      <Bar dataKey="candidate" name="Candidate" fill="#0f766e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div>
                <h3 className="mb-2 text-sm font-semibold">H20 Avg return (Base vs Candidate)</h3>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={rows.map((r) => ({
                        name: r.signal_type,
                        base: r.base.h20.avg_return ?? 0,
                        candidate: r.candidate.h20.avg_return ?? 0,
                      }))}
                      margin={{ top: 4, right: 8, left: 8, bottom: 4 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="base" name="Base" fill="#475569" />
                      <Bar dataKey="candidate" name="Candidate" fill="#0f766e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

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
                    <td
                      colSpan={11}
                      className="border px-2 py-2 text-center text-slate-500"
                    >
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

export default function ProfilesComparePage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-600">Loading...</p>}>
      <ComparePageContent />
    </Suspense>
  );
}

import type { ReactNode } from "react";
import type { CompareHorizon } from "@/types/api";

function ProfileSummaryCard({
  title,
  profile,
  isActive,
}: {
  title: string;
  profile: CompareResponse["base_profile"];
  isActive?: boolean;
}) {
  return (
    <div
      className={`rounded border p-3 text-sm shadow-sm ${
        isActive ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-white"
      }`}
    >
      <div className="mb-1 text-xs font-semibold uppercase text-slate-500">
        {title}
        {isActive && (
          <span className="ml-2 rounded bg-emerald-600 px-1.5 py-0.5 text-white">
            ACTIVE
          </span>
        )}
      </div>
      <div className="font-medium">
        {profile.name} <span className="text-slate-500">({profile.version})</span>
      </div>
      <div className="text-xs text-slate-500">id={profile.id}</div>
      {profile.source_proposal_id && (
        <div className="mt-1 text-xs">
          from proposal: {profile.source_proposal_name} (id=
          {profile.source_proposal_id})
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
        <td className="border px-2 py-1 text-right">
          {row.base.h20.evaluated_count}
        </td>
        <td className="border px-2 py-1 text-right">
          {row.base.h20.success_count}
        </td>
        <td className="border px-2 py-1 text-right">
          {row.base.h20.success_rate != null
            ? row.base.h20.success_rate.toFixed(2)
            : "-"}
        </td>
        <td className="border px-2 py-1 text-right">
          {row.base.h20.avg_return != null
            ? row.base.h20.avg_return.toFixed(4)
            : "-"}
        </td>
      </tr>
      <tr className="odd:bg-white">
        <td className="border px-2 py-1 text-right font-medium">Candidate</td>
        <td className="border px-2 py-1 text-right">
          {row.candidate.total_signals}
        </td>
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
