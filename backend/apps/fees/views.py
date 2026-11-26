from apps.accounts.viewsets import TenantModelViewSet

from .models import FeeStructure, Invoice, Payment
from .serializers import FeeStructureSerializer, InvoiceSerializer, PaymentSerializer


class FeeStructureViewSet(TenantModelViewSet):
    queryset = FeeStructure.objects.all()
    serializer_class = FeeStructureSerializer


class InvoiceViewSet(TenantModelViewSet):
    queryset = Invoice.objects.select_related("student", "fee_structure")
    serializer_class = InvoiceSerializer
    student_scope_field = "student_id"


class PaymentViewSet(TenantModelViewSet):
    queryset = Payment.objects.select_related("invoice").order_by("-paid_on", "-id")
    serializer_class = PaymentSerializer
    student_scope_field = "invoice__student_id"

    def get_create_kwargs(self):
        return {"recorded_by": self.request.user}
