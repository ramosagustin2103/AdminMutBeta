from datetime import datetime, date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django_afip.models import *
from django.db import transaction
from django.db.models import Count
from django_mercadopago.models import Preference, Payment
from django.db.models import Q
from django.views import generic
from django.utils.decorators import method_decorator
from django.core.files.storage import FileSystemStorage
from formtools.wizard.views import SessionWizardView
from django.utils.timezone import now
from tablib import Dataset
from functools import partial, wraps

from admincu.funciones import *
from admincu.generic import OrderQS
from consorcios.models import *
from contabilidad.asientos.funciones import asiento_comp, asiento_compens
from arquitectura.models import *
from .funciones import *
from .forms import *
from .models import *
from .manager import ComprobanteCreator
from .filters import *
from expensas_pagas.models import CobroExp


mensaje_success = "Comprobante generado con exito."


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Index(OrderQS):

	""" Index de comprobantes """

	model = Comprobante
	template_name = 'comprobantes/index.html'
	filterset_class = ComprobanteFilter
	paginate_by = 10

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['a_generar_mp'] = len(
					Cobro.objects.filter(
						consorcio=consorcio(self.request),
						comprobante__isnull=True,
						preference__paid=True,
					).values('preference').annotate(mp=Count('preference'))
				)
		context['a_generar_exp'] = len(CobroExp.objects.filter(
			codigo_consorcio=consorcio(self.request).id,
			documentado__isnull=True
		))
				
		return context


@method_decorator(group_required('socio'), name='dispatch')
class IndexSocio(OrderQS):

	"""
		Index para el socio.
	"""

	model = Comprobante
	template_name = "comprobantes/socio/index.html"
	filterset_class = ComprobanteFilterSocio
	paginate_by = 50

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		socio = self.request.user.socio_set.first()
		context["pagos"] = Preference.objects.filter(
				cobro__socio=socio,
				cobro__comprobante__isnull=True,
				paid=True,
			).distinct()
		return context


	def get_queryset(self):
		return super().get_queryset(
			socio=self.request.user.socio_set.first()
		)


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Registro(OrderQS):

	""" Registro de comprobantes """

	model = Comprobante
	filterset_class = ComprobanteFilter
	template_name = 'comprobantes/registros/comprobantes.html'
	paginate_by = 50


