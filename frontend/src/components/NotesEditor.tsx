"use client";

import { useState, useMemo, useEffect } from "react";
import { Save, Download, Loader2, FileText, Eye, Edit3 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, backendBaseUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { DocumentRecord } from "@/lib/types";

export function NotesEditor({
  videoId,
  documents,
  onUpdate,
}: {
  videoId: number;
  documents: DocumentRecord[];
  onUpdate: () => void;
}) {
  const { token } = useAuth();
  const [activeId, setActiveId] = useState<number | null>(documents[0]?.id ?? null);
  const [content, setContent] = useState<string>(documents[0]?.content ?? "");
  const [mode, setMode] = useState<"edit" | "preview">("preview");
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Sync state when the active document or list changes
  useEffect(() => {
    if (documents.length === 0) {
      setActiveId(null);
      setContent("");
      return;
    }
    if (activeId == null || !documents.find((d) => d.id === activeId)) {
      setActiveId(documents[0].id);
      setContent(documents[0].content);
    }
  }, [documents, activeId]);

  const activeDoc = useMemo(
    () => documents.find((d) => d.id === activeId) ?? null,
    [documents, activeId],
  );

  function pickDoc(id: number) {
    setActiveId(id);
    const d = documents.find((x) => x.id === id);
    if (d) {
      setContent(d.content);
      setSavedAt(null);
    }
  }

  async function save() {
    if (!activeDoc) return;
    setSaving(true);
    setError(null);
    try {
      await api.put(`/documents/${activeDoc.id}`, { content });
      setSavedAt(new Date());
      onUpdate();
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  function download() {
    if (!activeDoc) return;
    // The backend returns the file directly; we use the axios baseURL by hand
    // to avoid triggering the JSON response interceptor.
    const url = `${backendBaseUrl}/documents/${activeDoc.id}/download`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${activeDoc.title.replace(/[^a-z0-9-_]+/gi, "_")}.md`;
        a.click();
        URL.revokeObjectURL(a.href);
      });
  }

  if (documents.length === 0) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
        No notes generated yet. They will appear here once processing finishes.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-gray-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 p-3">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-gray-500" />
          <select
            value={activeId ?? ""}
            onChange={(e) => pickDoc(Number(e.target.value))}
            className="rounded-md border border-gray-300 bg-white px-2 py-1 text-sm"
          >
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex overflow-hidden rounded-md border border-gray-300 text-sm">
            <button
              onClick={() => setMode("preview")}
              className={`flex items-center gap-1 px-3 py-1.5 ${
                mode === "preview" ? "bg-brand-50 text-brand-700" : "bg-white text-gray-600"
              }`}
            >
              <Eye className="h-3.5 w-3.5" />
              Preview
            </button>
            <button
              onClick={() => setMode("edit")}
              className={`flex items-center gap-1 border-l border-gray-300 px-3 py-1.5 ${
                mode === "edit" ? "bg-brand-50 text-brand-700" : "bg-white text-gray-600"
              }`}
            >
              <Edit3 className="h-3.5 w-3.5" />
              Edit
            </button>
          </div>
          <button
            onClick={download}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
          >
            <Download className="h-3.5 w-3.5" />
            Download .md
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="inline-flex items-center gap-1.5 rounded-md bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white shadow hover:bg-brand-700 disabled:opacity-60"
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      <div className="p-4">
        {error && (
          <div className="mb-3 rounded-md bg-rose-50 border border-rose-200 p-2 text-sm text-rose-700">
            {error}
          </div>
        )}
        {savedAt && (
          <div className="mb-3 rounded-md bg-emerald-50 border border-emerald-200 p-2 text-sm text-emerald-700">
            Saved at {savedAt.toLocaleTimeString()}
          </div>
        )}

        {mode === "edit" ? (
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="h-[70vh] w-full resize-none rounded-lg border border-gray-300 p-4 font-mono text-sm leading-6 outline-none focus:border-brand-500"
          />
        ) : (
          <article className="markdown-body max-h-[70vh] overflow-auto rounded-lg border border-gray-100 bg-gray-50 p-5">
            {content ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            ) : (
              <p className="text-gray-500">No content.</p>
            )}
          </article>
        )}
      </div>
    </div>
  );
}
