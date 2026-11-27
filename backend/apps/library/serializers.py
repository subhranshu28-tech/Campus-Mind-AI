from rest_framework import serializers

from .models import Book, BookIssue


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = "__all__"
        read_only_fields = ("college", "created_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        total = attrs.get("total_copies", getattr(instance, "total_copies", 1))
        available = attrs.get("available_copies", getattr(instance, "available_copies", 0))
        if total < 1:
            raise serializers.ValidationError({"total_copies": "Total copies must be at least 1."})
        if available < 0:
            raise serializers.ValidationError({"available_copies": "Available copies cannot be negative."})
        if available > total:
            raise serializers.ValidationError({"available_copies": "Available copies cannot exceed total copies."})
        if instance is not None:
            active_issues = instance.issues.exclude(status=BookIssue.Status.RETURNED).count()
            if total < active_issues:
                raise serializers.ValidationError({"total_copies": "Total copies cannot be less than active issues."})
            min_available = max(total - active_issues, 0)
            # if admin didn't explicitly change available, keep it consistent
            if "available_copies" not in attrs:
                attrs["available_copies"] = min_available
            elif attrs["available_copies"] != min_available and "total_copies" in attrs and "available_copies" not in self.initial_data:
                attrs["available_copies"] = min_available
        return attrs


class BookIssueSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)

    class Meta:
        model = BookIssue
        fields = (
            "id", "book", "book_title", "student", "student_name", "issued_on",
            "due_on", "returned_on", "status", "fine",
        )
        read_only_fields = ("issued_on",)

    def validate_fine(self, value):
        if value < 0:
            raise serializers.ValidationError("Fine cannot be negative.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        status = attrs.get("status", getattr(instance, "status", BookIssue.Status.ISSUED))
        returned_on = attrs.get("returned_on", getattr(instance, "returned_on", None))
        issued_on = getattr(instance, "issued_on", None)
        due_on = attrs.get("due_on", getattr(instance, "due_on", None))
        if status == BookIssue.Status.RETURNED and not returned_on:
            from django.utils import timezone
            attrs["returned_on"] = timezone.localdate()
        if status in {BookIssue.Status.ISSUED, BookIssue.Status.OVERDUE} and attrs.get("returned_on"):
            raise serializers.ValidationError({"returned_on": "Returned date is only valid for returned issues."})
        if returned_on and issued_on and returned_on < issued_on:
            raise serializers.ValidationError({"returned_on": "Return date cannot be before issue date."})
        if due_on and issued_on and due_on < issued_on:
            raise serializers.ValidationError({"due_on": "Due date cannot be before issue date."})
        return attrs
