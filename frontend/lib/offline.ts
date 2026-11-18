"use client";

/**
 * Offline mode. When online, the app saves the "offline bundle" (danger-sign rules, symptoms, care types and every
 * verified hospital with its services) on the phone. With no signal, the same rules and matching run here, so a
 * family still gets the emergency plan and the closest hospitals that can treat them. Hospitals are NOT alerted until
 * the phone is back online; the request is queued and sent then.
 *
 * The logic mirrors backend/app/engines/triage/{red_flags,care}.py and engines/matching/engine.py. Keep them in step.
 */
import { createStore, del, get, set } from "idb-keyval";
import type { HospitalCard, Tap, TriageOut } from "@/lib/api";

const store = typeof indexedDB !== "undefined" ? createStore("vitalis-offline", "data") : undefined;

type Svc = { status: string; last_confirmed_at: string | null };
export type OfflineFacility = {
  id: string; name: string; lga: string; type: string; lat: number; lng: number; phone: string | null;
  accepts_nhia: boolean; free_maternal_care: boolean; services: Record<string, Svc>;
};
type Atom = Record<string, unknown>;
type Rule = { id: string; care_type: string; message: string; all?: Atom[]; any?: Atom[];
  care_type_if_pregnant?: string; care_type_if_child?: string };
type CareType = { label: string; essential: string[]; preferred: string[]; what_to_bring: string[] };
export type Bundle = {
  generated_at: string;
  taxonomy: unknown;
  emergencies: { code: string; context: Record<string, unknown>; symptoms: { code: string; region?: string }[] }[];
  red_flags: { version: string; rules: Rule[] };
  care: {
    services: Record<string, string>;
    care_types: Record<string, CareType>;
    context_overrides: { pregnant_regions: Record<string, string>; child_care_type: string };
    region_defaults: Record<string, string>;
    action_rules: { rules: { if: Record<string, unknown>; action: string }[]; self_care_return_if: string[] };
  };
  matching: { nearby_km: number; confirmed_h: number; stale_h: number; speed_kmh: number };
  facilities: OfflineFacility[];
  lines?: Lines;
};

export type Line = { name: string; number: string };
export type Lines = {
  national: Line;
  max_km: number;
  ambulances: Record<string, Line>;
  lgas: { name: string; lat: number; lng: number; state?: string | null }[];
};

// ---------------- the bundle on this phone ----------------
let memo: Bundle | null | undefined;

export async function getBundle(): Promise<Bundle | null> {
  if (memo !== undefined) return memo;
  memo = store ? (((await get("bundle", store)) as Bundle | undefined) ?? null) : null;
  return memo;
}

let fetchedAt = 0;
const REFRESH_MS = 10 * 60 * 1000; // availability changes slowly; don't spend the family's data on every page load

/** Fetches a fresh bundle when online (at most every 10 minutes). Quietly keeps the saved one when not. */
export async function refreshBundle(force = false): Promise<Bundle | null> {
  if (!force && memo && Date.now() - fetchedAt < REFRESH_MS) return memo;
  try {
    const res = await fetch("/api/v1/offline/bundle", { credentials: "same-origin" });
    if (!res.ok) return getBundle();
    const b = (await res.json()).data as Bundle;
    memo = b;
    fetchedAt = Date.now();
    if (store) await set("bundle", b, store);
    return b;
  } catch {
    return getBundle();
  }
}

export function isOffline(): boolean {
  return typeof navigator !== "undefined" && navigator.onLine === false;
}

/** A network failure (no signal), as opposed to the server saying no. */
export function isNetworkError(e: unknown): boolean {
  return e instanceof TypeError || (e instanceof Error && /fetch|network|load failed/i.test(e.message));
}

// ---------------- a request saved while offline ----------------
export type PendingRequest = {
  taps: Tap[]; facility_id: string; facility_name: string; facility_phone: string | null; saved_at: string;
};
export const savePending = (p: PendingRequest) => (store ? set("pending-request", p, store) : Promise.resolve());
export const getPending = async () => (store ? ((await get("pending-request", store)) as PendingRequest | undefined) ?? null : null);
export const clearPending = () => (store ? del("pending-request", store) : Promise.resolve());

// ---------------- the triage, computed on the phone ----------------
export type LocalReport = {
  context: Record<string, unknown>;
  answers: { symptoms: { code: string; region?: string | null; severity?: number; onset?: string }[]; regions: string[];
    severity?: number; onset?: string };
  lat?: number; lng?: number; lga?: string;
};

