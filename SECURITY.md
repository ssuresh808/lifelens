# Security

LifeLens is a thin, hardened proxy in front of a multimodal LLM. This document
describes the security baseline and how to operate it safely.

## Reporting a vulnerability

Please do not open a public issue for security problems. Instead, open a private
GitHub security advisory on this repository, or email the maintainer at
mail2surajsuresh@gmail.com. We aim to acknowledge reports within a few days.

## Secrets

- The Anthropic API key is the only secret. It lives **server-side only**, read
  from the `ANTHROPIC_API_KEY` environment variable in `backend/app/main.py`. It
  is never sent to or referenced by the frontend.
- `.env` is gitignored and has never been committed. Only `backend/.env.example`,
  which holds placeholders, is tracked.
- In production the key is held by the platform's secret store (Render environment
  variables), not a plaintext file. Any managed secrets manager (AWS Secrets
  Manager, Vault, platform env vars) works the same way: inject it as an env var.

### Least privilege and rotation

- Create a **workspace-scoped** key in the Anthropic console rather than an
  org-wide one, so its blast radius is limited to this project.
- Set a **hard monthly spend limit** on that key in the console. This is the real
  cost backstop; the in-app daily budget below is a fast-acting complement, not a
  billing guarantee.
- Rotate the key if it is ever exposed (shared screen, logs, a leaked dotfile).
  Rotation is a console action plus updating the `ANTHROPIC_API_KEY` env var on
  the host; no code change is needed.

## Rate limiting and cost controls

All public endpoints (`/scan`, `/chat`) are guarded. `/health` is not, so uptime
checks stay cheap.

- **Per-IP, layered windows.** A burst window (default 5 requests / 60s) stops
  rapid-fire abuse, and a sustained window (default 20 / hour) caps longer-run
  use. Whichever trips first returns **429** with a `Retry-After` header. A
  blocked caller's hit is not recorded, so retries do not push them deeper.
- **Service-wide daily budget.** The Anthropic API has no per-request hard
  ceiling, so total upstream calls are capped per UTC day (default 1000). Once
  spent, endpoints return **503** with a `Retry-After` pointing at the next UTC
  midnight. The budget is charged only on an actual upstream call, so rejected
  input never consumes it.

All limits are tunable via environment variables (see `backend/.env.example`).

### Pausing the service

To take the API offline (incident response, maintenance, runaway cost), set
`LIFELENS_PAUSED` to `1` on the host. `/scan` and `/chat` then return 503 and
stop all upstream calls; `/health` stays up and reports `"paused": true`. Unset
it to resume. The flag is read per request, so no code change is needed to flip
it. This is a kill switch only; it does not stop direct traffic to the host if
the host itself stays running, so for a hard stop also suspend the service in
your platform dashboard.

> Scaling note: the limiter and budget are in-memory and per-process. That is
> correct on a single instance (the current Render deployment). If you scale to
> multiple instances, move this state to a shared store such as Redis so the
> limits hold across the fleet.

## Transport and headers

- HTTPS is terminated by the hosting platforms (Render for the API, Vercel for the
  frontend). The browser only ever talks to one origin; Vercel rewrites `/scan`
  and `/chat` to the API server-side.
- The **API** sends `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, a restrictive
  `Permissions-Policy`, and `Content-Security-Policy: default-src 'none'` on every
  response, including errors. The API only returns JSON, so it renders nothing.
- The **frontend** (`frontend/vercel.json`) sends HSTS with `preload`, a strict
  enforced CSP (`script-src 'self'`, no inline scripts), `X-Frame-Options: DENY`,
  nosniff, `Referrer-Policy`, and a `Permissions-Policy` that allows the camera
  (the PWA needs it) while denying microphone and geolocation. `'unsafe-inline'`
  is permitted for styles only; scripts remain locked to same-origin.

## Input validation

Requests are validated by Pydantic schemas (`backend/app/models.py`) before any
model call: an allowlist of image media types, base64 validated and size-capped at
5 MB, note and message length caps, and caps on message and image counts. Source
URLs returned by the model are only rendered as links when they match `https?://`,
so a `javascript:` URL cannot become a clickable link.
