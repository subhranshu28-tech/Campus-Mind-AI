from django.contrib import admin

from .models import FeeStructure, Invoice, Payment

admin.site.register(FeeStructure)
admin.site.register(Invoice)
admin.site.register(Payment)
