from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django_afip.models import PointOfSales
from django.db import transaction
from django.views import generic
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from django.urls import reverse_lazy

from admincu.funciones import *
from consorcios.models import *
from .models import *
from .forms import *
from creditos.models import Factura

@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Index(generic.TemplateView):

	""" Index de parametros """

	template_name = 'arquitectura/index.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		ingresos = Ingreso.objects.filter(consorcio=consorcio(self.request)).count()
		gastos = Gasto.objects.filter(consorcio=consorcio(self.request)).count()
		puntos = PointOfSales.objects.filter(owner=consorcio(self.request).contribuyente).count()
		cajas = Caja.objects.filter(consorcio=consorcio(self.request)).count()
		intereses = Accesorio.objects.filter(consorcio=consorcio(self.request), clase='interes', finalizacion__isnull=True).count()
		descuentos = Accesorio.objects.filter(consorcio=consorcio(self.request), clase='descuento', finalizacion__isnull=True).count()
		bonificaciones = Accesorio.objects.filter(consorcio=consorcio(self.request), clase='bonificacion', finalizacion__isnull=True).count()
		cajas = Caja.objects.filter(consorcio=consorcio(self.request)).count()
		socios = Socio.objects.filter(consorcio=consorcio(self.request), es_socio=True, baja__isnull=True).count()
		dominios = Dominio.objects.filter(consorcio=consorcio(self.request)).count()
		grupos = Grupo.objects.filter(consorcio=consorcio(self.request), baja__isnull=True).count()
		acreedores = Acreedor.objects.filter(consorcio=consorcio(self.request)).count()
		clientes = Socio.objects.filter(consorcio=consorcio(self.request), es_socio=False, baja__isnull=True).count()
		context.update(locals())
		return context


PIVOT = {
	'Ingreso': ['Recursos', ingresoForm],
	'Gasto': ['Erogaciones', gastoForm],
	'Caja': ['Tesoro', cajaForm],
	'Punto': ['Puntos de gestion', ],
	'Socio': ['Socios', socioForm],
	'Dominio': ['Dominios', dominioForm],
	'Grupo': ['Grupos de dominios', grupoForm],
	'Acreedor': ['Acreedores', acreedorForm],
	'Cliente': ['Clientes', clienteForm],
	'interes': ['Intereses', interesForm],
	'descuento': ['Descuentos', descuentoForm],
	'bonificacion': ['Bonificaciones', bonificacionForm],

}

@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Listado(generic.ListView):

	""" Lista del modelo seleccionado """

	template_name = 'arquitectura/parametro.html'

	def get_queryset(self, **kwargs):
		if self.kwargs['modelo'] == "Punto":
			objetos = PointOfSales.objects.filter(owner=consorcio(self.request).contribuyente).order_by('number')
		elif self.kwargs['modelo'] == "Cliente":
			objetos = Socio.objects.filter(consorcio=consorcio(self.request), es_socio=False)
		else:
			objetos = eval(self.kwargs['modelo']).objects.filter(consorcio=consorcio(self.request))
			if self.kwargs['modelo'] == "Socio":
				objetos = objetos.filter(es_socio=True)

		return objetos

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context["parametro"] = self.kwargs['modelo']
		context["nombre_parametro"] = PIVOT[self.kwargs['modelo']][0]
		return context


@group_required('administrativo', 'contable')
def arq_puntos(request):
	if valid_demo(request.user):
		return redirect('parametro', modelo="Punto")

	try:
		puntos = consorcio(request).contribuyente.fetch_points_of_sales()
	except:
		messages.error(request, 'Hubo un error al consultar en la base de datos de AFIP. Intentalo nuevamente y si el error persiste comunicate con el encargado de sistemas.')

	return redirect('parametro', modelo="Punto")


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Crear(generic.CreateView):

	""" Para crear una nueva instancia de cualquier modelo excepto Punto """

	template_name = 'arquitectura/instancia.html'
	model = None

	def get_form_class(self):
		return PIVOT[self.kwargs['modelo']][1]

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['consorcio'] = consorcio(self.request)
		return kwargs

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		parametro = self.kwargs['modelo']
		pregunta = PIVOT[self.kwargs['modelo']][0]
		alerta = "Solo podes modificar estas opciones en un %s principal. Si necesita ayuda comuniquese con el encargado de sistema" % parametro
		context.update(locals())
		return context

	def get_success_url(self, **kwargs):
		return reverse_lazy('parametro', args=(self.kwargs['modelo'],))

	@transaction.atomic
	def form_valid(self, form):
		objeto = form.save(commit=False)
		objeto.consorcio = consorcio(self.request)
		try:
			objeto.validate_unique()
			if self.kwargs['modelo'] == "Cliente":
				objeto.es_socio = False
			objeto.save()
			form.save_m2m()
			mensaje = "{} guardado con exito".format(self.kwargs['modelo'])
			messages.success(self.request, mensaje)
		except ValidationError:
			form._errors["numero"] = ErrorList([u"Ya existe el numero que desea utilizar."])
			return super().form_invalid(form)

		return super().form_valid(form)

