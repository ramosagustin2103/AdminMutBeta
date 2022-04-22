from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models.functions import TruncMonth, TruncYear
from django_afip.models import *
from django.template.loader import render_to_string
from weasyprint import HTML
from django.db import transaction
from django.urls import reverse
from django.http import HttpResponse
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from django.utils.decorators import method_decorator
from django.views import generic
from django.urls import reverse_lazy

from admincu.funciones import *
from .manager import *
from consorcios.models import *
from arquitectura.models import *
from .models import *
from .forms import *
from .funciones import *
from contabilidad.models import *
from contabilidad.asientos.funciones import asiento_liq_auto
from contabilidad.funciones import generacionSyS
from comprobantes.models import *


@method_decorator(group_required('administrativo', 'contable', 'socio'), name='dispatch')
class Index(generic.ListView):

	"""
		Index de reportes.
	"""

	model = Cierre
	template_name = "reportes/index.html"

	# El socio solo tiene que poder ver la lista de reportes y solo los confirmados

	def get_queryset(self):
		cierres = Cierre.objects.filter(consorcio=consorcio(self.request))
		if self.request.user.groups.all()[0].name == "socio":
			cierres = cierres.filter(confirmado= True)
		return cierres.order_by('-periodo')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		cierres = self.get_queryset()
		years = list(cierres.annotate(year=TruncYear('periodo')).values('year'))
		context['anios'] = {
			anio['year'].year: cierres.filter(periodo__year=anio['year'].year) for anio in years
		}
		return context

@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class NuevoPeriodo(generic.CreateView):

	""" Para crear un nuevo periodo """

	model = Cierre
	template_name = 'reportes/nuevo/periodo.html'
	form_class = periodoForm

	def get_success_url(self, **kwargs):
		return reverse_lazy('cierre-procesamiento', args=(self.object.pk,))

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['consorcio'] = consorcio(self.request)
		return kwargs

	@transaction.atomic
	def form_valid(self, form):
		self.object = form.save(commit=False)
		self.object.consorcio = consorcio(self.request)
		return super().form_valid(form)


class HeaderExeptMixin:

	def dispatch(self, request, *args, **kwargs):
		try:
			objeto = self.model.objects.get(consorcio=consorcio(self.request), pk=kwargs['pk'])
		except:
			messages.error(request, 'No se pudo encontrar.')
			return redirect('reportes')

		return super().dispatch(request, *args, **kwargs)


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class NuevoProcesamiento(HeaderExeptMixin, generic.UpdateView):

	""" Para procesar el periodo. Es UpdateView para poder ponerle auditor """

	model = Cierre
	template_name = 'reportes/nuevo/procesamiento.html' # Solo para que no arroje error
	form_class = auditorForm

	def get_success_url(self, **kwargs):
		return reverse_lazy('cierre-procesamiento', args=(self.object.pk,))

	@transaction.atomic
	def form_valid(self, form):
		self.object = form.save(commit=False)
		if not self.object.admission:
			messages.error(self.request, 'No se admite el tipo de archivo que desea subir.')
			return super().form_invalid(form)

		return super().form_valid(form)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		cierre = self.object
		# Tabla de resultados
		resultadosManager = ResultadosManager(cierre)
		columnas = resultadosManager.hacer_columnas()
		resultados = resultadosManager.hacer_filas_resultados()

		# Situacion patrimonial
		cierreManager = CierreManager(cierre)
		subtotales_activo = cierreManager.hacer_activo()
		suma_activo = cierreManager.sumar(subtotales_activo)
		subtotales_pasivo = cierreManager.hacer_pasivo()
		suma_pasivo = cierreManager.sumar(subtotales_pasivo)
		subtotales_patrimonio = cierreManager.hacer_patrimonio()
		suma_patrimonio = cierreManager.sumar(subtotales_patrimonio)
		suma_pasivo_patrimonio = suma_pasivo + suma_patrimonio


		context.update(locals())
		return context


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class ArchivoGuardar(generic.CreateView):

	model = Reporte
	template_name = 'reportes/nuevo/periodo.html' # Solo para que no de error
	form_class = pdfForm

	@transaction.atomic
	def form_valid(self, form):
		cierre = Cierre.objects.get(pk=self.kwargs['pk'])
		self.object = form.save(commit=False)
		self.object.consorcio = consorcio(self.request)
		self.object.cierre = cierre
		self.object.nombre = str(self.request.FILES['ubicacion'])
		if not self.object.admission:
			messages.error(self.request, 'No se admite el tipo de archivo que desea subir.')
			return redirect('cierre-procesamiento', pk=cierre.pk)

		return super().form_valid(form)

	def get_success_url(self, **kwargs):
		return reverse_lazy('cierre-procesamiento', args=(self.object.cierre.pk,))

