"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { OfflineSync } from "@/components/OfflineSync";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          // Offline-first: reads use what is already on screen; actions always run, and the outbox (lib/outbox)
          // decides whether to send now or keep them for when the signal returns.
          queries: { retry: 1, refetchOnWindowFocus: false, networkMode: "offlineFirst" },
          mutations: { networkMode: "always" },
        },
      }),
  );
  useEffect(() => {
    if (process.env.NODE_ENV === "production" && "serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }, []);
  return (
    <QueryClientProvider client={client}>
      {children}
      <OfflineSync />
    </QueryClientProvider>
  );
}
