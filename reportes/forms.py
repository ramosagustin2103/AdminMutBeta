from django import forms
from django.forms import Textarea, TextInput, NullBooleanSelect, Select
from .models import *
from admincu.forms import FormControl

class periodoForm(FormControl, forms.ModelForm):
	class Meta:
		model = Cierre
		fields = ['periodo']
		help_texts = {
			'periodo': 'Seleccione una fecha de corte de operaciones'
		}

	def __init__(self, consorcio, *args, **kwargs):
		self.consorcio = consorcio
		super(periodoForm, self).__init__(*args, **kwargs)

	def clean_periodo(self):
		periodo = self.cleaned_data['periodo']
		consulta = Cierre.objects.filter(consorcio=self.consorcio, periodo__gte=periodo)
		if consulta:
			raise forms.ValidationError("La fecha es menor o igual a un periodo ya cerrado.")
		return periodo



class auditorForm(FormControl, forms.ModelForm):
	class Meta:
		model = Cierre
		fields = ['auditor', 'logo_auditor']
		help_texts = {
			'auditor': 'Responsable de la auditoria del reporte',
			'logo_auditor': "Solo se admiten formatos '.png' y '.jpg'"
		}


class pdfForm(forms.ModelForm):
	class Meta:
		model = Reporte
		fields = ['ubicacion']

		labels = {
			'ubicacion': 'Seleccionar archivo'
		}
		help_texts = {
			'ubicacion': 'Solo se admiten archivos PDF, Excel y Word'
		}
