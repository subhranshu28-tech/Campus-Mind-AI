from rest_framework import serializers

from apps.accounts.serializers import TenantScopedUniqueNameMixin

from .models import FeeStructure, Invoice, Payment


class FeeStructureSerializer(TenantScopedUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = FeeStructure
        fields = "__all__"
        read_only_fields = ("college", "created_at")

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount cannot be negative.")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    fee_structure_name = serializers.CharField(source="fee_structure.name", read_only=True)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id", "college", "student", "student_name", "fee_structure",
            "fee_structure_name", "amount", "amount_paid", "balance", "due_date", "status", "paid_at",
            "created_at",
        )
        read_only_fields = ("college", "paid_at", "created_at")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        status = attrs.get("status", getattr(instance, "status", Invoice.Status.PENDING))
        amount = attrs.get("amount", getattr(instance, "amount", None))
        if instance is not None and amount is not None:
            paid = instance.amount_paid
            if amount < paid:
                raise serializers.ValidationError({"amount": "Amount cannot be less than the amount already paid."})
            if status == Invoice.Status.CANCELLED and paid > 0:
                raise serializers.ValidationError({"status": "Invoices with recorded payments cannot be cancelled."})
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    invoice_label = serializers.SerializerMethodField()
    student_name = serializers.CharField(source="invoice.student.user.get_full_name", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id", "invoice", "invoice_label", "student_name", "amount", "method", "reference",
            "paid_on", "recorded_by",
        )
        read_only_fields = ("paid_on", "recorded_by")

    def get_invoice_label(self, obj):
        if not obj.invoice_id:
            return ""
        return f"{obj.invoice.student.user.get_full_name()} · {obj.invoice.fee_structure.name}"

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        invoice = attrs.get("invoice", getattr(self.instance, "invoice", None))
        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        if invoice is not None:
            if invoice.status == Invoice.Status.CANCELLED:
                raise serializers.ValidationError({"invoice": "Cancelled invoices cannot receive payments."})
            paid = invoice.payments.exclude(pk=getattr(self.instance, "pk", None)).aggregate(total=sum_field())["total"] or 0
            # sum_field fallback handled below by simple query
            from django.db.models import Sum
            paid = invoice.payments.exclude(pk=getattr(self.instance, "pk", None)).aggregate(total=Sum("amount"))["total"] or 0
            if amount is not None and paid + amount > invoice.amount:
                raise serializers.ValidationError({"amount": "Payment exceeds the invoice balance."})
        return attrs


def sum_field():
    from django.db.models import Sum
    return Sum("amount")
