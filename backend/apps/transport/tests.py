from apps.accounts.testing import ERPAPITestCase

from .models import StudentTransport, TransportRoute, Vehicle


class TransportRouteApiTests(ERPAPITestCase):
    def test_create_sets_college_from_session(self):
        response = self.client.post(
            "/api/transport-routes/",
            {"name": "Route 1", "origin": "Station", "destination": "Campus", "fare": "25.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            TransportRoute.objects.get(pk=response.data["id"]).college, self.college
        )

    def test_list_only_returns_the_caller_college(self):
        mine = TransportRoute.objects.create(college=self.college, name="Route 1")
        TransportRoute.objects.create(college=self.other_college, name="Route 9")

        response = self.client.get("/api/transport-routes/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])

    def test_student_cannot_create_routes(self):
        self.as_student()

        response = self.client.post(
            "/api/transport-routes/", {"name": "Free route"}, format="json"
        )

        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(TransportRoute.objects.exists())


class VehicleApiTests(ERPAPITestCase):
    def test_create_rejects_route_from_another_college(self):
        other_route = TransportRoute.objects.create(
            college=self.other_college, name="Route 9"
        )

        response = self.client.post(
            "/api/vehicles/",
            {
                "registration_number": "OD-02-AB-1234",
                "capacity": 40,
                "route": other_route.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Vehicle.objects.exists())

    def test_vehicle_requires_a_route(self):
        response = self.client.post(
            "/api/vehicles/",
            {"registration_number": "OD-02-AB-5678", "capacity": 32},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Vehicle.objects.exists())

    def test_list_is_scoped_through_the_route(self):
        mine = TransportRoute.objects.create(college=self.college, name="Route 1")
        other_route = TransportRoute.objects.create(
            college=self.other_college, name="Route 9"
        )
        visible = Vehicle.objects.create(route=mine, registration_number="OD-01-AA-0001")
        Vehicle.objects.create(route=other_route, registration_number="OD-01-BB-0002")

        response = self.client.get("/api/vehicles/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [visible.id])


class StudentTransportApiTests(ERPAPITestCase):
    def setUp(self):
        super().setUp()
        self.route = TransportRoute.objects.create(
            college=self.college, name="Route 1", fare="25.00"
        )
        self.other_route = TransportRoute.objects.create(
            college=self.other_college, name="Route 9", fare="30.00"
        )

    def allocate(self, route, student):
        return StudentTransport.objects.create(route=route, student=student)

    def test_create_rejects_route_from_another_college(self):
        response = self.client.post(
            "/api/student-transport/",
            {
                "student": self.campus.student.id,
                "route": self.other_route.id,
                "pickup_point": "Station",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(StudentTransport.objects.exists())

    def test_create_rejects_student_from_another_college(self):
        response = self.client.post(
            "/api/student-transport/",
            {"student": self.other.student.id, "route": self.route.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(StudentTransport.objects.exists())

    def test_staff_can_allocate_transport(self):
        response = self.client.post(
            "/api/student-transport/",
            {"student": self.campus.student.id, "route": self.route.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)

    def test_student_only_sees_their_own_transport(self):
        mine = self.allocate(self.route, self.campus.student)
        _, other_student = self.add_student("transport")
        self.allocate(self.route, other_student)
        self.as_student()

        response = self.client.get("/api/student-transport/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [mine.id])
