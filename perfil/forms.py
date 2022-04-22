from django import forms
from django.contrib.auth.models import User
from arquitectura.models import *

class userForm(forms.ModelForm):
	class Meta:
		model = User
		fields = [
			'first_name',
			'last_name',
			'email',
		]
		labels = {
			'first_name': "Nombre",
			'last_name': "Apellido",
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in iter(self.fields):
			self.fields[field].widget.attrs.update({
	        			'class': 'form-control'
	        	})

	def clean_first_name(self):
		first_name = self.cleaned_data['first_name']
		if not first_name:
			raise forms.ValidationError("Este campo es obligatorio.")
		return first_name

	def clean_last_name(self):
		last_name = self.cleaned_data['last_name']
		if not last_name:
			raise forms.ValidationError("Este campo es obligatorio.")
		return last_name
