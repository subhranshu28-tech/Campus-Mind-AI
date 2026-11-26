from rest_framework import viewsets

from apps.accounts.tenancy import scope_queryset
from .models import FeeStructure, Invoice, Payment
from .serializers import FeeStructureSerializer, InvoiceSerializer, PaymentSerializer


class FeeStructureViewSet(viewsets.ModelViewSet):
    queryset = FeeStructure.objects.all()
    serializer_class = FeeStructureSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return scope_queryset(self.queryset, self.request.user)