export const emptyReport = (): LocalReport => ({ context: {}, answers: { symptoms: [], regions: [] } });

function addSymptom(r: LocalReport, item: { code: string; region?: string | null }) {
  const s = r.answers.symptoms.find((x) => x.code === item.code);
  if (s) Object.assign(s, Object.fromEntries(Object.entries(item).filter(([, v]) => v != null)));
  else r.answers.symptoms.push({ ...item });
}

export function applyTap(r: LocalReport, tap: Tap, b: Bundle): LocalReport {
  const t = tap as Record<string, unknown> & { kind: string };
  if (t.kind === "emergency") {
    const e = b.emergencies.find((x) => x.code === t.code);
    if (e) {
      Object.assign(r.context, e.context);
      e.symptoms.forEach((s) => addSymptom(r, s));
    }
  } else if (t.kind === "context") {
    for (const k of ["age_group", "sex", "who"]) if (t[k] != null) r.context[k] = t[k];
    if (t.pregnant != null) {
      r.context.pregnant = !!t.pregnant;
      if (t.pregnant) r.context.sex = "female";
    }
  } else if (t.kind === "region") {
    const region = String(t.region);
    if (!r.answers.regions.includes(region)) r.answers.regions.push(region);
  } else if (t.kind === "symptom") {
    if (t.selected === false) r.answers.symptoms = r.answers.symptoms.filter((s) => s.code !== t.code);
    else addSymptom(r, { code: String(t.code), region: (t.region as string) ?? null });
  } else if (t.kind === "severity") {
    const v = Number(t.value);
    r.answers.severity = v;
    r.answers.symptoms.forEach((s) => (s.severity = v));
  } else if (t.kind === "onset") {
    r.answers.onset = String(t.value);
    r.answers.symptoms.forEach((s) => (s.onset = String(t.value)));
  } else if (t.kind === "location") {
    if (t.lat != null && t.lng != null) { r.lat = Number(t.lat); r.lng = Number(t.lng); }
    if (t.lga) r.lga = String(t.lga);
  }
  return r;
}

type St = { age: string; pregnant: boolean; codes: Set<string>; regions: string[];
  sev: (code: string) => number | undefined; overall: number; onset?: string; hasSymptoms: boolean; child: boolean };

function state(r: LocalReport): St {
  const syms = r.answers.symptoms;
  const age = (r.context.age_group as string) || "adult";
  return {
    age, pregnant: !!r.context.pregnant, codes: new Set(syms.map((s) => s.code)), regions: r.answers.regions,
    sev: (code) => { const s = syms.find((x) => x.code === code); return s ? (s.severity ?? r.answers.severity) : undefined; },
    overall: Math.max(0, ...syms.map((s) => s.severity ?? 0), r.answers.severity ?? 0),
    onset: r.answers.onset, hasSymptoms: syms.length > 0, child: age === "under5" || age === "child",
  };
}

function atom(a: Atom, st: St): boolean {
  if ("pregnant" in a) return st.pregnant === a.pregnant;
  if ("age_group_in" in a) return (a.age_group_in as string[]).includes(st.age);
  if ("symptom" in a) return st.codes.has(a.symptom as string);
  if ("symptom_any" in a) return (a.symptom_any as string[]).some((c) => st.codes.has(c));
  if ("severity_gte" in a) return ((a.symptoms as string[]) ?? []).some((c) => (st.sev(c) ?? -1) >= (a.severity_gte as number));
  if ("vital" in a) return false; // vitals are entered by staff, never offline on the family's phone
  return false;
}

function redFlags(st: St, b: Bundle) {
  return b.red_flags.rules
    .filter((r) => (r.all || r.any) && (!r.all || r.all.every((a) => atom(a, st))) && (!r.any || r.any.some((a) => atom(a, st))))
    .map((r) => ({ message: r.message,
      care_type: st.pregnant && r.care_type_if_pregnant ? r.care_type_if_pregnant : st.child && r.care_type_if_child ? r.care_type_if_child : r.care_type }));
}

