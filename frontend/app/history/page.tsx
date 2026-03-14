"use client";

import { useEffect, useState } from "react";
import { request, deleteActivationHistory, getScoreProfiles } from "@/lib/api";
import type { ActivationHistoryItem, ScoreProfileListItem } from "@/types/api";

export default function HistoryPage() {
  const [items, setItems] = useState<ActivationHistoryItem[]>([]);
  const [profiles, setProfiles] = useState<ScoreProfileListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profileId, setProfileId] = useState<string>("");
  const [deletingId, setDeletingId] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (profileId) params.set("profile_id", profileId);
      const path =
        "/api/v1/score-profiles/activation-history/" +
        (params.toString() ? `?${params.toString()}` : "");
      const res = await request<ActivationHistoryItem[]>(path);
      setItems(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    getScoreProfiles()
      .then(setProfiles)
      .catch(() => setProfiles([]));
  }, []);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilterSubmit(e: React.FormEvent) {
    e.preventDefault();
    void load();
  }

  async function handleDelete(h: ActivationHistoryItem) {
    if (!confirm(`この有効化履歴（id=${h.id}）を削除しますか？`)) return;
    setDeletingId(h.id);
    setError(null);
    try {
      await deleteActivationHistory(h.id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">プロファイル変更履歴</h1>
      <form
        onSubmit={handleFilterSubmit}
        className="flex flex-wrap items-end gap-3 rounded border bg-white p-3 text-sm shadow-sm"
      >
        <label className="flex flex-col">
          <span className="mb-1 font-medium">プロファイル名</span>
          <select
            value={profileId}
            onChange={(e) => setProfileId(e.target.value)}
            className="min-w-[180px] rounded border px-2 py-1"
          >
            <option value="">(すべて)</option>
            {profiles.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
        >
          絞り込み
        </button>
      </form>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {loading && <p className="text-sm text-slate-600">読み込み中...</p>}

      <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
        <table className="min-w-full text-xs md:text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="border px-2 py-1 text-center">変更日時</th>
              <th className="border px-2 py-1 text-center">直前プロファイル</th>
              <th className="border px-2 py-1 text-center">現在プロファイル</th>
              <th className="border px-2 py-1 text-center">採用したAI提案</th>
              <th className="border px-2 py-1 text-center w-20">操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((h) => (
              <tr key={h.id} className="odd:bg-slate-50">
                <td className="border px-2 py-1">
                  {h.activated_at ? new Date(h.activated_at).toLocaleString() : "-"}
                </td>
                <td className="border px-2 py-1">
                  {h.previous_profile_name ?? "-"}
                </td>
                <td className="border px-2 py-1">
                  {h.activated_profile_name ?? "-"}
                </td>
                <td className="border px-2 py-1">
                  {h.source_proposal_id
                    ? `${h.source_proposal_name} [id=${h.source_proposal_id}]`
                    : "-"}
                </td>
                <td className="border px-2 py-1 text-center">
                  <button
                    type="button"
                    onClick={() => handleDelete(h)}
                    disabled={deletingId === h.id}
                    className="rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    {deletingId === h.id ? "削除中..." : "削除"}
                  </button>
                </td>
              </tr>
            ))}
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={5} className="border px-2 py-2 text-center text-slate-500">
                  履歴がありません。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

