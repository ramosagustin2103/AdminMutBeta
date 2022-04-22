from django import forms
from django.forms import Textarea, TextInput, NullBooleanSelect, Select
from arquitectura.models import *
from creditos.models import *
from expensas_pagas.models import CobroExp
from .models import *
from django_afip.models import *
from django.db.models import Count
from django.forms import formset_factory
from django_mercadopago.models import Preference

from admincu.forms import *

class FormControl(forms.Form):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in iter(self.fields):
			clase = 'form-control'
			if field == 'fecha_operacion':
				clase += ' datepicker'
			elif field == 'subtotal':
				clase += ' subtotal'
			elif field == 'caja':
				clase += ' caja'
			attrs = {
				'class': clase
			}
			if field == 'subtotal':
				attrs.update({
						'min': 0.01
					})

			self.fields[field].widget.attrs.update(attrs)


class InicialForm(FormControl, forms.Form):

	""" Paso 1 de Recibo C y Nota de Credito C """

	punto = forms.ModelChoiceField(queryset=PointOfSales.objects.none(), empty_label="-- Seleccionar Punto de gestion --", label="Punto de gestion")
	socio = forms.ModelChoiceField(queryset=Socio.objects.none(), empty_label="-- Seleccionar Socio --")
	fecha_operacion = forms.DateField(required=False, label="Fecha de la operacion")
	condonacion = forms.BooleanField(required=False)

	def __init__(self, *args, **kwargs):
		consorcio = kwargs.pop('consorcio')
		try:
			ok_ncc = kwargs.pop('ok_ncc')
		except:
			ok_ncc = False
		super().__init__(*args, **kwargs)
		self.fields['punto'].queryset = PointOfSales.objects.filter(owner=consorcio.contribuyente)
		self.fields['socio'].queryset = Socio.objects.filter(consorcio=consorcio)
		if ok_ncc:
			self.fields.pop('fecha_operacion')
			self.fields.pop('condonacion')

class CobroForm(FormControl, forms.Form):

	""" Paso de Creditos """

	credito = forms.IntegerField()
	subtotal = forms.DecimalField(required=False, max_digits=20, decimal_places=2)


CobroFormSet = formset_factory(
		form=CobroForm,
		extra=200
	)

class SaldoForm(FormControl, forms.Form):

	""" Paso de saldos """

	saldo = forms.IntegerField(required=False)
	subtotal = forms.DecimalField(required=False, max_digits=20, decimal_places=2)


SaldoFormSet = formset_factory(
		form=SaldoForm,
		extra=100
	)

