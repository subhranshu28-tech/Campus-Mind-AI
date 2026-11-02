from django.conf import settings
from django.db import models


class Department(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.PROTECT, related_name="departments")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=12)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="headed_departments",
        limit_choices_to={"role__in": ["hod", "faculty"]},
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["college", "name"], name="uniq_college_department_name"), models.UniqueConstraint(fields=["college", "code"], name="uniq_college_department_code")]

    def __str__(self):
        return f"{self.code} — {self.name}"


class AcademicYear(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.PROTECT, related_name="academic_years")
    name = models.CharField(max_length=32)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-starts_on"]
        constraints = [
            models.CheckConstraint(condition=models.Q(ends_on__gt=models.F("starts_on")), name="academic_year_end_after_start"),
            models.UniqueConstraint(fields=["college", "name"], name="uniq_college_academic_year_name"),
            models.UniqueConstraint(fields=["college"], condition=models.Q(is_active=True), name="one_active_academic_year_per_college"),
        ]

    def __str__(self):
        return self.name


class Course(models.Model):
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="courses")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20)
    duration_years = models.PositiveSmallIntegerField(default=4)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["department__code", "name"]
        constraints = [
            models.CheckConstraint(condition=models.Q(duration_years__gte=1), name="course_duration_positive"),
            models.UniqueConstraint(fields=["department", "code"], name="unique_department_course_code"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Semester(models.Model):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="semesters")
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, related_name="semesters"
    )
    number = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["course__code", "number"]
        constraints = [
            models.UniqueConstraint(fields=["course", "academic_year", "number"], name="unique_course_year_semester"),
            models.CheckConstraint(condition=models.Q(number__gte=1, number__lte=12), name="semester_number_valid"),
        ]

    def __str__(self):
        return f"{self.course.code} · Semester {self.number} · {self.academic_year.name}"


class Section(models.Model):
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="sections")
    name = models.CharField(max_length=24)
    capacity = models.PositiveSmallIntegerField(default=60)

    class Meta:
        ordering = ["semester__course__code", "semester__number", "name"]
        constraints = [
            models.UniqueConstraint(fields=["semester", "name"], name="unique_semester_section"),
            models.CheckConstraint(condition=models.Q(capacity__gte=1), name="section_capacity_positive"),
        ]

    def __str__(self):
        return f"{self.semester} · {self.name}"


