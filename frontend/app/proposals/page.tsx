"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { request } from "@/lib/api";
import type { ScoreProfileProposal } from "@/types/api";

type ProposalsListItem = Pick<
  ScoreProfileProposal,
  "id" | "proposal_name" | "status" | "score_profile_name_snapshot" | "score_profile_version_snapshot" | "created_at"
> & {
  applied_score_profile_id: number | null;
};

export default function ProposalsPage() {
  const [items, setItems] = useState<ProposalsListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">提案</h1>
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
              <th className="border px-2 py-1 text-left">ID</th>
              <th className="border px-2 py-1 text-left">名前</th>
              <th className="border px-2 py-1 text-left">状態</th>
              <th className="border px-2 py-1 text-left">プロファイル</th>
              <th className="border px-2 py-1 text-left">作成日時</th>
              <th className="border px-2 py-1 text-left">反映</th>
              <th className="border px-2 py-1 text-left">詳細</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id} className="odd:bg-slate-50">
                <td className="border px-2 py-1">{p.id}</td>
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
                <td colSpan={7} className="border px-2 py-2 text-center text-slate-500">
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