class CajaForm(FormControl, forms.Form):

	""" Paso de cajas """

	caja = forms.ModelChoiceField(queryset=Caja.objects.none(), empty_label="-- Seleccionar Caja --", label="Caja", required=False)
	referencia = forms.CharField(max_length=10, required=False)
	subtotal = forms.DecimalField(max_digits=20, decimal_places=2, required=False)

	def __init__(self, consorcio, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['caja'].queryset = Caja.objects.filter(consorcio=consorcio)

CajaFormSet = formset_factory(
		form=CajaForm,
		extra=5,
	)

class DescripcionForm(FormControl, forms.Form):

	""" Descripcion del comprobante """

	descripcion = forms.CharField(widget=forms.Textarea, required=False)


class MPForm(FormControl, forms.Form):

	""" Paso 1 de Recibo C a traves de un pago por MP """

	punto = forms.ModelChoiceField(queryset=PointOfSales.objects.none(), empty_label="-- Seleccionar Punto de gestion --", label="Punto de gestion")
	preference = forms.ModelChoiceField(queryset=Preference.objects.none(), empty_label="-- Seleccionar cobro --", label="Cobros desde MercadoPago")

	def __init__(self, *args, **kwargs):
		consorcio = kwargs.pop('consorcio')
		super().__init__(*args, **kwargs)
		self.fields['punto'].queryset = PointOfSales.objects.filter(owner=consorcio.contribuyente)
		self.fields['preference'].queryset = Preference.objects.filter(
			cobro__consorcio=consorcio,
			cobro__comprobante__isnull=True,
			paid=True
		).distinct()
		self.fields['preference'].label_from_instance = self.label_from_instance


	def label_from_instance(self, obj):
		socio = obj.cobro_set.first().socio
		return "{} - {}".format(socio, obj)



class EXPForm(FormControl, forms.Form):

	""" Paso 1 de Recibo C a traves de un pago por MP """

	punto = forms.ModelChoiceField(queryset=PointOfSales.objects.none(), empty_label="-- Seleccionar Punto de gestion --", label="Punto de gestion")
	cobroexp = forms.ModelChoiceField(queryset=CobroExp.objects.none(), empty_label="-- Seleccionar cobro --", label="Cobros desde ExpensasPagas")

	def __init__(self, *args, **kwargs):
		consorcio = kwargs.pop('consorcio')
		super().__init__(*args, **kwargs)
		self.fields['punto'].queryset = PointOfSales.objects.filter(owner=consorcio.contribuyente)
		self.fields['cobroexp'].queryset = CobroExp.objects.filter(
			codigo_consorcio=consorcio.id,
			documentado__isnull=True,
		).distinct()
		self.fields['cobroexp'].label_from_instance = self.label_from_instance

	def label_from_instance(self, obj):
		socio = Socio.objects.get(id=obj.unidad_funcional)
		canal_de_pago = obj.canal_de_pago

		return "{} - FECHA: {} - CANAL DE PAGO: {} - MONTO ABONADO: {}".format(socio, obj.fecha_cobro, obj.canal_de_pago, obj.importe_cobrado)


class ConfirmacionForm(FormControl, forms.Form):

	""" Confirmacion del comprobante """

	confirmacion = forms.IntegerField(widget=forms.HiddenInput(), required=False)


class cajaForm(forms.ModelForm):
	class Meta:
		model = CajaComprobante
		fields = ['caja', 'referencia', 'valor']

	def __init__(self, consorcio=None, *args, **kwargs):
		self.consorcio = consorcio
		super(cajaForm, self).__init__(*args, **kwargs)
		for field in iter(self.fields):
			self.fields[field].widget.attrs.update({
						'class': 'form-control',
				})
		self.fields['caja'].queryset = Caja.objects.filter(consorcio=self.consorcio, primario=False)


class descripcionForm(forms.ModelForm):
	class Meta:
		model = Comprobante
		fields = ['descripcion']
		labels = {
			'descripcion': 'Observaciones',
		}
		widgets = {
			'descripcion': Textarea(attrs={'rows': 3}),
		}

	def __init__(self, consorcio=None, *args, **kwargs):
		self.consorcio = consorcio
		super(descripcionForm, self).__init__(*args, **kwargs)
		for field in iter(self.fields):
			self.fields[field].widget.attrs.update({
						'class': 'form-control',
				})

class EXPMForm(FormControl, forms.Form):

	""" Paso 1 de Recibo C a traves de un pago por MP """

	punto = forms.ModelChoiceField(queryset=PointOfSales.objects.none(), empty_label="-- Seleccionar Punto de gestion --", label="Punto de gestion")
	cobroexp = forms.ModelMultipleChoiceField(queryset=CobroExp.objects.none(), label="Seleccionar Cobros de Expensas Pagas. Use ctrl para selección multiple")

	def __init__(self, *args, **kwargs):
		consorcio = kwargs.pop('consorcio')
		super().__init__(*args, **kwargs)
		self.fields['punto'].queryset = PointOfSales.objects.filter(owner=consorcio.contribuyente)
		used_query = CobroExp.objects.filter(
			codigo_consorcio=consorcio.id,
			documentado__isnull=True,
		).distinct().order_by('fecha_cobro')
		self.fields['cobroexp'].queryset = used_query
		self.fields['cobroexp'].label_from_instance = self.label_from_instance
		# intento de preseleccionar todos los cobros, otra idea puede ser crear un boton para seleccionar y deseleccionar todo
		# self.fields['cobroexp'].initial = [(cobroexp.fecha_cobro) for cobroexp in used_query]

	def label_from_instance(self, obj):
		socio = Socio.objects.get(id=obj.unidad_funcional)
		canal_de_pago = obj.canal_de_pago

		return "{} - FECHA: {} - CANAL DE PAGO: {} - MONTO ABONADO: {}".format(socio, obj.fecha_cobro, obj.canal_de_pago, obj.importe_cobrado)


class ImportacionForm(forms.Form):

	""" Importacion de un archivo """

	archivo = ExcelFileField()
