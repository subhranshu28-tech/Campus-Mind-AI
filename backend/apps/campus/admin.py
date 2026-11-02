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
admin.site.register(TimetableEntry)
admin.site.register(ExamSchedule)
admin.site.register(SubjectNote)
admin.site.register(PreviousYearQuestionPaper)
