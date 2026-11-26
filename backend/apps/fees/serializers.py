from rest_framework import serializers

from apps.accounts.serializers import TenantScopedUniqueNameMixin

from .models import FeeStructure, Invoice, Payment


class FeeStructureSerializer(TenantScopedUniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = FeeStructure
        fields = "__all__"
        read_only_fields = ("college",)


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ("college",)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ("paid_on", "recorded_by")
