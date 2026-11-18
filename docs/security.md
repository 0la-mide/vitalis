# Security and abuse limits

VITALIS runs on one VPS behind the host's Traefik. These are the layers, outside in.

## nginx (`deploy/nginx.conf.template`)

- **Real client IP**: X-Forwarded-For is trusted only from private Docker hops, so a client can't fake its IP to
  dodge limits. The backend gets just that IP.
- **Flood limits per IP**:
  - API: 40 requests/s, with bursts up to 400.
  - Sign-in, staff registration and patient recovery: 2/s, with bursts up to 20.
  - Web pages: 100/s.
  - At most 100 open connections per IP, live streams included.
- **Other protections**: slow-client timeouts, `server_tokens off`, HSTS, CSP, and frame and sniffing protection.
  Uploads are capped at 6 MB.

## Backend (`app/core/guard.py`, `app/core/middleware.py`, `@limiter.limit` on routes)

- **Every API route**: 1,200 requests/min per IP, on top of each route's own limit.
- **Per-route limits** (per IP unless noted):

| What | Limit |
|---|---|
| New patient | 60/min |
| Patient recovery | 5/min |
| Staff sign-in | 30/min per network, and **8 wrong passwords per account in 15 min locks that account** for the rest of the window |
| Triage | 30 or 120/min per device |
| Referral | 20/min per device |
| Staff registration | 5 or 10/hour |
| USSD simulator | 300/min to browse; **60 finished requests/hour per network**, so nobody can flood the demo hospitals |
| USSD gateway | 600/min, and only with `?key=USSD_SECRET` (off in prod until it's set) |

Limits are generous per IP on purpose: a hospital, or a venue's Wi-Fi during a demo, puts many people behind one
address.

- **Errors**: rate-limited requests get the normal error shape (`rate_limited` or `too_many_attempts`) and a
  `Retry-After` header, so the app shows a calm message.
- **Production**: no API docs or OpenAPI schema. The app refuses to start with a weak `JWT_SECRET`.
- **Already in place before this**:
  - httpOnly, SameSite cookies, and CSRF on staff changes.
  - Hashed device keys and recovery codes.
  - Facility scoping on every hospital route, consent for cross-hospital records, and a full audit log.
  - Uploads checked by their content (magic bytes), stored privately.

## Containers (`deploy/docker-compose.yml`)

- No privilege escalation (`no-new-privileges`).
- App containers drop all Linux capabilities and run as non-root users.
- Memory caps: postgres 1 GB, backend 1 GB, frontend 512 MB, model 384 MB, nginx 128 MB.
- A process limit for each container.
- Logs rotate at 10 MB × 3 per container, so they never fill the disk.
- Only nginx is reachable, through Traefik. Postgres and the model service sit on the internal network.

## deploy.sh

- Makes `.env` readable only by its owner (`chmod 600`).
- Creates a random `JWT_SECRET` if the current one is weak.
- Warns if `POSTGRES_PASSWORD` is weak.
- Backs up the database before every deploy and keeps 14 days of backups.

## Worth doing on the host (once, by hand)

- **Firewall**: allow only SSH, 80 and 443.

  ```bash
  ufw allow OpenSSH && ufw allow 80,443/tcp && ufw enable
  ```

- **SSH**: keys only (`PasswordAuthentication no`), plus `fail2ban` for SSH.
- **Demo data**: the shared demo password in `DEMO_LOGINS.pdf` opens every demo staff account. After the
  presentation, run `./deploy/deploy.sh --reset-demo` to get a new one, and set `DEMO_LOGINS=false` before any
  real pilot.
