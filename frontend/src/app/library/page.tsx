"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Trash2, MessageSquare, FileText, RefreshCw } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { ProgressBar, StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { Video, VideoSummary } from "@/lib/types";

export default function LibraryPage() {
  return (
    <RequireAuth>
      <AppShell>
        <LibraryInner />
      </AppShell>
    </RequireAuth>
  );
}

function LibraryInner() {
  const [videos, setVideos] = useState<VideoSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<VideoSummary[]>("/videos");
      setVideos(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Poll while anything is processing
  useEffect(() => {
    if (!videos.some((v) => v.status === "pending" || v.status === "processing")) return;
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, [videos, load]);

  async function handleDelete(id: number) {
    if (!confirm("Delete this video and all its notes? This cannot be undone.")) return;
    try {
      await api.delete(`/videos/${id}`);
      setVideos((vs) => vs.filter((v) => v.id !== id));
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || "Delete failed");
    }
  }

  async function handleReprocess(id: number) {
    try {
      await api.post(`/videos/${id}/process`);
      load();
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || "Re-process failed");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Video Library</h1>
          <p className="text-sm text-gray-500">All your uploaded and imported videos</p>
        </div>
        <Link
          href="/upload"
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-brand-700"
        >
          Add video
        </Link>
      </div>

      {error && (
        <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
        {loading ? (
          <div className="p-8 text-center text-sm text-gray-500">Loading…</div>
        ) : videos.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">
            No videos yet. <Link href="/upload" className="text-brand-600 underline">Upload one</Link>.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {videos.map((v) => (
                <tr key={v.id} className="border-t border-gray-100">
                  <td className="px-4 py-3 font-medium">
                    <Link href={`/videos/${v.id}`} className="hover:underline">
                      {v.title}
                    </Link>
                    {(v.status === "pending" || v.status === "processing") && (
                      <div className="mt-1.5 max-w-xs">
                        <ProgressBar
                          pct={v.progress_pct ?? 0}
                          label={v.progress ?? "Queued…"}
                        />
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{v.source_type}</td>
                  <td className="px-4 py-3"><StatusBadge status={v.status} /></td>
                  <td className="px-4 py-3 text-gray-600">
                    {new Date(v.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        href={`/videos/${v.id}`}
                        className="rounded p-1.5 text-gray-600 hover:bg-gray-100"
                        title="Open"
                      >
                        <FileText className="h-4 w-4" />
                      </Link>
                      <Link
                        href={`/videos/${v.id}/chat`}
                        className="rounded p-1.5 text-gray-600 hover:bg-gray-100"
                        title="Chat"
                      >
                        <MessageSquare className="h-4 w-4" />
                      </Link>
                      {v.status === "failed" && (
                        <button
                          onClick={() => handleReprocess(v.id)}
                          className="rounded p-1.5 text-gray-600 hover:bg-gray-100"
                          title="Re-process"
                        >
                          <RefreshCw className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(v.id)}
                        className="rounded p-1.5 text-rose-600 hover:bg-rose-50"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
