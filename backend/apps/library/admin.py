from django.contrib import admin

from .models import Book, BookIssue

admin.site.register(Book)
admin.site.register(BookIssue)
