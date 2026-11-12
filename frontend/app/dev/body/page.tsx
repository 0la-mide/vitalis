"use client";

import { notFound } from "next/navigation";
import { useState } from "react";
import { BodyMap } from "@/components/body-map/BodyMap";
import type { BodyType } from "@/components/body-map/geometry";

/** Dev-only gallery of every body type and view, for checking the artwork. */
export default function BodyGallery() {
  const [active, setActive] = useState<string | null>(null);
  if (process.env.NODE_ENV === "production") notFound();
  const types: BodyType[] = ["male", "female", "pregnant", "child", "adult"];
  return (
    <main className="p-4">
      <p className="mb-2 text-sm">Tapped: <b>{active ?? "—"}</b></p>
      <div className="grid grid-cols-5 gap-2">
        {types.map((t) => (
          <div key={t} className="space-y-1">
            <p className="text-center text-sm font-bold">{t}</p>
            <BodyMap view="front" type={t} active={active} labels={{}} onSelect={setActive} />
            <BodyMap view="back" type={t} active={active} labels={{}} onSelect={setActive} />
          </div>
        ))}
      </div>
      <div className="mt-4 w-64"><BodyMap view="head" type="male" active={active} labels={{}} onSelect={setActive} /></div>
    </main>
  );
}