class HeaderExeptMixin:

	def dispatch(self, request, *args, **kwargs):
		try:
			if kwargs['modelo'] == "Cliente":
				objeto = Socio.objects.get(consorcio=consorcio(self.request), pk=kwargs['pk'], es_socio=False)
			else:
				objeto = eval(kwargs['modelo']).objects.get(consorcio=consorcio(self.request), pk=kwargs['pk'])
		except:
			messages.error(request, 'No se pudo encontrar.')
			return redirect('parametros')

		return super().dispatch(request, *args, **kwargs)

@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Instancia(HeaderExeptMixin, Crear, generic.UpdateView):

	""" Para modificar una instancia de cualquier modelo excepto Punto """

	def get_object(self, queryset=None):
		if self.kwargs['modelo'] == "Cliente":
			objeto = Socio.objects.get(pk=self.kwargs['pk'], es_socio=False)
		else:
			objeto = eval(self.kwargs['modelo']).objects.get(pk=self.kwargs['pk'])
		return objeto

	@transaction.atomic
	def form_valid(self, form):
		retorno = super().form_valid(form)
		objeto = self.get_object()
		if self.kwargs['modelo'] in ["Cliente", "Socio"]:
			facturas = Factura.objects.filter(socio=objeto, receipt__receipt_number__isnull=True)
			for factura in facturas:
				factura.receipt.document_type = objeto.tipo_documento
				factura.receipt.document_number = objeto.numero_documento
				factura.receipt.save()
		return retorno


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class ListadoAccesorio(generic.ListView):

	""" Lista de accesorios, descuento o intereses """

	template_name = 'arquitectura/parametro.html'
	model = Accesorio

	def get_queryset(self, **kwargs):
		return Accesorio.objects.filter(consorcio=consorcio(self.request), clase=self.kwargs['clase']).order_by('-id')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context["parametro"] = self.kwargs['clase']
		context["nombre_parametro"] = PIVOT[self.kwargs['clase']][0]
		return context


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class CrearAccesorio(generic.CreateView):

	""" Crear un accesorio, descuento o interes """

	template_name = 'arquitectura/instancia.html'
	model = Accesorio


	def get_form_class(self):
		return PIVOT[self.kwargs['clase']][1]

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['pregunta'] = PIVOT[self.kwargs['clase']][0]
		return context

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['consorcio'] = consorcio(self.request)
		return kwargs

	def get_success_url(self, **kwargs):
		return reverse_lazy('listado_accesorio', args=(self.kwargs['clase'],))


	@transaction.atomic
	def form_valid(self, form):
		objeto = form.save(commit=False)
		objeto.consorcio = consorcio(self.request)
		objeto.clase = self.kwargs['clase']
		objeto.save()
		form.save_m2m()
		anteriores = Accesorio.objects.filter(
			consorcio=objeto.consorcio,
			clase=objeto.clase,
			ingreso__in=objeto.ingreso.all(),
			finalizacion__isnull=True,
			plazo__isnull=True if not objeto.plazo else False
		)
		if anteriores:
			anteriores.update(finalizacion=date.today())
		mensaje = "{} guardado con exito".format(self.kwargs['clase'])
		messages.success(self.request, mensaje)
		return super().form_valid(form)


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class FinalizarAccesorio(generic.UpdateView):

	""" Finalizar un accesorio, descuento o interes """

	template_name = 'arquitectura/instancia.html'
	model = Accesorio
	form_class = hiddenForm


	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		pregunta = self.get_object().clase
		respuesta = "Esta accion inutilizara la aplicacion de este {} en los futuras facturas que realice. Esta seguro? ".format(pregunta)
		context.update(locals())
		return context

	def get_success_url(self, **kwargs):
		return reverse_lazy('listado_accesorio', args=(self.get_object().clase,))


	@transaction.atomic
	def form_valid(self, form):
		objeto = self.get_object()
		objeto.finalizacion = date.today()
		objeto.save()
		return redirect('listado_accesorio', clase=objeto.clase)

	def dispatch(self, request, *args, **kwargs):
		try:
			accesorio = Accesorio.objects.get(pk=kwargs['pk'], consorcio=consorcio(request))
		except:
			messages.error(request, 'No se pudo encontrar.')
			return redirect('parametros')
		return super().dispatch(request, *args, **kwargs)



