# CampusMind AI

An actively evolving campus management platform. This initial foundation implements the Django/DRF project, PostgreSQL-ready configuration, JWT authentication, role-aware department management, core campus records, an API-backed responsive dashboard, and OpenAPI docs. The broader ERP and AI features in the product brief are not yet implemented; see **Roadmap** below.

## Requirements

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or Docker Desktop)

## Local setup

From the project root in VS Code:

1. Copy `.env.example` to `.env`. Set a long random `DJANGO_SECRET_KEY` and a private `POSTGRES_PASSWORD`.
2. Start PostgreSQL, for example with `docker compose up -d db`.
3. Configure and install the backend:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. Django reads the project-root `.env` automatically. Set `POSTGRES_HOST=localhost` in it to use the Docker database; leave `POSTGRES_HOST` unset to use local SQLite.

5. Apply the included database migrations and create an administrator:

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   ```

   The Django admin user is a secure bootstrap route; assign campus roles to additional users through Django admin. Do not use a shared demo credential in a deployed environment.

6. Start the API:

   ```powershell
   python manage.py runserver
   ```

7. In a second terminal:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Open the Vite URL (normally `http://localhost:5173`) and sign in using a Django user account.

## API

- JWT sign-in: `POST /api/auth/token/` with `{"username":"…","password":"…"}`
- Refresh: `POST /api/auth/token/refresh/`
- Current profile: `GET /api/auth/me/`
- Dashboard data: `GET /api/dashboard/summary/`
- Student workspace: `GET /api/student/portal/` returns only the signed-in student's profile, attendance history and rate, section subjects, weekly timetable, and upcoming exams.
- Subject notes: `/api/subject-notes/` lets faculty upload PDF notes for assigned subjects; students can list and download notes for their own section's assigned subjects. Faculty can list, upload, download, and delete their subject notes. Local uploads are stored under `backend/media/subject-notes/`.
- Subject notes subject selector: `GET /api/subject-notes/subjects/`; download: `GET /api/subject-notes/{id}/download/`. Uploads are restricted to PDF files up to 20 MB.
- Previous-year question papers: `/api/question-papers/` lets faculty upload past exam PDFs for assigned subjects with an exam year; students can list and download papers for subjects assigned to their own section. Uploads are restricted to PDF files up to 20 MB, and future exam years are rejected. Local uploads are stored under `backend/media/question-papers/`.
- Question paper subject selector: `GET /api/question-papers/subjects/`; download: `GET /api/question-papers/{id}/download/`.
- Department CRUD: `/api/departments/`
- Student and faculty CRUD (creates a password-hashed account with each profile): `/api/students/`, `/api/faculty/`
- Academic setup CRUD: `/api/academic-years/`, `/api/courses/`, `/api/semesters/`, `/api/sections/`, `/api/subjects/`
- Attendance CRUD: `/api/attendance/` (daily duplicate attendance is prevented)
- Room/lab inventory: `/api/classrooms/`
- Faculty subject/section load: `/api/teaching-assignments/`
- Faculty weekly time constraints: `/api/faculty-availability/`
- Exam schedules with room, section, invigilator, availability, and class-overlap checks: `/api/exam-schedules/`
- Conflict-free weekly timetable: `POST /api/timetable/generate/` with `{"semester": 1}`, then read `/api/timetable/entries/?section__semester=1`
- Subject-qualified substitution suggestions: `GET /api/timetable/entries/{entry_id}/substitutions/`
- Module lists support pagination, search, ordering, and API filters.
- Authenticated campus administrators/HODs can manage records; faculty can read records; other roles are denied access to these campus-management endpoints.
- Swagger UI: `/api/docs/`; OpenAPI schema: `/api/schema/`
- Django admin: `/admin/`

## Render deployment

The root `render.yaml` defines a React static site, Django API, and PostgreSQL database. The frontend and backend use separate Render services; the API host is passed to the frontend at build time, and Django allows requests from the deployed frontend origin.

To deploy:

