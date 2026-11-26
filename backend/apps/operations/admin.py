from django.contrib import admin

from .models import AuditLog, FacultyLeave, Notification, Substitution


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Audit rows are append-only: admins may inspect but never rewrite them."""

    list_display = ("created_at", "actor", "action", "entity", "entity_id", "college")
    list_filter = ("action", "entity", "college")
    search_fields = ("action", "entity", "entity_id", "actor__username")
    readonly_fields = (
        "college", "actor", "action", "entity", "entity_id", "detail", "created_at",
        "previous_hash", "entry_hash",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(FacultyLeave)
admin.site.register(Substitution)
admin.site.register(Notification)
