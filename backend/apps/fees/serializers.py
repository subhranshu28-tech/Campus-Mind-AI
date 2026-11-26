from rest_framework import serializers

from apps.accounts.serializers import TenantScopedUniqueNameMixin

from .models import FeeStructure, Invoice, Payment


class FeeStructureSerializer(TenantScopedUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = FeeStructure
        fields = "__all__"
        read_only_fields = ("college",)


class InvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    fee_structure_name = serializers.CharField(source="fee_structure.name", read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id", "college", "student", "student_name", "fee_structure",
            "fee_structure_name", "amount", "due_date", "status", "paid_at",
            "created_at",
        )
        read_only_fields = ("college",)


class PaymentSerializer(serializers.ModelSerializer):
    invoice_label = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id", "invoice", "invoice_label", "amount", "method", "reference",
            "paid_on", "recorded_by",
        )
        read_only_fields = ("paid_on", "recorded_by")

    def get_invoice_label(self, obj):
        return f"{obj.invoice.student.user.get_full_name()} · {obj.invoice.fee_structure.name}" if obj.invoice_id else ""
