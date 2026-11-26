from django.contrib import admin

from .models import CampusEvent, Notice

admin.site.register(Notice)
admin.site.register(CampusEvent)
