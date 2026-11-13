"use client";

import { useQuery } from "@tanstack/react-query";
import { Smartphone } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api, type Schemas } from "@/lib/api";
import { saveIdentity } from "@/lib/patient-store";

type Accounts = Schemas["DemoAccounts"];

/** Seeded demo patients. The server returns 404 when demo mode is off, and then nothing renders. */
function useDemoPatients() {
  return useQuery({
    queryKey: ["demo-patients"],
    queryFn: () => api<Accounts>("/demo/accounts"),
    retry: false,
    staleTime: 60_000,
  });
}

/** On the patient's record page: open a demo patient's record on this phone in one tap. */
export function DemoPatients({ onOpened }: { onOpened: () => void }) {
  const { data } = useDemoPatients();
  const [busy, setBusy] = useState<string | null>(null);
  if (!data?.patients.length) return null;
  return (
    <div className="space-y-2 border-t border-border pt-3">
      <p className="text-sm font-semibold">Demo: open a patient&apos;s phone</p>
      <div className="flex flex-wrap gap-2">
        {data.patients.map((p) => (
          <Button key={p.vitalis_id} size="sm" variant="outline" disabled={!!busy} onClick={async () => {
            setBusy(p.vitalis_id);
            try {
              const k = await api<Schemas["DemoPatientOut"]>("/demo/patient", { body: { vitalis_id: p.vitalis_id } });
              await saveIdentity({ patientId: k.patient_id, vitalisId: k.vitalis_id, deviceKey: k.device_key });
              onOpened();
            } finally {
              setBusy(null);
            }
          }}>
            <Smartphone className="size-4" />{p.name.replace(" (demo)", "")}
          </Button>
        ))}
      </div>
    </div>
  );
}
