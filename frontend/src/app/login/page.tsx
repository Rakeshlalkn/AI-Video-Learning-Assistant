"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Video } from "lucide-react";
import { useAuth } from "@/lib/auth";

// Google Identity Services types (loose; we don't ship @types for it)
declare global {
  interface Window {
    google?: any;
  }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

export default function LoginPage() {
  const {
    loginWithGoogleIdToken,
    loginWithCredentials,
    registerWithCredentials,
    token,
    ready,
  } = useAuth();
  const router = useRouter();
  const buttonDivRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [devEmail, setDevEmail] = useState("dev@example.com");
  const [devName, setDevName] = useState("Dev User");
  const [submitting, setSubmitting] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");

  // Redirect if already logged in
  useEffect(() => {
    if (ready && token) router.replace("/dashboard");
  }, [ready, token, router]);

  // Load Google Identity Services
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (!window.google || !buttonDivRef.current) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleCredentialResponse,
      });
      window.google.accounts.id.renderButton(buttonDivRef.current, {
        theme: "outline",
        size: "large",
        width: 320,
        text: "signin_with",
      });
    };
    document.head.appendChild(script);
    return () => {
      document.head.removeChild(script);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCredentialResponse(response: { credential: string }) {
    setError(null);
    setSubmitting(true);
    try {
      await loginWithGoogleIdToken(response.credential);
      router.replace("/dashboard");
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Sign-in failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function devLogin() {
    setError(null);
    setSubmitting(true);
    try {
      // Build an unsigned JWT-shaped string with the user info in the payload.
      // The backend falls back to decoding without verification when
      // GOOGLE_CLIENT_ID is not set (dev mode).
      const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
      const payload = btoa(
        JSON.stringify({
          sub: `dev-${devEmail}`,
          email: devEmail,
          name: devName,
          picture: "",
        }),
      );
      const fakeIdToken = `${header}.${payload}.`;
      await loginWithGoogleIdToken(fakeIdToken);
      router.replace("/dashboard");
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Dev login failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCredentialsSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "register") {
        await registerWithCredentials(name || email.split("@")[0], email, password);
      } else {
        await loginWithCredentials(email, password);
      }
      router.replace("/dashboard");
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  }

  const isDev = !GOOGLE_CLIENT_ID || GOOGLE_CLIENT_ID.includes("your-google-client-id");

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 via-white to-brand-100 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-white">
            <Video className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">AI Video Learning</h1>
            <p className="text-sm text-gray-500">Sign in to continue</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-gray-50 p-4">
            <div>
              <p className="text-sm font-medium">Manual credential login</p>
              <p className="text-xs text-gray-500">
                Use email/password to sign in or register.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
              className="rounded-full border border-gray-300 bg-white px-3 py-1 text-sm font-semibold text-gray-700 hover:bg-gray-100"
            >
              {mode === "login" ? "Register" : "Sign in"}
            </button>
          </div>

          {mode === "register" && (
            <label className="block text-sm">
              <span className="text-gray-700">Name</span>
              <input
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Optional"
              />
            </label>
          )}

          <label className="block text-sm">
            <span className="text-gray-700">Email</span>
            <input
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          <label className="block text-sm">
            <span className="text-gray-700">Password</span>
            <input
              type="password"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>

          <button
            onClick={handleCredentialsSubmit}
            disabled={submitting || !email || !password}
            className="w-full rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow hover:bg-brand-700 disabled:opacity-60"
          >
            {submitting
              ? mode === "register"
                ? "Creating account…"
                : "Signing in…"
              : mode === "register"
              ? "Create account"
              : "Sign in"}
          </button>

          {isDev && (
            <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
              <strong>Dev mode:</strong> set <code>NEXT_PUBLIC_GOOGLE_CLIENT_ID</code> in
              <code> frontend/.env.local</code> to enable real Google login. For now you can
              sign in as a dev user.
            </div>
          )}

          {isDev && (
            <div className="space-y-3">
              <label className="block text-sm">
                <span className="text-gray-700">Name</span>
                <input
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500"
                  value={devName}
                  onChange={(e) => setDevName(e.target.value)}
                />
              </label>
              <label className="block text-sm">
                <span className="text-gray-700">Email</span>
                <input
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500"
                  value={devEmail}
                  onChange={(e) => setDevEmail(e.target.value)}
                />
              </label>
              <button
                onClick={devLogin}
                disabled={submitting}
                className="w-full rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow hover:bg-brand-700 disabled:opacity-60"
              >
                {submitting ? "Signing in…" : "Sign in as dev user"}
              </button>
            </div>
          )}

          {!isDev && (
            <div className="flex flex-col items-center gap-3">
              <div ref={buttonDivRef} />
              {submitting && <p className="text-sm text-gray-500">Signing you in…</p>}
            </div>
          )}

          {error && (
            <div className="mt-4 rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
