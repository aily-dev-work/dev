"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { getScoreProfile, updateScoreProfile } from "@/lib/api";
import { DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS } from "@/lib/profileDefaults";
import {
  normalizeWeights,
  normalizeThresholds,
  weightsToApi,
  thresholdsToApi,
  ProfileWeightsForm,
  ProfileThresholdsForm,
} from "@/app/profiles/ProfileWeightsThresholdsForm";
import type { WeightsFormValue, ThresholdsFormValue } from "@/app/profiles/ProfileWeightsThresholdsForm";

export default function EditProfilePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [weights, setWeights] = useState<WeightsFormValue>(() => normalizeWeights(DEFAULT_WEIGHTS));
  const [thresholds, setThresholds] = useState<ThresholdsFormValue>(() => normalizeThresholds(DEFAULT_THRESHOLDS));
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (Number.isNaN(id)) {
      setError("無効なプロファイル ID です。");
      setLoading(false);
      return;
    }
    let ok = true;
    setLoading(true);
    setError(null);
    getScoreProfile(id)
      .then((p) => {
        if (ok) {
          setName(p.name);
          setDescription(p.description || "");
          setWeights(normalizeWeights(p.weights_json ?? DEFAULT_WEIGHTS));
          setThresholds(normalizeThresholds(p.thresholds_json ?? DEFAULT_THRESHOLDS));
        }
      })
      .catch((e) => {
        if (ok) setError((e as Error).message);
      })
      .finally(() => {
        if (ok) setLoading(false);
      });
    return () => {
      ok = false;
    };
  }, [id]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (Number.isNaN(id) || !name.trim()) {
      setError("名前は必須です。");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await updateScoreProfile(id, {
        name: name.trim(),
        description: description.trim(),
        weights_json: weightsToApi(weights),
        thresholds_json: thresholdsToApi(thresholds),
      });
      router.push("/profiles");
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Link href="/profiles" className="text-sm text-slate-600 hover:text-slate-900">
          ← プロファイル一覧
        </Link>
        <p className="text-sm text-slate-600">読み込み中...</p>
      </div>
    );
  }

  if (error && !name) {
    return (
      <div className="space-y-4">
        <Link href="/profiles" className="text-sm text-slate-600 hover:text-slate-900">
          ← プロファイル一覧
        </Link>
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Link href="/profiles" className="text-sm text-slate-600 hover:text-slate-900">
          ← プロファイル一覧
        </Link>
      </div>
      <h1 className="text-2xl font-semibold">プロファイル編集</h1>
      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="max-w-5xl space-y-4 rounded-lg border bg-white p-4 shadow-sm">
        <label className="block">
          <span className="text-sm font-medium text-slate-700">名前 *</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">説明（任意）</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm font-mono"
          />
        </label>
        <div className="block">
          <span className="text-sm font-medium text-slate-700">重み</span>
          <div className="mt-2 rounded-lg border border-slate-200 bg-white p-3">
            <ProfileWeightsForm value={weights} onChange={setWeights} />
          </div>
        </div>
        <div className="block">
          <span className="text-sm font-medium text-slate-700">閾値</span>
          <div className="mt-2 rounded-lg border border-slate-200 bg-white p-3">
            <ProfileThresholdsForm value={thresholds} onChange={setThresholds} />
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-60"
          >
            {submitting ? "保存中..." : "保存"}
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
