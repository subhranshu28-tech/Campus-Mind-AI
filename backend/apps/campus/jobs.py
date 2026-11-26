"""Background execution for expensive timetable optimisation runs.

The OR-Tools solver can block for seconds or minutes on real college data. This
module queues a :class:`~apps.campus.models.TimetableJob` and runs the solver
on a daemon thread so the HTTP request returns immediately with a job id that
the UI can poll.

For deployments that need durable queues, set ``TIMETABLE_ASYNC_EAGER=false``
and swap :func:`_start_worker` for a Celery/RQ task; the job model and the
``run_timetable_job`` entry point stay the same.
"""

import threading

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from .models import TimetableEntry, TimetableJob
from .timetable_optimizer import TimetableOptimizationError, generate_timetable


def enqueue_timetable_job(semester, user):
    """Create a job for ``semester`` and start it.

    With ``TIMETABLE_ASYNC_EAGER`` enabled (tests, tiny installs) the solve runs
    inline so callers observe the final state. Otherwise it is handed to a
    background thread once the creating transaction commits.
    """

    job = TimetableJob.objects.create(
        college_id=user.college_id,
        semester=semester,
        created_by=user,
    )
    if getattr(settings, "TIMETABLE_ASYNC_EAGER", False):
        run_timetable_job(job.pk)
        job.refresh_from_db()
    else:
        transaction.on_commit(lambda: _start_worker(job.pk))
    return job


def _start_worker(job_id):
    worker = threading.Thread(
        target=run_timetable_job,
        args=(job_id,),
        name=f"timetable-job-{job_id}",
        daemon=True,
    )
    worker.start()
    return worker


def run_timetable_job(job_id):
    """Execute one job, recording success or the failure reason."""

    close_old_connections()
    try:
        job = TimetableJob.objects.select_related(
            "semester__course__department"
        ).get(pk=job_id)
    except TimetableJob.DoesNotExist:
        close_old_connections()
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
        close_old_connections()
    return job
