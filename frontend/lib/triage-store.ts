"use client";

import { create } from "zustand";
import { api, ApiError, type Tap, type TriageOut } from "@/lib/api";
import { clearIdentity, getIdentity, saveIdentity, setPendingRecovery } from "@/lib/patient-store";
import type { PatientKeysOut } from "@/lib/api";

export type Step =
  | "who"
  | "who_child"
  | "sex"
  | "body"
  | "symptoms"
  | "severity"
  | "onset"
  | "results"
  | "emergency";

type Location = { lat: number; lng: number } | { lga: string } | null;

type State = {
  reportId: string | null;
  entry: string | null;
  result: TriageOut | null;
  step: Step;
  history: Step[];
  region: string | null;
  selected: string[];
  location: Location;
  busy: boolean;
  error: string | null;
  tapCount: number;
  startedAt: number | null;
  // actions
  reset: () => void;
  setLocation: (l: Location) => void;
  go: (s: Step) => void;
  back: () => void;
  countTap: () => void;
  begin: (taps: Tap[], next: Step) => Promise<TriageOut | null>;
  tap: (taps: Tap[]) => void;
  flush: () => Promise<TriageOut | null>;
  setRegion: (r: string | null) => void;
  toggleSymptom: (code: string, region: string | null) => void;
};

let queue: Tap[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
let inflight: Promise<TriageOut | null> | null = null;
const DEBOUNCE_MS = 250;

async function ensurePatient(): Promise<void> {
  if (await getIdentity()) return;
  const keys = await api<PatientKeysOut>("/patients/start", { body: {} });
  await saveIdentity({ patientId: keys.patient_id, vitalisId: keys.vitalis_id, deviceKey: keys.device_key });
  setPendingRecovery(keys.recovery_code);
}

function locationTap(l: Location): Tap[] {
  if (!l) return [];
  return "lga" in l ? [{ kind: "location", lga: l.lga }] : [{ kind: "location", lat: l.lat, lng: l.lng }];
}

function persistTimer(startedAt: number | null, taps: number) {
  try {
    sessionStorage.setItem("vitalis-timer", JSON.stringify({ startedAt, taps }));
  } catch {
    /* private mode */
  }
}

export const useTriage = create<State>((set, get) => ({
  reportId: null,
  entry: null,
  result: null,
  step: "who",
  history: [],
  region: null,
  selected: [],
  location: null,
  busy: false,
  error: null,
  tapCount: 0,
  startedAt: null,

  reset: () => {
    queue = [];
    set({ reportId: null, entry: null, result: null, step: "who", history: [], region: null, selected: [], error: null,
          tapCount: 0, startedAt: null });
  },
  setLocation: (location) => {
    set({ location });
    if (get().reportId) get().tap(locationTap(location));
  },
  go: (step) => set((s) => ({ history: [...s.history, s.step], step })),
  back: () =>
    set((s) => {
      const history = [...s.history];
      const prev = history.pop();
      return prev ? { history, step: prev } : {};
    }),
  countTap: () => {
    const startedAt = get().startedAt ?? Date.now();
    const tapCount = get().tapCount + 1;
    set({ tapCount, startedAt });
    persistTimer(startedAt, tapCount);
  },

  begin: async (taps, next) => {
    get().countTap();
    const entry = taps.find((t) => t.kind === "emergency")?.code ?? "other";
    set({ busy: true, error: null, step: next, history: [], entry, selected: [], region: null });
    try {
      await ensurePatient();
      const body = { taps: [...locationTap(get().location), ...taps] };
      let result: TriageOut;
      try {
        result = await api<TriageOut>("/triage", { body, patient: true });
      } catch (e) {
        // This phone's key is no longer known (e.g. demo reset): start a fresh patient once.
        if (!(e instanceof ApiError && e.code === "patient_key_invalid")) throw e;
        await clearIdentity();
        await ensurePatient();
        result = await api<TriageOut>("/triage", { body, patient: true });
      }
      set({ reportId: result.report_id, result, busy: false });
      if (result.red_flag.fired) set({ step: "emergency" });
      return result;
    } catch (e) {
      set({ busy: false, error: (e as Error).message });
      return null;
    }
  },

  tap: (taps) => {
    queue.push(...taps);
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => void get().flush(), DEBOUNCE_MS);
  },

  flush: async () => {
    if (timer) clearTimeout(timer);
    timer = null;
    if (inflight) await inflight;
    const id = get().reportId;
    if (!id || queue.length === 0) return get().result;
    const batch = queue;
    queue = [];
    inflight = (async () => {
      try {
        const result = await api<TriageOut>(`/triage/${id}/taps`, { body: { taps: batch }, patient: true });
        set({ result, error: null });
        if (result.red_flag.fired && get().step !== "emergency") {
          set((s) => ({ step: "emergency", history: [...s.history, s.step] }));
        }
        return result;
      } catch (e) {
        set({ error: (e as Error).message });
        return null;
      } finally {
        inflight = null;
      }
    })();
    return inflight;
  },

  setRegion: (region) => {
    set({ region });
    if (region) get().tap([{ kind: "region", region }]);
  },
  toggleSymptom: (code, region) => {
    const on = !get().selected.includes(code);
    set((s) => ({ selected: on ? [...s.selected, code] : s.selected.filter((c) => c !== code) }));
    get().tap([{ kind: "symptom", code, region: region ?? undefined, selected: on }]);
  },
}));
