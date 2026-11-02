"""Django-aware orchestration around the pure engines in engine.py."""
from collections import defaultdict
from datetime import timedelta
from io import BytesIO

from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.campus.models import (
    Classroom, ExamSchedule, Faculty, FacultyAvailability, Student, Subject,
    TeachingAssignment, TimetableEntry,
)

from . import engine
from .models import AuditLog, FacultyLeave, Notification, Substitution

EXAM_SESSIONS = [(1, 3), (5, 3)]  # morning (P1-3) and afternoon (P5-7)


# ------------------------------------------------------------------ audit + notifications
def log(actor, action, entity, entity_id="", **detail):
    AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action, entity=entity, entity_id=str(entity_id), detail=detail,
    )


def notify(users, title, message, kind="info"):
    seen, rows = set(), []
    for user in users:
        if user is None or user.pk in seen:
            continue
        seen.add(user.pk)
        rows.append(Notification(user=user, title=title[:120], message=message[:400], kind=kind))
    if rows:
        Notification.objects.bulk_create(rows)


def _name(faculty):
    return faculty.user.get_full_name() or faculty.user.username


def _section_students(section_id):
    return [row.user for row in Student.objects.filter(section_id=section_id).select_related("user")]


# ------------------------------------------------------------------ substitution workflow
def leave_dates(leave):
    day = leave.start_date
    while day <= leave.end_date:
        if day.weekday() < 5:
            yield day
        day += timedelta(days=1)


def affected_classes(leave):
    """Every recurring class the absent faculty member would miss, as (entry, date)."""
    dates = {day.weekday(): [] for day in leave_dates(leave)}
    for day in leave_dates(leave):
        dates[day.weekday()].append(day)
    entries = TimetableEntry.objects.filter(
        faculty=leave.faculty, weekday__in=list(dates)
    ).select_related("section__semester__course", "subject__course__department", "room", "faculty__user")
    pairs = [(entry, day) for entry in entries for day in dates[entry.weekday]]
    return sorted(pairs, key=lambda pair: (pair[1], pair[0].period))


def _allowed_by_availability(faculty_ids, weekday, period):
    allowed = set(faculty_ids)
    rows = defaultdict(list)
    for record in FacultyAvailability.objects.filter(faculty_id__in=faculty_ids):
        rows[record.faculty_id].append(record)
    for faculty_id, records in rows.items():
        explicit = {(r.weekday, r.period) for r in records if r.is_available}
        blocked = {(r.weekday, r.period) for r in records if not r.is_available}
        if (explicit and (weekday, period) not in explicit) or (weekday, period) in blocked:
            allowed.discard(faculty_id)
    return allowed


def rank_candidates(entry, day):
    subject = entry.subject
    same_subject = set(
        TeachingAssignment.objects.filter(subject=subject).exclude(faculty=entry.faculty).values_list("faculty_id", flat=True)
    )
    department = subject.course.department
    pool = Faculty.objects.filter(
        models.Q(id__in=same_subject) | models.Q(department=department)
    ).exclude(pk=entry.faculty_id).select_related("user")
    ids = [person.id for person in pool]
    if not ids:
        return []

    covered_away = set(Substitution.objects.filter(
        date=day, period=entry.period, status="assigned").values_list("original_faculty_id", flat=True))
    busy = set(TimetableEntry.objects.filter(weekday=day.weekday(), period=entry.period).values_list("faculty_id", flat=True)) - covered_away
    busy |= set(Substitution.objects.filter(date=day, period=entry.period, status="assigned").values_list("substitute_id", flat=True))
    on_leave = set(FacultyLeave.objects.filter(
        status="approved", start_date__lte=day, end_date__gte=day).values_list("faculty_id", flat=True))
    invigilating = {
        exam.invigilator_id for exam in ExamSchedule.objects.filter(date=day, invigilator__isnull=False)
        if exam.start_period <= entry.period < exam.start_period + exam.duration_periods
    }
    available = _allowed_by_availability(ids, day.weekday(), entry.period)
    loads = dict(TeachingAssignment.objects.filter(faculty_id__in=ids).values("faculty_id").annotate(
        total=Sum("periods_per_week")).values_list("faculty_id", "total"))
    cover_counts = dict(Substitution.objects.filter(substitute_id__in=ids, status="assigned").values("substitute_id").annotate(
        total=models.Count("id")).values_list("substitute_id", "total"))

    return engine.rank_substitutes([
        {
            "faculty_id": person.id, "name": _name(person), "employee_id": person.employee_id,
            "same_subject": person.id in same_subject, "same_department": person.department_id == department.id,
            "weekly_load": loads.get(person.id) or 0, "cover_count": cover_counts.get(person.id, 0),
            "busy": person.id in busy, "on_leave": person.id in on_leave,
            "unavailable": person.id not in available, "invigilating": person.id in invigilating,
        }
        for person in pool
    ])


