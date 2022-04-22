from .models import *
import django_filters


class LiquidacionFilter(django_filters.FilterSet):
    numero = django_filters.NumberFilter(label="Numero de liquidacion", lookup_expr="exact")
    fecha = django_filters.DateRangeFilter(label="Fecha de liquidacion", lookup_expr="icontains")

    class Meta:
        model = Liquidacion
        fields = ['estado']



class CreditoFilter(django_filters.FilterSet):
    liquidacion__numero = django_filters.NumberFilter(label="Numero de liquidacion", lookup_expr="exact")
    factura__receipt__receipt_number = django_filters.NumberFilter(label="Numero de factura", lookup_expr="icontains")
    periodo = django_filters.DateRangeFilter(label="Periodo", lookup_expr="icontains")
    ingreso__nombre = django_filters.CharFilter(label="Nombre del concepto", lookup_expr="icontains")
    dominio__numero = django_filters.NumberFilter(label="Numero del dominio", lookup_expr="exact")
    socio__apellido = django_filters.CharFilter(label="Apellido del destinatario", lookup_expr="icontains")

    class Meta:
        model = Credito
        fields = []


class CreditoFilterSocio(django_filters.FilterSet):
    factura__receipt__receipt_number = django_filters.NumberFilter(label="Numero de factura", lookup_expr="icontains")
    periodo = django_filters.DateRangeFilter(label="Periodo", lookup_expr="icontains")
    ingreso__nombre = django_filters.CharFilter(label="Nombre del concepto", lookup_expr="icontains")

    class Meta:
        model = Credito
        fields = []