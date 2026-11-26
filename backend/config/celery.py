"""Celery application for CampusMind AI.

Imported from ``config/__init__.py`` so the app is initialised whenever Django
starts. Tasks live next to the code they operate on (see
``apps.campus.jobs``).
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("campusmind")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")