def _create_cover(leave, entry, day, substitute):
    return Substitution.objects.create(
        leave=leave, timetable_entry=entry, section=entry.section, subject=entry.subject, room=entry.room,
        original_faculty=leave.faculty, substitute=substitute, date=day, period=entry.period,
    )


def _announce_cover(cover):
    text = f"{cover.subject.code} · {cover.section} on {cover.date:%a %d %b}, period {cover.period}, room {cover.room.code}"
    notify([cover.substitute.user], "Cover class assigned", f"You will take {text}.", "substitution")
    notify(_section_students(cover.section_id), "Class faculty changed",
           f"{text} will be taken by {_name(cover.substitute)}.", "substitution")


@transaction.atomic
def approve_leave(leave, actor):
    if leave.status != FacultyLeave.Status.PENDING:
        raise ValidationError({"detail": f"Only pending leave can be approved (this one is {leave.status})."})
    leave.status = FacultyLeave.Status.APPROVED
    leave.decided_by = actor
    leave.decided_at = timezone.now()
    leave.save(update_fields=["status", "decided_by", "decided_at"])

    assigned, unresolved = [], []
    for entry, day in affected_classes(leave):
        candidates = rank_candidates(entry, day)
        if not candidates:
            unresolved.append({"timetable_entry": entry.id, "date": day, "period": entry.period,
                               "subject": entry.subject.code, "section": str(entry.section)})
            continue
        best = Faculty.objects.select_related("user").get(pk=candidates[0]["faculty_id"])
        cover = _create_cover(leave, entry, day, best)
        _announce_cover(cover)
        assigned.append(cover)
    notify([leave.faculty.user], "Leave approved",
           f"Leave {leave.start_date} to {leave.end_date} approved. {len(assigned)} class(es) covered, {len(unresolved)} pending.", "leave")
    if unresolved:
        notify(_managers(leave.faculty.department.college_id), "Classes need cover", f"{len(unresolved)} class(es) for {_name(leave.faculty)} have no available substitute.", "alert")
    log(actor, "leave.approved", "FacultyLeave", leave.id, covered=len(assigned), unresolved=len(unresolved))
    return assigned, unresolved


def _managers(college_id):
    from apps.accounts.models import User
    return list(User.objects.filter(college_id=college_id, role__in=["super_admin", "college_admin", "hod"], is_active=True))


@transaction.atomic
def assign_manual(leave, entry_id, day, faculty, actor):
    if leave.status != FacultyLeave.Status.APPROVED:
        raise ValidationError({"detail": "Cover can only be assigned for approved leave."})
    entry = TimetableEntry.objects.filter(pk=entry_id, faculty=leave.faculty).select_related(
        "section", "subject__course__department", "room", "faculty__user").first()
    if not entry or day not in {d for d in leave_dates(leave)} or day.weekday() != entry.weekday:
        raise ValidationError({"detail": "That class is not affected by this leave."})
    Substitution.objects.filter(leave=leave, timetable_entry=entry, date=day, status="assigned").update(status="cancelled")
    allowed = {row["faculty_id"] for row in rank_candidates(entry, day)}
    if faculty.id not in allowed:
        raise ValidationError({"detail": f"{_name(faculty)} is busy, on leave or unavailable at that time."})
    cover = _create_cover(leave, entry, day, faculty)
    _announce_cover(cover)
    log(actor, "substitution.assigned", "Substitution", cover.id, substitute=_name(faculty))
    return cover


