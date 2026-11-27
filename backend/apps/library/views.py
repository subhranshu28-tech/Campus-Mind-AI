from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError

from apps.accounts.viewsets import TenantModelViewSet

from .models import Book, BookIssue
from .serializers import BookIssueSerializer, BookSerializer


class BookViewSet(TenantModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def perform_destroy(self, instance):
        if instance.issues.exclude(status=BookIssue.Status.RETURNED).exists():
            raise ValidationError({"detail": "Books with active issues cannot be deleted."})
        super().perform_destroy(instance)


class BookIssueViewSet(TenantModelViewSet):
    queryset = BookIssue.objects.select_related("book", "student__user")
    serializer_class = BookIssueSerializer
    student_scope_field = "student_id"

    def perform_create(self, serializer):
        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=serializer.validated_data["book"].pk)
            if book.available_copies < 1:
                raise ValidationError({"book": "No copies are available for this book."})
            super().perform_create(serializer)
            Book.objects.filter(pk=book.pk, available_copies__gt=0).update(available_copies=F("available_copies") - 1)

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = BookIssue.objects.select_for_update().select_related("book").get(pk=serializer.instance.pk)
            old_status = instance.status
            old_book_id = instance.book_id
            super().perform_update(serializer)
            instance = serializer.instance
            new_status = instance.status
            new_book_id = instance.book_id

            if old_book_id != new_book_id:
                raise ValidationError({"book": "Changing the book of an issue is not supported. Create a new issue instead."})

            was_active = old_status != BookIssue.Status.RETURNED
            is_active = new_status != BookIssue.Status.RETURNED
            if was_active and not is_active:
                Book.objects.filter(pk=old_book_id).update(available_copies=F("available_copies") + 1)
            elif (not was_active) and is_active:
                updated = Book.objects.filter(pk=old_book_id, available_copies__gt=0).update(available_copies=F("available_copies") - 1)
                if not updated:
                    raise ValidationError({"status": "No copies are available to reopen this issue."})

    def perform_destroy(self, instance):
        with transaction.atomic():
            book_id = instance.book_id
            was_active = instance.status != BookIssue.Status.RETURNED
            super().perform_destroy(instance)
            if was_active:
                Book.objects.filter(pk=book_id).update(available_copies=F("available_copies") + 1)
