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
from django.forms import modelformset_factory
from django.db import transaction
from .funciones import *

@group_required('contable')
@transaction.atomic
def asiento_index(request, numero=None):
	# Traer ejercicio activo
	try:
		ejercicio = Ejercicio.objects.get(consorcio=consorcio(request), activo=True)
		apropiadorDeAsientosPrincipales(ejercicio)
	except:
		mensaje = "Debe activar un ejercicio para poder realizar un asiento."
		messages.add_message(request, messages.ERROR, mensaje)
		return redirect('contabilidad')

	asientos = Asiento.objects.filter(
				consorcio=consorcio(request),
				fecha_asiento__range=[ejercicio.inicio, ejercicio.cierre]
			).order_by('fecha_asiento', 'id')
	q_asientos = asientos.count()
	if numero:
		# Tomar asiento a modificar
		try:
			asiento_mod = asientos[numero-1]
		except:
			mensaje = "No existe el asiento que desea buscar."
			messages.add_message(request, messages.ERROR, mensaje)
			return redirect('asiento')

		# Projimos
		anterior = numero-1 if numero > 1 else None
		posterior = numero+1 if numero < q_asientos else None
	else:
		asiento_mod = None

		# Projimo
		anterior = q_asientos



	form_asiento = asientoForm(
			data=request.POST or None,
			prefix="asiento",
			instance=asiento_mod if asiento_mod else None
		)

	extra = 4 if not asiento_mod else 0

	queryset = Operacion.objects.none() if not asiento_mod else asiento_mod.operaciones.all().order_by('haber')

	suma_debe, suma_haber = 0, 0
	for op in queryset:
		suma_debe += op.debe
		suma_haber += op.haber

	formset = modelformset_factory(
			Operacion,
			form=operacionForm,
			extra=extra,
			can_delete=True,

		)

	formSetOperaciones = formset(
			form_kwargs={
				'consorcio': consorcio(request),
				'data': request.POST or None,
			},
			prefix="op",
			queryset=queryset
			)

	if request.method == "POST":
		if valid_demo(request.user):
			return redirect('asiento')

		formSetOperaciones.extra = int(request.POST.get('op-TOTAL_FORMS'))
		if form_asiento.is_valid():
			# Validaciones
			errores = []
			# Validacion fecha del asiento
			if not (ejercicio.inicio <= form_asiento.cleaned_data['fecha_asiento'] <= ejercicio.cierre):
				error = "La fecha del asiento no corresponde al ejercicio activo."
				errores.append(error)

			# Validacion para no dejar cargar ni modificar asientos en ejercicios ya cerrados

			if ejercicio.asiento_cierre_pat:
				error = "No se puede cargar ni modificar asientos en ejercicios cerrados."
				errores.append(error)

			operaciones = []
			suma_debe = 0
			suma_haber = 0
			identificacion = randomNumber(Operacion, 'numero_aleatorio')
			for f in formSetOperaciones:
				pre, linea = str(f.prefix).split("-")
				linea = str(int(linea)+1)
				if f.is_valid():
					try:
						cuenta = f.cleaned_data['cuenta']
					except:
						cuenta = None
					if cuenta:
						debe = f.cleaned_data['debe'] or 0
						haber = f.cleaned_data['haber'] or 0
						# Validacion por debe y haber en 0
						if debe == 0 and haber == 0:
							break
						suma_debe += debe
						suma_haber += haber
						descripcion = f.cleaned_data['descripcion'] or ""
						operaciones.append(Operacion(
								numero_aleatorio=identificacion,
								cuenta=cuenta,
								debe=debe,
								haber=haber,
								descripcion=descripcion,
							))
						# Validacion numeros positivos
						if debe < 0 or haber < 0:
							error = "Linea %s: Solo se admiten numeros positivos." % linea
							errores.append(error)
						# Validacion importe en ambos lados
						if debe != 0 and haber != 0:
							error = "Linea %s: No se puede colocar importes en ambos campos (Debe y Haber)." % linea
							errores.append(error)

			# Validacion suma de asiento
			if suma_debe != suma_haber:
				error = "El asiento no cuadra."
				errores.append(error)

			if suma_debe == 0 or suma_haber == 0:
				error = "Debe colocar cuentas y valores en las lineas."
				errores.append(error)

			# Guardado
			if not errores and len(operaciones) >= 2:
				if asiento_mod:
					asiento_mod.operaciones.all().delete()

				# Guarda el asiento
				asiento = form_asiento.save(commit=False)
				asiento.consorcio = consorcio(request)
				Operacion.objects.bulk_create(operaciones)
				asiento.save()
				asiento.operaciones.add(*Operacion.objects.filter(numero_aleatorio=identificacion))


				messages.add_message(request, messages.SUCCESS, "Asiento guardado con exito.")
				return redirect('asiento')


	return render(request, 'contabilidad/asientos/asiento.html', locals())


