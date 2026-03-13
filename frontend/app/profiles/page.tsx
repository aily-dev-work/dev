"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { request } from "@/lib/api";
import type { OpsSummaryResponse } from "@/types/api";

type ProfileRow = {
  id: number;
  name: string;
  version: string;
  is_active: boolean;
  kind: "current" | "stale" | "underperforming" | "accepted_not_activated";
  source_proposal_id?: number;
  source_proposal_name?: string;
};

export default function ProfilesPage() {
  const [rows, setRows] = useState<ProfileRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activatingId, setActivatingId] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const ops = await request<OpsSummaryResponse>("/api/v1/score-profiles/ops-summary/");
      const list: ProfileRow[] = [];
      if (ops.current_active_profile) {
        list.push({
          ...ops.current_active_profile,
          kind: "current",
        });
      }
      ops.stale_active_profiles.forEach((p) =>
        list.push({
          ...p,
          kind: "stale",
        }),
      );
      ops.underperforming_profiles.forEach((p) =>
        list.push({
          ...p,
          kind: "underperforming",
        }),
      );
      ops.accepted_not_activated_profiles.forEach((p) =>
        list.push({
          ...p,
          kind: "accepted_not_activated",
          source_proposal_id: p.source_proposal_id,
          source_proposal_name: p.source_proposal_name,
        }),
      );
      // dedupe by id, prefer current > others
      const byId = new Map<number, ProfileRow>();
      for (const r of list) {
        if (!byId.has(r.id) || r.kind === "current") {
          byId.set(r.id, r);
        }
      }
      setRows(Array.from(byId.values()));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleActivate(id: number) {
    if (!confirm(`Activate profile id=${id}?`)) return;
    setActivatingId(id);
    setError(null);
    try {
      await request(`/api/v1/score-profiles/${id}/activate/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setActivatingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Profiles (summary)</h1>
      <p className="text-sm text-slate-600">
        This view is based on ops-summary and shows currently relevant profiles (current /
        stale / underperforming / accepted-but-not-activated).
      </p>
      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {loading && <p className="text-sm text-slate-600">Loading...</p>}

      <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="border px-2 py-1 text-left">ID</th>
              <th className="border px-2 py-1 text-left">Name</th>
              <th className="border px-2 py-1 text-left">Version</th>
              <th className="border px-2 py-1 text-left">Active</th>
              <th className="border px-2 py-1 text-left">Kind</th>
              <th className="border px-2 py-1 text-left">Source proposal</th>
              <th className="border px-2 py-1 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr
                key={p.id}
                className={`${p.is_active ? "bg-emerald-50" : "odd:bg-slate-50"}`}
              >
                <td className="border px-2 py-1">{p.id}</td>
                <td className="border px-2 py-1 font-medium">{p.name}</td>
                <td className="border px-2 py-1">{p.version}</td>
                <td className="border px-2 py-1">{String(p.is_active)}</td>
                <td className="border px-2 py-1">{p.kind}</td>
                <td className="border px-2 py-1">
                  {p.source_proposal_id ? (
                    <Link
                      href={`/proposals/${p.source_proposal_id}`}
                      className="text-blue-600 hover:underline"
                    >
                      {p.source_proposal_name} (id={p.source_proposal_id})
                    </Link>
                  ) : (
                    "-"
                  )}
                </td>
                <td className="border px-2 py-1">
                  <button
                    type="button"
                    onClick={() => handleActivate(p.id)}
                    disabled={activatingId === p.id}
                    className="rounded bg-slate-900 px-3 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-60"
                  >
                    {activatingId === p.id ? "Activating..." : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="border px-2 py-2 text-center text-slate-500">
                  No profiles in ops summary.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <section className="rounded border bg-white p-3 text-xs text-slate-600">
        <p className="font-semibold">Compare helper</p>
        <p>
          Use profile ids from this table on{" "}
          <Link href="/profiles/compare" className="text-blue-600 hover:underline">
            Compare
          </Link>{" "}
          page.
        </p>
      </section>
    </div>
  );
}

