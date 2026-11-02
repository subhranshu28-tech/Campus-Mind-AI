from rest_framework.permissions import BasePermission, SAFE_METHODS


class CampusStaffCanManage(BasePermission):
    allowed_roles = {"super_admin", "college_admin", "hod"}
    read_roles = allowed_roles | {"faculty"}

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return user.is_staff or user.role in self.read_roles
        return user.is_staff or user.role in self.allowed_roles


class IsCampusStudent(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "student")


class NotCampusStudent(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role != "student")


class SubjectNotePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.role in {"super_admin", "college_admin", "hod"}:
            return True
        if user.role == "student":
            return request.method in SAFE_METHODS
        if user.role == "faculty":
            return request.method in SAFE_METHODS or request.method == "POST"
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or user.role in {"super_admin", "college_admin", "hod"}:
            return True
        if user.role == "student":
            return request.method in SAFE_METHODS
        if user.role == "faculty":
            return request.method in SAFE_METHODS or obj.uploaded_by_id == user.id
        return False
