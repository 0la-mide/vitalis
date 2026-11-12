# NCS-Backend (team repo) vs. this VITALIS build

Reviewed: `K1ngDollyp/NCS-Backend` at commit `c601e7e` (merge of `feature/network-record-careconnect`), read-only.
Their code was not executed here (the review environment blocks running downloaded code), so every point below
comes from reading the source.

The separate frontend repo `ayofemiade/Vitalis` was also checked: it is **empty** (created, but no commits or branches
yet). The only frontend code available is `NCS-Backend/frontend/`.

## What their repo is

One FastAPI backend (SQLite by default, `create_all` instead of migrations) plus a Vite + React 19 + Tailwind
frontend. It is the **same product, VITALIS**, built from a different angle: the **unified patient record across
hospitals**, with the trip to hospital as the way in.

Demo story (their `docs/DEMO_SCRIPT.md`): Mrs Folake Adewale (54), seen at two hospitals, checks symptoms on her phone,
is matched to FMC Abeokuta for heart/BP care, shares her records with a one-time consent, FMC confirms, then reception →
nurse → doctor → lab. The doctor runs **VITALIS AI**, which spots a BP trend across 3 hospitals, a probable new type 2
diabetes, and a **drug–allergy clash** recorded at a different hospital.

### Their strengths (keep these, they win points)

| Area | What they have |
|---|---|
| **Our team's real ML models** | `ml_model/model_dir/heart_disease_prediction_pipeline.joblib` (Random Forest) and `diabetes_prediction_pipeline.joblib` (SVC), loaded by `app/services/ncs_model_adapter.py`. Shown as Low/Moderate/High bands with which inputs were measured vs. assumed. |
| **Doctor clinical AI** | `app/services/clinical_ai.py` (714 lines): cross-hospital trends, red flags, hypertension/diabetes/dyslipidaemia/malaria/respiratory assessments, every piece of evidence cites its source hospital + date. Deterministic, no external LLM. |
| **Medication safety** | `medication_safety.py`: blocks a prescription that clashes with an allergy from another hospital. The single best "wow" moment. |
| **Unified record + consent** | One-time code / QR consent, facility-scoped, 24 h, revocable; patient sees "who looked" and can revoke. |
| **Hospital workflow** | Reception, nursing (abnormal values flagged, previous readings beside new ones), doctor workspace, lab and **radiology** as separate roles, sample-collected → result → verify. |
| **CareConnect extras** | AI assistant chat, doctor booking/teleconsult, home visits, emergency coordination that asks hospitals one at a time, network analytics. |
| **Demo polish** | Rehearsed 7-minute script, one-click logins, judge Q&A prepared. |

### Problems found (fix before demo day)

1. **Their frontend does not build from the repo.** The root `.gitignore` (Python template) has `lib/`, which also
   ignores `frontend/src/lib/`. The app imports `lib/api`, `lib/auth`, `lib/format`, `lib/hooks`, `lib/types` from 37
   places, but those files were never pushed. Anyone cloning it, and any Vercel deploy, fails. **Fix:** add
   `!frontend/src/lib/` to `.gitignore` (after the `lib/` line) and have whoever has the files commit them.
2. **Pregnancy bleeding goes to the wrong care.** Red flags are keyword matches on free text
   (`app/engines/triage/rules.py`). The patient chip is "Severe bleeding", which matches the **haemorrhage → trauma /
   surgical** rule; the obstetric rule only fires on exact phrases like "pregnant bleeding" or "active labour". The
   hackathon brief's own story (Mrs. Adebayo, 34 weeks, bleeding) would be routed to surgery, not maternity. There is no
   "pregnant" context in their triage at all.
3. **Negation is not handled.** Because rules are substring matches, typing "no chest pain" in "Anything else?"
   triggers a chest-pain emergency.
4. **Patients must log in with a password** (`role=patient`). The brief says patients never register; a family at 2am
   (or a chemist on their behalf) can't create an account first. The patient flow also needs typing and is
   English-only, with no body map, pictures or audio.
