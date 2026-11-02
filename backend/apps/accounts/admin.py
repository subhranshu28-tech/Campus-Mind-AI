from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import College, User


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "slug", "is_active", "created_at")
    search_fields = ("name", "code", "email")
    list_filter = ("is_active",)
    readonly_fields = ("created_at",)


@admin.register(User)
class CampusUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Campus access", {"fields": ("role", "college")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Campus access", {"fields": ("email", "role", "college")}),)
    list_display = ("username", "email", "role", "college", "is_active", "is_staff")
    list_filter = ("college", "role", "is_active", "is_staff")
