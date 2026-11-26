from django.contrib import admin

from .models import StudentTransport, TransportRoute, Vehicle

admin.site.register(TransportRoute)
admin.site.register(Vehicle)
admin.site.register(StudentTransport)
