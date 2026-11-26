from rest_framework import serializers

from .models import Book, BookIssue


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = "__all__"
        read_only_fields = ("college",)


class BookIssueSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)

    class Meta:
        model = BookIssue
        fields = (
            "id", "book", "book_title", "student", "student_name", "issued_on",
            "due_on", "returned_on", "status", "fine",
        )
