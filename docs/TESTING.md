# VITALIS — how to test it yourself

Everything here uses **synthetic demo data**. Nothing you do can reach a real patient, hospital or phone number
(SMS messages are only printed in the backend terminal).

---

## 1. Start it

From the `vitalis` folder:

```bash
make dev            # starts the model stub (:8100), backend (:8000) and the app (:3000). Ctrl-C stops all three.
```

Open **http://localhost:3000**.

| Useful command | What it does |
|---|---|
| `make logins` | Shows every demo account and the shared password (also as `backend/var/DEMO_LOGINS.pdf`) |
| Demo patients | On `/card`: open a demo patient's phone in one tap. On by default; `DEMO_LOGINS=false` turns it off |
| `make demo-reset` | Wipes everything and reseeds in ~1 s. **Do this before each test round.** It also creates a new password, so run `make logins` again |
| `make overdue-now` | Makes every accepted referral look 3 hours old, so the overdue alert fires within a minute |
| `make test` | Runs the 79 automated backend tests |
| `make lint` | Lint + type checks |

> **Signing in as several people at once.** Sign-in is a browser cookie, so one browser window = one person. To play
> the family, the chemist and two hospitals at the same time, use **different browsers or profiles** (Chrome, Chrome
> Incognito, Safari, Firefox…), or your phone for the family.

### Testing on your phone (same Wi-Fi as the laptop)

1. Find your laptop's address: `ipconfig getifaddr en0` (e.g. `192.168.3.15`).
2. On the phone open `http://192.168.3.15:3000`.
3. Two things behave differently over plain `http` on a phone (they work on the HTTPS deployment):
   - **GPS is blocked** by the phone browser → the app shows "approximate location" and an **area picker**. That is the
     fallback working; pick *Abeokuta South* to match the demo.
   - **Offline mode / install as app** need HTTPS, so they won't work here.
4. **QR codes on a phone:** set `PUBLIC_BASE_URL=http://192.168.3.15:3000` in `.env` and restart the backend, so
   the patient's share QR points at the laptop rather than `localhost`. Staff scan it with the phone camera (there is
   no in-app scanner) and sign in if asked.

---

## 2. Who is who in the demo

| Account | Role | Notes |
|---|---|---|
| `admin@vitalis.demo` | Network admin | Verifies facilities and frontline workers |
| `chemist1@vitalis.demo` | Chemist (Mama Tola) | Approved frontline worker |
| `chemist3@vitalis.demo` | Chemist | **Pending** — should only see a status page |
| `doctor.central@…`, `nurse.central@…`, `receptionist.central@…`, `lab.central@…`, `facilityadmin.central@…` | Abeokuta Central Hospital | Ranked first for pregnancy bleeding; **declines** in the story |
| same roles `.sapon@vitalis.demo` | Sapon Mother & Child | Next in line; **accepts** |
| `facilityadmin.asero@vitalis.demo` | Asero Community Hospital | **Pending facility** — never appears to patients |
| `newnurse.central@vitalis.demo` | Nurse at Central | **Pending staff** — waiting for Central's facility admin |

Hospital roles exist for all 8 facilities with the pattern `role.slug@vitalis.demo` (slugs: `ibara`, `central`, `sapon`,
`teaching`, `lafenwa`, `kemta`, `obantoko`, `adigbe`). Patients never have accounts.

---

## 3. Test scenarios

Tick each box as you go. If something doesn't match "Expect", note the scenario number, the step and what you saw.

### A. Family emergency (the main demo) — 2 windows

Window 1 = family (phone or narrow window). Window 2 = `doctor.central@…`, Window 3 = `doctor.sapon@…`.

1. [ ] Family: open `/`, tap **Pregnancy problem**.
   *Expect:* body map; bottom bar says "8 nearby · 8 can handle this".
2. [ ] Tap **Private parts / groin** (on the figure or the button). The figure is a **pregnant** woman. Also try
   **Upper belly**: there is **no "Swollen belly"** card for a pregnant woman.
   *Expect:* bar drops to **4 can handle this**.
3. [ ] Tap **Heavy bleeding**.
   *Expect:* red **"This is an emergency"** screen immediately, Call 112 button, "Nearby hospitals have been alerted",
   Abeokuta Central first. Open "Not suitable right now": **Ibara Family Clinic — No obstetrician on duty**.
4. [ ] Window 2 (Central): **Incoming** already shows a **heads-up** card with "Heavy bleeding" — before anyone pressed
   send.
