from collections import defaultdict
from dataclasses import dataclass

from ortools.sat.python import cp_model

from .models import (
    Classroom,
    FacultyAvailability,
    TeachingAssignment,
    TimetableEntry,
)


@dataclass
class TimetableOptimizationError(Exception):
    detail: str

    def __str__(self):
        return self.detail


WEEKDAYS = range(5)
PERIODS = range(1, 9)
MAX_FACULTY_PERIODS_PER_DAY = 4
OVERLOAD_PENALTY = 800


def _faculty_open_slots(assignments):
    faculty_ids = {assignment.faculty_id for assignment in assignments}
    availability = FacultyAvailability.objects.filter(faculty_id__in=faculty_ids)
    records_by_faculty = defaultdict(list)
    for record in availability:
        records_by_faculty[record.faculty_id].append(record)

    allowed = {}
    for faculty_id, records in records_by_faculty.items():
        explicit = {(record.weekday, record.period) for record in records if record.is_available}
        blocked = {(record.weekday, record.period) for record in records if not record.is_available}
        if explicit:
            allowed[faculty_id] = explicit
        else:
            allowed[faculty_id] = {
                (weekday, period)
                for weekday in WEEKDAYS
                for period in PERIODS
                if (weekday, period) not in blocked
            }
    return allowed


def generate_timetable(semester):
    assignments = list(
        TeachingAssignment.objects.filter(section__semester=semester)
        .select_related("section__semester", "subject", "faculty__user")
        .order_by("section_id", "subject_id")
    )
    if not assignments:
        raise TimetableOptimizationError(
            "No teaching assignments exist for this semester. Assign a subject, faculty member, and weekly periods first."
        )

    rooms = list(Classroom.objects.filter(college_id=semester.course.department.college_id, is_active=True).order_by("code"))
    if not rooms:
        raise TimetableOptimizationError("Add at least one active classroom or laboratory before generating a timetable.")

    allowed_slots = _faculty_open_slots(assignments)
    existing_entries = TimetableEntry.objects.exclude(section__semester=semester).values(
        "faculty_id", "room_id", "weekday", "period"
    )
    reserved_faculty = set()
    reserved_rooms = set()
    for entry in existing_entries:
        reserved_faculty.add((entry["faculty_id"], entry["weekday"], entry["period"]))
        reserved_rooms.add((entry["room_id"], entry["weekday"], entry["period"]))

    model = cp_model.CpModel()
    room_vars = defaultdict(list)
    faculty_vars = defaultdict(list)
    section_vars = defaultdict(list)
    assignment_day_vars = defaultdict(list)
    faculty_day_vars = defaultdict(list)
    lessons = []
    objective = []

    for assignment in assignments:
        eligible_rooms = [
            room for room in rooms
            if room.capacity >= assignment.section.capacity
            and (not assignment.subject.is_lab or room.is_lab)
        ]
        if not eligible_rooms:
            room_kind = "laboratory" if assignment.subject.is_lab else "classroom"
            raise TimetableOptimizationError(
                f"No active {room_kind} has enough capacity for section {assignment.section} ({assignment.section.capacity} seats)."
            )

        faculty_slots = allowed_slots.get(
            assignment.faculty_id,
            {(weekday, period) for weekday in WEEKDAYS for period in PERIODS},
        )
        for lesson_number in range(assignment.periods_per_week):
            lesson_vars = []
            for weekday in WEEKDAYS:
                for period in PERIODS:
                    faculty_slot = (assignment.faculty_id, weekday, period)
                    if (weekday, period) not in faculty_slots or faculty_slot in reserved_faculty:
                        continue
                    for room in eligible_rooms:
                        room_slot = (room.id, weekday, period)
                        if room_slot in reserved_rooms:
                            continue
                        key = (
                            assignment.id, lesson_number, weekday, period, room.id,
                        )
                        variable = model.new_bool_var(
                            f"lesson_{assignment.id}_{lesson_number}_{weekday}_{period}_{room.id}"
                        )
                        lessons.append((variable, assignment, weekday, period, room))
                        lesson_vars.append(variable)
                        room_vars[(room.id, weekday, period)].append(variable)
                        faculty_vars[(assignment.faculty_id, weekday, period)].append(variable)
                        faculty_day_vars[(assignment.faculty_id, weekday)].append(variable)
                        section_vars[(assignment.section_id, weekday, period)].append(variable)
                        if assignment.periods_per_week <= len(WEEKDAYS):
                            assignment_day_vars[(assignment.id, weekday)].append(variable)
                        room_fit_penalty = room.capacity - assignment.section.capacity
                        objective.append((period * 100 + weekday + room_fit_penalty * 2, variable))
            if not lesson_vars:
                raise TimetableOptimizationError(
                    f"No available period and suitable room can be found for {assignment.subject} with {assignment.faculty}."
                )
            model.add_exactly_one(lesson_vars)

    for conflict_vars in (*room_vars.values(), *faculty_vars.values(), *section_vars.values()):
        model.add_at_most_one(conflict_vars)
    for day_vars in assignment_day_vars.values():
        model.add_at_most_one(day_vars)

    # Soft wellbeing rule: discourage more than MAX_FACULTY_PERIODS_PER_DAY classes for one teacher in a day.
    for (faculty_id, weekday), day_vars in faculty_day_vars.items():
        if len(day_vars) > MAX_FACULTY_PERIODS_PER_DAY:
            excess = model.new_int_var(0, len(PERIODS), f"excess_{faculty_id}_{weekday}")
            model.add(sum(day_vars) - MAX_FACULTY_PERIODS_PER_DAY <= excess)
            objective.append((OVERLOAD_PENALTY, excess))

    model.minimize(sum(cost * variable for cost, variable in objective))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15
    solver.parameters.num_search_workers = 8
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if status == cp_model.UNKNOWN:
            detail = "Timetable optimization reached its time limit without finding a schedule. Reduce constraints or retry."
        else:
            detail = (
                "No conflict-free timetable exists with the current faculty availability, room capacity, "
                "laboratory requirements, and weekly teaching loads. Review these constraints and try again."
            )
        raise TimetableOptimizationError(detail)

    return [
        TimetableEntry(
            assignment=assignment,
            section=assignment.section,
            subject=assignment.subject,
            faculty=assignment.faculty,
            room=room,
            weekday=weekday,
            period=period,
        )
        for variable, assignment, weekday, period, room in lessons
        if solver.boolean_value(variable)
    ]