@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Finalizar(HeaderExeptMixin, generic.UpdateView):


	""" Finalizar un grupo o socio """

	template_name = 'arquitectura/instancia.html'
	form_class = hiddenForm

	def get_object(self, queryset=None):
		if self.kwargs['modelo'] == "Cliente":
			objeto = Socio.objects.get(pk=self.kwargs['pk'], es_socio=False)
		else:
			objeto = eval(self.kwargs['modelo']).objects.get(pk=self.kwargs['pk'])
		return objeto


	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		pregunta = self.get_object()
		respuesta = "Estas por dar de baja del sistema al {} {}. Si estas seguro de continuar presiona guardar.".format(self.kwargs['modelo'], pregunta)
		context.update(locals())
		return context


	def get_success_url(self, **kwargs):
		return reverse_lazy('parametros')


	@transaction.atomic
	def form_valid(self, form):
		objeto = self.get_object()
		objeto.baja = date.today()
		objeto.save()
		if self.kwargs['modelo'] == "Socio":
			if objeto.usuarios.all():
				for usuario in objeto.usuarios.all():
					usuario.is_active = False
					usuario.save()
		return redirect('parametro', modelo=self.kwargs['modelo'])



@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Reactivar(HeaderExeptMixin, generic.UpdateView):


	""" Reactivar un grupo o socio """

	template_name = 'arquitectura/instancia.html'
	form_class = hiddenForm

	def get_object(self, queryset=None):
		if self.kwargs['modelo'] == "Cliente":
			objeto = Socio.objects.get(pk=self.kwargs['pk'], es_socio=False)
		else:
			objeto = eval(self.kwargs['modelo']).objects.get(pk=self.kwargs['pk'])
		return objeto


	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		pregunta = self.get_object()
		respuesta = "Estas deshacer la baja del {} {}. Si estas seguro de continuar presiona guardar.".format(self.kwargs['modelo'], pregunta)
		context.update(locals())
		return context

	def get_success_url(self, **kwargs):
		return reverse_lazy('parametros')


	@transaction.atomic
	def form_valid(self, form):
		objeto = self.get_object()
		objeto.baja = None
		objeto.save()
		if self.kwargs['modelo'] == "Socio":
			if objeto.usuarios.all():
				for usuario in objeto.usuarios.all():
					usuario.is_active = True
					usuario.save()
		return redirect('parametro', modelo=self.kwargs['modelo'])



@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class PDFCodigo(generic.DetailView):

	""" Ver PDF del codigo de socio """

	model = Socio
	template_name = 'arquitectura/pdfs/codigo-socio.html' # Solo para que no arroje error

	def get(self, request, *args, **kwargs):
		from django.http import HttpResponse
		socio = self.get_object()
		response = HttpResponse(socio.hacer_pdf(), content_type='application/pdf')
		nombre = "{}.pdf".format(socio.codigo)
		content = "inline; filename=%s" % nombre
		response['Content-Disposition'] = content
		return response

	def dispatch(self, request, *args, **kwargs):
		try:
			socio = Socio.objects.get(consorcio=consorcio(self.request), pk=kwargs['pk'])
		except:
			messages.error(request, 'No se pudo encontrar.')
			return redirect('parametros')

		return super().dispatch(request, *args, **kwargs)