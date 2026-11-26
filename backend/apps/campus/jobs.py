"""Background execution for expensive timetable optimisation runs.

The OR-Tools solver can block for seconds or minutes on real college data. This
module queues a :class:`~apps.campus.models.TimetableJob` and runs the solver on
a Celery worker so the HTTP request returns immediately with a job id that the
UI can poll.

With ``TIMETABLE_ASYNC_EAGER`` enabled (tests, tiny installs) or no broker
configured, the solve runs inline so callers observe the final state. The job
model and the :func:`run_timetable_job` entry point stay the same, so callers
and tests do not need to know which backend is in use.
"""

from celery import shared_task
from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from .models import TimetableEntry, TimetableJob
from .timetable_optimizer import TimetableOptimizationError, generate_timetable


@shared_task(name="campus.run_timetable_job")
def run_timetable_job_task(self, job_id):
    """Celery entry point: own the worker process DB connection lifecycle."""

    close_old_connections()
    try:
        return run_timetable_job(job_id)
    finally:
        close_old_connections()


def enqueue_timetable_job(semester, user):
    """Create a job for ``semester`` and start it."""

    job = TimetableJob.objects.create(
        college_id=user.college_id,
        semester=semester,
        created_by=user,
    )
    if getattr(settings, "TIMETABLE_ASYNC_EAGER", False) or getattr(
        settings, "CELERY_TASK_ALWAYS_EAGER", False
    ):
        run_timetable_job(job.pk)
        job.refresh_from_db()
    else:
        transaction.on_commit(
            lambda: run_timetable_job_task.delay(job.pk)
        )
    return job


def run_timetable_job(job_id):
    """Execute one job, recording success or the failure reason."""

    try:
        job = TimetableJob.objects.select_related(
            "semester__course__department"
        ).get(pk=job_id)
    except TimetableJob.DoesNotExist:
        return None

    job.status = "running"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    try:
        entries = generate_timetable(job.semester)
        with transaction.atomic():
            TimetableEntry.objects.filter(section__semester=job.semester).delete()
            TimetableEntry.objects.bulk_create(entries)
        job.status = "succeeded"
        job.entry_count = len(entries)
        job.error = ""
    except TimetableOptimizationError as error:
        job.status = "failed"
        job.error = str(error)
    except Exception as error:  # pragma: no cover - defensive catch-all
        job.status = "failed"
        job.error = f"Unexpected failure: {error}"
    finally:
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "entry_count", "error", "finished_at"])
    return job
