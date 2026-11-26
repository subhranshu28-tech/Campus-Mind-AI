from rest_framework import viewsets

from apps.accounts.tenancy import scope_queryset
from .models import Book, BookIssue
from .serializers import BookIssueSerializer, BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)


class BookIssueViewSet(viewsets.ModelViewSet):
    queryset = BookIssue.objects.all()
    serializer_class = BookIssueSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)
