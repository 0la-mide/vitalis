# Demo script — Mrs. Adebayo, 34 weeks, bleeding at 2am

Setup (2 minutes before): `make demo-reset`, `make dev`. Open two windows:

- **Phone** (or Chrome devtools mobile view): http://localhost:3000 — add `?timer=1` on a production build to show the
  tap/second counter (it shows automatically in dev).
- **Hospital laptop**: http://localhost:3000/auth/login as `doctor.central@vitalis.demo` (Abeokuta Central Hospital).
  A second tab as `doctor.sapon@vitalis.demo` (Sapon Mother & Child). Password in `backend/var/DEMO_LOGINS.md`.

## The story (≤ 5 taps)

1. **Phone — tap "Pregnancy problem"** (tap 1). No login, no typing. The live bar already shows hospitals nearby.
2. **Tap "Private parts / groin"** (tap 2). The bar narrows: only hospitals with an obstetrician, blood and theatre can
   handle this. *Point out:* Ibara Family Clinic is the closest but has no obstetrician, so it is excluded.
3. **Tap "Heavy bleeding"** (tap 3). The red-flag rule fires instantly — no AI involved. Emergency screen: one
   instruction, Call 112, best hospital. "Nearby hospitals have been alerted."
4. **Laptop:** Central's incoming queue already shows a heads-up with symptoms — before anyone pressed send.
5. **Phone — tap "Send to this hospital"** on Abeokuta Central (tap 4). "Waiting for the hospital to confirm…"
6. **Laptop (Central) — Decline → "Theatre busy".** Within 3 seconds the phone switches to Sapon Mother & Child
   automatically. The family never sees the internal reason.
7. **Laptop (Sapon) — Accept.** Phone: **"Go now. They are ready for you."** 6 min away, directions, what to bring,
   VITALIS ID to show at reception. Timer stops.
8. **Show the VITALIS card** at the bottom: ID + one-time recovery code.

## The chemist down the street (< 1 minute)

1. Sign in as `chemist1@vitalis.demo` (Mama Tola) → **New walk-in**. Optional family phone for alerts.
2. Tap **Something else → Adult → Male → Whole body → Hot body / fever → Next → Bad → 2–3 days**.
3. The **Vitals** panel opens on the results: enter temperature 38.6 and pulse 104 → **Save vitals**.
   *Point out:* try systolic 84 instead — the low-BP red flag fires instantly and the screen turns into an emergency.
4. **Send to this hospital** → the referral page shows live status and the **recovery slip** to hand over (Print).
5. Accept on the hospital side: the chemist's page flips to "Accepted — on the way". The hospital card shows "via
   Mama Tola" and the chemist's vitals.

Simulated with a 1.5 s pause per action: 10 taps + 2 vitals + send in about 19 s.

## Talking points

- *Safety rules before models:* stop the model (`Ctrl-C` on the model process) and repeat — the red flag still fires.
- *Data honesty:* each hospital shows Confirmed / Stale / Unknown with time. Ogun Teaching Hospital is big but stale
  (12 h), so it ranks lower. Hospital staff update availability with one tap on **Availability**.
- *A referral is not accepted until the hospital says so* — and not finished until reception confirms arrival.
- *Overdue:* if she does not arrive by ETA + 30 min, the referral turns overdue and the family gets an SMS (console in
  dev).
- *Verification:* sign in as `facilityadmin.asero@vitalis.demo` — pending facility, status page only, never matched.
  Then as `admin@vitalis.demo`: **Verifications** shows Asero and a pending chemist with their (synthetic) licence
  PDFs; approve Asero and it appears in matching immediately. **Audit log** shows every decision and document view.
- *Staff join their hospital:* register at `/auth/register` → Hospital staff; sign in as
  `facilityadmin.central@vitalis.demo` → **Staff** to approve (a pending nurse is already waiting).
