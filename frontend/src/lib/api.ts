/**
 * Axios instance configured to talk to the FastAPI backend.
 *
 * - Reads the base URL from NEXT_PUBLIC_BACKEND_URL or uses the same-origin proxy /api/backend.
 * - Attaches a Bearer token from localStorage on every request when present.
 */
import axios from "axios";

function getBackendUrl() {
  const envUrl = process.env.NEXT_PUBLIC_BACKEND_URL;

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    const isLocalHost = hostname === "localhost" || hostname === "127.0.0.1";

    if (envUrl && !envUrl.includes("http://backend:8000")) {
      return envUrl;
    }

    if (isLocalHost) {
      return `${protocol}//${hostname}:8000`;
    }

    return "/api/backend";
  }

  return envUrl || "http://backend:8000";
}

const BACKEND_URL = getBackendUrl();

export const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 600_000, // 10 min — long file uploads / processing
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("token");
    if (token) {
      config.headers = config.headers || {};
      (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export const backendBaseUrl = BACKEND_URL;
