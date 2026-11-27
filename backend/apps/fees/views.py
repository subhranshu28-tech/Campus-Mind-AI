from rest_framework.exceptions import ValidationError

from apps.accounts.viewsets import TenantModelViewSet

from .models import FeeStructure, Invoice, Payment
from .serializers import FeeStructureSerializer, InvoiceSerializer, PaymentSerializer


class FeeStructureViewSet(TenantModelViewSet):
    queryset = FeeStructure.objects.all()
    serializer_class = FeeStructureSerializer


class InvoiceViewSet(TenantModelViewSet):
    queryset = Invoice.objects.select_related("student__user", "fee_structure")
    serializer_class = InvoiceSerializer
    student_scope_field = "student_id"

    def perform_create(self, serializer):
        super().perform_create(serializer)
        serializer.instance.sync_status(save=True)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        serializer.instance.sync_status(save=True)

    def perform_destroy(self, instance):
        if instance.payments.exists():
            raise ValidationError({"detail": "Invoices with recorded payments cannot be deleted. Cancel the invoice instead."})
        super().perform_destroy(instance)


class PaymentViewSet(TenantModelViewSet):
    queryset = Payment.objects.select_related("invoice__student__user", "invoice__fee_structure")
    serializer_class = PaymentSerializer
    student_scope_field = "invoice__student_id"

    def get_create_kwargs(self):
        return {"recorded_by": self.request.user}

    def perform_create(self, serializer):
        super().perform_create(serializer)
        serializer.instance.invoice.sync_status(save=True)

    def perform_update(self, serializer):
        old_invoice = serializer.instance.invoice
        super().perform_update(serializer)
        serializer.instance.invoice.sync_status(save=True)
        if old_invoice.pk != serializer.instance.invoice_id:
            old_invoice.sync_status(save=True)

    def perform_destroy(self, instance):
        invoice = instance.invoice
        super().perform_destroy(instance)
        invoice.sync_status(save=True)
