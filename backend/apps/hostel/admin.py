from django.contrib import admin

from .models import Hostel, HostelAllocation, HostelRoom

admin.site.register(Hostel)
admin.site.register(HostelRoom)
admin.site.register(HostelAllocation)
