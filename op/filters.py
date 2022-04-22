from .models import *
import django_filters


class DeudaFilter(django_filters.FilterSet):
    acreedor__nombre = django_filters.CharFilter(label="Nombre del acreedor", lookup_expr="icontains")
    fecha = django_filters.DateRangeFilter(label="Fecha", lookup_expr="icontains")
    numero = django_filters.NumberFilter(label="Numero del comprobante", lookup_expr="exact")

    class Meta:
        model = Deuda
        fields = []


class OPFilter(django_filters.FilterSet):
    acreedor__nombre = django_filters.CharFilter(label="Nombre del acreedor", lookup_expr="icontains")
    fecha = django_filters.DateRangeFilter(label="Fecha", lookup_expr="icontains")
    numero = django_filters.NumberFilter(label="Numero del comprobante", lookup_expr="exact")

    class Meta:
        model = OP
        fields = []
