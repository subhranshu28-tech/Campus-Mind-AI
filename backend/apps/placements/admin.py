from django.contrib import admin

from .models import Company, JobPosting, PlacementApplication

admin.site.register(Company)
admin.site.register(JobPosting)
admin.site.register(PlacementApplication)
