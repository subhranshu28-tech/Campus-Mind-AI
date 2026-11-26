from django.contrib import admin

from .models import (
    AcademicYear,
    AttendanceRecord,
    Classroom,
    Department,
    ExamSchedule,
    Faculty,
    FacultyAvailability,
    Section,
    Semester,
    Student,
    Subject,
    TeachingAssignment,
    TimetableEntry,
    SubjectNote,
    PreviousYearQuestionPaper,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Prevent the admin from bypassing serializer conflict checks."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True


@admin.register(ExamSchedule)
class ExamScheduleAdmin(ReadOnlyAdmin):
    list_display = ("date", "start_period", "section", "subject", "room", "invigilator")
    list_filter = ("date", "room", "section__semester__course__department__college")
    search_fields = ("subject__code", "section__name", "room__code")


@admin.register(TimetableEntry)
class TimetableEntryAdmin(ReadOnlyAdmin):
    list_display = ("weekday", "period", "section", "subject", "faculty", "room")
    list_filter = ("weekday", "room", "section__semester__course__department__college")
    search_fields = ("subject__code", "section__name", "faculty__employee_id", "room__code")


admin.site.register(Department)
admin.site.register(Student)
admin.site.register(Faculty)
admin.site.register(AttendanceRecord)
admin.site.register(AcademicYear)
admin.site.register(Semester)
admin.site.register(Section)
admin.site.register(Subject)
admin.site.register(Classroom)
admin.site.register(TeachingAssignment)
admin.site.register(FacultyAvailability)
admin.site.register(SubjectNote)
admin.site.register(PreviousYearQuestionPaper)
