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
Registration endpoints (`/auth/register/{facility|staff|worker}`) come with the verification queues.

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

## Public

`GET /facilities?care_type=&lat=&lng=` — verified facilities ranked for a care type. `GET /health`.

## Disease model contract (internal)

`POST http://model:8100/predict` — see `model/app.py`. Request
`{patient{age_group, sex, pregnant}, symptoms[{code, region, severity, onset}], vitals{}}`, response
`{model_version, predictions[{condition_code, label, likelihood}]}`. UI symptom codes map to model codes through
`model_code` in `backend/data/symptoms.json`.