class WizardComprobanteManager:

	""" Administrador de comprobantes """

	TEMPLATES = {
		"inicial": "comprobantes/nuevo/inicial.html",
		"creditos": "comprobantes/nuevo/creditos.html",
		"saldos": "comprobantes/nuevo/saldos.html",
		"cajas": "comprobantes/nuevo/cajas.html",
		"descripcion": "comprobantes/nuevo/descripcion.html",
		"importacion": "comprobantes/nuevo/importacion.html",
		"confirmacion": "comprobantes/nuevo/confirmacion.html",
		"revision": "comprobantes/nuevo/revision.html",
	}
	def obtener_creditos(self, socio, tipo):

		""" Obtiene los creditos a cobrar de un socio """
		if tipo == "Recibo X exp masivo":
			dominios = socio.socio.all()
			if dominios:
				creditos = Credito.objects.filter(
						dominio__in=dominios,
						fin__isnull=True,
						liquidacion__estado="confirmado",
						).order_by('periodo', 'fecha')
			else:
				creditos = Credito.objects.filter(
						socio=socio,
						liquidacion__estado="confirmado",
						dominio__isnull=True,
						fin__isnull=True,
						).order_by('periodo', 'fecha')
			return creditos


		data_inicial = self.hacer_inicial(tipo)
		fecha_operacion = data_inicial['fecha_operacion'] if data_inicial['fecha_operacion'] else date.today()
		condonacion = data_inicial['condonacion']

		dominios = socio.socio.all()
		#Ahora están ordenados de más antiguo a más reciente"
		if dominios:
			creditos = Credito.objects.filter(
					dominio__in=dominios,
					fin__isnull=True,
					liquidacion__estado="confirmado",
					).order_by('periodo', 'fecha')
		else:
			creditos = Credito.objects.filter(
					socio=socio,
					liquidacion__estado="confirmado",
					dominio__isnull=True,
					fin__isnull=True,
					).order_by('periodo', 'fecha')

		if creditos:
			cobros_mp = Cobro.objects.filter(
					credito__in=creditos,
					preference__paid=True,
				)
			if cobros_mp:
				excluir = [c.credito.id for c in cobros_mp]
				creditos = creditos.exclude(id__in=excluir)

			for c in creditos:
				if tipo == "Nota de Credito C" and c.int_desc() < 0:
					c.neto = c.bruto
				else:
					c.neto = c.subtotal(fecha_operacion=fecha_operacion, condonacion=condonacion)
					c.detalle_procesado = c.detalle_acc(fecha_operacion=fecha_operacion, condonacion=condonacion)

				c.interes = c.intereses(fecha_operacion=fecha_operacion) or 0.01

		return creditos

	def obtener_saldos(self, socio):

		""" Obtiene los saldos a favor de un socio """

		saldos = socio.get_saldos(fecha=date.today())
		return saldos


	def hacer_inicial(self, tipo):

		""" Crea la data inicial con el tipo de comprobante que debe realizar """

		data_inicial = self.get_cleaned_data_for_step('inicial')
		if data_inicial:
			data_inicial['tipo'] = tipo
			if tipo == "Nota de Credito C":
				data_inicial['fecha_operacion'] = None
				data_inicial['condonacion'] = False
			if tipo == "Recibo X exp":
				data_inicial['fecha_operacion'] = data_inicial['cobroexp'].fecha_cobro
				data_inicial['condonacion'] = False
			if tipo == "Recibo X exp masivo":
				data_inicial['fecha_operacion'] = None
				data_inicial['condonacion'] = False
		return data_inicial

	def hacer_cobros(self):

		"""
		Crea lista de DICCIONARIOS de cobros. No lista de objetos
		Para poder utilizar mejor en manager.py
		"""

		cobros = []
		data_creditos = self.get_cleaned_data_for_step('creditos')
		if data_creditos:
			for d in data_creditos:
				if d:
					if d['subtotal']:
						data = {
							'credito': Credito.objects.get(id=d['credito']),
							'subtotal': d['subtotal'] # Lo que coloca el usuario
						}
						cobros.append(data)


		return cobros


	def hacer_utilizaciones_de_saldos(self):

		"""
		Crea lista de DICCIONARIOS de saldos. No lista de objetos
		Para poder utilizar mejor en manager.py
		"""

		saldos = []
		data_saldos = self.get_cleaned_data_for_step('saldos')
		if data_saldos:
			for d in data_saldos:
				if d:
					if d['subtotal']:
						data = {
							'saldo': Saldo.objects.get(id=d['saldo']),
							'subtotal': d['subtotal'] # Lo que coloca el usuario
						}
						saldos.append(data)

		return saldos

	def hacer_cajas(self):

		"""
		Crea lista de DICCIONARIOS de caja. No lista de objetos
		Para poder utilizar mejor en manager.py
		"""

		cajas = []
		data_cajas = self.get_cleaned_data_for_step('cajas')
		if data_cajas:
			for d in data_cajas:
				if d:
					if d['subtotal']:
						data = {
							'caja': d['caja'],
							'referencia': d['referencia'],
							'subtotal': d['subtotal'] # Lo que coloca el usuario
						}
						cajas.append(data)
		return cajas

	def hacer_nuevo_saldo(self, **kwargs):

		"""
		Retorna solo el valor del nuevo saldo
		Para poder utilizar mejor en manager.py
		"""

		diferencia = kwargs['total'] - kwargs['suma']
		if diferencia > 0:
			return diferencia
		return

	def hacer_descripcion(self, tipo):

		""" Crea el string descripcion """

		descripcion = ""
		data_inicial = self.hacer_inicial(tipo)
		data_descripcion = self.get_cleaned_data_for_step('descripcion')
		if data_descripcion:
			descripcion += data_descripcion['descripcion']
			if data_inicial['fecha_operacion']:
				descripcion += '* Cobrado el dia {}.'.format(data_inicial['fecha_operacion'])
			if data_inicial['condonacion']:
				descripcion += '* Condonacion de intereses.'
		return descripcion


