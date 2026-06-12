/**
 * Axios instance configured to talk to the FastAPI backend.
 *
 * - Reads the base URL from NEXT_PUBLIC_BACKEND_URL (defaults to localhost:8000).
 * - Attaches a Bearer token from localStorage on every request when present.
 */
import axios from "axios";

const BACKEND_URL =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_BACKEND_URL) ||
  "http://localhost:8000";

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
