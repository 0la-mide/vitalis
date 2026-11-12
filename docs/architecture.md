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
