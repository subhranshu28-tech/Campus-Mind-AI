from django.core.exceptions import PermissionDenied

# Paths from each tenant-owned model to its College row.
TENANT_LOOKUPS = {
    "Department": "college_id", "AcademicYear": "college_id", "Classroom": "college_id",
    "Student": "department__college_id", "Faculty": "department__college_id",
    "Course": "department__college_id", "Semester": "course__department__college_id",
    "Section": "semester__course__department__college_id",
    "Subject": "course__department__college_id",
    "AttendanceRecord": "student__department__college_id",
    "SubjectNote": "subject__course__department__college_id",
    "PreviousYearQuestionPaper": "subject__course__department__college_id",
    "TeachingAssignment": "section__semester__course__department__college_id",
    "FacultyAvailability": "faculty__department__college_id",
    "TimetableEntry": "section__semester__course__department__college_id",
    "ExamSchedule": "section__semester__course__department__college_id",
    "FacultyLeave": "faculty__department__college_id",
    "Substitution": "section__semester__course__department__college_id",
    "AuditLog": "college_id",
    "Notice": "college_id",
    "CampusEvent": "college_id",
    "Assignment": "college_id",
    "Submission": "assignment__college_id",
    "FeeStructure": "college_id",
    "Invoice": "college_id",
    "Payment": "invoice__college_id",
    "Book": "college_id",
    "BookIssue": "book__college_id",
    "Hostel": "college_id",
    "HostelRoom": "hostel__college_id",
    "HostelAllocation": "room__hostel__college_id",
    "TransportRoute": "college_id",
    "Vehicle": "route__college_id",
    "StudentTransport": "route__college_id",
    "Company": "college_id",
    "JobPosting": "company__college_id",
    "PlacementApplication": "job__company__college_id",
}

def scope_queryset(queryset, user):
    if not user or not user.is_authenticated or not getattr(user, "college_id", None):
        return queryset.none()
    lookup = TENANT_LOOKUPS.get(queryset.model.__name__)
    if lookup is None:
        return queryset.none()
    return queryset.filter(**{lookup: user.college_id})

def require_same_college(user, *objects):
    college_id = getattr(user, "college_id", None)
    if not college_id or any(obj is not None and tenant_id_for(obj) != college_id for obj in objects):
        raise PermissionDenied("This resource belongs to a different college.")


def tenant_id_for(obj):
    if obj is None:
        return None
    lookup = TENANT_LOOKUPS.get(obj.__class__.__name__)
    if not lookup:
        return getattr(obj, "college_id", None)
    value = obj
    for part in lookup.split("__"):
        value = getattr(value, part, None)
        if value is None:
            return None
    return value
