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

## At the hospital: arrival to discharge, no re-typing

1. Sapon receptionist (`receptionist.sapon@vitalis.demo`) → **Incoming** → **Confirm arrival & open encounter**. The
   encounter already has the referral, symptoms and the chemist's vitals.
2. Nurse (`nurse.sapon@…`) → **Patients** → record vitals: they appear beside the chemist's with ↑/↓ arrows (an SpO₂
   below 92 is flagged urgent). **Send to doctor**.
3. Doctor (`doctor.sapon@…`) → write the note → **Save draft** → **Sign note** → **Order tests** (tap twice for urgent).
4. Lab (`lab.sapon@…`) → **Lab** → enter each result → **Verify**. The encounter returns to the doctor as
   "Results ready".
5. Doctor → **Decide disposition** (e.g. admitted) → receptionist → **Complete encounter**. The timeline shows every
   handoff with time and name; the chemist's referral shows "Completed".

## The doctor and VITALIS AI (Folake, from the team's NCS demo)

1. `doctor.central@vitalis.demo` → **Patients** → open **Mrs. Folake Adewale (demo)** in the Doctor column (54, headache,
   blurred vision, thirst, frequent urination; BP 174/108, glucose 236).
2. Point at **Patient record**: hypertension on amlodipine, and an allergy to **sulfonamides recorded at Ogun Teaching
   Hospital** 7 months ago.
3. **Run VITALIS AI** and let the steps reveal. Read the three wins:
   - Red flag: markedly raised BP with blurred vision.
   - Uncontrolled stage 2 hypertension (BP 148 → 152 → 156 → 174 across visits) and **probable new type 2 diabetes**,
     with the **team's diabetes model** (Moderate band) and **heart model** (High band) showing which inputs were
     measured vs assumed.
   - **"Do not give Hydrochlorothiazide"**: the usual next BP drug, but it cross-reacts with the allergy recorded at
     another hospital.
4. **Prescribe**: type *Hydrochlorothiazide* → **Check safety** → blocked (override needs a reason, audited). Type
   *Lisinopril*, dose *10 mg once daily* → **Prescribe**. It joins her record as a current medicine.
5. **Accept and draft note** → the AI text lands in the doctor's draft note; nothing is recorded until they sign.

6. **Her record, her choice.** Before step 3, the other hospitals' visits are locked. Click **Ask the patient to
   share**; on her phone tap **Allow** (or show her **Share** QR and scan it). The visits appear, and the AI trend now
   spans three hospitals. On her phone, **Who looked** lists every view, with **Stop**.

## Talking points

- *Safety rules before models:* stop the model (`Ctrl-C` on the model process) and repeat — the red flag still fires.
- *Data honesty:* each hospital shows Confirmed / Stale / Unknown with time. Ogun Teaching Hospital is big but stale
  (12 h), so it ranks lower. Hospital staff update availability with one tap on **Availability**.
- *A referral is not accepted until the hospital says so* — and not finished until reception confirms arrival.
- *Overdue:* if she does not arrive by ETA + 30 min, the referral turns overdue and the family gets an SMS (console in
  dev).
- *AI that can't hallucinate a value:* every piece of evidence cites its source (visit, lab or other hospital) and
  the AI never gives doses. External LLMs are off by default; with `ALLOW_EXTERNAL_LLM=true` Gemini/Groq only rephrase
  the summary, and any output containing a dose is rejected.
- *Verification:* sign in as `facilityadmin.asero@vitalis.demo` — pending facility, status page only, never matched.
  Then as `admin@vitalis.demo`: **Verifications** shows Asero and a pending chemist with their (synthetic) licence
  PDFs; approve Asero and it appears in matching immediately. **Audit log** shows every decision and document view.
- *Staff join their hospital:* register at `/auth/register` → Hospital staff; sign in as
  `facilityadmin.central@vitalis.demo` → **Staff** to approve (a pending nurse is already waiting).
