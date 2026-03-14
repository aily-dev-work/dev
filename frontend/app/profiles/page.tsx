"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getScoreProfiles, request } from "@/lib/api";
import type { ScoreProfileListItem } from "@/types/api";

export default function ProfilesPage() {
  const [rows, setRows] = useState<ScoreProfileListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activatingId, setActivatingId] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const list = await getScoreProfiles();
      setRows(list);
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
      <h1 className="text-2xl font-semibold">Profiles</h1>
      <p className="text-sm text-slate-600">
        Full list of ScoreProfiles. Activate or compare from here.
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
              <th className="border px-2 py-1 text-left">Description</th>
              <th className="border px-2 py-1 text-left">Source proposal</th>
              <th className="border px-2 py-1 text-left">Created</th>
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
                <td className="max-w-[200px] truncate border px-2 py-1 text-slate-600">
                  {p.description || "-"}
                </td>
                <td className="border px-2 py-1">
                  {p.source_proposal_id ? (
                    <Link
                      href={`/proposals/${p.source_proposal_id}`}
                      className="text-blue-600 hover:underline"
                    >
                      {p.source_proposal_name ?? "?"} (id={p.source_proposal_id})
                    </Link>
                  ) : (
                    "-"
                  )}
                </td>
                <td className="border px-2 py-1 text-xs text-slate-500">
                  {p.created_at ? new Date(p.created_at).toLocaleDateString() : "-"}
                </td>
                <td className="border px-2 py-1">
                  <span className="flex flex-wrap gap-1">
                    <button
                      type="button"
                      onClick={() => handleActivate(p.id)}
                      disabled={activatingId === p.id}
                      className="rounded bg-slate-900 px-3 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-60"
                    >
                      {activatingId === p.id ? "Activating..." : "Activate"}
                    </button>
                    <Link
                      href={`/profiles/compare?base=${p.id}`}
                      className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
                    >
                      Compare
                    </Link>
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 && !loading && (
              <tr>
                <td colSpan={8} className="border px-2 py-2 text-center text-slate-500">
                  No profiles.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
