import type { components } from "@/types/api";
import { getDeviceKey } from "@/lib/patient-store";

export type Schemas = components["schemas"];
export type TriageOut = Schemas["TriageOut"];
export type Tap = Schemas["Tap"];
export type HospitalCard = Schemas["HospitalCard"];
export type ReferralPatientOut = Schemas["ReferralPatientOut"];
export type IncomingItem = Schemas["IncomingItem"];
export type MeOut = Schemas["MeOut"];
export type PatientKeysOut = Schemas["PatientKeysOut"];

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

type Opts = { method?: string; body?: unknown; form?: FormData; patient?: boolean; signal?: AbortSignal };
type Retry = Opts & { _retried?: boolean };
export type Page<T> = { data: T; meta: Schemas["PageMeta"] | null };

async function request<T>(path: string, opts: Retry = {}): Promise<Page<T>> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.patient) {
    const key = await getDeviceKey();
    if (key) headers["X-Patient-Key"] = key;
  }
  const hasBody = opts.body !== undefined || opts.form !== undefined;
  const method = opts.method ?? (hasBody ? "POST" : "GET");
  if (method !== "GET") {
    const csrf = readCookie("vt_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  const res = await fetch(`/api/v1${path}`, {
    method,
    headers,
    credentials: "same-origin",
    body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
    signal: opts.signal,
  });
  // Staff access tokens are short-lived: refresh once and retry.
  if (res.status === 401 && !opts.patient && !path.startsWith("/auth/") && !opts._retried) {
    const csrf = readCookie("vt_csrf");
    const r = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "same-origin",
      headers: csrf ? { "X-CSRF-Token": csrf } : {},
    });
    if (r.ok) return request<T>(path, { ...opts, _retried: true });
  }
  const json = await res.json().catch(() => null);
  if (!res.ok) {
    const err = json?.error ?? {};
    let message: string = err.message ?? res.statusText;
    if (err.code === "validation_error" && Array.isArray(err.details) && err.details[0]) {
      const d = err.details[0] as { loc?: unknown[]; msg?: string };
      message = `${String(d.loc?.[d.loc.length - 1] ?? "field").replace(/_/g, " ")}: ${d.msg}`;
    }
    throw new ApiError(res.status, err.code ?? "error", message, err.details);
  }
  return { data: json.data as T, meta: json.meta ?? null };
}

export async function api<T>(path: string, opts: Opts = {}): Promise<T> {
  return (await request<T>(path, opts)).data;
}

export function apiPage<T>(path: string, opts: Opts = {}): Promise<Page<T>> {
  return request<T>(path, opts);
}