@method_decorator(group_required('administrativo'), name='dispatch')
class RCXWizard(WizardComprobanteManager, SessionWizardView):

	form_list = [
		('inicial', InicialForm),
		('creditos', CobroFormSet),
		('saldos', SaldoFormSet),
		('cajas', CajaFormSet),
		('descripcion', DescripcionForm),
		('confirmacion', ConfirmacionForm),
	]

	def calcular_total(self, **kwargs):

		""" Total particular en recibos """

		suma = 0
		try:
			for caja in kwargs['cajas']:
				suma += caja['subtotal']
		except:
			for k, v in kwargs.items():
				if k == "saldos":
					for saldo in v:
						suma -= saldo['subtotal']
				if k == "cobros":
					for cobro in v:
						suma += cobro['subtotal']
		return suma

	def get_template_names(self):
		return [self.TEMPLATES[self.steps.current]]

	def get_context_data(self, form, **kwargs):
		context = super().get_context_data(form=form, **kwargs)
		tipo = "Recibo X"
		extension = 'comprobantes/nuevo/Recibo.html'
		data_inicial = self.hacer_inicial(tipo)
		if data_inicial:
			socio = data_inicial['socio']
			cobros = self.hacer_cobros()
			utilizacion_saldos = self.hacer_utilizaciones_de_saldos()
			cajas = self.hacer_cajas()
			descripcion = self.hacer_descripcion(tipo)
			suma = self.calcular_total(cobros=cobros, saldos=utilizacion_saldos)
			total = self.calcular_total(cajas=cajas)
			nuevo_saldo = self.hacer_nuevo_saldo(
					total=total,
					suma=suma,
				)

			if self.steps.current == 'creditos':
				creditos = self.obtener_creditos(socio, tipo)
				bloqueo = bloqueador(creditos)
				sumar = True

			elif self.steps.current == 'saldos':
				saldos_a_utilizar = self.obtener_saldos(socio)
				validar = "La suma de saldos utilizados no puede ser mayor a {}".format(suma)

			elif self.steps.current == 'cajas':
				validar = "La suma no puede ser menor a {}".format(suma)

			elif self.steps.current == 'confirmacion':
				documento = ComprobanteCreator(
					data_inicial=data_inicial,
					data_descripcion=descripcion,
					data_cobros=cobros,
					data_utilizacion_saldos=utilizacion_saldos,
					data_nuevo_saldo=nuevo_saldo,
					data_cajas=cajas
				)
				cobros, creditos = documento.hacer_cobros_y_creditos()
				saldos = documento.hacer_utilizaciones_de_saldos()
				cajas = documento.hacer_cajas()
				nuevo_saldo = documento.hacer_nuevo_saldo()

		context.update(locals())

		return context

	def get_form_kwargs(self, step):
		kwargs = super().get_form_kwargs()
		if step == "inicial":
			kwargs.update({
					'consorcio': consorcio(self.request)
				})
		return kwargs

	def get_form(self, step=None, data=None, files=None):
		form = super().get_form(step, data, files)
		formset = False
		if data:
			if 'cajas' in data['rcx_wizard-current_step']:
				formset = True
		if step == "cajas":
			formset = True

		if formset:
			formset = formset_factory(wraps(CajaForm)(partial(CajaForm, consorcio=consorcio(self.request))), extra=5)
			form = formset(prefix='cajas', data=data)
		return form

	@transaction.atomic
	def done(self, form_list, **kwargs):
		tipo = "Recibo X"
		cobros = self.hacer_cobros()
		utilizacion_saldos = self.hacer_utilizaciones_de_saldos()
		cajas = self.hacer_cajas()
		suma = self.calcular_total(cobros=cobros, saldos=utilizacion_saldos)
		total = self.calcular_total(cajas=cajas)
		documento = ComprobanteCreator(
			data_inicial=self.hacer_inicial(tipo),
			data_descripcion=self.hacer_descripcion(tipo),
			data_cobros=cobros,
			data_utilizacion_saldos=utilizacion_saldos,
			data_nuevo_saldo=self.hacer_nuevo_saldo(total=total,suma=suma),
			data_cajas=cajas
		)
		evaluacion = documento.guardar()
		if type(evaluacion) == list:
			messages.error(self.request, evaluacion[0])
		else:
			messages.success(self.request, mensaje_success)
		return redirect('cobranzas')