@require_http_methods('POST')
@group_required('contable')
def asiento_eliminar(request):
	if valid_demo(request.user):
		return redirect('asiento')

	try:
		asiento = Asiento.objects.get(id=request.POST.get('eliminar'))
	except:
		asiento = None

	try:
		ejercicio = Ejercicio.objects.filter(consorcio=consorcio(request), cierre__gte=asiento.fecha_asiento).order_by('cierre')[0]
	except:
		ejercicio = None

	if asiento:
		if asiento.principal:
			# Para saber si tiene asientos principales posteriores
			try:
				asiento_principal_posterior = Asiento.objects.get(
					consorcio=consorcio(request),
					fecha_asiento__range=[ejercicio.inicio, ejercicio.cierre],
					principal__gt=asiento.principal
				)
			except:
				asiento_principal_posterior = None

			if not asiento_principal_posterior:
				try:
					ejercicio_posterior = Ejercicio.objects.filter(consorcio=consorcio(request), inicio__gt=ejercicio.cierre).order_by('inicio')[0]

					asiento_principal_posterior = Asiento.objects.get(
						consorcio=consorcio(request),
						fecha_asiento__range=[ejercicio_posterior.inicio, ejercicio_posterior.cierre],
						principal__isnull=False,
					)
				except:
					asiento_principal_posterior = None

			if not asiento_principal_posterior:
				eliminarAsiento(asiento)
				messages.add_message(request, messages.SUCCESS, "Asiento eliminado con exito.")
				devolucion = redirect('ejercicio_set', ejercicio=ejercicio.numero_aleatorio)
			else:
				messages.add_message(request, messages.ERROR, "No se puede eliminar el asiento porque tiene asientos posteriores vinculados")
				devolucion = redirect('ejercicio_set', ejercicio=ejercicio.numero_aleatorio)

		else:
			eliminarAsiento(asiento)
			messages.add_message(request, messages.SUCCESS, "Asiento eliminado con exito.")
			devolucion = redirect('asiento')
	else:
		devolucion = redirect('asiento')
		messages.add_message(request, messages.ERROR, "Hubo un error al eliminar el asiento. Intentelo de nuevo mas tarde.")

	return devolucion


@require_http_methods('POST')
@group_required('contable')
def asiento_generador_principales(request):
	if valid_demo(request.user):
		return redirect('asiento')

	try:
		operacion = request.POST.get('operacion')
		ejercicio = Ejercicio.objects.get(id=request.POST.get('ejercicio'))
	except:
		return redirect('home')

	# Tipos de asientos principales
	tipo = {
		'asiento_apertura': 1,
		'asiento_cierre_res': 2,
		'asiento_cierre_pat': 3,
	}

	# Para evitar doble submit
	try:
		asiento_principal = Asiento.objects.get(
				consorcio=consorcio(request),
				fecha_asiento__range=[ejercicio.inicio, ejercicio.cierre],
				principal=tipo[operacion]
			)
	except:
		asiento_principal = None

	# Generacion del asiento
	realizacion = eval(operacion)(ejercicio) if not asiento_principal else None

	if realizacion == True:
		messages.add_message(request, messages.SUCCESS, "Asiento generado con exito.")
	else:
		messages.add_message(request, messages.ERROR, realizacion)


	return redirect('ejercicio_set', ejercicio=ejercicio.numero_aleatorio)

def asiento_redireccion(request, id_asiento):
	try:
		ejercicio = Ejercicio.objects.get(consorcio=consorcio(request), activo=True)
	except:
		mensaje = "Debe activar un ejercicio para poder visualizar el asiento."
		messages.add_message(request, messages.ERROR, mensaje)
		return redirect('asiento')
	try:
		asiento = Asiento.objects.get(id=id_asiento)
	except:
		mensaje = "No se pudo encontrar el asiento."
		messages.add_message(request, messages.ERROR, mensaje)
		return redirect('asiento')

	if not ejercicio.inicio <= asiento.fecha_asiento <= ejercicio.cierre:
		mensaje = "El asiento que desea visualizar no corresponde al ejercicio activo."
		messages.add_message(request, messages.ERROR, mensaje)
		return redirect('asiento')

	asientos = asientosNumerados(ejercicio)
	for a in asientos:
		if a.id == asiento.id:
			return redirect('asiento_mod', numero=a.numero)

	return redirect('asiento')