5. [ ] Family: **Send to this hospital** on Central (4th tap).
   *Expect:* "Waiting for the hospital to confirm…". Window 2 shows it as **pending** without refreshing.
6. [ ] Window 2: **Decline → Theatre busy**.
   *Expect:* within ~3 s the family screen switches to **Sapon Mother & Child** by itself. The family never sees
   "Theatre busy".
7. [ ] Window 3 (Sapon): **Accept**.
   *Expect:* family sees **"Go now. They are ready for you."**, minutes away, Directions, Call hospital, what to bring,
   VITALIS ID, and the recovery slip.
8. [ ] Open the app as `/?timer=1` to show the small tap/second counter. Target: **≤ 5 taps, ≤ 15 s**.

### B. Safety rules don't need the AI

1. [ ] In the `make dev` terminal, the model runs as its own process. Stop just the model: `pkill -f "app:app --port 8100"`.
2. [ ] Family: home → **Can't breathe**.
   *Expect:* emergency screen still appears instantly.
3. [ ] Restart everything with `make dev` afterwards.

### C. Non-urgent path (taps only, no typing)

1. [ ] Family: **Something else → Man → Whole body → Hot body / fever → Bad → 2–3 days**.
   *Expect:* each symptom card moves on with **one tap** (no "Next"). "See a chemist or clinic", a map, hospitals with **Confirmed / Stale / Unknown** freshness labels. **No
   disease names anywhere** on the family's screens.
2. [ ] Try the **speaker** buttons (English voice) and the **language picker** (other languages fall back to English
   for now — translations aren't filled in yet).

### D. Chemist walk-in (< 1 minute)

Sign in as `chemist1@vitalis.demo` → you land on **New walk-in**.

1. [ ] **Something else → Man → Whole body → Hot body / fever → Bad → 2–3 days.**
   *Expect:* "On behalf of patient · VT-…" bar at the top; the **Vitals** form opens on the results.
2. [ ] Enter temperature **38.6**, pulse **104** → **Save vitals**. *Expect:* chips with the saved readings; care type
   stays the same.
3. [ ] **Send to this hospital**. *Expect:* referral page with live status and the **"Hand this to the family"** slip
   (VITALIS ID + recovery code, Print button).
4. [ ] Start another walk-in, but enter **BP systolic 84**. *Expect:* the screen turns into the **emergency** view
   ("Blood pressure is very low").
5. [ ] **My referrals** updates live when a hospital accepts/declines (sign in as that hospital's doctor in another
   browser to try).

### E. At the hospital: arrival → discharge with no re-typing

Use a referral to **Sapon** (from A or D). Sign in as each Sapon role in turn (or 4 browsers):

1. [ ] `receptionist.sapon` → **Incoming** → **Confirm arrival & open encounter**.
   *Expect:* encounter already shows the referral, symptoms and the chemist's vitals (if any).
2. [ ] `nurse.sapon` → **Patients** → open the patient → record vitals (try **SpO₂ 89**).
   *Expect:* readings beside the chemist's with ↑/↓ arrows; SpO₂ 89 marked **urgent**. Click **correct** on one reading
   → the original stays, crossed out, under "Corrected readings". **Send to doctor**.
3. [ ] `doctor.sapon` → write a note → **Save draft** → **Sign note** → **Order tests** (tap a test once = routine,
   twice = urgent) → **Send**. *Expect:* state "Waiting for tests".
4. [ ] `lab.sapon` → **Lab** → enter each result → **Verify** each. *Expect:* the encounter goes to **Results ready**.
5. [ ] `doctor.sapon` → **Decide disposition** (try "Discharged" first *without* a signed note on a new encounter — it
   should refuse) → Confirm.
6. [ ] `receptionist.sapon` → **Complete encounter**.
   *Expect:* timeline lists every step with time, name and role; the chemist's referral shows **Completed**.
7. [ ] **Patients → Register walk-in** (reception): fill complaint → Register → slip with VITALIS ID + recovery code.
   Tick **Emergency** on another one → it goes straight to the **Doctor** column.

### E2. Doctor AI and safe prescribing

1. [ ] `doctor.central@…` → **Patients** → the visit in the Doctor column (headache, blurred vision, thirst) →
   **Run VITALIS AI**.
   *Expect:* BP red flag; "Uncontrolled stage 2 hypertension" and "Type 2 diabetes (probable new diagnosis)"; two
   model cards (diabetes Moderate, heart High); **Do not give Hydrochlorothiazide** citing Ogun Teaching Hospital; no
   doses anywhere in the AI's suggestions.
2. [ ] **Prescribe** Hydrochlorothiazide → **Check safety** → blocked. Lisinopril 10 mg once daily → prescribed.
3. [ ] **Reject** needs a reason; **Accept and draft note** adds the text to your draft note.
4. [ ] `lab.central@…` → **Lab**: tests like HbA1c / Lipid profile show number fields with reference ranges and flag
   high/low automatically.

### E3. Shared record and QR consent (2 windows)

Patient window: `/card` → **Mrs. Folake Adewale** under *Demo: open a patient's phone* (or restore with her VITALIS ID
and recovery code from `make logins`).
1. [ ] Doctor on Folake's visit: **Records from other hospitals** is locked ("2 visit(s) at other hospitals… private").
   Allergy from Ogun Teaching still shows. **Ask the patient to share** → "Waiting for the patient…".