function careType(st: St, hits: { care_type: string }[], b: Bundle): string | null {
  if (hits.length) return hits[0].care_type;
  const o = b.care.context_overrides;
  if (st.pregnant) for (const region of [...st.regions].reverse()) if (o.pregnant_regions[region]) return o.pregnant_regions[region];
  if (st.child && (st.hasSymptoms || st.regions.length)) return o.child_care_type;
  if (st.regions.length) return b.care.region_defaults[st.regions[st.regions.length - 1]] ?? "general_medical";
  if (st.hasSymptoms) return "general_medical";
  return null;
}

function actionLevel(st: St, fired: boolean, ct: string | null, b: Bundle): TriageOut["action_level"] {
  if (fired) return "go_now";
  if (!st.hasSymptoms) return null;
  for (const rule of b.care.action_rules.rules) {
    const c = rule.if as { severity_gte?: number; care_type_in?: string[]; onset_in?: string[] };
    if (c.severity_gte != null && st.overall < c.severity_gte) continue;
    if (c.care_type_in && !c.care_type_in.includes(ct ?? "")) continue;
    if (c.onset_in && !c.onset_in.includes(st.onset ?? "")) continue;
    return rule.action as TriageOut["action_level"];
  }
  return "self_care";
}

const km = (a: number, b: number, c: number, d: number) => {
  const R = 6371, rad = Math.PI / 180, dp = (c - a) * rad, dl = (d - b) * rad;
  const x = Math.sin(dp / 2) ** 2 + Math.cos(a * rad) * Math.cos(c * rad) * Math.sin(dl / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
};
const AVAIL: Record<string, number> = { available: 1, limited: 0.5, unknown: 0.25 };
const FRESH: Record<string, number> = { confirmed: 1, stale: 0.5, unknown: 0 };
const RANK: Record<string, number> = { confirmed: 2, stale: 1, unknown: 0 };

function freshness(ts: string | null, now: number, m: Bundle["matching"]): "confirmed" | "stale" | "unknown" {
  if (!ts) return "unknown";
  const h = (now - Date.parse(ts)) / 3.6e6;
  return h < m.confirmed_h ? "confirmed" : h < m.stale_h ? "stale" : "unknown";
}

function match(b: Bundle, ct: string | null, lat: number, lng: number, now: number) {
  const cfg = b.care.care_types[ct ?? ""] ?? { essential: [], preferred: [] };
  const name = (c: string) => b.care.services[c] ?? c;
  const m = b.matching;
  let nearby = 0;
  const matches: (HospitalCard & { _score: number })[] = [];
  const excluded: TriageOut["hospitals"]["excluded"] = [];
  for (const f of b.facilities) {
    const dist = km(lat, lng, f.lat, f.lng);
    if (dist > m.nearby_km) continue;
    nearby++;
    const missing: string[] = [];
    for (const c of cfg.essential) {
      const s = f.services[c];
      if (!s) missing.push(`No ${name(c).toLowerCase()}`);
      else if (s.status === "unavailable") missing.push(`${name(c)}: not available right now`);
    }
    if (missing.length) { excluded.push({ facility_id: f.id, name: f.name, distance_km: +dist.toFixed(1), reasons: missing }); continue; }
    const ess = cfg.essential.map((c) => ({ code: c, ...f.services[c] }));
    const essScore = ess.length ? ess.reduce((a, s) => a + (s.status === "unknown" ? 0.5 : 1), 0) / ess.length : 1;
    const prefHave = cfg.preferred.filter((c) => f.services[c] && f.services[c].status !== "unavailable");
    const prefScore = cfg.preferred.length ? prefHave.length / cfg.preferred.length : 1;
    const all = Object.values(f.services);
    const avail = ess.length ? ess.reduce((a, s) => a + (AVAIL[s.status] ?? 0.25), 0) / ess.length
      : all.length ? all.reduce((a, s) => a + (AVAIL[s.status] ?? 0.25), 0) / all.length : 0.25;
    const stamps = (ess.length ? ess : all).map((s) => s.last_confirmed_at);
    const labels = stamps.length ? stamps.map((t) => freshness(t, now, m)) : ["unknown" as const];
    const worst = labels.reduce((a, x) => (RANK[x] < RANK[a] ? x : a), labels[0]);
    const known = stamps.filter(Boolean) as string[];
    let score = 100 * (0.4 * (0.8 * essScore + 0.2 * prefScore) + 0.25 * avail + 0.2 * Math.max(0, 1 - dist / m.nearby_km)
      + 0.15 * (labels.reduce((a, x) => a + FRESH[x], 0) / labels.length));
    const reasons: string[] = [];
    const warnings: string[] = [];
    if (cfg.essential.length) reasons.push(`Has ${cfg.essential.map((c) => name(c).toLowerCase()).join(", ")}`);
    if (ess.length && ess.every((s) => s.status === "available")) reasons.push("All needed services marked available");
    for (const s of ess) {
      if (s.status === "unknown") warnings.push(`${name(s.code)}: availability unknown`);
      else if (s.status === "limited") warnings.push(`${name(s.code)}: limited`);
    }
    if (worst === "stale") warnings.push("Availability not confirmed in the last 6 hours");
    else if (worst === "unknown") warnings.push("Availability not confirmed recently");
    if (prefHave.length) reasons.push(`Also has ${prefHave.slice(0, 3).map((c) => name(c).toLowerCase()).join(", ")}`);
    if (f.free_maternal_care && (ct === "obstetrics" || ct === "paediatrics")) {
      score = Math.min(100, score + 2);
      reasons.push("Free maternal and child care");
    }
    matches.push({
      facility_id: f.id, name: f.name, lga: f.lga, lat: f.lat, lng: f.lng, phone: f.phone,
      distance_km: +dist.toFixed(1), eta_minutes: Math.max(3, Math.round((dist / m.speed_kmh) * 60)), eta_is_estimate: true,
      score: +score.toFixed(1), freshness: worst, last_confirmed_at: known.sort()[0] ?? null,
      ready_now: ess.length > 0 && ess.every((s) => s.status === "available") && worst === "confirmed",
      reasons, warnings, accepts_nhia: f.accepts_nhia, free_maternal_care: f.free_maternal_care, _score: score,
    });
  }
  matches.sort((a, c) => c._score - a._score || a.distance_km - c.distance_km);
  excluded.sort((a, c) => a.distance_km - c.distance_km);
  return { nearby, matches, excluded };
}

/** The state ambulance for where she is: the named LGA's state, or the nearest known LGA within max_km. Same as the server. */
export function ambulanceFor(l: Lines | undefined, lat: number, lng: number, lgaName?: string | null): Line | null {
  if (!l?.lgas.length) return null;
  let state: string | null | undefined = lgaName ? l.lgas.find((x) => x.name === lgaName)?.state : undefined;
  if (state === undefined) {
    const best = l.lgas.reduce((a, c) => (km(lat, lng, c.lat, c.lng) < km(lat, lng, a.lat, a.lng) ? c : a));
    state = km(lat, lng, best.lat, best.lng) <= l.max_km ? best.state : null;
  }
  return (state && l.ambulances[state]) || null;
}

/** The same answer the server would give, minus the hospital alert. */
export function evaluateOffline(r: LocalReport, b: Bundle, now = Date.now()): TriageOut {
  const st = state(r);
  const hits = redFlags(st, b);
  const ct = careType(st, hits, b);
  const action = actionLevel(st, hits.length > 0, ct, b);
  const lgas = (b.taxonomy as { lgas: { name: string; lat: number; lng: number }[] }).lgas;
  const lga = lgas.find((l) => l.name === r.lga) ?? lgas.find((l) => l.name === "Abeokuta South") ?? lgas[0];
  const exact = r.lat != null && r.lng != null;
  const lat = exact ? r.lat! : lga.lat;
  const lng = exact ? r.lng! : lga.lng;
  const res = match(b, ct, lat, lng, now);
  const top = res.matches.map(({ _score, ...h }) => h); // eslint-disable-line @typescript-eslint/no-unused-vars
  const cfg = b.care.care_types[ct ?? ""];
  return {
    report_id: "offline",
    status: hits.length ? "emergency" : "open",
    red_flag: { fired: hits.length > 0, message: hits[0]?.message ?? null },
    care_type: ct,
    care_label: cfg?.label ?? null,
    action_level: action,
    self_care_return_if: action === "self_care" ? b.care.action_rules.self_care_return_if : [],
    what_to_bring: cfg?.what_to_bring ?? [],
    heads_up_sent: false,
    hospitals: {
      nearby: res.nearby, can_handle: res.matches.length, ready_now: top.filter((h) => h.ready_now).length,
      top: top.slice(0, 5), excluded: res.excluded.slice(0, 5), approximate_location: !exact,
    },
    context: r.context,
    answers: r.answers as unknown as TriageOut["answers"],
    active_referral_id: null,
    ambulance: ambulanceFor(b.lines, lat, lng, r.lga),
  };
}
