"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  MessageSquare,
  FileText,
  RefreshCw,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { DocumentRecord, Video } from "@/lib/types";
import { NotesEditor } from "@/components/NotesEditor";

type Tab = "overview" | "notes" | "transcript";

export default function VideoDetailPage() {
  return (
    <RequireAuth>
      <AppShell>
        <VideoDetailInner />
      </AppShell>
    </RequireAuth>
  );
}

function VideoDetailInner() {
  const params = useParams<{ id: string }>();
  const id = Number(Array.isArray(params?.id) ? params?.id[0] : params?.id);
  const router = useRouter();
  const [video, setVideo] = useState<Video | null>(null);
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [v, d] = await Promise.all([
        api.get<Video>(`/videos/${id}`),
        api.get<DocumentRecord[]>(`/videos/${id}/documents`),
      ]);
      setVideo(v.data);
      setDocs(d.data);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll while processing
  useEffect(() => {
    if (!video) return;
    if (video.status !== "pending" && video.status !== "processing") return;
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [video, load]);

  async function handleReprocess() {
    try {
      await api.post(`/videos/${id}/process`);
      load();
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this video and all its notes?")) return;
    try {
      await api.delete(`/videos/${id}`);
      router.push("/library");
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message);
    }
  }

  if (error) {
    return (
      <div className="rounded-lg bg-rose-50 border border-rose-200 p-4 text-sm text-rose-700">
        {error}
      </div>
    );
  }
  if (!video) {
    return <div className="text-sm text-gray-500">Loading…</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/library"
          className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-800"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to library
        </Link>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{video.title}</h1>
          <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
            <StatusBadge status={video.status} />
            <span>·</span>
            <span>{video.source_type === "youtube" ? "YouTube" : "Upload"}</span>
            <span>·</span>
            <span>{new Date(video.created_at).toLocaleString()}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={`/videos/${video.id}/chat`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
          >
            <MessageSquare className="h-4 w-4" />
            Chat
          </Link>
          {video.status === "failed" && (
            <button
              onClick={handleReprocess}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
            >
              <RefreshCw className="h-4 w-4" />
              Re-process
            </button>
          )}
          <button
            onClick={handleDelete}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-sm font-medium text-rose-700 hover:bg-rose-50"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </button>
        </div>
      </header>

      {video.status === "failed" && video.error_message && (
        <div className="flex items-start gap-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <div>
            <div className="font-medium">Processing failed</div>
            <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap text-xs">
              {video.error_message}
            </pre>
          </div>
        </div>
      )}

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {(["overview", "notes", "transcript"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`border-b-2 px-1 pb-3 text-sm font-medium capitalize transition ${
                tab === t
                  ? "border-brand-600 text-brand-700"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {tab === "overview" && (
        <OverviewTab video={video} docsCount={docs.length} />
      )}

      {tab === "notes" && (
        <NotesEditor
          videoId={video.id}
          documents={docs}
          onUpdate={load}
        />
      )}

      {tab === "transcript" && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6">
          <h2 className="mb-3 text-lg font-semibold">Transcript</h2>
          {video.transcript ? (
            <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm leading-6 text-gray-800">
              {video.transcript}
            </pre>
          ) : (
            <p className="text-sm text-gray-500">Transcript not available yet.</p>
          )}
        </div>
      )}
    </div>
  );
}

function OverviewTab({ video, docsCount }: { video: Video; docsCount: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div className="rounded-2xl border border-gray-200 bg-white p-5">
        <div className="text-sm text-gray-500">Status</div>
        <div className="mt-2"><StatusBadge status={video.status} /></div>
      </div>
      <div className="rounded-2xl border border-gray-200 bg-white p-5">
        <div className="text-sm text-gray-500">Documents</div>
        <div className="mt-2 text-2xl font-semibold">{docsCount}</div>
      </div>
      <div className="rounded-2xl border border-gray-200 bg-white p-5">
        <div className="text-sm text-gray-500">Transcript length</div>
        <div className="mt-2 text-2xl font-semibold">
          {video.transcript ? `${Math.max(1, Math.round(video.transcript.length / 5))} words` : "—"}
        </div>
      </div>
    </div>
  );
}
