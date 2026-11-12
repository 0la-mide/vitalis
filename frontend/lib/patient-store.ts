"use client";

import { createStore, del, get, set } from "idb-keyval";

// Patients never log in. The device key lives in IndexedDB on this phone only.
const store = typeof indexedDB !== "undefined" ? createStore("vitalis", "patient") : undefined;

export type PatientIdentity = { patientId: string; vitalisId: string; deviceKey: string };

let cached: PatientIdentity | null | undefined;

export async function getIdentity(): Promise<PatientIdentity | null> {
  if (cached !== undefined) return cached;
  if (!store) return null;
  cached = ((await get("identity", store)) as PatientIdentity | undefined) ?? null;
  return cached;
}

export async function getDeviceKey(): Promise<string | null> {
  return (await getIdentity())?.deviceKey ?? null;
}

export async function saveIdentity(id: PatientIdentity): Promise<void> {
  cached = id;
  if (store) await set("identity", id, store);
}

export async function clearIdentity(): Promise<void> {
  cached = null;
  if (store) await del("identity", store);
}

// The recovery code is shown once, then forgotten. Kept in memory only until the slip is seen.
let pendingRecovery: string | null = null;
export const setPendingRecovery = (code: string | null) => (pendingRecovery = code);
export const getPendingRecovery = () => pendingRecovery;
