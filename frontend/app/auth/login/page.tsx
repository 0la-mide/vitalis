"use client";

import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DemoAccounts } from "@/components/auth/DemoAccounts";
import { api, type MeOut } from "@/lib/api";
import { homeFor } from "@/lib/staff";

export default function LoginPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Back to where they came from (e.g. a patient's QR link), but only within this app.
  const goOn = (me: MeOut) => {
    const next = new URLSearchParams(window.location.search).get("next");
    router.push(next && next.startsWith("/") && !next.startsWith("//") ? next : homeFor(me));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await api<MeOut>("/auth/login", { body: { email, password } });
      qc.setQueryData(["me"], me);
      goOn(me);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <main className="relative mx-auto flex w-full max-w-sm flex-1 flex-col justify-center px-4 py-10">
      <ThemeToggle className="absolute right-2 top-2" />
      <div className="mb-6 text-center">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/icons/icon-192.png" alt="" className="mx-auto h-12 w-12 rounded-xl" />
        <h1 className="mt-3 text-2xl font-bold">VITALIS staff</h1>
        <p className="text-sm text-muted-foreground">Hospitals, frontline workers and admins</p>
      </div>
      <Card>
        <form onSubmit={submit} className="grid gap-3">
          <label className="grid gap-1 text-sm font-medium">
            Email
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-11 rounded-lg border border-border bg-card px-3 text-base"
            />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            Password
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-11 rounded-lg border border-border bg-card px-3 text-base"
            />
          </label>
          {error ? <p className="text-sm text-emergency">{error}</p> : null}
          <Button type="submit" size="lg" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </Card>
      <DemoAccounts onSignedIn={goOn} />
      <p className="mt-4 text-center text-sm">
        New hospital, staff member or chemist? <Link href="/auth/register" className="font-semibold text-primary underline">Register</Link>
      </p>
      <p className="mt-2 text-center text-sm text-muted-foreground">
        Patients never need an account. <Link href="/" className="underline">Go to VITALIS</Link>
      </p>
    </main>
  );
}
