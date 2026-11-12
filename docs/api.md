# VITALIS API (v1)

All routes are under `/api/v1`. Interactive docs at `/api/docs` (dev only); schema at `/api/openapi.json`, which
generates `frontend/types/api.ts` (`make types`).

**Envelope:** success `{"data": ..., "meta": null | {total, limit, offset}}`; error
`{"error": {"code", "message", "details"}}`.

## Patient (no login, header `X-Patient-Key`)

| Method | Path | Notes |
|---|---|---|
| POST | `/patients/start` | → `{patient_id, vitalis_id, device_key, recovery_code}`; 10/min/IP |
| POST | `/patients/recover` | `{vitalis_id, recovery_code}` → new key + new code; 5/min/IP |
| GET | `/triage/taxonomy` | public UI taxonomy (regions, symptoms, emergencies, who, severity, onset, LGAs) |
| POST | `/triage` | `{taps: Tap[]}` → `TriageOut` |
| POST | `/triage/{id}/taps` | `{taps: Tap[]}` → `TriageOut`; 120/min per IP+key |
| GET | `/triage/{id}` | current state (no model call) |
| POST | `/triage/{id}/referral` | `{facility_id?}` → `ReferralPatientOut` |
| GET | `/referrals/{id}` | family view (no clinical labels; decline reason hidden) |
| GET | `/referrals/{id}/stream` | SSE: `referral.*`, `alert.ready` events for this triage report |

`Tap.kind`: `emergency{code}`, `context{age_group, sex, pregnant, who}`, `region{region}`,
`symptom{code, region, selected}`, `severity{value 1-5}`, `onset{value now|today|days|week}`, `location{lat,lng | lga}`.

## Auth (staff, workers, admins)

`POST /auth/login` · `POST /auth/refresh` · `POST /auth/logout` · `GET /auth/me` (works for pending users).

## Registration (public, rate limited) — everything starts `pending`

| Method | Path | Notes |
|---|---|---|
| GET | `/auth/register/options` | LGAs, services, facility/worker types, staff roles |
| GET | `/auth/register/facilities` | verified facilities staff can join |
| POST | `/auth/register/facility` | multipart: facility fields + admin account + `document`; 5/hour/IP |
| POST | `/auth/register/staff` | JSON: `facility_id` (must be verified), `role` (receptionist/nurse/doctor/lab), `licence_number`; 10/hour |
| POST | `/auth/register/worker` | multipart: `worker_type`, `licence_number`, `lga`, `document`; 5/hour |
| POST | `/auth/resubmit` | signed in, status `rejected`: new `document` (facility/worker) and/or `licence_number` → `pending` |

Documents: PDF/JPG/PNG by **magic bytes**, max 5 MB, random file names in `UPLOAD_DIR` (outside the web root).