1. Keep `.env` out of source control; it is ignored by `.gitignore`. The Render Blueprint generates a separate Django secret key.
2. Push the project to a GitHub repository you control.
3. In Render, create a **Blueprint** and connect that repository. Review the services and apply the Blueprint.
4. Once the deploy finishes, open the static site's Render URL. The API health check is at `/healthz/`.
5. Create a Django superuser in the API service's Render Shell with `python manage.py createsuperuser`. Then assign its campus role using `python manage.py shell -c "from apps.accounts.models import User; User.objects.filter(username='YOUR_USERNAME', is_superuser=True).update(role='super_admin')"`; replace `YOUR_USERNAME` with the account just created. Use Django Admin to create or manage other accounts.

This Blueprint intentionally uses Render's free plans at the user's request. Free API services can sleep when idle and take time to wake. Free PostgreSQL expires 30 days after creation; if it is not upgraded within the additional 14-day grace period, Render deletes the database and its data. The API filesystem is ephemeral, so uploaded subject notes and question papers can disappear after a restart, sleep, or deploy. Do not use this configuration for important or production records; upgrade the database and use persistent or object storage before relying on it.

The Blueprint is prepared locally but has not been deployed. Render requires this project to be pushed to a Git provider and connected to a Render account before it can create the services. Local users, passwords, database records, and uploaded files are not copied into the cloud database.

## Tests

```powershell
python manage.py test apps.accounts
```

The API tests cover JWT login/profile, authentication and role permissions, department CRUD, student/faculty account creation and password hashing, student-only portal data, subject-note and past-paper access, PDF validation, year validation, section privacy, academic relationships, attendance duplication, academic-year validation, dashboard metrics, OR-Tools timetable generation against constrained availability, laboratory capacity errors, substitution qualification/availability, and overlapping exam prevention.

## Scheduling setup and constraints

1. Create a department, faculty, academic year, course, semester, section, and subjects.
2. Register active classrooms and laboratories with real seat capacity.
3. Add teaching assignments for each section/subject/faculty and set periods per week. Subject, section semester, and faculty department must match.
4. Optionally add faculty availability rows. If no period is marked available, a faculty member is flexible except for rows marked unavailable. If one or more periods are marked available, only marked periods are schedulable. Explicit unavailable rows always block a slot.
5. Open **AI smart timetable**, select a semester, and generate. OR-Tools CP-SAT assigns every requested weekly class to a suitable weekday, period, and room; it avoids section/faculty/room collisions, respects faculty availability and lab/capacity requirements, preserves other semesters' schedules, and prefers earlier periods and tighter-fitting rooms.
6. Use **Substitutes** on a class to see subject-qualified faculty who are free at that time, ordered by assigned teaching load. The feature suggests a candidate; it does not silently change a published schedule.
7. Create exams under **Exam schedules**. The API rejects overlapping room, section, or invigilator exams; checks room/lab capacity and faculty availability; and rejects exam slots that collide with recurring class entries.

The current timetable model is Monday–Friday, eight periods per day. Exam period lengths use that same eight-period day. This is a working constraint-based scheduler, not a generative AI model; its optimized constraints and persisted timetable are inspectable records.

## Roadmap / current scope

The product request covers a multi-module ERP and production deployment, which cannot be represented honestly as complete by these phases alone. Implemented now: custom role-bearing accounts, JWT login/refresh, role-checked CRUD APIs and responsive screens for departments, student/faculty profiles and accounts, academic years/courses/semesters/sections/subjects, daily attendance recording/correction, rooms and laboratories, weekly faculty availability, teaching assignments and workloads, a persisted OR-Tools timetable optimizer, subject-qualified faculty substitute suggestions, exam schedule CRUD and conflict checking, database-backed dashboard metrics, API schema/docs, PostgreSQL/Docker database configuration, Render deployment configuration (not yet deployed), and API tests.

Not yet implemented: fees, library, hostel, transport, placements, assignments, notices and events as complete ERP workflows; fine-grained department-level object policies; a full immutable audit trail for every data mutation; a grounded academic assistant; frontend automated tests; configurable school-specific time periods; and production deployment hardening. Multi-college tenant provisioning and application-level tenant scoping are now implemented, but still require staging migration and cross-tenant verification.

