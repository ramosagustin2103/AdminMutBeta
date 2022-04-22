from django import forms
from django.forms import Textarea, TextInput, NullBooleanSelect, Select
from contabilidad.models import *

class ejercicioForm(forms.ModelForm):
	class Meta:
		model = Ejercicio
		fields = ['nombre', 'inicio', 'cierre']
		labels = {
			'nombre': 'Nombre del ejercicio',
			'inicio': 'Fecha de inicio',
			'cierre': 'Fecha de cierre',
		}

	def __init__(self, consorcio=None, *args, **kwargs):
		self.consorcio = consorcio
		super(ejercicioForm, self).__init__(*args, **kwargs)
		for field in iter(self.fields):
			self.fields[field].widget.attrs.update({
						'class': 'form-control',
				})
