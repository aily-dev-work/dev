"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createScoreProfile } from "@/lib/api";
import { DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS } from "@/lib/profileDefaults";

const initialWeightsJson = JSON.stringify(DEFAULT_WEIGHTS, null, 2);
const initialThresholdsJson = JSON.stringify(DEFAULT_THRESHOLDS, null, 2);

export default function NewProfilePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [version, setVersion] = useState("");
  const [description, setDescription] = useState("");
  const [weightsJson, setWeightsJson] = useState(initialWeightsJson);
  const [thresholdsJson, setThresholdsJson] = useState(initialThresholdsJson);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !version.trim()) {
      setError("名前とバージョンは必須です。");
      return;
    }
    let weights: Record<string, unknown>;
    let thresholds: Record<string, unknown>;
    try {
      weights = JSON.parse(weightsJson) as Record<string, unknown>;
      if (typeof weights !== "object" || weights === null) throw new Error("重みはオブジェクトである必要があります");
    } catch {
      setError("重みの JSON が不正です。");
      return;
    }
    try {
      thresholds = JSON.parse(thresholdsJson) as Record<string, unknown>;
      if (typeof thresholds !== "object" || thresholds === null) throw new Error("閾値はオブジェクトである必要があります");
    } catch {
      setError("閾値の JSON が不正です。");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createScoreProfile({
        name: name.trim(),
        version: version.trim(),
        description: description.trim() || undefined,
        weights_json: weights,
        thresholds_json: thresholds,
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
            className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm font-mono"
            placeholder="このプロファイルの用途やメモ"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">重み（JSON） *</span>
          <textarea
            value={weightsJson}
            onChange={(e) => setWeightsJson(e.target.value)}
            rows={14}
            className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm font-mono"
            spellCheck={false}
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">閾値（JSON） *</span>
          <textarea
            value={thresholdsJson}
            onChange={(e) => setThresholdsJson(e.target.value)}
            rows={6}
            className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm font-mono"
            spellCheck={false}
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
