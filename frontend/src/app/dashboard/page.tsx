"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileVideo, FileText, CheckCircle2, Upload as UploadIcon } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { ProgressBar, StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { DashboardResponse } from "@/lib/types";

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: any;
  label: string;
  value: number | string;
  accent: string;
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-500">{label}</div>
        <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${accent}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="mt-2 text-3xl font-semibold">{value}</div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <AppShell>
        <DashboardInner />
      </AppShell>
    </RequireAuth>
  );
}

function DashboardInner() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<DashboardResponse>("/dashboard")
      .then((r) => setData(r.data))
      .catch((e) => setError(e?.response?.data?.detail || e?.message));
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-gray-500">Overview of your video library</p>
        </div>
        <Link
          href="/upload"
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-brand-700"
        >
          <UploadIcon className="h-4 w-4" />
          Upload Video
        </Link>
      </div>

      {error && (
        <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          icon={FileVideo}
          label="Total Videos"
          value={data?.total_videos ?? "—"}
          accent="bg-brand-100 text-brand-700"
        />
        <StatCard
          icon={FileText}
          label="Total Documents"
          value={data?.total_documents ?? "—"}
          accent="bg-emerald-100 text-emerald-700"
        />
        <StatCard
          icon={CheckCircle2}
          label="Ready"
          value={data?.ready_videos ?? "—"}
          accent="bg-amber-100 text-amber-700"
        />
      </div>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Recent Uploads</h2>
        <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
          {data && data.recent.length === 0 ? (
            <div className="p-8 text-center text-sm text-gray-500">
              No videos yet.{" "}
              <Link href="/upload" className="text-brand-600 underline">
                Upload your first one
              </Link>
              .
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {data?.recent.map((v) => (
                  <tr key={v.id} className="border-t border-gray-100">
                    <td className="px-4 py-3 font-medium">
                      {v.title}
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
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/videos/${v.id}`}
                        className="text-brand-600 hover:underline"
                      >
                        Open →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