# ------------------------------------------------------------------ timetable move with live conflict check
def check_move(entry, weekday, period, room):
    problems = []
    if not 0 <= weekday <= 4 or not 1 <= period <= 8:
        return ["Choose a weekday between Monday and Friday and a period between 1 and 8."]
    slot = TimetableEntry.objects.filter(weekday=weekday, period=period).exclude(pk=entry.pk)
    if slot.filter(section=entry.section).exists():
        problems.append("The section already has a class in this period.")
    if slot.filter(faculty=entry.faculty).exists():
        problems.append(f"{_name(entry.faculty)} already teaches in this period.")
    if slot.filter(room=room).exists():
        problems.append(f"Room {room.code} is already booked in this period.")
    if not room.is_active:
        problems.append("The room is inactive.")
    if room.capacity < entry.section.capacity:
        problems.append(f"Room {room.code} seats {room.capacity}; the section has {entry.section.capacity} students.")
    if entry.subject.is_lab and not room.is_lab:
        problems.append("A laboratory subject needs a laboratory room.")
    if (weekday, period) not in _faculty_slots(entry.faculty_id):
        problems.append(f"{_name(entry.faculty)} is not available in this period.")
    return problems


def _faculty_slots(faculty_id):
    records = list(FacultyAvailability.objects.filter(faculty_id=faculty_id))
    explicit = {(r.weekday, r.period) for r in records if r.is_available}
    blocked = {(r.weekday, r.period) for r in records if not r.is_available}
    if explicit:
        return explicit - blocked
    return {(d, p) for d in range(5) for p in range(1, 9)} - blocked


@transaction.atomic
def apply_move(entry, weekday, period, room, actor):
    before = f"{entry.get_weekday_display()} P{entry.period} {entry.room.code}"
    entry.weekday, entry.period, entry.room = weekday, period, room
    entry.save(update_fields=["weekday", "period", "room"])
    after = f"{entry.get_weekday_display()} P{entry.period} {room.code}"
    message = f"{entry.subject.code} · {entry.section} moved from {before} to {after}."
    notify([entry.faculty.user], "Timetable changed", message, "timetable")
    notify(_section_students(entry.section_id), "Timetable changed", message, "timetable")
    log(actor, "timetable.moved", "TimetableEntry", entry.id, before=before, after=after)


# ------------------------------------------------------------------ automatic exam scheduling
def _session_periods(session):
    start, duration = session
    return set(range(start, start + duration))