@method_decorator(group_required('administrativo'), name='dispatch')
class RCXFacturaWizard(WizardComprobanteManager, SessionWizardView):

	form_list = [
		('saldos', SaldoFormSet),
		('cajas', CajaFormSet),
		('confirmacion', ConfirmacionForm),
	]

	def get_object(self):

		return Factura.objects.get(pk=self.kwargs['pk'])


	def calcular_total(self, **kwargs):

		""" Total particular en recibos """

		suma = 0
		try:
			for caja in kwargs['cajas']:
				suma += caja['subtotal']
		except:
			for k, v in kwargs.items():
				if k == "saldos":
					for saldo in v:
						suma -= saldo['subtotal']
				if k == "cobros":
					for cobro in v:
						suma += cobro['subtotal']
		return suma


	def get_template_names(self):
		return [self.TEMPLATES[self.steps.current]]

	def hacer_cobros(self):

		""" Particular """

		factura = self.get_object()
		creditos = factura.credito_set.all()
		cobros = []
		for c in creditos:
			data = {
				'credito': c,
				'subtotal': c.subtotal()
			}
			cobros.append(data)
		return cobros

	def hacer_inicial(self, tipo):

		""" Particular """
		factura = self.get_object()
		return {
			'punto': factura.receipt.point_of_sales,
			'socio': factura.socio,
			'fecha_operacion': None,
			'condonacion': False,
			'tipo': tipo
		}


	def get_context_data(self, form, **kwargs):
		context = super().get_context_data(form=form, **kwargs)
		tipo = "Recibo X"
		extension = 'comprobantes/nuevo/Recibo.html'
		factura = self.get_object()
		socio = factura.socio
		data_inicial = self.hacer_inicial(tipo)

		cobros = self.hacer_cobros()
		utilizacion_saldos = self.hacer_utilizaciones_de_saldos()
		cajas = self.hacer_cajas()
		descripcion = self.hacer_descripcion(tipo)
		suma = self.calcular_total(cobros=cobros, saldos=utilizacion_saldos)
		total = self.calcular_total(cajas=cajas)
		nuevo_saldo = self.hacer_nuevo_saldo(
				total=total,
				suma=suma,
			)

		if self.steps.current == 'saldos':
			saldos_a_utilizar = self.obtener_saldos(socio)
			validar = "La suma de saldos utilizados no puede ser mayor a {}".format(suma)

		elif self.steps.current == 'cajas':
			validar = "La suma no puede ser menor a {}".format(suma)

		elif self.steps.current == 'confirmacion':
			documento = ComprobanteCreator(
				data_inicial=data_inicial,
				data_descripcion=descripcion,
				data_cobros=cobros,
				data_utilizacion_saldos=utilizacion_saldos,
				data_nuevo_saldo=nuevo_saldo,
				data_cajas=cajas
			)
			cobros, creditos = documento.hacer_cobros_y_creditos()
			saldos = documento.hacer_utilizaciones_de_saldos()
			cajas = documento.hacer_cajas()
			nuevo_saldo = documento.hacer_nuevo_saldo()

		context.update(locals())

		return context

	def get_form_kwargs(self, step):
		kwargs = super().get_form_kwargs()
		if step == "inicial":
			kwargs.update({
					'consorcio': consorcio(self.request)
				})
		return kwargs

	def get_form(self, step=None, data=None, files=None):
		from functools import partial, wraps
		form = super().get_form(step, data, files)
		formset = False
		if data:
			if 'cajas' in data['rcx_factura_wizard-current_step']:
				formset = True
		if step == "cajas":
			formset = True

		if formset:
			formset = formset_factory(wraps(CajaForm)(partial(CajaForm, consorcio=consorcio(self.request))), extra=5)
			form = formset(prefix='cajas', data=data)
		return form

	@transaction.atomic
	def done(self, form_list, **kwargs):
		tipo = "Recibo X"
		data_inicial = self.hacer_inicial(tipo)
		cobros = self.hacer_cobros()
		utilizacion_saldos = self.hacer_utilizaciones_de_saldos()
		cajas = self.hacer_cajas()
		suma = self.calcular_total(cobros=cobros, saldos=utilizacion_saldos)
		total = self.calcular_total(cajas=cajas)
		documento = ComprobanteCreator(
			data_inicial=self.hacer_inicial(tipo),
			data_descripcion=self.hacer_descripcion(tipo),
			data_cobros=cobros,
			data_utilizacion_saldos=utilizacion_saldos,
			data_nuevo_saldo=self.hacer_nuevo_saldo(total=total,suma=suma),
			data_cajas=cajas
		)
		evaluacion = documento.guardar()
		if type(evaluacion) == list:
			messages.error(self.request, evaluacion[0])
		else:
			messages.success(self.request, mensaje_success)
		return redirect('cobranzas')


@method_decorator(group_required('administrativo'), name='dispatch')
class RCXMPWizard(WizardComprobanteManager, SessionWizardView):

	form_list = [
		('inicial', MPForm),
		('confirmacion', ConfirmacionForm),
	]

	def calcular_total(self, **kwargs):

		""" Total particular en mp """

		suma = 0
		for k, v in kwargs.items():
			if v:
				for cobro in v:
					suma += cobro.subtotal
		return suma

	def get_template_names(self):
		return [self.TEMPLATES[self.steps.current]]

	def get_context_data(self, form, **kwargs):
		context = super().get_context_data(form=form, **kwargs)
		tipo = "Recibo X"
		extension = 'comprobantes/nuevo/Recibo.html'
		data_inicial = self.hacer_inicial(tipo)
		if data_inicial:
			preference = data_inicial['preference']
			payment = preference.payments.filter(status="approved").first()
			cobros = preference.cobro_set.all()
			socio = cobros.first().socio
			data_inicial['socio'] = socio
			data_inicial['fecha_operacion'] = payment.created.date()
			data_inicial['condonacion'] = False
			suma = self.calcular_total(cobros=cobros)
			total = suma
			descripcion = "Cobrado por MercadoPago"

			if self.steps.current == 'confirmacion':
				documento = ComprobanteCreator(
					data_inicial=data_inicial,
					data_descripcion=descripcion,
					data_mp=cobros
				)
				cobros, creditos = documento.hacer_cobros_y_creditos()
				cajas = documento.hacer_cajas()

		context.update(locals())

		return context

	def get_form_kwargs(self, step):
		kwargs = super().get_form_kwargs()
		if step == "inicial":
			kwargs.update({
					'consorcio': consorcio(self.request)
				})
		return kwargs

	@transaction.atomic
	def done(self, form_list, **kwargs):
		tipo = "Recibo X"
		data_inicial = self.hacer_inicial(tipo)
		preference = data_inicial['preference']
		payment = preference.payments.filter(status="approved").first()
		cobros = preference.cobro_set.all()
		data_inicial['socio'] = cobros.first().socio
		data_inicial['fecha_operacion'] = payment.created.date()
		data_inicial['condonacion'] = False
		descripcion = "Cobrado por MercadoPago"
		documento = ComprobanteCreator(
			data_inicial=data_inicial,
			data_descripcion=descripcion,
			data_mp=cobros
		)
		evaluacion = documento.guardar()
		if type(evaluacion) == list:
			messages.error(self.request, evaluacion[0])
		else:
			messages.success(self.request, mensaje_success)
		return redirect('cobranzas')


