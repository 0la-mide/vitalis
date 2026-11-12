# VITALIS architecture

## Shape

One VPS, Docker Compose: `nginx` → `frontend` (Next.js PWA) on `/` and `backend` (FastAPI) on `/api`; `postgres` and
`model` are on the internal network only. The backend is a **modular monolith**; the disease model is the only other
service.

```
Patient phone / worker / hospital  ──HTTPS──>  nginx ──/──────> Next.js PWA
                                                  └──/api───> FastAPI ──> PostgreSQL
                                                                 └────> model:8100 (/predict, 800 ms timeout)
```

## Backend modules (`backend/app`)

| Module | Responsibility |
|---|---|
| `core/` | config, async DB session, security (Argon2, JWT, hashing), deps (auth, roles, facility scoping, CSRF, patient key), errors/envelope, middleware (request ID, security headers), rate limits, audit |
| `engines/triage/` | taxonomy loader, `TriageState`, deterministic red-flag evaluator, care-type + action-level rules |
| `engines/model_client/` | adapter for the disease model: builds the request from `model_code`s, 800 ms timeout, never raises |
| `engines/matching/` | haversine, hard filter, 40/25/20/15 score, freshness, reasons; pure functions over snapshots |
| `services/` | triage pipeline, referral state machine, overdue job, patient identity, notifications (SMS interface) |
| `realtime/` | in-process pub/sub broker for SSE (channels `report:`, `referral:`, `facility:`, `worker:`) |
| `api/v1/` | routers: health, auth, patients, triage, referrals, facilities, hospital |

## Triage pipeline (every tap)

1. **Red-flag rules** (`data/red_flags.json`): local, deterministic, no I/O. If any fires: status `emergency`,
   `action_level=go_now`, care type from the rule, heads-up to the top 3 facilities. The model is not called.
2. **Disease model** (only when no red flag): `POST /predict` with `model_code`s. Timeout/error → logged,
   `model_predictions.ok=false`, continue.
3. **Care type**: red flag > pregnancy+pelvic region > model condition (`care_types.json`) > child override > region
   default.
4. **Matching** on verified facilities only.

The family-facing response (`TriageOut`) contains no condition names or likelihoods; tests assert this.

## Patient identity without login

`POST /patients/start` creates a patient with a `VT-XXXX-XX` ID and returns a 32-byte device key and a one-time
recovery code. Only SHA-256 hashes are stored. The PWA keeps the key in IndexedDB and sends `X-Patient-Key`.
`POST /patients/recover` rotates both. SSE for patients uses `fetch` streaming because `EventSource` cannot send headers.

## Staff auth

Argon2 passwords; access (15 min) + refresh (7 d) JWTs in httpOnly, SameSite=Lax cookies (`Secure` in prod); CSRF
double-submit (`vt_csrf` cookie echoed as `X-CSRF-Token`) on all staff mutations. `require_hospital_staff(*roles)`
checks role, approved account and approved facility; every hospital query is filtered by `user.facility_id`, and
cross-facility IDs return 404. Pending / rejected / suspended accounts can only call `/auth/me`.

## Frontline worker app

The worker app reuses the patient tap flow (`components/triage/TriageFlow.tsx` with `mode="worker"`). Calls go to
`/worker/*` with cookie auth instead of `X-Patient-Key`. `POST /worker/triage` creates the walk-in patient
(`created_by_worker_id`) and returns the VITALIS ID and one-time recovery code for the paper slip; the worker never holds
the patient's device key. Vitals are stored with `source=worker`, `entered_by` and `report_id`, and re-run the red-flag
rules (reusing the last stored model prediction, so the care type does not change). Referrals carry `worker_id`, so the
worker's SSE channel and the overdue job (SMS to the worker's phone) both reach them.

## Receiving hospital

Reception confirms arrival, which opens an `encounter` linked to the referral and triage report, so the symptoms, danger
sign, care type and the chemist's vitals are already there. Emergencies go straight to the doctor; others to nursing.
Every step writes an `encounter_events` row (time, staff, from/to state) that the timeline shows. Nurse vitals sit next
to the chemist's with a trend arrow; a correction is a new reading pointing at the old one (`corrected_from`), never an
overwrite. Doctor notes are private drafts until signed; signed notes are immutable and amended by a new version. Orders
move the encounter to `awaiting_investigation`; lab enters a result and verifies it as a separate action, and when all
orders are verified the encounter returns to the doctor as `results_ready`. A disposition needs a signed note;
completing it also completes the referral (the chemist sees "Completed").

## Doctor AI (ported from the team's NCS repo)

`engines/clinical/assessment.py` is the NCS `clinical_ai.py` rules (red flags, hypertension, diabetes, dyslipidaemia,
malaria, respiratory, trends, provenance) on this data model. Two changes: the AI shows drug names and reasons only
(no doses, per the brief), and a positive malaria test today counts as evidence. `services/clinical_ai.py` builds the
input: this facility's visits with the patient, the referral (incl. chemist vitals), verified structured lab values and
the patient's history entries with their source hospital. The team's models (`ml_models/*.joblib`, scikit-learn 1.8.0)
load through `engines/ncs_models/adapter.py`: SHA-256 pinned, unpickled through a class allowlist, run off the event
loop, shown as Low/Moderate/High bands; any failure falls back to rules only. Medication safety
(`data/medication_safety.json`, needs clinical review) checks allergies with cross-reactivity, interactions and
condition/pregnancy contraindications; prescribing a conflicting drug needs an audited override. Each run is an
`ai_drafts` row (inputs, output, model versions, narrative provider, doctor action). The narrative is canned unless
`ALLOW_EXTERNAL_LLM=true` (Gemini → Groq), forced to JSON, schema-validated, and rejected if it contains a dose.

## Registration and verification

Self-registration creates `pending` accounts plus a `verifications` row (subject `facility`, `worker` or `staff`) with
the submitted licence details and document upload ids. The **network admin** reviews facilities and workers; each
**facility admin** reviews staff at their own facility. Decisions: `pending → approved | rejected`,
`approved → suspended`, `suspended → approved`. Approving or suspending a facility applies to its facility-admin account
too; a suspended facility drops out of matching and its staff lose work screens. Rejected applicants resubmit, which
creates a new `pending` verification linked to the old one. Every decision and document view is audited.

## Referral state machine

`pending → accepted | declined | more_info | cancelled`, `more_info → accepted | declined | cancelled`,
`accepted → arrived | overdue | cancelled`, `overdue → arrived | cancelled`, `arrived → completed`.
Every transition stamps its own timestamp and is audited. Decline requires a reason and automatically creates the next
referral to the best-ranked facility not yet tried. The overdue job runs every minute:
`now > accepted_at + ETA + 30 min` → `overdue`, SMS to the family if a phone was given, SSE to everyone.

## Known MVP limits

- SSE broker is in-process: run **one** backend worker (the Dockerfile does). Swap for Postgres LISTEN/NOTIFY to scale.
- Web Push (VAPID) subscriptions table exists; sending is the next step of Phase 4.
- Docker images are written but were not built in the dev environment (no Docker installed there).
