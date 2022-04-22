from django import forms
from django.forms import Textarea, TextInput, NullBooleanSelect, Select, NumberInput, DateInput
from contabilidad.models import *
from django.forms import modelformset_factory
from admincu import settings

class asientoForm(forms.ModelForm):
	class Meta:
		model = Asiento
		fields = ['fecha_asiento', 'descripcion',]
		labels = {
			'fecha_asiento': 'Fecha',
			'descripcion': 'Descripcion',
		}
		widgets = {
			'fecha_asiento': DateInput(attrs={'placeholder': 'DD/MM/AAAA'}),
		}

	def __init__(self, *args, **kwargs):
		super(asientoForm, self).__init__(*args, **kwargs)
		for field in iter(self.fields):
			self.fields[field].widget.attrs.update({
						'class': 'form-control input-sm',
				})

class operacionForm(forms.ModelForm):
	class Meta:
		model = Operacion
		fields = ['cuenta','debe','haber','descripcion']

	def __init__(self, consorcio=None, *args, **kwargs):
		self.consorcio = consorcio
		super(operacionForm, self).__init__(*args, **kwargs)
		for field in iter(self.fields):
			clase = 'form-control input-sm no-border {}'.format(field)
			self.fields[field].widget.attrs.update({
						'class': clase,
				})
		self.fields['cuenta'].queryset = Plan.objects.get(consorcio=self.consorcio).cuentas.filter(nivel=4).order_by('numero')