@transaction.atomic
def auto_schedule_exams(semester, start, end, holidays, avoid_class_clashes, replace_existing, preview, actor):
    dates = engine.exam_dates(start, end, set(holidays))
    if not dates:
        raise ValidationError({"detail": "The exam window has no working days."})
    if len(dates) > 90:
        raise ValidationError({"detail": "Exam window is too long (maximum 90 working days)."})
    assignments = list(TeachingAssignment.objects.filter(section__semester=semester).select_related("section", "subject", "faculty__user"))
    if not assignments:
        raise ValidationError({"detail": "This semester has no teaching assignments to examine."})
    rooms = list(Classroom.objects.filter(college_id=semester.course.department.college_id, is_active=True))
    if not rooms:
        raise ValidationError({"detail": "Add at least one active room before scheduling exams."})

    tasks, teachers = {}, defaultdict(set)
    for item in assignments:
        key = f"{item.section_id}:{item.subject_id}"
        tasks[key] = engine.ExamTask(key, item.section_id, item.subject_id, item.section.capacity, item.subject.is_lab)
        teachers[key].add(item.faculty_id)

    if replace_existing:
        ExamSchedule.objects.filter(section__semester=semester).delete()
    section_ids = {task.section_id for task in tasks.values()}
    blocked_sections, blocked_rooms, busy_faculty = set(), set(), set()
    existing = ExamSchedule.objects.filter(date__range=(start, end))
    for exam in existing:
        for index, session in enumerate(EXAM_SESSIONS):
            if _session_periods(session) & set(range(exam.start_period, exam.start_period + exam.duration_periods)):
                blocked_rooms.add((exam.room_id, exam.date, index))
                if exam.section_id in section_ids:
                    blocked_sections.add((exam.section_id, exam.date, index))
                if exam.invigilator_id:
                    busy_faculty.add((exam.invigilator_id, exam.date, index))
    if avoid_class_clashes:
        class_slots = defaultdict(list)
        for row in TimetableEntry.objects.all():
            class_slots[row.weekday].append(row)
        for day in dates:
            for index, session in enumerate(EXAM_SESSIONS):
                periods = _session_periods(session)
                for row in class_slots[day.weekday()]:
                    if row.period in periods:
                        blocked_rooms.add((row.room_id, day, index))
                        busy_faculty.add((row.faculty_id, day, index))
                        if row.section_id in section_ids:
                            blocked_sections.add((row.section_id, day, index))
    for cover in Substitution.objects.filter(status="assigned", date__range=(start, end)):
        for index, session in enumerate(EXAM_SESSIONS):
            if cover.period in _session_periods(session):
                busy_faculty.add((cover.substitute_id, cover.date, index))

    plan = engine.schedule_exams(
        list(tasks.values()), [{"id": r.id, "capacity": r.capacity, "is_lab": r.is_lab} for r in rooms],
        dates, EXAM_SESSIONS, blocked_sections, blocked_rooms,
    )
    college_id = semester.course.department.college_id
    invigilator_pool = [
        {"id": f.id, "department_id": f.department_id}
        for f in Faculty.objects.filter(department__college_id=college_id)
    ]
    on_leave = {(l.faculty_id, l.start_date, l.end_date) for l in FacultyLeave.objects.filter(status="approved")}
    for faculty_id, left, right in on_leave:
        for day in dates:
            if left <= day <= right:
                busy_faculty.update((faculty_id, day, index) for index in range(len(EXAM_SESSIONS)))
    invigilators = engine.assign_invigilators(
        [(task.key, day, index) for task, day, index, _ in plan.assignments], invigilator_pool,
        busy_faculty, {key: teachers[key] for key in tasks},
    )

    room_by_id = {room.id: room for room in rooms}
    subjects = {s.id: s for s in Subject.objects.filter(id__in={t.subject_id for t in tasks.values()})}
    sections = {a.section_id: a.section for a in assignments}
    faculty_by_id = {f.id: f for f in Faculty.objects.select_related("user")}
    rows, created = [], []
    for task, day, index, room_id in plan.assignments:
        start_period, duration = EXAM_SESSIONS[index]
        invigilator_id = invigilators.get(task.key)
        rows.append({
            "section": str(sections[task.section_id]), "subject": subjects[task.subject_id].code, "date": day,
            "session": "Morning" if index == 0 else "Afternoon", "start_period": start_period, "duration_periods": duration,
            "room": room_by_id[room_id].code,
            "invigilator": _name(faculty_by_id[invigilator_id]) if invigilator_id else None,
        })
        created.append(ExamSchedule(
            section_id=task.section_id, subject_id=task.subject_id, room_id=room_id, invigilator_id=invigilator_id,
            date=day, start_period=start_period, duration_periods=duration,
        ))
    unscheduled = [{"subject": subjects[t.subject_id].code, "section": str(sections[t.section_id]), "reason": why} for t, why in plan.unscheduled]
    if preview:
        transaction.set_rollback(True)
    else:
        ExamSchedule.objects.bulk_create(created)
        notify([row.user for row in Student.objects.filter(section_id__in=section_ids).select_related("user")],
               "Exam timetable published", f"Exams are scheduled between {start:%d %b} and {end:%d %b}.", "exam")
        log(actor, "exams.auto_scheduled", "Semester", semester.id, scheduled=len(created), unscheduled=len(unscheduled))
    return {"preview": preview, "scheduled": rows, "unscheduled": unscheduled,
            "stats": {"exams": len(rows), "unscheduled": len(unscheduled), "days_used": len({r["date"] for r in rows}),
                      "without_invigilator": sum(1 for r in rows if not r["invigilator"])}}