@method_decorator(group_required('administrativo'), name='dispatch')
class RCXEXPWizard(WizardComprobanteManager, SessionWizardView):

	form_list = [
		('inicial', EXPForm),
		('creditos', CobroFormSet),
		('confirmacion', ConfirmacionForm),
	]

	def calcular_total(self, **kwargs):

		""" Total particular en exp """
		suma = 0
		try:
			for cobro in kwargs['cobros']:
				suma += cobro['subtotal']
		except:
			suma = self.hacer_inicial("Recibo X exp")['cobroexp'].importe_cobrado
		return suma


	def get_template_names(self):
		return [self.TEMPLATES[self.steps.current]]

	def get_context_data(self, form, **kwargs):
		context = super().get_context_data(form=form, **kwargs)
		tipo = "Recibo X exp"
		extension = 'comprobantes/nuevo/Recibo.html'
		data_inicial = self.hacer_inicial(tipo)
		if data_inicial:
			cobroexp = data_inicial['cobroexp']
			socio = Socio.objects.get(id=cobroexp.unidad_funcional)
			data_inicial['socio'] = socio			
			cobros = self.hacer_cobros()
			cajas = [{
					'subtotal': cobroexp.importe_cobrado,
					'referencia':'',
					'caja' : Caja.objects.get(consorcio=consorcio(self.request), nombre='Expensas Pagas')
			}]
			descripcion = "Cobrado Por Expensas Pagas - Canal de Pago: {} - Fecha: {}".format(cobroexp.canal_de_pago, cobroexp.fecha_cobro)
			data_inicial['condonacion'] = False
			total = cobroexp.importe_cobrado
			suma = self.calcular_total(cobros=cobros)
			total = self.calcular_total()
			nuevo_saldo = self.hacer_nuevo_saldo(
					total=total,
					suma=suma,
				)

			if self.steps.current == 'creditos':
				creditos = self.obtener_creditos(socio, tipo)
				bloqueo = bloqueador(creditos)
				sumar = True
				suma = total
				validar = "La suma de los creditos no puede ser mayor al cobro"


			if self.steps.current == 'confirmacion':
				documento = ComprobanteCreator(
					data_inicial=data_inicial,
					data_descripcion=descripcion,
					data_cobros=cobros,
					data_nuevo_saldo=nuevo_saldo,
					data_cajas=cajas
				)
				cobros, creditos = documento.hacer_cobros_y_creditos()
				cajas = documento.hacer_cajas()
				nuevo_saldo = documento.hacer_nuevo_saldo()

		context.update(locals())

		return context

	def get_form_kwargs(self, step):
		kwargs = super().get_form_kwargs()
		if step == "inicial":
			kwargs.update({
					'consorcio': consorcio(self.request)
				})
		return kwargs

	@transaction.atomic
	def done(self, form_list, **kwargs):
		tipo = "Recibo X exp"
		cobros = self.hacer_cobros()
		data_inicial = self.hacer_inicial(tipo)
		cobroexp = data_inicial['cobroexp']
		cajas = [{
				'subtotal': cobroexp.importe_cobrado,
				'referencia':'',
				'caja' : Caja.objects.get(consorcio=consorcio(self.request), nombre='Expensas Pagas')
		}]
		data_inicial['socio'] = Socio.objects.get(id=cobroexp.unidad_funcional)
		data_inicial['condonacion'] = False
		descripcion = "Cobrado Por Expensas Pagas - Canal de Pago: {} - Fecha: {}".format(cobroexp.canal_de_pago, cobroexp.fecha_cobro)
		suma = self.calcular_total(cobros=cobros)
		total = self.calcular_total(cajas=cajas)
		documento = ComprobanteCreator(
			data_inicial=data_inicial,
			data_descripcion=descripcion,
			data_cobros=cobros,
			data_nuevo_saldo=self.hacer_nuevo_saldo(total=total,suma=suma),
			data_cajas=cajas
		)
		evaluacion = documento.guardar()
		cobroexp.documentado = date.today() 
		cobroexp.save()
		if type(evaluacion) == list:
			messages.error(self.request, evaluacion[0])
		else:
			messages.success(self.request, mensaje_success)
		return redirect('cobranzas')

