"use client";

import { KeyRound } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useT } from "@/lib/i18n";
import { getIdentity, getPendingRecovery, setPendingRecovery } from "@/lib/patient-store";

/** Shows the VITALIS ID + one-time recovery code once, after the urgent part is over. */
export function RecoverySlip({ always }: { always?: boolean }) {
  const t = useT();
  const [vid, setVid] = useState<string | null>(null);
  const [code, setCode] = useState<string | null>(null);
  useEffect(() => {
    void getIdentity().then((id) => {
      setVid(id?.vitalisId ?? null);
      setCode(getPendingRecovery());
    });
  }, []);
  if (!vid || (!code && !always)) return null;
  return (
    <Card className="border-2 border-dashed border-primary">
      <div className="flex items-center gap-2 font-bold">
        <KeyRound className="h-5 w-5 text-primary" aria-hidden /> {t("slip.title")}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{t("slip.keep")}</p>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <dt className="text-sm text-muted-foreground">VITALIS ID</dt>
        <dd className="font-mono text-lg font-bold">{vid}</dd>
        {code ? (
          <>
            <dt className="text-sm text-muted-foreground">{t("slip.code")}</dt>
            <dd className="font-mono text-lg font-bold">{code}</dd>
          </>
        ) : null}
      </dl>
      {code ? (
        <Button
          className="mt-3 w-full"
          size="lg"
          variant="mint"
          onClick={() => {
            setPendingRecovery(null);
            setCode(null);
          }}
        >
          {t("slip.continue")}
        </Button>
      ) : null}
    </Card>
  );
}
