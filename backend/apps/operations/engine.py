"""Pure-Python scheduling and analytics engines (no Django imports).

Keeping the algorithms free of ORM code makes them fast to unit-test and easy to reason about.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta

DAYS = 5
PERIODS = 8
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


# --------------------------------------------------------------------------- analytics
def room_utilization(rooms, entries, low_threshold=30.0):
    """rooms: [{id, code, name, capacity, is_lab}], entries: [{room_id, ...}]."""
    used = defaultdict(int)
    for entry in entries:
        used[entry["room_id"]] += 1
    total = DAYS * PERIODS
    rows = []
    for room in rooms:
        pct = round(used[room["id"]] / total * 100, 1)
        rows.append({
            "room": room["id"], "code": room["code"], "name": room["name"],
            "is_lab": room["is_lab"], "capacity": room["capacity"],
            "used_slots": used[room["id"]], "total_slots": total, "utilization": pct,
            "underused": pct < low_threshold,
        })
    return sorted(rows, key=lambda row: row["utilization"], reverse=True)


def demand_heatmap(rooms_count, entries):
    """Share of rooms busy at each weekday/period (0-100)."""
    counts = [[0] * PERIODS for _ in range(DAYS)]
    for entry in entries:
        if 0 <= entry["weekday"] < DAYS and 1 <= entry["period"] <= PERIODS:
            counts[entry["weekday"]][entry["period"] - 1] += 1
    denominator = max(rooms_count, 1)
    return [[round(cell / denominator * 100) for cell in row] for row in counts]


def faculty_load(faculty, entries, weekly_limit=18, daily_limit=5):
    """faculty: [{id, name}], entries: [{faculty_id, weekday}]."""
    weekly = defaultdict(int)
    daily = defaultdict(lambda: defaultdict(int))
    for entry in entries:
        weekly[entry["faculty_id"]] += 1
        daily[entry["faculty_id"]][entry["weekday"]] += 1
    rows = []
    for person in faculty:
        days = daily[person["id"]]
        peak_day = max(days, key=days.get) if days else None
        peak = days[peak_day] if days else 0
        rows.append({
            "faculty": person["id"], "name": person["name"], "weekly_periods": weekly[person["id"]],
            "peak_day": DAY_NAMES[peak_day] if peak_day is not None else None, "peak_day_periods": peak,
            "overloaded": weekly[person["id"]] > weekly_limit or peak > daily_limit,
        })
    return sorted(rows, key=lambda row: row["weekly_periods"], reverse=True)


def detect_conflicts(entries):
    """Report any faculty/room/section double-booking in a list of slot dicts."""
    seen = defaultdict(list)
    for index, entry in enumerate(entries):
        for kind in ("faculty_id", "room_id", "section_id"):
            if entry.get(kind) is not None:
                seen[(kind, entry[kind], entry["weekday"], entry["period"])].append(index)
    return [
        {"type": key[0].replace("_id", ""), "id": key[1], "weekday": DAY_NAMES[key[2]], "period": key[3]}
        for key, indexes in seen.items() if len(indexes) > 1
    ]


def build_insights(rooms, load, heatmap, conflicts, unresolved_cover=0):
    insights = []
    if conflicts:
        insights.append({"severity": "critical", "text": f"{len(conflicts)} scheduling conflict(s) detected - regenerate or move the affected classes."})
    if unresolved_cover:
        insights.append({"severity": "critical", "text": f"{unresolved_cover} class(es) lack a substitute - assign cover manually."})
    idle = [room for room in rooms if room["underused"]]
    if idle:
        names = ", ".join(room["code"] for room in idle[:4])
        insights.append({"severity": "warning", "text": f"{len(idle)} room(s) are under 30% utilised ({names}). Consider consolidating classes or lending them to other departments."})
    busy = [person for person in load if person["overloaded"]]
    if busy:
        names = ", ".join(person["name"] for person in busy[:3])
        insights.append({"severity": "warning", "text": f"{len(busy)} faculty member(s) exceed workload limits ({names}). Rebalance teaching assignments."})
    if heatmap:
        flat = [(value, day, period) for day, row in enumerate(heatmap) for period, value in enumerate(row, 1)]
        peak = max(flat)
        low = min(flat)
        if peak[0] > 0:
            insights.append({"severity": "info", "text": f"Peak demand is {DAY_NAMES[peak[1]]} period {peak[2]} ({peak[0]}% of rooms in use); the quietest slot is {DAY_NAMES[low[1]]} period {low[2]} ({low[0]}%)."})
    if not insights:
        insights.append({"severity": "success", "text": "No conflicts or resource problems detected."})
    return insights


# --------------------------------------------------------------------------- substitution ranking
def rank_substitutes(candidates):
    """candidates: [{faculty_id, name, same_subject, same_department, weekly_load, cover_count,
    busy, on_leave, unavailable, invigilating}]. Returns eligible candidates, best first."""
    eligible = []
    for candidate in candidates:
        if candidate["busy"] or candidate["on_leave"] or candidate["unavailable"] or candidate["invigilating"]:
            continue
        tier = 0 if candidate["same_subject"] else 1
        score = tier * 1000 + candidate["weekly_load"] * 3 + candidate["cover_count"] * 5
        reasons = ["teaches the same subject" if candidate["same_subject"] else "same department"]
        reasons.append(f"{candidate['weekly_load']} periods/week")
        eligible.append({**candidate, "score": score, "reason": ", ".join(reasons)})
    return sorted(eligible, key=lambda row: (row["score"], row["name"].casefold()))


# --------------------------------------------------------------------------- exam engine
@dataclass(frozen=True)
class ExamTask:
    key: str
    section_id: int
    subject_id: int
    seats: int
    is_lab: bool = False


@dataclass
class ExamPlan:
    assignments: list = field(default_factory=list)   # (task, date, session_index, room_id)
    unscheduled: list = field(default_factory=list)   # (task, reason)


def exam_dates(start, end, holidays=()):
    day, dates = start, []
    while day <= end:
        if day.weekday() < DAYS and day not in holidays:
            dates.append(day)
        day += timedelta(days=1)
    return dates


def schedule_exams(tasks, rooms, dates, sessions, blocked_sections=frozenset(), blocked_rooms=frozenset(),
                   max_exams_per_day=1):
    """Greedy most-constrained-first scheduler.

    rooms: [{id, capacity, is_lab}]; sessions: [(start_period, duration)];
    blocked_*: sets of (id, date, session_index). Hard rules: no room/section double-booking,
    capacity, lab rooms for lab subjects. Soft: earliest dates, a rest day between a section's
    exams, tight-fitting rooms, balanced load per day.
    """
    plan = ExamPlan()
    room_taken = set(blocked_rooms)
    section_days = defaultdict(lambda: defaultdict(int))
    section_slots = set(blocked_sections)
    day_load = defaultdict(int)
    index_of = {day: index for index, day in enumerate(dates)}

    ordered = sorted(tasks, key=lambda task: (not task.is_lab, -task.seats, task.key))
    for task in ordered:
        best, best_cost = None, None
        eligible = [room for room in rooms if room["capacity"] >= task.seats and (room["is_lab"] or not task.is_lab)]
        if not eligible:
            plan.unscheduled.append((task, "No room with enough capacity" + (" (laboratory required)" if task.is_lab else "")))
            continue
        for day in dates:
            if section_days[task.section_id][day] >= max_exams_per_day:
                continue
            adjacent = (
                section_days[task.section_id].get(day - timedelta(days=1), 0)
                + section_days[task.section_id].get(day + timedelta(days=1), 0)
            )
            for session_index in range(len(sessions)):
                if (task.section_id, day, session_index) in section_slots:
                    continue
                for room in eligible:
                    if (room["id"], day, session_index) in room_taken:
                        continue
                    cost = index_of[day] * 10 + session_index * 2 + adjacent * 40
                    cost += (room["capacity"] - task.seats) * 0.05 + day_load[day] * 0.8
                    if best_cost is None or cost < best_cost:
                        best, best_cost = (day, session_index, room["id"]), cost
        if best is None:
            plan.unscheduled.append((task, "No free date/session/room left in the exam window"))
            continue
        day, session_index, room_id = best
        room_taken.add((room_id, day, session_index))
        section_slots.add((task.section_id, day, session_index))
        section_days[task.section_id][day] += 1
        day_load[day] += 1
        plan.assignments.append((task, day, session_index, room_id))
    return plan


def assign_invigilators(exams, faculty, busy=frozenset(), excluded=None):
    """exams: [(key, date, session_index)], faculty: [{id, department_id}]; busy: {(faculty_id, date, session)};
    excluded: {key: {faculty_ids}} (e.g. the subject's own teacher). Balanced greedy assignment."""
    excluded = excluded or {}
    counts = defaultdict(int)
    taken = set(busy)
    result = {}
    for key, day, session_index in sorted(exams, key=lambda item: (item[1], item[2], item[0])):
        pool = [
            person for person in faculty
            if (person["id"], day, session_index) not in taken and person["id"] not in excluded.get(key, ())
        ]
        if not pool:
            result[key] = None
            continue
        chosen = min(pool, key=lambda person: (counts[person["id"]], person["id"]))
        counts[chosen["id"]] += 1
        taken.add((chosen["id"], day, session_index))
        result[key] = chosen["id"]
    return result
