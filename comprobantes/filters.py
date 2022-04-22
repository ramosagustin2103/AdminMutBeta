from .models import *
import django_filters


class ComprobanteFilter(django_filters.FilterSet):
    socio__apellido = django_filters.CharFilter(label="Apellido del destinatario", lookup_expr="icontains")
    fecha = django_filters.DateRangeFilter(label="Fecha", lookup_expr="icontains")
    numero = django_filters.NumberFilter(label="Numero de recibo", lookup_expr="exact")
    nota_credito__receipt_number = django_filters.NumberFilter(label="Numero de Nota de credito C", lookup_expr="exact")

    class Meta:
        model = Comprobante
        fields = []


class ComprobanteFilterSocio(django_filters.FilterSet):
    fecha = django_filters.DateRangeFilter(label="Fecha", lookup_expr="icontains")
    numero = django_filters.NumberFilter(label="Numero de recibo", lookup_expr="exact")
    nota_credito__receipt_number = django_filters.NumberFilter(label="Numero de Nota de credito C", lookup_expr="exact")

    class Meta:
        model = Comprobante
        fields = []