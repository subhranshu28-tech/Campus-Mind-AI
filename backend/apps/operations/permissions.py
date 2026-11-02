from rest_framework.permissions import BasePermission

MANAGER_ROLES = {"super_admin", "college_admin", "hod"}


def is_manager(user):
    return bool(user and user.is_authenticated and (user.is_staff or user.role in MANAGER_ROLES))


class IsCampusManager(BasePermission):
    def has_permission(self, request, view):
        return is_manager(request.user)


class IsCampusStaffMember(BasePermission):
    """Managers and faculty; students and other roles are excluded."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (is_manager(user) or user.role == "faculty"))
