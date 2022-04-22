from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from admincu.funciones import *
from consorcios.models import *
from arquitectura.models import *
from contabilidad.models import *
from django_afip.models import *
from .forms import *


@group_required('contable')
def pc_index(request):
	try:
		plan = Plan.objects.get(consorcio=consorcio(request))
	except:
		return redirect('contabilidad')

	rubros = plan.cuentas.filter(dependencia__isnull=True)
	rubros = rubros.exclude(nivel=0)

	return render(request, 'contabilidad/cuentas/index.html', locals())


@group_required('contable')
def pc_nuevo(request):
	if valid_demo(request.user):
		return redirect('cuentas')
	try:
		plan = Plan.objects.get(consorcio=consorcio(request))
	except:
		return redirect('contabilidad')

	form = cuentaForm(
		data=request.POST or None,
		consorcio=consorcio(request),
		)
	pregunta = "Cuenta contable"

	if form.is_valid():
		errores = []
		dependencia = form.cleaned_data['dependencia']
		numero = form.cleaned_data['numero']
		nombre = form.cleaned_data['nombre'].upper()
		# Validaciones
		## No dependencia
		if not dependencia:
			errores.append('Dependencia del rubro: Debe colocar el rubro al que pertenece la cuenta.')

		## No numero en field numero
		try:
			valid_numero = int(numero)
		except:
			valid_numero = None
			errores.append('Numero de cuenta: Debe colocar solo numeros.')

		if valid_numero:
			## Numero duplicado
			if plan.cuentas.filter(numero=numero):
				error = "Ya existe una cuenta con el numero {}.".format(numero)
				errores.append(error)


			## Numero incorrecto correspondiente a la dependencia
			if dependencia:
				numero_inicial = int(dependencia.numero)
				try:
					numero_final = int(plan.cuentas.filter(nivel=3, numero__gt=dependencia.numero).order_by('numero')[0].numero)
				except:
					numero_final = 600000
				if not (numero_inicial < valid_numero < numero_final):
					error = "El numero de cuenta segun su dependencia deberia estar entre {} y {}.".format(str(numero_inicial),str(numero_final))
					errores.append(error)

		if not errores:
			cuenta = form.save(commit=False)
			cuenta.nivel = 4
			cuenta.consorcio = consorcio(request)
			cuenta.save()
			plan.cuentas.add(cuenta)
			messages.add_message(request, messages.SUCCESS, "Cuenta agregada con exito")
			return redirect('cuentas')


	return render(request, 'contabilidad/cuentas/nuevo.html', locals())


@group_required('contable')
def pc_set(request, cuenta):

	try:
		cuenta = Plan.objects.get(consorcio=consorcio(request)).cuentas.get(numero=cuenta)
	except:
		return redirect('contabilidad')

	asientos = Asiento.objects.filter(
			consorcio=consorcio(request),
			operaciones__cuenta=cuenta,
		).order_by('-fecha_asiento', '-id')

	return render(request, 'contabilidad/cuentas/set.html', locals())


@group_required('contable')
def pc_desvincular(request, cuenta):
	if valid_demo(request.user):
		return redirect('cuentas')
	try:
		cuenta = Plan.objects.get(consorcio=consorcio(request)).cuentas.get(numero=cuenta)
	except:
		return redirect('contabilidad')

	operaciones = Asiento.objects.filter(
			consorcio=consorcio(request),
			operaciones__cuenta=cuenta,
		)
	cajas = cuenta.caja_set.filter(consorcio=consorcio(request))
	ingresos = cuenta.ingreso_set.filter(consorcio=consorcio(request))
	gastos = cuenta.gasto_set.filter(consorcio=consorcio(request))
	acreedores = cuenta.acreedor_set.filter(consorcio=consorcio(request))
	cuentas_importantes = [
		'112101', '112103', '121101',
		'211101', '212101', '212102',
		'213101', '213102', '213103',
		'213104', '213110', '311101',
		'321001', '411101', '411103',
		'511101', '511102', '511125',
		'511135'
		]
	if cuenta.numero in cuentas_importantes:
		messages.add_message(request, messages.ERROR, "No se puede eliminar esta cuenta. Es fundamental para el funcionamiento del sistema")
	else:
		if not cajas and not ingresos and not gastos and not acreedores and not operaciones:
			if cuenta.consorcio:
				cuenta.delete()
			else:
				Plan.objects.get(consorcio=consorcio(request)).cuentas.remove(cuenta)
			messages.add_message(request, messages.SUCCESS, "Cuenta desvinculada")
		else:
			messages.add_message(request, messages.ERROR, "No se puede desvincular la cuenta ya que tiene movimientos o parametros asociados")

	return redirect('cuentas')
