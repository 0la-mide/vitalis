"use client";

import { MapPin } from "lucide-react";
import { useT } from "@/lib/i18n";
import { useTriage } from "@/lib/triage-store";
import { useTaxonomy } from "./shared";

/** Shown when GPS was refused: pick an area instead. */
export function LocationPicker() {
  const t = useT();
  const { data: tax } = useTaxonomy();
  const { result, setLocation, flush, location } = useTriage();
  if (!result?.hospitals.approximate_location || !tax) return null;
  const current = location && "lga" in location ? location.lga : "";
  return (
    <div className="rounded-xl bg-warning-soft p-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-warning">
        <MapPin className="h-4 w-4" aria-hidden /> {t("location.pick")}
      </div>
      <div className="mt-2 flex gap-2">
        <select
          className="min-h-12 flex-1 rounded-lg border border-border bg-card px-2"
          value={current}
          onChange={(e) => {
            setLocation({ lga: e.target.value });
            void flush();
          }}
          aria-label={t("location.title")}
        >
          <option value="" disabled>
            {t("location.title")}
          </option>
          {tax.lgas.map((l) => (
            <option key={l.name} value={l.name}>
              {l.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="min-h-12 rounded-lg bg-card px-3 text-sm font-semibold"
          onClick={() =>
            navigator.geolocation?.getCurrentPosition((p) => {
              setLocation({ lat: p.coords.latitude, lng: p.coords.longitude });
              void flush();
            })
          }
        >
          {t("location.use_gps")}
        </button>
      </div>
    </div>
  );
}
