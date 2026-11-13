"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import en from "@/i18n/en.json";
import ha from "@/i18n/ha.json";
import ig from "@/i18n/ig.json";
import pcm from "@/i18n/pcm.json";
import yo from "@/i18n/yo.json";

// Only English is translated so far; the others show as "coming soon" and cannot be picked.
export const LANGS = [
  { code: "en", label: "English", ready: true },
  { code: "pcm", label: "Pidgin", ready: false },
  { code: "yo", label: "Yorùbá", ready: false },
  { code: "ha", label: "Hausa", ready: false },
  { code: "ig", label: "Igbo", ready: false },
] as const;
export type Lang = (typeof LANGS)[number]["code"];
export type MsgKey = keyof typeof en;

const DICTS: Record<Lang, Record<string, string>> = { en, pcm, yo, ha, ig };

export const useLang = create<{ lang: Lang; setLang: (l: Lang) => void }>()(
  persist((set) => ({ lang: "en", setLang: (lang) => set({ lang }) }), { name: "vitalis-lang" }),
);

/** The language in use: a saved choice that is not ready yet falls back to English. */
export function useActiveLang(): Lang {
  return useLang((s) => (LANGS.find((l) => l.code === s.lang)?.ready ? s.lang : "en"));
}

/** Falls back to English when a translation is still empty. */
export function useT() {
  const lang = useActiveLang();
  return (key: MsgKey) => DICTS[lang]?.[key] || en[key] || key;
}

export function pickLabel(labels: Record<string, string> | undefined, lang: Lang): string {
  if (!labels) return "";
  const ready = LANGS.find((l) => l.code === lang)?.ready;
  return (ready && labels[lang]) || labels.en || "";
}
