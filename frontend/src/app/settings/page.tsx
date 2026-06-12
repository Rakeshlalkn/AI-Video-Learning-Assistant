"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, User as UserIcon, Info } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

export default function SettingsPage() {
  return (
    <RequireAuth>
      <AppShell>
        <SettingsInner />
      </AppShell>
    </RequireAuth>
  );
}

function SettingsInner() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .get("/health")
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold">
          <UserIcon className="h-5 w-5" />
          Account
        </h2>
        {user ? (
          <div className="flex items-center gap-4">
            {user.profile_image ? (
              <img src={user.profile_image} alt={user.name} className="h-14 w-14 rounded-full" />
            ) : (
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-100 text-brand-700 text-xl font-semibold">
                {user.name?.[0]?.toUpperCase()}
              </div>
            )}
            <div>
              <div className="font-medium">{user.name}</div>
              <div className="text-sm text-gray-500">{user.email}</div>
            </div>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Not signed in.</p>
        )}
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold">
          <Info className="h-5 w-5" />
          System
        </h2>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500">Backend</dt>
            <dd>
              {backendOk === null ? "Checking…" : backendOk ? "Connected ✓" : "Unreachable ✗"}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Storage</dt>
            <dd>Local filesystem</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Vector store</dt>
            <dd>ChromaDB (local)</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">AI model</dt>
            <dd>Gemini 2.5 Flash</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Transcription</dt>
            <dd>Faster-Whisper (local)</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
