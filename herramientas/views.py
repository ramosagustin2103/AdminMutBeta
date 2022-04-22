from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views import generic
from formtools.wizard.views import SessionWizardView
from django.db import transaction
from django.http import HttpResponse

from consorcios.models import *
from admincu.funciones import *
from creditos.models import Credito
from resumenes.models import *
from admincu.generic import OrderQS
from comprobantes.forms import CajaForm, CajaFormSet, ConfirmacionForm
from .models import *
from .filters import *
from .forms import *
from .manager import *


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Index(generic.TemplateView):

	"""
		Index de herramientas.
	"""

	template_name = 'herramientas/index.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['resumenes'] = Resumen.objects.all().order_by('nombre')
		return context



@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Rg3369(generic.TemplateView):

	template_name = 'herramientas/rg3369/index.html'

	def post(self, request, *args, **kwargs):
		fechas = request.POST.get('fechas')
		if fechas:
			rango = fechas.split(" / ")
			creditos = Credito.objects.filter(
					consorcio=consorcio(request),
					periodo__range=rango,
					dominio__isnull=False
				)
			informantes = {}
			for c in creditos:
				valor = informantes.setdefault(c.socio, [[], 0]) # El primer valor es la superficie y el segundo el monto
				valor[0].append(c.dominio) if not c.dominio in valor[0] else c.socio.socio.first()
				valor[1] += c.capital
				informantes[c.socio] = valor


			for socio, parametros in informantes.copy().items():

				# Parametros segun afip
				afip_monto = 8000
				afip_superficie = 100 if consorcio(request).tipo.nombre == "CONSORCIO DE EDIF DE DEPTO Y PH" else 400

				# Determinacion
				monto = True if parametros[1] < afip_monto else False
				superficies = True if sum([d.superficie_total or 0 for d in parametros[0]]) < afip_superficie else False

				if monto and superficies:
					del informantes[socio]

			espacio = " "

		return render(request, self.template_name, locals())


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class TransferenciasIndex(OrderQS):

	""" Index de transferencias """

	model = Transferencia
	template_name = 'herramientas/transferencias/index.html'
	filterset_class = TransferenciaFilter
	paginate_by = 10


@method_decorator(group_required('administrativo'), name='dispatch')
class TransferenciaWizard(SessionWizardView):

	TEMPLATES = {
		"inicial": "herramientas/transferencias/nuevo/inicial.html",
		"cajas": "herramientas/transferencias/nuevo/cajas.html",
		"confirmacion": "herramientas/transferencias/nuevo/confirmacion.html",
	}

	form_list = [
		('inicial', InicialForm),
		('cajas', CajaFormSet),
		('confirmacion', ConfirmacionForm),
	]

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

	def calcular_total(self, **kwargs):

		""" Total de transferencias """

		suma = 0
		for caja in kwargs['cajas']:
			suma += caja['subtotal']
		return suma


	def get_template_names(self):
		return [self.TEMPLATES[self.steps.current]]

	def get_context_data(self, form, **kwargs):
		context = super().get_context_data(form=form, **kwargs)
		data_inicial = self.get_cleaned_data_for_step('inicial')
		if data_inicial:
			cajas = self.hacer_cajas()
			total = self.calcular_total(cajas=cajas)

			if self.steps.current == 'confirmacion':
				documento = TransferenciaCreator(
					data_inicial=data_inicial,
					data_cajas=cajas
				)

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

	def get_form(self, step=None, data=None, files=None):
		from functools import partial, wraps
		form = super().get_form(step, data, files)
		formset = False
		if data:
			if 'cajas' in data['transferencia_wizard-current_step']:
				formset = True
		if step == "cajas":
			formset = True

		if formset:
			formset = formset_factory(wraps(CajaForm)(partial(CajaForm, consorcio=consorcio(self.request))), extra=5)
			form = formset(prefix='cajas', data=data)
		return form

	@transaction.atomic
	def done(self, form_list, **kwargs):
		data_inicial = self.get_cleaned_data_for_step('inicial')
		cajas = self.hacer_cajas()
		documento = TransferenciaCreator(
			data_inicial=data_inicial,
			data_cajas=cajas
		)
		documento.guardar()
		messages.success(self.request, "Transferencia entre cajas generada con exito")
		return redirect('transferencias')


class HeaderExeptMixin:

	def dispatch(self, request, *args, **kwargs):
		try:
			objeto = self.model.objects.get(consorcio=consorcio(self.request), pk=kwargs['pk'])
		except:
			messages.error(request, 'No se pudo encontrar.')
			return redirect('transferencias')

		return super().dispatch(request, *args, **kwargs)


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class PDFTransferencia(HeaderExeptMixin, generic.DetailView):

	""" Ver PDF de una transferencia """

	model = Transferencia
	template_name = 'herramientas/transferencias/index.html' # Solo para que no arroje error

	def get(self, request, *args, **kwargs):
		transferencia = self.get_object()
		response = HttpResponse(transferencia.pdf, content_type='application/pdf')
		nombre = "Transferencia_%s.pdf" % (transferencia.formatoAfip())
		content = "inline; filename=%s" % nombre
		response['Content-Disposition'] = content
		return response


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class RegistroTransferencias(OrderQS):

	""" Registro de transferenias """

	model = Transferencia
	filterset_class = TransferenciaFilter
	template_name = "herramientas/transferencias/registros/transferencias.html"
	paginate_by = 50
