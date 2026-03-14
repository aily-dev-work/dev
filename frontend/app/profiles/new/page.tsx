"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createScoreProfile } from "@/lib/api";

export default function NewProfilePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [version, setVersion] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !version.trim()) {
      setError("名前とバージョンは必須です。");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createScoreProfile({
        name: name.trim(),
        version: version.trim(),
        description: description.trim() || undefined,
      });
      router.push("/profiles");
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Link href="/profiles" className="text-sm text-slate-600 hover:text-slate-900">
          ← プロファイル一覧
        </Link>
      </div>
      <h1 className="text-2xl font-semibold">プロファイル新規作成</h1>
      <p className="text-sm text-slate-600">
        名前・バージョン・説明を入力してください。重み・閾値はデフォルトで作成されます。
      </p>
      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="max-w-lg space-y-4 rounded-lg border bg-white p-4 shadow-sm">
        <label className="block">
          <span className="text-sm font-medium text-slate-700">名前 *</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm"
            placeholder="例: デフォルトスコアプロファイル"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">バージョン *</span>
          <input
            type="text"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm"
            placeholder="例: v1"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">説明（任意）</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm"
            placeholder="このプロファイルの用途やメモ"
          />
        </label>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-60"
          >
            {submitting ? "作成中..." : "作成"}
          </button>
          <Link
            href="/profiles"
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            キャンセル
          </Link>
        </div>
      </form>
    </div>
  );
}
