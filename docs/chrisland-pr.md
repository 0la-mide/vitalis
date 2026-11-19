# VITALIS: healthcare coordination for Nigeria (ITDC 2026)

This brings VITALIS into the team repo with its full history (49 commits). VITALIS gets a patient from "something is
wrong" to "a hospital that can treat this is ready for you", on a smartphone, a basic phone (USSD), or with no signal
at all.

**Live demo:** https://vitalis.olamide.cloud (synthetic data only).

## What's in it

- **Family app, no account needed:**
  - Triage in three taps, with red-flag rules, the disease model and live hospital matching.
  - Referrals that hospitals accept or decline in real time.
  - Alerts and SMS, plus "My health record" with consent, QR sharing and "who looked".
- **Healthcare for everyone:**
  - **USSD** (`*384*8482#`, a demo code) for basic phones with no data; the hospital's answer goes back by SMS.
  - The **Ogun State Ambulance** (0811 200 0033) beside 112 everywhere.
  - Works **with no signal**: the nearby-hospital list is saved on the phone (6 KB) and requests are sent when the
    signal returns.
- **Chemists:** walk-in triage with vitals, live referrals, and a monthly summary of their referrals.
- **Hospitals:** every role, each with its own screen:
  - Reception, nursing, doctor, lab and radiology.
  - The doctor gets VITALIS AI, the team's diabetes and heart risk models, and medicine safety checks that use
    history from other hospitals.
  - Cost and coverage: accepts NHIA, free maternal care.
- **Network admin console:**
  - Overview charts by channel, plus every account, device and model.
  - A full audit log with search and CSV export.
  - Patients are always anonymous here.
- **Security:**
  - Rate limits sized for shared Wi-Fi, and lockout after repeated wrong passwords.
  - Consent before any other hospital sees a record, and an audit log of every access.
  - Hardened nginx and Docker settings.
  - Details in `docs/security.md`.

## Layout

| Folder | What |
|---|---|
| `backend/` | FastAPI, PostgreSQL, Alembic (`uv`) |
| `frontend/` | Next.js PWA (works offline) |
| `model/` | the disease model service |
| `deploy/` | Docker Compose, nginx, `deploy.sh` (one VPS behind Traefik) |
| `docs/` | API, architecture, security, USSD, testing, demo script |
| `pitch/` | deck, film and teleprompter sources (the built files are not committed) |

## Run it

```bash
make setup && make db && make migrate && make demo-reset
make backend   # :8000
make model     # :8100
make frontend  # :3000
```

Demo logins are written to `backend/var/DEMO_LOGINS.md` (never committed). Deploying to a server is covered in
`deploy/deploy.sh`.

## Checks

- `make test`: 134 backend tests pass.
- `make lint`: ruff, eslint and tsc are clean.
- Offline engine parity with the server: `node frontend/scripts/offline-parity.mjs`.

## Notes for reviewers

- **Synthetic data only.** Every hospital, person and phone number is fictional. The clinical rules in
  `backend/data/*.json` are drafts marked `needs_clinical_review`.
- **USSD isn't live.** It's a demo until an NCC-licensed gateway issues a code (`docs/ussd.md`). The website has a
  simulator at `/ussd`.
- **NHIA.** VITALIS works alongside the NHIA (formerly NHIS) and is not affiliated with it.
- **No secrets in the repo.** `.env`, demo passwords, keys and uploads are all git-ignored.
