# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems. Report them privately
to the repository maintainer (or use GitHub's **Report a vulnerability**
feature) with:

- the affected endpoint or component,
- reproduction steps,
- the impact you believe it has,
- any suggested fix.

You will receive an acknowledgement as soon as possible. Please allow time for
a fix before publishing details.

## Supported versions

Only the latest commit on the default branch is supported.

## Deployment checklist

Before exposing CampusMind AI to real institutional data:

- Set `DJANGO_DEBUG=false` and a unique `DJANGO_SECRET_KEY` of at least 50
  random characters. The project refuses to start otherwise.
- Serve the API over HTTPS. Keep `DJANGO_SECURE_SSL_REDIRECT=true` when a
  proxy terminates TLS.
- Set `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`,
  `CSRF_TRUSTED_ORIGINS`, and `PUBLIC_FRONTEND_HOST`.
- Configure `REDIS_URL` so login, registration, reset, and AI throttles are
  shared across workers instead of per-process.
- Configure PostgreSQL with backups, persistent object storage for PDFs, and
  SMTP (or another provider) plus `PASSWORD_RESET_URL`.
- Keep the audit log append-only: do not grant admin users write access to
  `AuditLog`.
- Run `python manage.py check --deploy` and the test suite in CI.
- Rotate any bootstrap passwords created with `create_default_admin --force`.

## Known limitations

- The browser client stores JWTs in `sessionStorage`; an XSS would expose them.
  Add a strict Content-Security-Policy and consider HttpOnly cookie auth.
- Throttling falls back to per-process memory when `REDIS_URL` is unset.
- The free Render plan uses an expiring database and ephemeral disk.
- The OR-Tools solver is CPU- and memory-heavy; run it on a worker or a
  properly sized service, not a short-lived serverless function.