class Subject(models.Model):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="subjects")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="subjects")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=140)
    is_lab = models.BooleanField(default=False)
    credits = models.PositiveSmallIntegerField(default=3)

    class Meta:
        ordering = ["course__code", "semester__number", "code"]
        constraints = [
            models.CheckConstraint(condition=models.Q(credits__gte=1), name="subject_credits_positive"),
            models.UniqueConstraint(fields=["course", "code"], name="unique_course_subject_code"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.semester_id and self.course_id and self.semester.course_id != self.course_id:
            raise ValidationError({"semester": "Semester must belong to the selected course."})

    def __str__(self):
        return f"{self.code} — {self.name}"


class Student(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="student_record"
    )
    student_id = models.CharField(max_length=24, unique=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="students"
    )
    semester = models.PositiveSmallIntegerField()
    section = models.ForeignKey(
        Section, null=True, blank=True, on_delete=models.PROTECT, related_name="students"
    )
    enrolled_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["student_id"]
        indexes = [models.Index(fields=["department", "semester"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(semester__gte=1), name="student_semester_positive"),
        ]

    def __str__(self):
        return self.student_id


class Faculty(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="faculty_record"
    )
    employee_id = models.CharField(max_length=24, unique=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="faculty"
    )
    qualification = models.CharField(max_length=160, blank=True)
    experience_years = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["employee_id"]

    def __str__(self):
        return self.employee_id


class Classroom(models.Model):
    college = models.ForeignKey("accounts.College", on_delete=models.PROTECT, related_name="classrooms")
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=20)
    capacity = models.PositiveSmallIntegerField()
    is_lab = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["college", "code"], name="uniq_college_classroom_code"),
            models.CheckConstraint(condition=models.Q(capacity__gte=1), name="classroom_capacity_positive"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class TeachingAssignment(models.Model):
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="teaching_assignments")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="teaching_assignments")
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="teaching_assignments")
    periods_per_week = models.PositiveSmallIntegerField(default=3)

    class Meta:
        ordering = ["section__semester__course__code", "section__name", "subject__code"]
        constraints = [
            models.UniqueConstraint(fields=["section", "subject"], name="one_teacher_per_section_subject"),
            models.CheckConstraint(condition=models.Q(periods_per_week__gte=1, periods_per_week__lte=25), name="teaching_periods_valid"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if self.section_id and self.subject_id:
            if self.section.semester_id != self.subject.semester_id:
                errors["subject"] = "Subject must belong to the section's semester."
        if self.faculty_id and self.subject_id:
            if self.faculty.department_id != self.subject.course.department_id:
                errors["faculty"] = "Faculty member must belong to the subject's department."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.section} · {self.subject.code} · {self.faculty.employee_id}"


class FacultyAvailability(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"

    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="availability")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    period = models.PositiveSmallIntegerField()
    is_available = models.BooleanField(default=False)

    class Meta:
        ordering = ["faculty__employee_id", "weekday", "period"]
        constraints = [
            models.UniqueConstraint(fields=["faculty", "weekday", "period"], name="unique_faculty_availability_slot"),
            models.CheckConstraint(condition=models.Q(weekday__gte=0, weekday__lte=4), name="availability_weekday_valid"),
            models.CheckConstraint(condition=models.Q(period__gte=1, period__lte=8), name="availability_period_valid"),
        ]

    def __str__(self):
        return f"{self.faculty.employee_id} · {self.get_weekday_display()} · Period {self.period}"


class TimetableEntry(models.Model):
    assignment = models.ForeignKey(TeachingAssignment, on_delete=models.CASCADE, related_name="timetable_entries")
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="timetable_entries")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="timetable_entries")
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="timetable_entries")
    room = models.ForeignKey(Classroom, on_delete=models.PROTECT, related_name="timetable_entries")
    weekday = models.PositiveSmallIntegerField(choices=FacultyAvailability.Weekday.choices)
    period = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["weekday", "period", "section__name"]
        constraints = [
            models.UniqueConstraint(fields=["section", "weekday", "period"], name="unique_section_timetable_slot"),
            models.UniqueConstraint(fields=["faculty", "weekday", "period"], name="unique_faculty_timetable_slot"),
            models.UniqueConstraint(fields=["room", "weekday", "period"], name="unique_room_timetable_slot"),
            models.CheckConstraint(condition=models.Q(weekday__gte=0, weekday__lte=4), name="timetable_weekday_valid"),
            models.CheckConstraint(condition=models.Q(period__gte=1, period__lte=8), name="timetable_period_valid"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.assignment_id and (
            self.assignment.section_id != self.section_id
            or self.assignment.subject_id != self.subject_id
            or self.assignment.faculty_id != self.faculty_id
        ):
            raise ValidationError("Timetable entry must match its teaching assignment.")

    def __str__(self):
        return f"{self.section} · {self.get_weekday_display()} · Period {self.period}"


class ExamSchedule(models.Model):
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="exams")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="exams")
    room = models.ForeignKey(Classroom, on_delete=models.PROTECT, related_name="exams")
    invigilator = models.ForeignKey(
        Faculty, null=True, blank=True, on_delete=models.PROTECT, related_name="invigilated_exams"
    )
    date = models.DateField()
    start_period = models.PositiveSmallIntegerField()
    duration_periods = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["date", "start_period", "section__name"]
        indexes = [models.Index(fields=["date", "start_period"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(start_period__gte=1, start_period__lte=8), name="exam_start_period_valid"),
            models.CheckConstraint(condition=models.Q(duration_periods__gte=1, duration_periods__lte=8), name="exam_duration_valid"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if self.section_id and self.subject_id and self.section.semester_id != self.subject.semester_id:
            errors["subject"] = "Exam subject must belong to the section's semester."
        if self.room_id and self.section_id:
            if self.room.capacity < self.section.capacity:
                errors["room"] = "Room capacity is below the section capacity."
            if self.subject_id and self.subject.is_lab and not self.room.is_lab:
                errors["room"] = "A laboratory subject requires a laboratory room."
        if self.start_period and self.duration_periods and self.start_period + self.duration_periods - 1 > 8:
            errors["duration_periods"] = "The exam must finish within the academic day."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.subject.code} · {self.date} · {self.room.code}"


class AttendanceRecord(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField()
    is_present = models.BooleanField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="attendance_entries"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "student__student_id"]
        constraints = [
            models.UniqueConstraint(fields=["student", "date"], name="one_attendance_per_student_day"),
        ]
        indexes = [models.Index(fields=["date", "is_present"])]

    def __str__(self):
        return f"{self.student.student_id} · {self.date}"


class SubjectNote(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="notes")
    title = models.CharField(max_length=160)
    description = models.TextField(max_length=2000, blank=True)
    file = models.FileField(upload_to="subject-notes/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_subject_notes"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return f"{self.subject.code} · {self.title}"


class PreviousYearQuestionPaper(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="question_papers")
    title = models.CharField(max_length=160)
    exam_year = models.PositiveSmallIntegerField()
    description = models.TextField(max_length=2000, blank=True)
    file = models.FileField(upload_to="question-papers/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_question_papers",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-exam_year", "-uploaded_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(exam_year__gte=1950),
                name="question_paper_exam_year_valid",
            ),
        ]

    def __str__(self):
        return f"{self.subject.code} · {self.exam_year} · {self.title}"
