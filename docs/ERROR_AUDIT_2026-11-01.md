# CampusMind AI — Error Audit and Fixes (2026-11-01)

## Fixes applied in this pass

1. **PDF uploads failed at creation:** a duplicate method definition had replaced the upload handler that set `uploaded_by`. The final handler now sets `uploaded_by=request.user`, validates related objects against the current college, and converts database integrity errors into an API validation response. This applies to subject notes and previous-year question papers.
2. **Faculty leave request crashed:** the leave-create endpoint called `_managers()` without its required `college_id`. It now calls `_managers(user.college_id)`, so notifications are sent only to managers in the requesting faculty member's college.
3. **Operations test tenant setup:** the demo admin in operations tests is now assigned to the seeded `DEMO` college. A regression test checks that leave-request notifications do not reach another college's managers.
4. **Shared tenant validation helper:** `require_same_college` now resolves tenant ownership through parent relationships (for example, a Student's Department) instead of assuming every model has a direct `college_id` field.
5. **College registration code validation:** college codes must contain at least one alphanumeric character, preventing punctuation-only codes from producing empty slugs.
6. **Documentation:** removed an outdated sentence claiming the current code was single-tenant.

## Checks completed

- `python -m compileall -q backend manage.py` — passed.
- Python AST parse of backend modules — passed; no duplicate class methods remain.
- Source ZIP integrity — checked after packaging.

## Checks not completed

- Django system checks, migration execution, and Django tests were not run: Django and the project dependencies are not installed, and package downloads failed because network/DNS is unavailable in this environment.
- Frontend production build was not run: `frontend/node_modules` is absent and package installation could not be completed.
- No PostgreSQL instance or live SMTP/AI/object-storage credentials were available.

## Run these checks locally before deployment

```bash
pip install -r requirements.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
python manage.py test apps.accounts apps.operations
python manage.py check --deploy
```

In another terminal:

```bash
cd frontend
npm ci
npm run build
```

Take a database backup before applying migrations to an existing installation. Do not treat this archive as production-certified until the commands above and a two-college read/write isolation test pass against a staging PostgreSQL database.

## Additional fixes from the full source review

7. **Cross-college exam invigilator pool:** automatic exam scheduling previously offered every college's faculty to the invigilator assignment engine. It now limits the pool to faculty in the semester's college. A database-backed regression test was added.
8. **Student section validation:** section validation compared raw request strings from HTML/API clients with integer model fields, which could reject valid section assignments. It now validates the converted serializer values and handles create/update consistently. A regression test using string primary keys was added.
9. **Vercel API base URL:** production frontend builds without an explicit API host previously fell back to `localhost:8000`. They now use same-origin `/api`; Vite development continues to use `http://localhost:8000/api` unless overridden.
10. **Vercel allowed hosts:** Django now accepts the deployment hostnames exposed through `VERCEL_URL` and `VERCEL_PROJECT_PRODUCTION_URL`.

## Additional checks

- `PYTHONPATH=backend python -m unittest apps.operations.tests_engine -v` — 7 pure scheduling/analytics engine tests passed.
- Python AST audit — passed; no duplicate class methods found.
- Migration dependency reference audit — passed.
- Frontend relative-import audit — passed; no missing relative imports found.

The new database-backed regression tests were added but could not be executed in this environment because Django and its dependencies are not installed. `npm ci` timed out before installing Vite, so the frontend production build remains unverified.
