"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { deleteScoreProfile, getScoreProfiles, request } from "@/lib/api";
import type { ScoreProfileListItem } from "@/types/api";
import { ProfileWeightsMiniChart } from "@/app/profiles/ProfileWeightsMiniChart";

export default function ProfilesPage() {
  const [rows, setRows] = useState<ScoreProfileListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activatingId, setActivatingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

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

  async function handleUse(id: number) {
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

  async function handleDelete(id: number, name: string) {
    if (!confirm(`プロファイル「${name}」(id=${id}) を削除しますか？\nアクティブなプロファイルは削除できません。`)) return;
    setDeletingId(id);
    setError(null);
    try {
      await deleteScoreProfile(id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">プロファイル</h1>
          <p className="text-sm text-slate-600">
            スコアプロファイルの一覧。「使用する」でスコア計算に使うプロファイルを切り替えられます。
          </p>
        </div>
        <Link
          href="/profiles/new"
          className="rounded-md bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-teal-700"
        >
          新規作成
        </Link>
      </div>
      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {loading && <p className="text-sm text-slate-600">読み込み中...</p>}

      <div className="w-full overflow-x-auto rounded-lg border bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="w-24 border px-2 py-1 text-center">使用</th>
              <th className="min-w-[140px] border px-2 py-1 text-center">名前</th>
              <th className="min-w-[220px] border px-2 py-1 text-center">説明</th>
              <th className="min-w-[480px] border px-2 py-1 text-center">設定（重み）</th>
              <th className="min-w-[120px] border px-2 py-1 text-center">操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr
                key={p.id}
                className={p.is_active ? "bg-teal-50" : "odd:bg-slate-50"}
              >
                <td className="border px-2 py-1 text-center">
                  {p.is_active ? (
                    <span className="inline-flex items-center rounded-md bg-teal-600 px-2.5 py-1 text-xs font-medium text-white">
                      使用中
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleUse(p.id)}
                      disabled={activatingId === p.id}
                      className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                    >
                      {activatingId === p.id ? "適用中..." : "使用する"}
                    </button>
                  )}
                </td>
                <td className="border px-2 py-1 text-center font-medium">{p.name}</td>
                <td className="border px-2 py-1 text-center text-slate-600">
                  <span className="line-clamp-2" title={p.description || undefined}>
                    {p.description || "-"}
                  </span>
                </td>
                <td className="border px-2 py-1 align-middle text-center">
                  <div className="mx-auto flex justify-center">
                    <ProfileWeightsMiniChart weightsJson={p.weights_json} />
                  </div>
                </td>
                <td className="border px-2 py-1 text-center">
                  <span className="inline-flex flex-wrap justify-center gap-1">
                    <Link
                      href={`/profiles/${p.id}/edit`}
                      className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
                    >
                      編集
                    </Link>
                    <button
                      type="button"
                      onClick={() => handleDelete(p.id, p.name)}
                      disabled={deletingId === p.id || p.is_active}
                      className="rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      title={p.is_active ? "使用中のプロファイルは削除できません" : undefined}
                    >
                      {deletingId === p.id ? "削除中..." : "削除"}
                    </button>
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 && !loading && (
              <tr>
                <td colSpan={5} className="border px-2 py-2 text-center text-slate-500">
                  プロファイルがありません。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
