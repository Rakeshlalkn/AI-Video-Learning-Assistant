"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Send, Loader2, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { ChatResponse, Video } from "@/lib/types";

type Message = { role: "user" | "assistant"; content: string };

const SUGGESTIONS = [
  "Summarize this lesson",
  "What are the key concepts?",
  "Explain the main topic",
  "Generate 5 quiz questions",
  "Create 5 flashcards",
];

export default function ChatPage() {
  return (
    <RequireAuth>
      <AppShell>
        <ChatInner />
      </AppShell>
    </RequireAuth>
  );
}

function ChatInner() {
  const params = useParams<{ id: string }>();
  const videoId = Number(Array.isArray(params?.id) ? params?.id[0] : params?.id);
  const [video, setVideo] = useState<Video | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    api.get<Video>(`/videos/${videoId}`).then((r) => setVideo(r.data)).catch((e) =>
      setError(e?.response?.data?.detail || e?.message),
    );
  }, [videoId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const send = useCallback(
    async (q: string) => {
      const text = q.trim();
      if (!text || loading) return;
      setMessages((m) => [...m, { role: "user", content: text }]);
      setInput("");
      setLoading(true);
      setError(null);
      try {
        const { data } = await api.post<ChatResponse>("/chat", {
          video_id: videoId,
          question: text,
        });
        setMessages((m) => [...m, { role: "assistant", content: data.answer }]);
      } catch (e: any) {
        setError(e?.response?.data?.detail || e?.message || "Chat failed");
        setMessages((m) => [
          ...m,
          { role: "assistant", content: "Sorry — something went wrong. Please try again." },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [loading, videoId],
  );

  function onKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  const ready = video?.status === "ready";

  return (
    <div className="flex h-screen flex-col">
      <header className="border-b border-gray-200 bg-white px-6 py-3">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href={`/videos/${videoId}`}
              className="rounded p-1.5 text-gray-500 hover:bg-gray-100"
              title="Back"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div>
              <div className="font-semibold">{video?.title ?? "Loading…"}</div>
              {video && (
                <div className="text-xs text-gray-500">
                  <StatusBadge status={video.status} />
                </div>
              )}
            </div>
          </div>
          <div className="text-xs text-gray-500">Powered by Gemini · RAG over transcript</div>
        </div>
      </header>

      <main ref={scrollRef} className="flex-1 overflow-y-auto bg-gray-50">
        <div className="mx-auto max-w-4xl space-y-4 px-6 py-6">
          {messages.length === 0 && (
            <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center">
              <Sparkles className="mx-auto mb-3 h-8 w-8 text-brand-500" />
              <h2 className="text-lg font-semibold">What do you want to know?</h2>
              <p className="mt-1 text-sm text-gray-500">
                I only answer from the video, so if the speaker didn't cover
                it, I'll say so. That keeps me honest.
              </p>
              {!ready && video && (
                <p className="mt-3 text-sm text-amber-700">
                  Hang on — the video is still being processed
                  ({video.status}). I'll be ready as soon as it is.
                </p>
              )}
              {ready && (
                <div className="mt-5 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="rounded-full border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:border-brand-500 hover:text-brand-700"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-2xl rounded-2xl px-4 py-3 ${
                  m.role === "user"
                    ? "bg-brand-600 text-white"
                    : "bg-white border border-gray-200"
                }`}
              >
                {m.role === "assistant" ? (
                  <article className="markdown-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </article>
                ) : (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Looking through the transcript…
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
              {error}
            </div>
          )}
        </div>
      </main>

      <footer className="border-t border-gray-200 bg-white">
        <div className="mx-auto max-w-4xl px-6 py-3">
          <div className="flex items-end gap-2 rounded-2xl border border-gray-300 bg-white p-2 focus-within:border-brand-500">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              placeholder={ready ? "Ask about the video…   (Enter to send · Shift+Enter for newline)" : "Waiting for video to be ready…"}
              disabled={!ready || loading}
              className="flex-1 resize-none px-2 py-2 text-sm outline-none disabled:opacity-60"
            />
            <button
              onClick={() => send(input)}
              disabled={!ready || loading || !input.trim()}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow hover:bg-brand-700 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
