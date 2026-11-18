"use client";

/**
 * Hospital outbox. With no signal, accept / decline, arrival and vitals are saved on this phone and sent, in order,
 * as soon as the signal returns. Vitals keep the time they were taken. If the server refuses one later (another
 * nurse already acted, the referral moved on), it is dropped and shown as a failed item.
 */
import { createStore, get, set } from "idb-keyval";
import { api, ApiError } from "@/lib/api";
import { isNetworkError } from "@/lib/offline";

export type OutboxItem = { id: string; path: string; method: string; body?: unknown; label: string; saved_at: string };
export type Failed = { label: string; reason: string };
type Snapshot = { items: OutboxItem[]; failed: Failed[]; online: boolean; sending: boolean };

const store = typeof indexedDB !== "undefined" ? createStore("vitalis-outbox", "data") : undefined;
let items: OutboxItem[] = [];
let failed: Failed[] = [];
let sending = false;
let loaded = false;
const listeners = new Set<() => void>();
let snapshot: Snapshot = { items, failed, online: true, sending };

function emit() {
  snapshot = { items: [...items], failed: [...failed], online: typeof navigator === "undefined" || navigator.onLine, sending };
  listeners.forEach((l) => l());
}
async function save() {
  if (store) await set("items", items, store);
}
async function load() {
  if (loaded) return;
  loaded = true;
  items = store ? (((await get("items", store)) as OutboxItem[] | undefined) ?? []) : [];
  emit();
}

export function subscribe(fn: () => void) {
  listeners.add(fn);
  void load();
  return () => listeners.delete(fn);
}
export const getSnapshot = () => snapshot;
export const dismissFailed = () => {
  failed = [];
  emit();
};

export type Queued = { queued: true; label: string };
export const isQueued = (x: unknown): x is Queued => !!x && typeof x === "object" && (x as Queued).queued === true;

/** Sends now, or keeps it for later when there is no signal. */
export async function sendOrQueue<T>(path: string, opts: { method?: string; body?: unknown }, label: string): Promise<T | Queued> {
  await load();
  const method = opts.method ?? "POST";
  const enqueue = async (): Promise<Queued> => {
    items.push({ id: `${Date.now()}-${items.length}`, path, method, body: opts.body, label, saved_at: new Date().toISOString() });
    await save();
    emit();
    return { queued: true, label };
  };
  if (typeof navigator !== "undefined" && !navigator.onLine) return enqueue();
  // Keep the order: if older actions are still waiting, this one waits behind them.
  if (items.length) {
    const queued = await enqueue();
    void flushOutbox();
    return queued;
  }
  try {
    return await api<T>(path, { method, body: opts.body });
  } catch (e) {
    if (isNetworkError(e)) return enqueue();
    throw e;
  }
}

/** Sends everything waiting, oldest first. Stops at the first network failure. */
export async function flushOutbox(onSent?: () => void): Promise<void> {
  await load();
  if (sending || !items.length || (typeof navigator !== "undefined" && !navigator.onLine)) return;
  sending = true;
  emit();
  try {
    while (items.length) {
      const it = items[0];
      try {
        await api(it.path, { method: it.method, body: it.body });
      } catch (e) {
        if (isNetworkError(e)) break;
        failed.push({ label: it.label, reason: e instanceof ApiError ? e.message : String(e) });
      }
      items.shift();
      await save();
      emit();
      onSent?.();
    }
  } finally {
    sending = false;
    emit();
  }
}
