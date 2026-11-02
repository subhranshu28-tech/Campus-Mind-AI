import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("campus", "0007_previousyearquestionpaper"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FacultyLeave",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("reason", models.CharField(blank=True, max_length=240)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled")], default="pending", max_length=12)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("decided_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("faculty", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="leaves", to="campus.faculty")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="facultyleave",
            constraint=models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="leave_end_not_before_start"),
        ),
        migrations.CreateModel(
            name="Substitution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("period", models.PositiveSmallIntegerField()),
                ("status", models.CharField(choices=[("assigned", "Assigned"), ("cancelled", "Cancelled")], default="assigned", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("leave", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="substitutions", to="operations.facultyleave")),
                ("original_faculty", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cover_given_up", to="campus.faculty")),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="campus.classroom")),
                ("section", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="campus.section")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="campus.subject")),
                ("substitute", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cover_assignments", to="campus.faculty")),
                ("timetable_entry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="campus.timetableentry")),
            ],
            options={"ordering": ["date", "period"]},
        ),
        migrations.AddIndex(
            model_name="substitution",
            index=models.Index(fields=["date", "period"], name="ops_sub_date_period_idx"),
        ),
        migrations.AddConstraint(
            model_name="substitution",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "assigned")), fields=("substitute", "date", "period"), name="unique_active_substitute_slot"),
        ),
        migrations.AddConstraint(
            model_name="substitution",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "assigned")), fields=("section", "date", "period"), name="unique_active_cover_section_slot"),
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("message", models.CharField(max_length=400)),
                ("kind", models.CharField(default="info", max_length=30)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["user", "is_read"], name="ops_notif_user_read_idx"),
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=60)),
                ("entity", models.CharField(max_length=60)),
                ("entity_id", models.CharField(blank=True, max_length=40)),
                ("detail", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
