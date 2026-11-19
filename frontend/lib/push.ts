"use client";

import { api } from "@/lib/api";

export type PushState = "unsupported" | "needs-install" | "denied" | "off" | "on";
type Who = "patient" | "staff";

const supported = () =>
  typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

const isIos = () => typeof navigator !== "undefined" && /iphone|ipad|ipod/i.test(navigator.userAgent);
const standalone = () =>
  typeof window !== "undefined" &&
  (window.matchMedia("(display-mode: standalone)").matches || (navigator as { standalone?: boolean }).standalone === true);

function keyBytes(b64: string): Uint8Array {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

async function registration(): Promise<ServiceWorkerRegistration | null> {
  const reg = await navigator.serviceWorker.getRegistration();
  return reg ?? null;
}

/** True when this browser's subscription was made with the server's current key (or the browser doesn't say). */
function sameKey(sub: PushSubscription, key: Uint8Array): boolean {
  const k = sub.options?.applicationServerKey;
  if (!k) return true;
  const a = new Uint8Array(k);
  return a.length === key.length && a.every((b, i) => b === key[i]);
}

export async function pushState(): Promise<PushState> {
  if (!supported()) return isIos() && !standalone() ? "needs-install" : "unsupported";
  if (Notification.permission === "denied") return "denied";
  const reg = await registration();
  if (!reg) return "unsupported"; // dev server: no service worker
  return Notification.permission === "granted" && (await reg.pushManager.getSubscription()) ? "on" : "off";
}

/**
 * Makes sure the server has this browser's subscription, for whoever is using the phone now.
 * The server can lose it (demo data reset, the subscription expired) or have it under someone else (another demo
 * patient or staff member opened on this phone), so this runs every time an alerts screen opens. If the server's
 * key changed, the old subscription is replaced.
 */
async function register(who: Who, reg: ServiceWorkerRegistration): Promise<void> {
  const key = keyBytes((await api<{ public_key: string }>("/push/key")).public_key);
  let sub = await reg.pushManager.getSubscription();
  if (sub && !sameKey(sub, key)) {
    await sub.unsubscribe();
    sub = null;
  }
  sub ??= await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key as BufferSource });
  const json = sub.toJSON();
  await api(who === "patient" ? "/me/push" : "/push/subscribe", {
    body: { endpoint: json.endpoint, keys: json.keys },
    patient: who === "patient",
  });
}

/** Asks for permission (must run from a tap) and registers this browser for alerts. */
export async function enablePush(who: Who): Promise<PushState> {
  if (!supported()) return isIos() && !standalone() ? "needs-install" : "unsupported";
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return permission === "denied" ? "denied" : "off";
  const reg = await registration();
  if (!reg) return "unsupported";
  await register(who, reg);
  return "on";
}

/** Quietly re-registers a browser that already has alerts on. Never asks for anything; never throws. */
export async function syncPush(who: Who): Promise<PushState> {
  try {
    if (!supported() || Notification.permission !== "granted") return pushState();
    const reg = await registration();
    if (!reg) return "unsupported";
    await register(who, reg);
    return "on";
  } catch {
    return pushState();
  }
}

/** Sends a test alert to every device of the current patient or staff member. */
export async function testPush(who: Who): Promise<number> {
  const r = await api<{ devices: number }>(who === "patient" ? "/me/push/test" : "/push/test", {
    method: "POST",
    patient: who === "patient",
  });
  return r.devices;
}
