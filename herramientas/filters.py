from .models import *
import django_filters


class TransferenciaFilter(django_filters.FilterSet):
    fecha = django_filters.DateRangeFilter(label="Fecha", lookup_expr="icontains")
    numero = django_filters.NumberFilter(label="Numero de transferencia", lookup_expr="exact")

    class Meta:
        model = Transferencia
        fields = []
