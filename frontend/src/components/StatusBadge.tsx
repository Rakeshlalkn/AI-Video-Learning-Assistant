"use client";

import clsx from "clsx";
import type { VideoStatus } from "@/lib/types";

const labels: Record<VideoStatus, string> = {
  pending: "Pending",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

const colors: Record<VideoStatus, string> = {
  pending: "bg-gray-100 text-gray-700",
  processing: "bg-amber-100 text-amber-800",
  ready: "bg-emerald-100 text-emerald-800",
  failed: "bg-rose-100 text-rose-800",
};

export function StatusBadge({ status }: { status: VideoStatus }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        colors[status],
      )}
    >
      {status === "processing" && (
        <span className="mr-1.5 h-2 w-2 animate-pulse rounded-full bg-amber-500" />
      )}
      {labels[status]}
    </span>
  );
}
