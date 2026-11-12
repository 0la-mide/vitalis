"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { subscribe } from "@/lib/sse";

/** One live connection per screen: any facility event refreshes the given query keys. */
export function useFacilityStream(keys: string[][]) {
  const qc = useQueryClient();
  const [live, setLive] = useState(false);
  const sig = JSON.stringify(keys);
  useEffect(() => {
    const list = JSON.parse(sig) as string[][];
    return subscribe("/hospital/stream", (e) => {
      if (e.event === "ready") setLive(true);
      else if (e.event === "error") setLive(false);
      else for (const k of list) void qc.invalidateQueries({ queryKey: k });
    });
  }, [qc, sig]);
  return live;
}
