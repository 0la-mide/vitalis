"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, MessageSquareText, Phone, PhoneOff, Radio, Smartphone } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { prettyNumber, useLines } from "@/components/Lines";
import { Card } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

type Reply = { reply: string; done: boolean };
type Sms = { at: string; text: string };

/** A demo number for this browser (0000 000 0xxx): the server keeps its texts instead of sending them. */
function useDemoPhone() {
  const [phone, setPhone] = useState("0000 000 0001");
  useEffect(() => {
    let n = "";
    try {
      n = localStorage.getItem("vitalis-ussd-phone") ?? "";
      if (!/^0000 000 0\d{3}$/.test(n)) {
        n = `0000 000 0${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;
        localStorage.setItem("vitalis-ussd-phone", n);
      }
    } catch {
      n = "0000 000 0001";
    }
    setPhone(n); // eslint-disable-line react-hooks/set-state-in-effect -- read once from this browser's storage
  }, []);
  return phone;
}

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"];

export default function UssdSimulator() {
  const phone = useDemoPhone();
  const { data: lines } = useLines();
  const code = lines?.ussd_code ?? "*384*8482#";
  const [dialled, setDialled] = useState("");
  const [session, setSession] = useState<string | null>(null); // the answers so far, "1*7*2"; null = not in a call
  const [screen, setScreen] = useState<Reply | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inbox = useQuery({
    queryKey: ["demo-sms", phone],
    queryFn: () => api<Sms[]>(`/demo/sms?phone=${encodeURIComponent(phone)}`),
    refetchInterval: 3000,
  });

  const send = async (text: string) => {
    setBusy(true);
    setError(null);
    try {
      const r = await api<Reply>("/demo/ussd", { method: "POST", body: { phone, text } });
      setScreen(r);
      setSession(r.done ? null : text);
      setInput("");
      if (r.done) void inbox.refetch();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Network problem. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const call = () => {
    if (dialled.replace(/\s/g, "") !== code) {
      setError(`Dial ${code}`);
      return;
    }
    setDialled("");
    void send("");
  };
  const hangUp = () => {
    setSession(null);
    setScreen(null);
    setInput("");
    setDialled("");
    setError(null);
  };
  const press = (k: string) => {
    if (screen?.done) return;
    if (session === null && !screen) setDialled((d) => d + k);
    else setInput((i) => (i + k).slice(0, 4));
  };
  const answer = () => {
    if (session === null || !input) return;
    void send(session ? `${session}*${input}` : input);
  };
  const inCall = session !== null || !!screen;

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-10">
      <header className="flex items-center gap-3 py-4">
        <Link href="/" aria-label="Back to VITALIS" className="rounded-full p-2 hover:bg-muted">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">Healthcare for everyone</p>
          <h1 className="text-2xl font-bold leading-tight">No smartphone? No data? Dial {code}</h1>
        </div>
      </header>

      <div className="grid gap-6 md:grid-cols-[340px_1fr]">
        {/* the basic phone */}
        <div className="mx-auto w-full max-w-[340px] rounded-[2.5rem] bg-[#1d1d1f] p-5 shadow-xl">
          <div className="mb-3 flex justify-between px-2 text-xs text-neutral-400">
            <span className="inline-flex items-center gap-1"><Radio className="h-3 w-3" aria-hidden /> 2G</span>
            <span>{phone}</span>
          </div>
          <div
            className="min-h-56 rounded-xl bg-[#c9d8b6] p-3 font-mono text-[15px] leading-snug text-[#1d2a12] shadow-inner"
            aria-live="polite"
            data-testid="ussd-screen"
          >
            {!inCall ? (
              <div className="flex h-52 flex-col justify-between">
                <p className="text-xs">Dial the VITALIS code, then press the green key.</p>
                <p className="break-all text-right text-2xl">{dialled || " "}</p>
              </div>
            ) : (
              <>
                <p className="whitespace-pre-wrap">{busy && !screen ? "Connecting…" : screen?.reply}</p>
                {!screen?.done ? (
                  <p className="mt-2 border-t border-[#1d2a12]/30 pt-1">
                    &gt; {input}
                    <span className="animate-pulse">_</span>
                  </p>
                ) : null}
              </>
            )}
          </div>
          {error ? <p className="mt-2 text-center text-sm text-red-300">{error}</p> : null}

          <div className="mt-4 grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={inCall ? answer : call}
              disabled={busy || (inCall && (!input || !!screen?.done))}
              className="flex h-12 items-center justify-center rounded-full bg-[#2f9e55] text-white disabled:opacity-40"
              aria-label={inCall ? "Send" : "Call"}
            >
              {inCall ? <span className="font-semibold">Send</span> : <Phone className="h-5 w-5" />}
            </button>
            <button
              type="button"
              onClick={() => (inCall ? setInput((i) => i.slice(0, -1)) : setDialled((d) => d.slice(0, -1)))}
              className="h-12 rounded-full bg-neutral-700 text-sm font-semibold text-white"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={hangUp}
              className="flex h-12 items-center justify-center rounded-full bg-[#c0392b] text-white"
              aria-label="End"
            >
              <PhoneOff className="h-5 w-5" />
            </button>
            {KEYS.map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => press(k)}
                className="h-12 rounded-xl bg-neutral-800 text-xl font-semibold text-white active:bg-neutral-600"
              >
                {k}
              </button>
            ))}
          </div>
          {!inCall ? (
            <button
              type="button"
              onClick={() => setDialled(code)}
              className="mt-3 w-full rounded-full border border-neutral-600 py-2 text-sm text-neutral-300"
            >
              Type {code} for me
            </button>
          ) : null}
        </div>

        {/* what happens */}
        <div className="space-y-4">
          <Card className="space-y-2">
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <MessageSquareText className="h-5 w-5 text-primary" aria-hidden /> Texts to {phone}
            </h2>
            {(inbox.data ?? []).length ? (
              <ul className="space-y-2">
                {inbox.data!.map((m) => (
                  <li key={m.at} className="rounded-2xl rounded-tl-sm bg-muted px-3 py-2 text-sm">
                    <span className="block text-xs text-muted-foreground">
                      VITALIS · {new Date(m.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                    {m.text}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                No texts yet. When the hospital answers, the SMS appears here.
              </p>
            )}
          </Card>

          <Card className="space-y-3 text-sm leading-relaxed">
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <Smartphone className="h-5 w-5 text-primary" aria-hidden /> How it works
            </h2>
            <ol className="list-decimal space-y-1 pl-5">
              <li>Dial {code} on any phone. No app, no data, no smartphone.</li>
              <li>Choose what is happening, then your local government area.</li>
              <li>
                The nearest hospital that can treat it gets the request on its screen, marked{" "}
                <b>Dialled by USSD</b>, with your number to call back.
              </li>
              <li>The hospital accepts, and the answer reaches you by SMS.</li>
            </ol>
            {lines?.ambulances.length ? (
              <p className="rounded-xl bg-emergency-soft px-3 py-2 font-semibold text-emergency">
                {lines.ambulances.map((a) => `${a.name}: ${prettyNumber(a.number)}`).join(" · ")} · National emergency:{" "}
                {lines.national.number}
              </p>
            ) : null}
            <p className={cn("text-xs text-muted-foreground")}>
              This is a simulator with demo numbers (0000 000 0xxx): the texts above are not really sent. A live code
              needs a USSD gateway such as Africa&apos;s Talking and a short code approved by the NCC.
            </p>
          </Card>
        </div>
      </div>
    </main>
  );
}
