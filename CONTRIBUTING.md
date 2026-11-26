# Contributing

## Setup

1. Copy `.env.example` to `.env`, set `DJANGO_SECRET_KEY`, and keep
   `DJANGO_DEBUG=true` for local work.
2. Start PostgreSQL: `docker compose up -d db` (or use SQLite by leaving
   `POSTGRES_HOST` unset).
3. Install and migrate:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements-dev.txt
   python manage.py migrate
   ```

4. Run the API: `python manage.py runserver`
5. Run the frontend: `cd frontend && npm ci && npm run dev`

## Checks before opening a pull request

```bash
ruff check backend api manage.py
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.accounts apps.operations
cd frontend && npm run build && npm audit --audit-level=high
```

CI runs the same checks against PostgreSQL on every push and pull request.

## Code conventions

- Keep the pure scheduling and analytics logic in
  `backend/apps/operations/engine.py` free of Django imports so it stays
  unit-testable.
- Scope every tenant-owned queryset with `apps.accounts.tenancy.scope_queryset`
  and add a two-college regression test for new endpoints.
- Validate related records against the requesting user's college; never trust
  primary keys from the client.
- Prefer normal imports over dynamic `__import__` calls.
- Add a migration for every model change and keep `makemigrations --check`
  clean.
- Do not log secrets, tokens, passwords, or student PII.

## Security

See [SECURITY.md](SECURITY.md). Do not report vulnerabilities in public issues.