@method_decorator(group_required('administrativo'), name='dispatch')
class NCCWizard(WizardComprobanteManager, SessionWizardView):

	form_list = [
		('inicial', InicialForm),
		('creditos', CobroFormSet),
		('descripcion', DescripcionForm),
		('confirmacion', ConfirmacionForm),
	]

	def calcular_total(self, **kwargs):

		""" Total particular en notas de credito """

		suma = 0
		for k, v in kwargs.items():
			if v:
				for cobro in v:
					suma += cobro['subtotal']
		return suma

	def get_template_names(self):
		return [self.TEMPLATES[self.steps.current]]

	def get_context_data(self, form, **kwargs):
		context = super().get_context_data(form=form, **kwargs)
		tipo = "Nota de Credito C"
		extension = 'comprobantes/nuevo/13.html'
		data_inicial = self.hacer_inicial(tipo)
		if data_inicial:
			socio = data_inicial['socio']
			cobros = self.hacer_cobros()
			utilizacion_saldos = self.hacer_utilizaciones_de_saldos()
			descripcion = self.hacer_descripcion(tipo)
			suma = self.calcular_total(cobros=cobros)
			total = suma

			if self.steps.current == 'creditos':
				creditos = self.obtener_creditos(socio, tipo)
				bloqueo = bloqueador(creditos)
				sumar = True
				no_cero = True


			elif self.steps.current == 'confirmacion':
				documento = ComprobanteCreator(
					data_inicial=data_inicial,
					data_descripcion=descripcion,
					data_cobros=cobros,
				)
				cobros, creditos = documento.hacer_cobros_y_creditos()

		context.update(locals())

		return context

	def get_form_kwargs(self, step):
		kwargs = super().get_form_kwargs()
		if step == "inicial":
			kwargs.update({
					'consorcio': consorcio(self.request),
					'ok_ncc': True
				})
		return kwargs


	@transaction.atomic
	def done(self, form_list, **kwargs):
		tipo = "Nota de Credito C"
		documento = ComprobanteCreator(
			data_inicial=self.hacer_inicial(tipo),
			data_descripcion=self.hacer_descripcion(tipo),
			data_cobros=self.hacer_cobros(),
		)
		evaluacion = documento.guardar()
		if type(evaluacion) == list:
			messages.error(self.request, evaluacion[0])
		else:
			messages.success(self.request, mensaje_success)
		return redirect('cobranzas')


class HeaderExeptMixin:

	def dispatch(self, request, *args, **kwargs):
		try:
			objeto = self.model.objects.get(consorcio=consorcio(self.request), pk=kwargs['pk'])
		except:
			messages.error(request, 'No se pudo encontrar.')
			return redirect('cobranzas')

		return super().dispatch(request, *args, **kwargs)


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Ver(HeaderExeptMixin, generic.DetailView):

	""" Ver un comprobante """

	template_name = 'comprobantes/ver/comprobante.html'
	model = Comprobante

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['comprobante'] = self.get_object()
		return context


@method_decorator(group_required('administrativo', 'contable', 'socio'), name='dispatch')
class PDF(HeaderExeptMixin, generic.DetailView):


	""" Ver PDF de un comprobante """

	model = Comprobante
	template_name = 'comprobantes/ver/comprobante.html' # Solo para que no arroje error

	def get(self, request, *args, **kwargs):
		comprobante = self.get_object()
		if comprobante.pdf_anulado:
			response = HttpResponse(comprobante.pdf_anulado, content_type='application/pdf')
		else:
			response = HttpResponse(comprobante.pdf, content_type='application/pdf')
		nombre = "{}_{}.pdf".format(
			comprobante.tipo(),
			comprobante.nombre(),
		)
		content = "inline; filename=%s" % nombre
		response['Content-Disposition'] = content
		return response

	def dispatch(self, request, *args, **kwargs):
		disp = super().dispatch(request, *args, **kwargs)
		if disp.status_code == 200:
			if request.user.groups.first().name == "socio" and self.get_object().socio != request.user.socio_set.first():
				messages.error(request, 'No se pudo encontrar.')
				return redirect('home')
		return disp


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Anular(HeaderExeptMixin, generic.DeleteView):

	""" Para anular un comprobante """

	template_name = 'comprobantes/anular/comprobante.html'
	model = Comprobante

	@transaction.atomic
	def delete(self, request, *args, **kwargs):
		comprobante = self.get_object()
		# messages.error(request, 'Accion inhabilitada')
		saldo_comprobante = comprobante.saldos.filter(padre__isnull=True).first()
		if saldo_comprobante:
			if saldo_comprobante.saldo() != saldo_comprobante.subtotal:
				ultimo_hijo = saldo_comprobante.hijos.last()
				comprobante_destino = ultimo_hijo.comprobante_destino
				messages.error(request, 'Debe anular primero el comprobante {} {}.'.format(comprobante_destino.tipo(), comprobante_destino.nombre()))
				return redirect('ver-comprobante', pk=comprobante.pk)
		comprobante.anular()
		messages.success(request, 'Comprobante anulado con exito.')
		return redirect('ver-comprobante', pk=comprobante.pk)

	def dispatch(self, request, *args, **kwargs):
		disp = super().dispatch(request, *args, **kwargs)
		if disp.status_code == 200:
			comprobante = self.get_object()
			if not comprobante.punto:
				messages.error(request, 'No se puede anular una nota de credito.')
				return redirect('ver-comprobante', pk=comprobante.pk)
		return disp


