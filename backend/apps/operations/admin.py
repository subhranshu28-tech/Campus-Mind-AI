from django.contrib import admin

from .models import AuditLog, FacultyLeave, Notification, Substitution

admin.site.register(FacultyLeave)
admin.site.register(Substitution)
admin.site.register(Notification)
admin.site.register(AuditLog)
