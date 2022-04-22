import datetime
from datetime import date, timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from admincu.funciones import *
from consorcios.models import *
from arquitectura.models import *
from contabilidad.funciones import *
from contabilidad.models import *
from django_afip.models import *
from .forms import *


@group_required('contable')
def mayores_index(request):
	# Traer ejercicio activo
	try:
		ejercicio = Ejercicio.objects.get(consorcio=consorcio(request), activo=True)
	except:
		mensaje = "Debe activar un ejercicio para ver mayores."
		messages.add_message(request, messages.ERROR, mensaje)
		return redirect('contabilidad')

	if request.method == "POST":
		cuentas = Cuenta.objects.filter(id__in=request.POST.getlist('cuentas'))
		fechas = request.POST.get('fechas')
		fecha_ini, fecha_fin = fechas.split(" / ")
		fecha_ini = datetime.strptime(fecha_ini, "%Y-%m-%d").date()
		fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
		if ejercicio.inicio <= fecha_ini <= ejercicio.cierre and \
			ejercicio.inicio <= fecha_fin <= ejercicio.cierre:
			asientos = asientosNumerados(ejercicio)
		else:
			mensaje = "Debes seleccionar un periodo entre {} y {}. (Ejercicio: {}).".format(ejercicio.inicio, ejercicio.cierre, ejercicio)
			messages.add_message(request, messages.ERROR, mensaje)
			fechas = None

	return render(request, 'contabilidad/libros/mayores.html', locals())


@group_required('contable')
def sys_index(request):

	if request.method == "POST":
		fechas = request.POST.get('fechas')
		fecha_ini, fecha_fin = fechas.split(" / ")
		cuentas = Plan.objects.get(consorcio=consorcio(request)).cuentas.filter(nivel=4).order_by('numero')
		asientos = Asiento.objects.filter(
				consorcio=consorcio(request),
				fecha_asiento__range=[fecha_ini, fecha_fin]
			).order_by('fecha_asiento', 'id')
		operaciones = [op.id for a in asientos for op in a.operaciones.all()]
		operaciones = Operacion.objects.filter(id__in=operaciones)
		generacionSyS(cuentas, operaciones)


	return render(request, 'contabilidad/libros/sys.html', locals())