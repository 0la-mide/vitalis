"use client";

import type { Lang } from "@/lib/i18n";

/**
 * Pre-recorded prompts live at /audio/{lang}/{code}.mp3 (see public/audio/manifest.json).
 * If a file is missing, English falls back to Web Speech synthesis. No speech recognition.
 */
let current: HTMLAudioElement | null = null;

export async function speak(code: string, text: string, lang: Lang): Promise<void> {
  current?.pause();
  if (typeof window !== "undefined") window.speechSynthesis?.cancel();
  const audio = new Audio(`/audio/${lang}/${code}.mp3`);
  current = audio;
  try {
    await audio.play();
    return;
  } catch {
    // file missing or blocked
  }
  if (lang === "en" && typeof window !== "undefined" && "speechSynthesis" in window && text) {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-NG";
    u.rate = 0.95;
    window.speechSynthesis.speak(u);
  }
}