@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class ArchivoEliminar(HeaderExeptMixin, generic.DeleteView):

	model = Reporte
	template_name = 'reportes/nuevo/eliminar.html'

	def get_success_url(self, **kwargs):
		return reverse_lazy('cierre-procesamiento', args=(self.object.cierre.pk,))


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class CierreEliminar(HeaderExeptMixin, generic.DeleteView):

	model = Cierre
	template_name = 'reportes/nuevo/eliminar.html'
	success_url = '/reportes/'

	def dispatch(self, request, *args, **kwargs):
		disp = super().dispatch(request, *args, **kwargs)
		if disp.status_code == 200 and self.get_object().confirmado:
			messages.error(request, 'No se pudo encontrar.')
			return redirect('reportes')
		return disp

@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class CierreConfirmar(HeaderExeptMixin, generic.DeleteView):

	model = Cierre
	template_name = 'reportes/nuevo/confirmar.html'
	success_url = "/reportes/"

	@transaction.atomic
	def delete(self, request, *args, **kwargs):

		""" Confirmacion del cierre """

		cierre = self.get_object()
		statics = request.build_absolute_uri()

		# Resultados
		resultadosManager = ResultadosManager(cierre)
		resultadosManager.guardar(statics)

		# Situacion patrimonial
		cierreManager = CierreManager(cierre)
		cierreManager.guardar(statics)

		messages.success(self.request, 'Cierre confirmado con exito. Mails en cola de envios')
		return redirect('reportes')

	def dispatch(self, request, *args, **kwargs):
		disp = super().dispatch(request, *args, **kwargs)
		if disp.status_code == 200 and self.get_object().confirmado:
			messages.error(request, 'No se pudo encontrar.')
			return redirect('reportes')
		return disp

@method_decorator(group_required('administrativo', 'contable', 'socio'), name='dispatch')
class CierreVer(HeaderExeptMixin, generic.DetailView):

	model = Cierre
	template_name = 'reportes/ver/cierre.html' # Solo para que no arroje error

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		cierre = self.object
		# Tabla de resultados
		resultadosManager = ResultadosManager(cierre)
		columnas = resultadosManager.hacer_columnas()
		resultados = resultadosManager.hacer_filas_resultados()

		# Situacion patrimonial
		cierreManager = CierreManager(cierre)
		subtotales_activo = cierreManager.hacer_activo()
		suma_activo = cierreManager.sumar(subtotales_activo)
		subtotales_pasivo = cierreManager.hacer_pasivo()
		suma_pasivo = cierreManager.sumar(subtotales_pasivo)
		subtotales_patrimonio = cierreManager.hacer_patrimonio()
		suma_patrimonio = cierreManager.sumar(subtotales_patrimonio)
		suma_pasivo_patrimonio = suma_pasivo + suma_patrimonio


		context.update(locals())
		return context

	def dispatch(self, request, *args, **kwargs):
		disp = super().dispatch(request, *args, **kwargs)
		if disp.status_code == 200 and not self.get_object().confirmado:
			messages.error(request, 'No se pudo encontrar.')
			return redirect('reportes')
		return disp


@method_decorator(group_required('administrativo', 'contable', 'socio'), name='dispatch')
class PDFReporte(HeaderExeptMixin, generic.DetailView):

	""" Ver PDF de un reporte """

	model = Reporte
	template_name = 'reportes/pdfs/sit-pat.html' # Solo para que no arroje error

	def get(self, request, *args, **kwargs):
		reporte = self.get_object()
		response = HttpResponse(reporte.ubicacion, content_type='application/pdf')
		nombre = reporte.nombre
		content = "attachment; filename=%s" % nombre
		response['Content-Disposition'] = content
		return response