## Problem statement coverage (intelligent academic scheduling)

| Requirement | Where it lives |
| --- | --- |
| Timetables with faculty availability, room and lab capacity | CP-SAT optimizer (`apps/campus/timetable_optimizer.py`), now with a soft per-teacher daily load rule |
| Classroom / laboratory allocation and utilisation | `GET /api/analytics/overview/` - per-room utilisation, demand heatmap, idle slots, rule-based insights |
| Faculty absence and substitution | `/api/leaves/` request -> approve -> automatic, conflict-free substitute per class (same-subject first, lowest load), manual override via `assign-cover`, notifications to substitute and students |
| Examination scheduling | `POST /api/exams/auto-schedule/` - preview then publish; no room/section/invigilator clashes, capacity and lab rules, rest days between a section's exams, balanced invigilators |
| Reduce conflicts | `POST /api/timetable/entries/{id}/move/` live conflict check (`dry_run`) before moving a class |
| Coordination | In-app notifications (`/api/notifications/`), audit trail (`/api/audit-logs/`), Excel export (`/api/exports/timetable/?scope=section|faculty|room&id=`) |

UI: **Operations center** in the sidebar (analytics, leave and substitutes, exam planner, audit trail) and a notification bell in the header.

Demo data: `python manage.py seed_demo` builds a small college with a generated timetable (accounts use a random password printed once, or pass `--password`).

Tests: `python -m unittest apps.operations.tests_engine` (engine, no database) and `python manage.py test apps.operations apps.accounts` (API).

### Current operating limits
Multi-college workspaces are implemented with application-level tenant scoping; staging migration and cross-tenant verification are still required before public production use. Scheduling currently uses Monday-Friday with eight periods and exam sessions fixed at P1-3 / P5-7. Notifications are in-app only (no email/SMS), and frontend automated tests are not yet included. The OR-Tools solver is large and long-running: on Vercel it may exceed function size/time limits, so host the API on Render/Railway/Fly (or move the solver to a background worker) and keep Vercel for the React frontend; use hosted PostgreSQL and persistent object storage for uploaded files.

## Security notes

- Passwords use Django's configured password hashers; no plaintext password field is exposed through the API.
- JWT access tokens are short-lived. The current browser client keeps tokens in `sessionStorage`; production deployments should evaluate an HttpOnly-cookie design, HTTPS, CSP, secure headers, secret rotation, rate limiting, and explicit deployment origins.
- The Render Blueprint sets `DJANGO_DEBUG=false`, generates a secret key, restricts CORS to the deployed frontend host, and enables HTTPS-related protections.
- The default development secret is unsafe and must never be used in a deployed environment.

## Multi-college SaaS tenancy

CampusMind now provisions one isolated workspace per college. Register a college at `POST /api/auth/register-college/` (or use the `/register-college` frontend page). The endpoint creates the College tenant and its first `college_admin` account in one database transaction. College codes and slugs are unique.

### Tenant migration

Run migrations before starting the app:

```bash
python manage.py migrate
```

Migration `accounts.0002_college_tenant` creates the College table and assigns existing accounts to the `LEGACY` workspace. Migration `campus.0008_college_scoping` assigns existing departments, academic years and classrooms to that same workspace. Existing rows are preserved; they are not copied or deleted. New workspaces start with no access to legacy records.

Campus API querysets are filtered using the authenticated user's `college_id`; related-object serializer querysets and write validation are also tenant-scoped. Operations, timetable exports, analytics and the optimizer use the same tenant boundary. Users without an assigned college receive no tenant data. The `super_admin` role remains scoped to its assigned college; it is not a cross-tenant bypass.

### Production notes

- Back up PostgreSQL before applying migrations and verify the restore procedure.
- Create a separate college administrator for each institution; never share accounts across colleges.
- Keep `DJANGO_DEBUG=false`, configure allowed hosts/CORS/CSRF, and use PostgreSQL in production.
- Apply database-level row-level security if your hosting/database policy requires defense-in-depth beyond Django's application-level tenant filters.
- Run the full test suite and a two-tenant isolation smoke test before opening registration publicly.
