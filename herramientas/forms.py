from django import forms
from django_afip.models import *
from django.db.models import Count
from django.forms import formset_factory

from arquitectura.models import *
from .models import *
from admincu.forms import FormControl


class InicialForm(FormControl, forms.Form):

	""" Paso 1 de Recibo C y Nota de Credito C """

	punto = forms.ModelChoiceField(queryset=PointOfSales.objects.none(), empty_label="-- Seleccionar Punto de gestion --", label="Punto de gestion")
	fecha = forms.DateField(label="Fecha de la transferencia", widget=forms.TextInput(attrs={'placeholder':'YYYY-MM-DD'}))
	caja_destino = forms.ModelChoiceField(queryset=Caja.objects.none(), empty_label="-- Seleccionar destino de la transferencia --", label="Destino de la transferencia")

	def __init__(self, *args, **kwargs):
		consorcio = kwargs.pop('consorcio')
		super().__init__(*args, **kwargs)
		self.fields['punto'].queryset = PointOfSales.objects.filter(owner=consorcio.contribuyente)
		self.fields['caja_destino'].queryset = Caja.objects.filter(consorcio=consorcio)
