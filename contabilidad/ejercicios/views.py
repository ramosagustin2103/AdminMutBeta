from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.views.decorators.http import require_http_methods
from admincu.funciones import *
from consorcios.models import *
from arquitectura.models import *
from contabilidad.models import *
from django_afip.models import *
from .forms import *
from contabilidad.funciones import *


@group_required('contable')
def ejercicios_index(request):

	ejercicios = Ejercicio.objects.filter(consorcio=consorcio(request))

	return render(request, 'contabilidad/ejercicios/index.html', locals())


@group_required('contable')
def ejercicio_nuevo(request):
	if valid_demo(request.user):
		return redirect('ejercicios')
	ejercicios = Ejercicio.objects.filter(consorcio=consorcio(request))

	form = ejercicioForm(
		data=request.POST or None,
		consorcio=consorcio(request),
		)
	pregunta = "Encabezado"
	if form.is_valid():
		nombre = form.cleaned_data['nombre']
		inicio = form.cleaned_data['inicio']
		cierre = form.cleaned_data['cierre']
		error = None
		# Validaciones
		## Fechas al reves
		if ejercicios.filter(nombre=nombre):
			error = "El nombre de periodo ya existe"
		else:
			if cierre < inicio:
				error = "La fecha de cierre debe ser superior a la fecha de inicio"
			else:
				## Si existe uno con fecha de inicio posterior
				if ejercicios.filter(inicio__gte=cierre):
					error = "Existe un ejercicio con fecha de inicio posterior a la fecha ingresada como cierre"
				else:
					# Si existe alguno que ya abarque el periodo solicitado
					if ejercicios.filter(cierre__gte=inicio):
						error = "Existe un ejercicio que abarca el periodo seleccionado"

		# Fin de las validaciones
		if error:
			messages.add_message(request, messages.ERROR, error)
		else:
			ej = form.save(commit=False)
			ej.consorcio = consorcio(request)
			ej.numero_aleatorio = randomNumber(Ejercicio, 'numero_aleatorio')
			ej.activo = True
			ej.save()
			messages.add_message(request, messages.SUCCESS, "Ejercicio cargado con exito")
			return redirect(ejercicio_set, ejercicio=ej.numero_aleatorio)

	return render(request, 'contabilidad/ejercicios/nuevo.html', locals())


@group_required('contable')
def ejercicio_set(request, ejercicio):
	if valid_demo(request.user):
		return redirect('ejercicios')
	try:
		ejercicio = Ejercicio.objects.get(numero_aleatorio=ejercicio)
	except:
		return redirect(ejercicios_index)


	# Para saber si es el primer ejercicio
	try:
		ejercicio_anterior = Ejercicio.objects.filter(consorcio=consorcio(request), cierre__lt=ejercicio.inicio).order_by('-cierre')[0]
	except:
		ejercicio_anterior = None


	apropiadorDeAsientosPrincipales(ejercicio)


	if request.method == "POST":
		if request.POST.get('activar'):
			ejercicio.activo = True
			ejercicio.save()
			mensaje = "Ejercicio activado"
			messages.add_message(request, messages.SUCCESS, mensaje)
			return redirect('ejercicio_set', ejercicio=ejercicio.numero_aleatorio)
		elif request.POST.get('eliminar'):
			if ejercicio.asiento_apertura or ejercicio.asiento_cierre_res or ejercicio.asiento_cierre_pat:
				mensaje = "Hay asientos de apertura o cierre cargados en el ejercicio que desea eliminar"
				messages.add_message(request, messages.ERROR, mensaje)
			else:
				ejercicio.delete()
				messages.add_message(request, messages.SUCCESS, "Ejercicio eliminado con exito.")
				return redirect('ejercicios')


	return render(request, 'contabilidad/ejercicios/set.html', locals())


@group_required('contable')
def ejercicio_diario(request, ejercicio):
	try:
		ejercicio = Ejercicio.objects.get(numero_aleatorio=ejercicio)
	except:
		return redirect(ejercicios_index)

	asientos = asientosNumerados(ejercicio)


	return render(request, 'contabilidad/ejercicios/diario.html', locals())