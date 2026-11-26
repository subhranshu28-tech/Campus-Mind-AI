from apps.accounts.testing import ERPAPITestCase

from .models import Hostel, HostelAllocation, HostelRoom


class HostelApiTests(ERPAPITestCase):
    def test_create_sets_college_from_session(self):
        response = self.client.post(
            "/api/hostels/",
            {"name": "Ganga Hostel", "gender": "male", "capacity": 120, "warden": "Dr Rao"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            Hostel.objects.get(pk=response.data["id"]).college, self.college
        )

    def test_list_only_returns_the_caller_college(self):
        mine = Hostel.objects.create(college=self.college, name="Ganga", capacity=100)
        Hostel.objects.create(college=self.other_college, name="Yamuna", capacity=80)

        response = self.client.get("/api/hostels/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])

    def test_student_cannot_create_hostels(self):
        self.as_student()

        response = self.client.post(
            "/api/hostels/", {"name": "Free stay", "capacity": 1}, format="json"
        )

        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Hostel.objects.exists())

    def test_room_create_rejects_hostel_from_another_college(self):
        other_hostel = Hostel.objects.create(
            college=self.other_college, name="Yamuna", capacity=80
        )

        response = self.client.post(
            "/api/hostel-rooms/",
            {"hostel": other_hostel.id, "room_number": "101", "capacity": 4},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(HostelRoom.objects.exists())


class HostelAllocationApiTests(ERPAPITestCase):
    def setUp(self):
        super().setUp()
        self.hostel = Hostel.objects.create(
            college=self.college, name="Ganga", capacity=100
        )
        self.room = HostelRoom.objects.create(
            hostel=self.hostel, room_number="101", capacity=4
        )
        other_hostel = Hostel.objects.create(
            college=self.other_college, name="Yamuna", capacity=80
        )
        self.other_room = HostelRoom.objects.create(
            hostel=other_hostel, room_number="201", capacity=4
        )

    def allocate(self, room, student):
        return HostelAllocation.objects.create(room=room, student=student)

    def test_create_rejects_room_from_another_college(self):
        response = self.client.post(
            "/api/hostel-allocations/",
            {"student": self.campus.student.id, "room": self.other_room.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(HostelAllocation.objects.exists())

    def test_create_rejects_student_from_another_college(self):
        response = self.client.post(
            "/api/hostel-allocations/",
            {"student": self.other.student.id, "room": self.room.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(HostelAllocation.objects.exists())

    def test_staff_can_allocate_a_room(self):
        response = self.client.post(
            "/api/hostel-allocations/",
            {"student": self.campus.student.id, "room": self.room.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)

    def test_student_only_sees_their_own_allocation(self):
        mine = self.allocate(self.room, self.campus.student)
        _, other_student = self.add_student("hostel")
        self.allocate(self.room, other_student)
        self.as_student()

        response = self.client.get("/api/hostel-allocations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])
