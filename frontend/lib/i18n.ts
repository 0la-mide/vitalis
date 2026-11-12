"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import en from "@/i18n/en.json";
import ha from "@/i18n/ha.json";
import ig from "@/i18n/ig.json";
import pcm from "@/i18n/pcm.json";
import yo from "@/i18n/yo.json";

export const LANGS = [
  { code: "en", label: "English" },
  { code: "pcm", label: "Pidgin" },
  { code: "yo", label: "Yorùbá" },
  { code: "ha", label: "Hausa" },
  { code: "ig", label: "Igbo" },
] as const;
export type Lang = (typeof LANGS)[number]["code"];
export type MsgKey = keyof typeof en;

const DICTS: Record<Lang, Record<string, string>> = { en, pcm, yo, ha, ig };

export const useLang = create<{ lang: Lang; setLang: (l: Lang) => void }>()(
  persist((set) => ({ lang: "en", setLang: (lang) => set({ lang }) }), { name: "vitalis-lang" }),
);

/** Falls back to English when a translation is still empty. */
export function useT() {
  const lang = useLang((s) => s.lang);
  return (key: MsgKey) => DICTS[lang]?.[key] || en[key] || key;
}

export function pickLabel(labels: Record<string, string> | undefined, lang: Lang): string {
  if (!labels) return "";
  return labels[lang] || labels.en || "";
}
