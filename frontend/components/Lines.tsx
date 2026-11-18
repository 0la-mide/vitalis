"use client";

import { useQuery } from "@tanstack/react-query";
import { Ambulance } from "lucide-react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { getBundle, type Line } from "@/lib/offline";
import { cn } from "@/lib/utils";

export type LinesInfo = { national: Line; ambulances: Line[]; ussd_code: string };

const USSD_FALLBACK = "*384*8482#";

/** Emergency numbers and the USSD code. With no signal, the copy saved in the offline bundle. */
export function useLines() {
  return useQuery({
    queryKey: ["lines"],
    queryFn: async (): Promise<LinesInfo> => {
      try {
        return await api<LinesInfo>("/lines");
      } catch (e) {
        const l = (await getBundle())?.lines;
        if (!l) throw e;
        return { national: l.national, ambulances: Object.values(l.ambulances), ussd_code: USSD_FALLBACK };
      }
    },
    staleTime: 24 * 3600 * 1000,
    retry: 0,
  });
}

/** 08112000033 -> 0811 200 0033 */
export const prettyNumber = (n: string) => n.replace(/^(\d{4})(\d{3})(\d{4})$/, "$1 $2 $3");

/** +2348031234567 -> 0803 123 4567 (how people read Nigerian numbers) */
export const localPhone = (p: string) => {
  const d = p.replace(/\D/g, "");
  const local = d.startsWith("234") && d.length === 13 ? `0${d.slice(3)}` : d;
  return prettyNumber(local);
};

/** A big "Call ambulance" button, shown under Call 112 where VITALIS knows the state ambulance. */
export function AmbulanceButton({ line, compact = false }: { line: Line; compact?: boolean }) {
  const t = useT();
  return (
    <a
      href={`tel:${line.number}`}
      className={cn(
        "flex items-center justify-center gap-3 rounded-2xl border-2 border-emergency/60 bg-card px-4 font-bold text-emergency",
        compact ? "min-h-14 text-base" : "min-h-16 text-lg",
      )}
    >
      <Ambulance className="h-6 w-6 shrink-0" aria-hidden />
      <span className="text-left leading-tight">
        {t("emergency.ambulance")}
        <span className="block text-sm font-semibold opacity-80">
          {line.name} · {prettyNumber(line.number)}
        </span>
      </span>
    </a>
  );
}

/** Every ambulance VITALIS knows (today: Ogun State), for screens that don't know where she is. */
export function AmbulanceButtons({ compact = false }: { compact?: boolean }) {
  const { data } = useLines();
  return (
    <>
      {(data?.ambulances ?? []).map((l) => (
        <AmbulanceButton key={l.number} line={l} compact={compact} />
      ))}
    </>
  );
}