5. **No frontline worker (chemist/PPMV/CHEW) role.** The brief's "chemist down the street" path doesn't exist.
6. **Everything polls** (every 2–8 s, ~17 places) instead of pushing updates. Works for a demo, wasteful on cheap
   Android data.
7. **Real institutions in seed data.** "Federal Medical Centre (FMC), Abeokuta", "State Hospital, Sokenu" and "Chrisland
   University Health Services" (the host!) appear with made-up capabilities ("doesn't report a heart service"). A judge
   from one of them may object. Add "(Demo)" or use fictional names. Some seeded phone numbers look real
   (`+234-803-123-4567`); use reserved `0800` numbers.
8. **Security gaps a judge may probe:** JWT lives 24 h (`ACCESS_TOKEN_EXPIRE_MINUTES=1440`) with no refresh; the shared
   demo password is written in the public repo's demo script; `Base.metadata.create_all` with no migrations; only 3
   automated tests.
9. **Model contract mismatch with the brief.** Their models predict heart disease and diabetes from tabular
   measurements (age, BP, cholesterol, glucose…), not "symptoms → condition". That's fine for the **doctor** screen,
   but it can't drive patient triage. Triage must stay rules + care-type mapping, which matches what both builds do.

## What this build adds that theirs doesn't

| Feature | Where it lives here | Effort to bring into their app |
|---|---|---|
| **Tap-only patient triage**: 8 emergency buttons, who-picker, body map (male / female / pregnant / child), symptom picture cards, faces, onset, speaker buttons, 5-language keys | `frontend/components/triage/*`, `components/body-map/*`, `backend/data/symptoms.json` | Medium: port the React components into their Vite app; call their `/triage/sessions` |
| **Structured red flags with patient context** (pregnant, age group, vitals), versioned, 19 rule tests | `backend/data/red_flags.json`, `engines/triage/red_flags.py` | Small: drop-in Python module; fixes problems 2 and 3 above |
| **No-login patient identity** (device key + VITALIS ID + one-time recovery code) | `services/patients.py`, `lib/patient-store.ts` | Medium |
| **Frontline worker app**: walk-in on behalf of patient, vitals that re-run red flags, live "My referrals", printable recovery slip | `/worker/*` | Medium |
| **Heads-up to top 3 hospitals** the moment a red flag fires, decline → next hospital automatically, overdue alert with SMS | `services/triage.py`, `services/referrals.py` | Small–medium |
| **Live updates (SSE)** instead of polling | `realtime/broker.py`, `lib/sse.ts` | Medium |
| **Verification**: facility/worker/staff registration with licence documents (magic-byte checks), admin queue, suspend, audit | `api/v1/registration.py`, `admin.py` | Medium |
| **Security hardening**: httpOnly cookies + CSRF, 15-min tokens + refresh, facility scoping tests, rate limits, security headers | `core/*` | Medium |
| **79 tests** incl. scoping/IDOR, red flags, matching, referrals | `backend/tests` | — |

## Recommendation (to win)

Go with their app as the base, as the team decided, and bring in the pieces that answer the brief's opening story,
which is the first thing judges will test against:

1. **Today:** fix the `.gitignore` / missing `lib/` (problem 1), add "(Demo)" to real hospital names, and remove the
   password from the public script. These take minutes and avoid embarrassment.
2. **Biggest win:** replace their keyword triage with our structured rules (`red_flags.json` + evaluator) so pregnancy
   bleeding goes to obstetrics and negation can't trigger alarms. Add our **tap-only patient flow with the body map**
   as the "Check my symptoms" screen. This is the brief's hero feature ("tap, never type"), and it's what they lack.
3. **Second:** the **chemist walk-in** flow and **decline → next hospital** live update. The brief's story depends on
   both.
4. Keep their doctor AI, medication-safety catch and unified record as the climax of the demo. Ours has nothing as
   strong there.
5. Open the demo with Mrs. Adebayo (the brief's story, 4 taps to "Go now"), then hand over to Folake for the
   cross-hospital record and AI. That covers the brief end to end.
