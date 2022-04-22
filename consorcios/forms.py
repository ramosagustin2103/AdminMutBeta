from django import forms
from django.forms import Textarea, TextInput, NullBooleanSelect, Select
from .models import *
from arquitectura.models import *
from contabilidad.models import *
from django_afip.models import TaxPayer


class contribuyenteForm(forms.ModelForm):
	class Meta:
		model = TaxPayer
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super(contribuyenteForm, self).__init__(*args, **kwargs)
		for field in iter(self.fields):
			self.fields[field].widget.attrs.update({
						'class': 'form-control',
				})

class consorcioForm(forms.ModelForm):
	class Meta:
		model = Consorcio
		fields = [
		'nombre', 'nombre_completo',
		'tipo', 'abreviatura', 'domicilio',
		'provincia', 'superficie',
		]
		# labels = {
		# 	'tipo': 'Tipo de comprobante',
		# 	'punto': 'Punto de gestion',
		# 	'socio': 'Seleccionar socio'
		# }

	def __init__(self, *args, **kwargs):
		super(consorcioForm, self).__init__(*args, **kwargs)
		for field in iter(self.fields):
			self.fields[field].widget.attrs.update({
						'class': 'form-control',
				})