@method_decorator(group_required('administrativo'), name='dispatch')
class RCXEXPMWizard(WizardComprobanteManager, SessionWizardView):

	form_list = [
		('inicial', EXPMForm),
		('confirmacion', ConfirmacionForm),
	]

	def calcular_total(self, **kwargs):

		""" Total particular en exp """
		suma = 0
		try:
			for cobro in kwargs['cobros']:
				suma += cobro['subtotal']
		except:
			suma = self.hacer_inicial("Recibo X exp")['cobroexp'].importe_cobrado
		return suma



	def get_template_names(self):
		return [self.TEMPLATES[self.steps.current]]

	# Esto es lo que tengo que modificar para el segundo paso: revisión de la imputación de los créditos.
	def get_context_data(self, form, **kwargs):
		context = super().get_context_data(form=form, **kwargs)
		tipo = "Recibo X exp masivo"
		extension = 'comprobantes/nuevo/Recibo.html'
		data_inicial = self.hacer_inicial(tipo)
		seleccion_multiple = True
		if data_inicial:
			caja = Caja.objects.get(consorcio=consorcio(self.request), nombre="Expensas Pagas")
			if self.steps.current == 'confirmacion':
				documentos = []
				creditos_predocumentados = []
				for cobro in data_inicial['cobroexp']:
					socio = Socio.objects.get(id=cobro.unidad_funcional)
					data_inicial['socio'] = socio
					fecha_operacion = cobro.fecha_cobro
					data_inicial['fecha_operacion'] = fecha_operacion
					creditos = self.obtener_creditos(socio,tipo)
					cobros = []
					remanente = cobro.importe_cobrado
					for c in creditos:
						if c not in creditos_predocumentados:
							subtotal = c.subtotal(fecha_operacion=fecha_operacion, condonacion=False)
							#Aquí es donde hay que corregir para que pueda imputar pagos parciales.
							if remanente >= subtotal:
								cobros.append({
									"credito" : c,
									"subtotal" : subtotal,
								})
								remanente -= subtotal
							creditos_predocumentados.append(c)
							
					nuevo_saldo = remanente	or None
					cajas = [{
						'subtotal': cobro.importe_cobrado,
						'referencia':'',
						'caja' : caja
					}]
					descripcion = "Cobrado Por Expensas Pagas - Canal de Pago: {} - Fecha: {}".format(cobro.canal_de_pago, cobro.fecha_cobro)
					data_inicial['tipo'] = "Recibo X exp"
					documento = ComprobanteCreator(
						data_inicial=data_inicial,
						data_descripcion=descripcion,
						data_cobros=cobros,
						data_nuevo_saldo=nuevo_saldo,
						data_cajas=cajas
					)
					cobros, creditos = documento.hacer_cobros_y_creditos()
					documentos.append(documento)
				masivo = True
			
		context.update(locals())

		return context

	def get_form_kwargs(self, step):
		kwargs = super().get_form_kwargs()
		if step == "inicial":
			kwargs.update({
					'consorcio': consorcio(self.request)
				})
		return kwargs

	

	@transaction.atomic
	def done(self, form_list, **kwargs):
		tipo = "Recibo X exp masivo"
		#cobros = self.hacer_cobros()
		data_inicial = self.hacer_inicial(tipo)
		if data_inicial:
			caja = Caja.objects.get(consorcio=consorcio(self.request), nombre="Expensas Pagas")
			creditos_predocumentados = []
			for cobro in data_inicial['cobroexp']:
				socio = Socio.objects.get(id=cobro.unidad_funcional)
				data_inicial['socio'] = socio
				fecha_operacion = cobro.fecha_cobro
				data_inicial['fecha_operacion'] = fecha_operacion
				creditos = self.obtener_creditos(socio,tipo)
				cobros = []
				remanente = cobro.importe_cobrado
				for c in creditos:
					if c not in creditos_predocumentados:
						subtotal = c.subtotal(fecha_operacion=fecha_operacion, condonacion=False)
						if remanente >= subtotal:
							cobros.append({
								"credito" : c,
								"subtotal" : subtotal,
							})
							remanente -= subtotal
						creditos_predocumentados.append(c)
						
				nuevo_saldo = remanente	
				cajas = [{
					'subtotal': cobro.importe_cobrado,
					'referencia':'',
					'caja' : caja
				}]
				descripcion = "Cobrado Por Expensas Pagas - Canal de Pago: {} - Fecha: {}".format(cobro.canal_de_pago, cobro.fecha_cobro)
				data_inicial['tipo'] = "Recibo X exp"
				documento = ComprobanteCreator(
					data_inicial=data_inicial,
					data_descripcion=descripcion,
					data_cobros=cobros,
					data_nuevo_saldo=nuevo_saldo,
					data_cajas=cajas
				)
				evaluacion = documento.guardar(masivo=True)
				cobro.documentado = date.today() 
				cobro.save()
				if type(evaluacion) == list:
					messages.error(self.request, evaluacion[0])
				else:
					messages.success(self.request, mensaje_success)
		return redirect('cobranzas')