## Network admin (role `network_admin`)

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/verifications?status=&kind=&limit=&offset=` | facilities + workers, paginated (`meta`) |
| GET/PATCH | `/admin/verifications/{id}` | `{decision: approve|reject|suspend, reason}`; reason required for reject/suspend; approve also reinstates a suspension |
| GET | `/admin/documents/{upload_id}` | served inline with `CSP: sandbox`; also open to a facility admin for their own staff's documents; audited |
| GET | `/admin/audit?action=&actor_id=&facility_id=&since=&until=` | `action` is a prefix match (e.g. `verification.`) |
| GET | `/admin/metrics` | counts only: triage, red flags, referrals, median acceptance time, arrival rate, overdue, pending queues |

## Hospital (cookie auth + `X-CSRF-Token` on mutations; scoped to the user's facility)

| Method | Path | Roles |
|---|---|---|
| GET | `/hospital/incoming` | any hospital role |
| GET | `/hospital/stream` | any hospital role (SSE: `referral.*`, `alert.*`) |
| GET | `/hospital/referrals/{id}` | any hospital role (audited) |
| PATCH | `/hospital/referrals/{id}` | doctor, nurse, facility_admin — `{action: accept|decline|more_info, reason}` |
| POST | `/hospital/referrals/{id}/arrived` | receptionist, nurse, facility_admin |
| POST | `/hospital/alerts/{id}/ready` | doctor, nurse, facility_admin |
| GET | `/hospital/services` | any hospital role |
| PATCH | `/hospital/services/{id}` | any hospital role — `{availability_status}` stamps `last_confirmed_at` |
| GET | `/hospital/staff` | facility_admin — staff at their facility incl. pending |
| PATCH | `/hospital/staff/{user_id}` | facility_admin — `{decision: approve|reject|suspend, reason}`; other facilities' staff → 404 |

## Receiving hospital encounters (facility-scoped)

| Method | Path | Roles |
|---|---|---|
| POST | `/hospital/referrals/{id}/arrived` | receptionist, nurse, facility_admin — now also opens the encounter (`encounter_id` in the response) |
| POST | `/hospital/encounters` | receptionist, nurse, facility_admin — register a walk-in (returns VITALIS ID + recovery code) |
| GET | `/hospital/encounters?state=` | any hospital role — open encounters by default (patient board) |
| GET | `/hospital/encounters/{id}` | any hospital role — referral, vitals (chemist + hospital), signed notes, orders/results, timeline, `allowed` actions; audited |
| POST | `/hospital/encounters/{id}/transition` | `{to, disposition?, note?, reason?}` — role rules in `ENCOUNTER_TRANSITIONS`; disposition needs a signed note; cancel needs a reason |
| POST | `/hospital/encounters/{id}/vitals` | nurse, doctor — `{readings, corrected_from?, correction_reason?}`; corrections keep the original; urgent readings flagged by the red-flag vitals rules |
| POST | `/hospital/encounters/{id}/notes` | doctor — `{body, note_id?}`: new draft, edit own draft, or amend a signed note (new version) |
| POST | `/hospital/encounters/{id}/notes/{nid}/sign` | doctor (author only) |
| POST | `/hospital/encounters/{id}/orders` | doctor — `{items[{test_code, priority}]}` → state `awaiting_investigation` |
| GET | `/hospital/tests` | test catalogue (`data/investigations.json`) |
| GET | `/hospital/lab/queue` | lab |
| POST | `/hospital/orders/{id}/result` | lab — `{result_text, abnormal}` |
| POST | `/hospital/orders/{id}/verify` | lab — separate step; when every order is verified → `results_ready` |

States: `registered → awaiting_nursing → awaiting_doctor → awaiting_investigation → results_ready →
awaiting_disposition → completed | cancelled`. Emergency (red flag or ticked at registration) skips to the doctor.

## Doctor tools (facility-scoped)

| Method | Path | Roles |
|---|---|---|
| GET | `/hospital/encounters/{id}/record` | any hospital role — allergies, conditions, medicines, family history (each with source hospital + date) and this visit's prescriptions; audited |
| POST | `/hospital/encounters/{id}/history` | nurse, doctor — `{kind: allergy|condition|medication|family, text, detail?, onset_age?}` |
| POST | `/hospital/encounters/{id}/ai-draft` | doctor — runs VITALIS AI (rules + the team's ML models + medication safety + narrative); stored as an AI draft |
| GET | `/hospital/encounters/{id}/ai-draft` | doctor — latest draft |
| PATCH | `/hospital/ai-drafts/{id}` | doctor — `{action: accepted|edited|rejected, rationale}`; accept puts the draft into the doctor's draft note; reject needs a reason |
| POST | `/hospital/encounters/{id}/prescriptions/check` | doctor — `{drug}` → `{verdict: ok|caution|avoid, alerts[]}` |
| POST | `/hospital/encounters/{id}/prescriptions` | doctor — `{drug, dose, override_reason?}`; a conflict returns 409 `safety_conflict` unless an override reason is given (audited) |

Lab results accept structured values: `POST /hospital/orders/{id}/result {values: {"HbA1c": {"value": 7.4, "unit": "%"}}}`;
H/L/POS flags come from the test catalogue's reference ranges.

## Frontline worker (role `worker`, approved; scoped to the worker's own reports)

| Method | Path | Notes |
|---|---|---|
| POST | `/worker/triage` | `{taps, family_phone?}` → creates the walk-in patient + report; returns `triage`, `vitalis_id`, one-time `recovery_code` (no device key). Defaults location to the worker's shop |
| POST | `/worker/triage/{id}/taps` | same taps as the patient app |
| GET | `/worker/triage/{id}` | current state |
| POST | `/worker/patients/{patient_id}/vitals` | `{report_id, readings[{kind, value, measured_at?}]}`; kinds: systolic_bp, diastolic_bp, pulse, temp_c, spo2, resp_rate, weight_kg (units fixed, plausibility ranges enforced); re-runs red flags → `TriageOut` |
| POST | `/worker/triage/{id}/referral` | `{facility_id?}` → `WorkerReferralOut` |
| GET | `/worker/referrals` | last 7 days, live status (incl. decline reason, arrived, overdue) |
| GET | `/worker/referrals/{id}` | one referral |
| GET | `/worker/referrals/stream` | SSE on `worker:<id>` |

The worker sees care type, danger-sign message and suggested hospitals — never model likelihoods.

## Public

`GET /facilities?care_type=&lat=&lng=` — verified facilities ranked for a care type. `GET /health`.

## Disease model contract (internal)

`POST http://model:8100/predict` — see `model/app.py`. Request
`{patient{age_group, sex, pregnant}, symptoms[{code, region, severity, onset}], vitals{}}`, response
`{model_version, predictions[{condition_code, label, likelihood}]}`. UI symptom codes map to model codes through
`model_code` in `backend/data/symptoms.json`.
