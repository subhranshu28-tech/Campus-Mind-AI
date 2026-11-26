from apps.accounts.viewsets import TenantModelViewSet

from .models import Book, BookIssue
from .serializers import BookIssueSerializer, BookSerializer


class BookViewSet(TenantModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer


class BookIssueViewSet(TenantModelViewSet):
    queryset = BookIssue.objects.select_related("book", "student")
    serializer_class = BookIssueSerializer
    student_scope_field = "student_id"