# ------------------------------------------------------------------ analytics
def analytics(semester=None, weekly_limit=18, daily_limit=5, college_id=None):
    if not college_id:
        return {"summary": {}, "rooms": [], "faculty": [], "heatmap": [], "days": engine.DAY_NAMES, "conflicts": [], "insights": []}
    entries_qs = TimetableEntry.objects.filter(section__semester__course__department__college_id=college_id)
    if semester:
        entries_qs = entries_qs.filter(section__semester=semester)
    entries = list(entries_qs.values("room_id", "faculty_id", "section_id", "weekday", "period"))
    rooms = [{"id": r.id, "code": r.code, "name": r.name, "capacity": r.capacity, "is_lab": r.is_lab}
             for r in Classroom.objects.filter(college_id=college_id, is_active=True)]
    faculty = [{"id": f.id, "name": _name(f)} for f in Faculty.objects.filter(department__college_id=college_id).select_related("user")]
    utilization = engine.room_utilization(rooms, entries)
    load = engine.faculty_load(faculty, entries, weekly_limit, daily_limit)
    heat = engine.demand_heatmap(len(rooms), entries)
    conflicts = engine.detect_conflicts(entries)
    today = timezone.localdate()
    pending = FacultyLeave.objects.filter(faculty__department__college_id=college_id, status="pending").count()
    covered = Substitution.objects.filter(section__semester__course__department__college_id=college_id, status="assigned", date__gte=today).count()
    unresolved = _unresolved_count(college_id)
    total_slots = len(rooms) * 40
    used = len(entries)
    return {
        "summary": {
            "rooms": len(rooms), "scheduled_classes": used,
            "overall_utilization": round(used / total_slots * 100, 1) if total_slots else 0,
            "idle_room_slots": max(total_slots - used, 0), "conflicts": len(conflicts),
            "overloaded_faculty": sum(1 for p in load if p["overloaded"]),
            "pending_leaves": pending, "upcoming_cover": covered, "unresolved_cover": unresolved,
            "exams_scheduled": ExamSchedule.objects.filter(section__semester__course__department__college_id=college_id).count(),
        },
        "rooms": utilization, "faculty": load[:15], "heatmap": heat,
        "days": engine.DAY_NAMES, "conflicts": conflicts,
        "insights": engine.build_insights(utilization, load, heat, conflicts, unresolved),
    }


def _unresolved_count(college_id):
    count = 0
    for leave in FacultyLeave.objects.filter(faculty__department__college_id=college_id, status="approved", end_date__gte=timezone.localdate()):
        wanted = len(affected_classes(leave))
        done = Substitution.objects.filter(leave=leave, status="assigned").count()
        count += max(wanted - done, 0)
    return count


# ------------------------------------------------------------------ export
def timetable_workbook(scope, object_id):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    queryset = TimetableEntry.objects.select_related("section", "subject", "faculty__user", "room")
    field = {"section": "section_id", "faculty": "faculty_id", "room": "room_id"}[scope]
    entries = queryset.filter(**{field: object_id})
    grid = defaultdict(list)
    for entry in entries:
        label = {"section": f"{entry.subject.code}\n{_name(entry.faculty)}\n{entry.room.code}",
                 "faculty": f"{entry.subject.code}\n{entry.section}\n{entry.room.code}",
                 "room": f"{entry.subject.code}\n{entry.section}\n{_name(entry.faculty)}"}[scope]
        grid[(entry.weekday, entry.period)].append(label)
    book = Workbook()
    sheet = book.active
    sheet.title = "Timetable"
    sheet.append(["Period"] + engine.DAY_NAMES)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1D4ED8")
        cell.alignment = Alignment(horizontal="center")
    for period in range(1, 9):
        sheet.append([f"P{period}"] + ["\n---\n".join(grid.get((day, period), [])) or "-" for day in range(5)])
        sheet.row_dimensions[period + 1].height = 62
        for cell in sheet[period + 1]:
            cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    sheet.column_dimensions["A"].width = 9
    for column in "BCDEF":
        sheet.column_dimensions[column].width = 24
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()