2. [ ] Patient: a banner "Abeokuta Central Hospital wants to see your health record" → **Allow**.
   *Expect:* within ~3 s the doctor sees the Lafenwa and Ogun Teaching visits; **Run VITALIS AI** now says
   "3 earlier visit(s)" with BP 148 → 152 → 156 across three hospitals.
3. [ ] Patient → **Who looked**: the hospital with **Stop**, and each view listed. Tap **Stop**.
4. [ ] Patient → **Share** → **Show my QR code** (10:00 countdown). Open the link on the doctor's device →
   "Record shared with your hospital" → straight to her visit. Open it again → "already used".

### E4. Lab, radiology and alerts

1. [ ] Doctor orders an FBC and an obstetric ultrasound. `lab.<hospital>@…` sees only the FBC: **Sample collected**
   → result → **Verify**. `radiology.<hospital>@…` sees only the scan: report → **Verify**. Both verified → back to
   the doctor.
2. [ ] On the live site (HTTPS), tap **Get alerts on this phone** on a family referral page and on **Incoming**.
   Accept the referral: the family phone gets "Hospital is ready" even with the app closed.

### F. Registration and verification

1. [ ] Sign out → **Register** → **Frontline worker**: fill it in, attach any small **PDF/JPG/PNG** (≤ 5 MB) → Submit.
   Try a `.docx` or a renamed file first — it should be **rejected**.
2. [ ] Sign in as the new worker. *Expect:* only a **status page** ("waiting for verification").
3. [ ] `admin@vitalis.demo` → **Verifications** → open the document → **Reject** with a reason.
4. [ ] New worker: status page shows the reason → **Resubmit** with a new document.
5. [ ] Admin: **Approve**. Worker now lands on **New walk-in**.
6. [ ] **Register → Hospital staff** at Central (pending facilities like Asero are not in the list).
   `facilityadmin.central` → **Staff** → approve (Funmi, a pending nurse, is already waiting).
7. [ ] Admin → approve **Asero Community Hospital** → it now appears in patient results. **Suspend** it → it
   disappears again and its staff lose their screens.
8. [ ] Admin → **Audit log**: filter "Verification decisions" and "Document views" — your actions are listed.
   **Overview** shows counts with no patient names.

### G. Overdue alert

1. [ ] Create a referral and have the hospital **Accept** it (don't confirm arrival).
2. [ ] Run `make overdue-now`.
3. [ ] Within a minute: family and chemist screens show **Overdue**; the backend terminal prints an `sms` line (masked
   phone) if a family phone / chemist phone exists.

### H. Security spot checks

1. [ ] `chemist3@vitalis.demo` (pending) and `facilityadmin.asero@…` (pending facility): only the status page, even if
   you type `/hospital` or `/worker` in the address bar.
2. [ ] Copy an encounter URL from Sapon and open it signed in as `nurse.central@…` → **Not found**.
3. [ ] Copy a document link from the admin queue and open it as a doctor → **Not found**.

---

## 4. Known limits (expected, not bugs)

- Doctor's view of the model's output and AI-drafted summaries: **not built yet** (next phase).
- Patient records on their phone and QR sharing: not built yet.
- Translations for Pidgin, Yorùbá, Hausa, Igbo: keys exist, text is empty → English is shown. Audio prompts: only the
  English computer voice; recordings not made yet.
- Web push notifications: not sent yet (SMS goes to the terminal log).
- The disease model is a **stub** with a few hand-written rules.
- Docker/VPS deployment files exist but haven't been run.

## 5. Reporting a problem

For each issue note: scenario + step, which account, what you expected, what happened, and a screenshot. If the
backend terminal printed an error, copy the last few lines (they contain a `request_id` that pins the request).