@method_decorator(group_required('administrativo'), name='dispatch')
class CobrosImportacionWizard(WizardComprobanteManager, SessionWizardView):

	""" Index y registro de conceptos """

	file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'cobros'))

	form_list = [
		('importacion', ImportacionForm),
		('revision', ConfirmacionForm),
	]

	def leer_datos(self, archivo):

		""" Retorna los datos limpios """

		datos = Dataset()
		return datos.load(in_stream=archivo.read(), format='xls')

	def limpiar_datos(self, datos):

		"""
			Retorna un diccionario con diccionarios, uno para ingresos y otro para dominios
			Clave: lo que coloco el usuario
			Valor: El objeto en si
		"""

		# Validacion de columnas
		columnas_necesarias = ['socio', 'fecha', 'importe', 'caja']
		columnas_archivo = datos.headers
		print("hola")
		errores = ['Falta la columna "{}" en el archivo que deseas importar'.format(columna) for columna in columnas_necesarias if not columna in columnas_archivo]
		if errores:
			return errores


		data_socios = set(datos['socio'])
		socios = {}
		for s in data_socios:
			if not s in socios.keys():
				try:
					socios[s] = Socio.objects.get(consorcio=consorcio(self.request), id=s)
				except:
					pass

		data_cajas = set(datos['caja'])
		cajas = {}
		for c in data_cajas:
			if not c in cajas.keys():
				try:
					cajas[c] = Caja.objects.get(consorcio=consorcio(self.request), id=c)
				except:
					pass

		return {
			'socios': socios,
			'cajas': cajas,
		}


	def convertirFecha(self, valor):
		inicio_excel = date(1900, 1, 1)
		diferencia = timedelta(days=int(valor)-2)
		dia = (inicio_excel + diferencia)
		return dia

	def hacer_cobros(self, datos, objetos_limpios):

		"""
			Retorna un diccionario con diccionarios, uno para ingresos y otro para dominios
			Clave: lo que coloco el usuario
			Valor: El objeto en si
		"""

		cobros = []
		errores = []

		datos = datos.dict

		fila = 2 # Fila posterior a la de los titulos de las columnas
		for d in datos:
			if d['caja'] and d['socio'] and d['fecha'] and d['importe']:
				try:
					caja = objetos_limpios['cajas'][d['caja']]
					try:
						socio = objetos_limpios['socios'][d['socio']]
						try:
							fecha = self.convertirFecha(d['fecha'])
							try:
								importe = float(d['importe'])
								cobros.append({
									'codigo_consorcio':consorcio(self.request).id,
									'fecha_cobro':fecha,
									'canal_de_pago':caja,
									'unidad_funcional':socio,
									'importe_cobrado':importe,
								})
							except:
								errores.append("Linea {}: Debe escribir un numero en importe".format(fila))
						except:
							errores.append("Linea {}: Debe escribir una fecha valida en fecha".format(fila))
					except:
						errores.append("Linea {}: No se reconoce el socio".format(fila))
				except:
					errores.append("Linea {}: No se reconoce el metodo de cobro".format(fila))


			fila += 1

		return cobros, errores


	def get_template_names(self):
		return [self.TEMPLATES[self.steps.current]]

	def get_context_data(self, form, **kwargs):
		context = super().get_context_data(form=form, **kwargs)
		extension = 'comprobantes/nuevo/Recibo.html'
		peticion = "Carga de Cobros"
		tipo = "Importacion"
		archivo = self.get_cleaned_data_for_step('importacion')
		if archivo:
			archivo = self.get_cleaned_data_for_step('importacion')['archivo']
			datos = self.leer_datos(archivo)
			objetos_limpios = self.limpiar_datos(datos)
		if self.steps.current == 'revision':
			if type(objetos_limpios) == dict:
				cobros, errores = self.hacer_cobros(datos, objetos_limpios)
			else:
				errores = objetos_limpios

		context.update(locals())
		return context

	@transaction.atomic
	def done(self, form_list, **kwargs):
		data_inicial = {
			"punto": consorcio(self.request).contribuyente.points_of_sales.first(),
			"fecha_operacion": None,
			"concepto": None,
			"fecha_factura": None
		}
		archivo = self.get_cleaned_data_for_step('importacion')['archivo']
		datos = self.leer_datos(archivo)
		objetos_limpios = self.limpiar_datos(datos)
		cobros, errores = self.hacer_cobros(datos, objetos_limpios)
		cobrosexp = []
		for cobro in cobros:
			cobrosexp.append(CobroExp(
				codigo_consorcio=cobro['codigo_consorcio'],
				fecha_cobro=cobro['fecha_cobro'],
				canal_de_pago=cobro['canal_de_pago'].id,
				unidad_funcional=cobro['unidad_funcional'].id,
				importe_cobrado=cobro['importe_cobrado'],			
			))
		CobroExp.objects.bulk_create(cobrosexp)
		messages.success(self.request, "Cobros guardados con exito")
		return redirect('cobranzas')


