"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Upload as UploadIcon, Youtube, Loader2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { api } from "@/lib/api";
import type { Video } from "@/lib/types";

const ALLOWED = [".mp4", ".mkv", ".mov", ".avi", ".webm"];

export default function UploadPage() {
  return (
    <RequireAuth>
      <AppShell>
        <UploadInner />
      </AppShell>
    </RequireAuth>
  );
}

function UploadInner() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [youtubeTitle, setYoutubeTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  async function handleFileUpload() {
    if (!file) return;
    setError(null);
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (title) fd.append("title", title);
      const { data } = await api.post<Video>("/videos/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      router.push(`/videos/${data.id}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Upload failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleYoutube() {
    if (!youtubeUrl) return;
    setError(null);
    setSubmitting(true);
    try {
      const { data } = await api.post<Video>("/videos/youtube", {
        url: youtubeUrl,
        title: youtubeTitle || null,
      });
      router.push(`/videos/${data.id}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "YouTube import failed");
    } finally {
      setSubmitting(false);
    }
  }

  function pickFile(f: File | null) {
    if (!f) return;
    const ext = "." + (f.name.split(".").pop() || "").toLowerCase();
    if (!ALLOWED.includes(ext)) {
      setError(`Unsupported file type. Allowed: ${ALLOWED.join(", ")}`);
      return;
    }
    setError(null);
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Add a video</h1>
        <p className="text-sm text-gray-500">Upload a file or import from YouTube</p>
      </div>

      {error && (
        <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* File upload */}
        <section className="rounded-2xl border border-gray-200 bg-white p-6">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <UploadIcon className="h-5 w-5" />
            Upload a file
          </h2>
          <label className="block text-sm font-medium text-gray-700">Title (optional)</label>
          <input
            className="mt-1 mb-4 w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500"
            placeholder="My lecture video"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) pickFile(f);
            }}
            className={`flex h-44 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed text-center text-sm transition ${
              dragOver
                ? "border-brand-500 bg-brand-50"
                : "border-gray-300 bg-gray-50 hover:border-gray-400"
            }`}
            onClick={() => document.getElementById("file-input")?.click()}
          >
            <UploadIcon className="mb-2 h-6 w-6 text-gray-400" />
            {file ? (
              <div>
                <div className="font-medium text-gray-800">{file.name}</div>
                <div className="text-xs text-gray-500">
                  {(file.size / (1024 * 1024)).toFixed(1)} MB
                </div>
              </div>
            ) : (
              <div className="text-gray-600">
                <div>Drag &amp; drop a video, or click to select</div>
                <div className="mt-1 text-xs text-gray-500">
                  Supported: {ALLOWED.join(", ")}
                </div>
              </div>
            )}
            <input
              id="file-input"
              type="file"
              accept={ALLOWED.join(",")}
              className="hidden"
              onChange={(e) => pickFile(e.target.files?.[0] || null)}
            />
          </div>

          <button
            onClick={handleFileUpload}
            disabled={!file || submitting}
            className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadIcon className="h-4 w-4" />}
            {submitting ? "Uploading…" : "Upload & process"}
          </button>
        </section>

        {/* YouTube */}
        <section className="rounded-2xl border border-gray-200 bg-white p-6">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <Youtube className="h-5 w-5" />
            Import from YouTube
          </h2>
          <label className="block text-sm font-medium text-gray-700">YouTube URL</label>
          <input
            className="mt-1 mb-4 w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500"
            placeholder="https://www.youtube.com/watch?v=…"
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
          />

          <label className="block text-sm font-medium text-gray-700">Title (optional)</label>
          <input
            className="mt-1 mb-4 w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500"
            placeholder="Auto-detected from the video"
            value={youtubeTitle}
            onChange={(e) => setYoutubeTitle(e.target.value)}
          />

          <button
            onClick={handleYoutube}
            disabled={!youtubeUrl || submitting}
            className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-rose-600 py-2.5 text-sm font-semibold text-white shadow hover:bg-rose-700 disabled:opacity-50"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Youtube className="h-4 w-4" />}
            {submitting ? "Importing…" : "Import & process"}
          </button>
        </section>
      </div>
    </div>
  );
}
