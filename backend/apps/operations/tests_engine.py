"""Dependency-free tests for the scheduling engine. Run: python -m unittest apps.operations.tests_engine"""
import unittest
from collections import Counter
from datetime import date

from . import engine


class ExamEngineTests(unittest.TestCase):
    def setUp(self):
        self.rooms = [
            {"id": 1, "capacity": 60, "is_lab": False},
            {"id": 2, "capacity": 60, "is_lab": True},
            {"id": 3, "capacity": 45, "is_lab": False},
        ]
        self.dates = engine.exam_dates(date(2026, 11, 16), date(2026, 11, 27))
        self.sessions = [(1, 3), (5, 3)]

    def test_weekends_and_holidays_are_skipped(self):
        days = engine.exam_dates(date(2026, 11, 13), date(2026, 11, 17), {date(2026, 11, 16)})
        self.assertEqual(days, [date(2026, 11, 13), date(2026, 11, 17)])

    def test_no_room_or_section_double_booking(self):
        tasks = [engine.ExamTask(f"{s}-{j}", s, j, 40, j == 0) for s in range(1, 5) for j in range(4)]
        plan = engine.schedule_exams(tasks, self.rooms, self.dates, self.sessions)
        self.assertEqual(plan.unscheduled, [])
        self.assertEqual(len({(r, d, s) for _, d, s, r in plan.assignments}), len(plan.assignments))
        per_day = Counter((t.section_id, d) for t, d, _, _ in plan.assignments)
        self.assertEqual(max(per_day.values()), 1)
        for task, _, _, room_id in plan.assignments:
            room = next(r for r in self.rooms if r["id"] == room_id)
            self.assertGreaterEqual(room["capacity"], task.seats)
            self.assertTrue(room["is_lab"] or not task.is_lab)

    def test_reports_unschedulable_exam(self):
        plan = engine.schedule_exams([engine.ExamTask("x", 1, 1, 500)], self.rooms, self.dates, self.sessions)
        self.assertEqual(len(plan.unscheduled), 1)

    def test_blocked_slots_are_respected(self):
        task = engine.ExamTask("x", 1, 1, 30)
        blocked = {(1, self.dates[0], 0), (3, self.dates[0], 0), (1, self.dates[0], 1), (3, self.dates[0], 1)}
        plan = engine.schedule_exams([task], self.rooms[:1] + self.rooms[2:], self.dates, self.sessions, blocked_rooms=blocked)
        self.assertNotEqual(plan.assignments[0][1], self.dates[0])

    def test_invigilators_balanced_and_exclusions_honoured(self):
        exams = [(f"e{i}", self.dates[i // 2], i % 2) for i in range(6)]
        staff = [{"id": i, "department_id": 1} for i in range(1, 4)]
        result = engine.assign_invigilators(exams, staff, excluded={"e0": {1}})
        self.assertNotEqual(result["e0"], 1)
        self.assertLessEqual(max(Counter(result.values()).values()), 2)


class AnalyticsEngineTests(unittest.TestCase):
    def test_conflict_detection_and_utilization(self):
        entries = [
            {"room_id": 1, "faculty_id": 1, "section_id": 1, "weekday": 0, "period": 1},
            {"room_id": 1, "faculty_id": 2, "section_id": 2, "weekday": 0, "period": 1},
        ]
        self.assertEqual(engine.detect_conflicts(entries)[0]["type"], "room")
        rooms = [{"id": 1, "code": "R1", "name": "R1", "capacity": 60, "is_lab": False}]
        self.assertEqual(engine.room_utilization(rooms, entries)[0]["used_slots"], 2)

    def test_substitute_ranking_prefers_same_subject_then_light_load(self):
        base = dict(cover_count=0, busy=False, on_leave=False, unavailable=False, invigilating=False, same_department=True)
        ranked = engine.rank_substitutes([
            {**base, "faculty_id": 1, "name": "B", "same_subject": False, "weekly_load": 2},
            {**base, "faculty_id": 2, "name": "A", "same_subject": True, "weekly_load": 16},
            {**base, "faculty_id": 3, "name": "C", "same_subject": True, "weekly_load": 8},
            {**base, "faculty_id": 4, "name": "D", "same_subject": True, "weekly_load": 1, "busy": True},
        ])
        self.assertEqual([row["faculty_id"] for row in ranked], [3, 2, 1])


if __name__ == "__main__":
    unittest.main()
