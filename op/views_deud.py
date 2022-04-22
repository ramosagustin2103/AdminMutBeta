from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.utils.decorators import method_decorator


from admincu.funciones import *
from admincu.generic import OrderQS
from consorcios.models import *
from arquitectura.models import *
from .models import *
from .forms import *
from contabilidad.asientos.funciones import asiento_deuda
from .funciones import *
from .filters import *



@group_required('administrativo', 'contable')
def deud_index(request):
	hoy = date.today()

	deudas = Deuda.objects.filter(consorcio=consorcio(request), confirmado=True, aceptado=True).order_by('-id')

	# Saldo total de creditos pendientes
	saldo = sum([d.saldo for d in deudas.filter(pagado=False)])

	borrar_deudas_no_confirmadas(request.user)

	deudas = deudas[:5]

	return render(request, 'deudas/index.html', locals())


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Registro(OrderQS):

	""" Registro de deudas """

	model = Deuda
	filterset_class = DeudaFilter
	template_name = 'deudas/registros/deudas.html'
	paginate_by = 50



@group_required('administrativo', 'contable')
def deud_registro(request):

	deudas = Deuda.objects.filter(consorcio=consorcio(request), confirmado=True).order_by('-id')

	borrar_deudas_no_confirmadas(request.user)

	if request.POST.get('fechas'):
		rango = request.POST.get('fechas').split(" / ")
		deudas = deudas.filter(fecha__range=rango)
	else:
		deudas = deudas[:20]

	return render(request, 'deudas/registro.html', locals())


@group_required('administrativo')
def deud_nuevo(request):
	if valid_demo(request.user):
		return redirect('deudas')
	request.session['fecha'] = None
	request.session['numero'] = None
	request.session['acreedor'] = None

	borrar_deudas_no_confirmadas(request.user)

	form = encabezadoDeudaForm(
			data=request.POST or None,
			consorcio=consorcio(request),
		)
	pregunta = "Seleccione las siguientes opciones"
	if form.is_valid():
		# Validacion para no cargar con fecha de periodos cerrados
		fecha = form.cleaned_data['fecha']
		try:
			ultimo_cierre = Cierre.objects.filter(consorcio=consorcio(request), confirmado=True).order_by('-periodo')[0].periodo
		except:
			ultimo_cierre = None

		if ultimo_cierre and fecha <= ultimo_cierre:
			messages.add_message(request, messages.ERROR, 'No se puede generar deudas con fecha anterior a la de periodos cerrados.')
		else:
			request.session['fecha'] = request.POST.get('fecha')
			request.session['numero'] = request.POST.get('numero')
			request.session['acreedor'] = request.POST.get('acreedor')
			try:
				deuda_existente = Deuda.objects.get(
						numero=request.session['numero'],
						acreedor=Acreedor.objects.get(id=request.session['acreedor'])
					)
				messages.add_message(request, messages.ERROR, 'La deuda que desea cargar ya existe')
			except:
				deuda_existente = None
			if not deuda_existente:
				return redirect(deud_vinculaciones)
	else:
		messages.add_message(request, messages.ERROR, 'Debes rellenar todos los campos para poder continuar') if request.method == "POST" else None


	return render(request, 'deudas/nuevo.html', locals())


@group_required('administrativo')
@transaction.atomic
def deud_vinculaciones(request):
	try:
		acreedor = Acreedor.objects.get(id=request.session['acreedor'])
		fecha = request.session['fecha']
		numero = request.session['numero']
	except:
		return redirect(deud_index)

	form = detallesDeudaForm(
			consorcio=consorcio(request),
			data=request.POST or None
			)

	erogaciones_posibles = acreedor.tipo.exclude(cuenta_contable=acreedor.cuenta_contable)

	if request.method == "POST":
		errores = []
		gastos = [
		{
			"nombre": gasto.split("_")[1],
			"valor": float(valor)
		} for gasto, valor in request.POST.items() if "gasto_" in gasto and valor != 0 and valor != ""
		]
		errores.append("Debes cargar valores en los gastos vinculados al acreedor") if not gastos else None

		if not errores:
			observacion = request.POST.get('observacion') or None
			total = sum([val for gasto in gastos for g,val in gasto.items() if g == "valor"])
			# Creacion de la deuda
			deuda = Deuda(
				consorcio=consorcio(request),
				fecha=fecha,
				numero=numero,
				acreedor=acreedor,
				total=total,
				observacion=observacion,
				)
			deuda.save()

			# Creacion de objeto de gastos
			listado_gastos = []
			for gasto in gastos:
				gastoDeuda = GastoDeuda(
					deuda=deuda,
					gasto=Gasto.objects.get(id=gasto['nombre']),
					valor=gasto["valor"],
					)
				listado_gastos.append(gastoDeuda)

			# Guardado de gastos en base de datos
			try:
				guardar_gastos = GastoDeuda.objects.bulk_create(listado_gastos)
			except:
				deuda.delete()
				messages.add_message(request, messages.ERROR, 'Hubo un error, debe realizar el proceso de generacion de la deuda')
				return redirect(deud_index)

			return redirect(deud_confirm, pk=deuda.pk)


	return render(request, 'deudas/vinculaciones.html', locals())


@group_required('administrativo')
@transaction.atomic
def deud_confirm(request, pk):
	try:
		deuda = Deuda.objects.get(
				consorcio=consorcio(request),
				pk=pk,
				confirmado=False
				)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error, debe realizar el proceso de generacion de deuda')
		return redirect(deud_index)

	gastoDeuda = GastoDeuda.objects.filter(deuda=deuda)

	if request.method == "POST":
		if request.POST.get('accion') =='confirm':
			deuda.confirmado = True
			gastoDeuda.update(fecha=deuda.fecha)
			deuda.save()
			try:
				asiento = asiento_deuda(deuda)
			except:
				asiento = None

			if asiento == True:
				messages.add_message(request, messages.SUCCESS, "Deuda generada con exito.")
			else:
				messages.add_message(request, messages.ERROR, asiento)

			return redirect(deud_index)

	return render(request, 'deudas/confirmacion.html', locals())


@group_required('administrativo')
@transaction.atomic
def deud_eliminar(request, pk):
	try:
		deuda = Deuda.objects.get(
				consorcio=consorcio(request),
				pk=pk,
				confirmado=False
				)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error al cancelar el proceso de generacion de deuda')
		return redirect(deud_index)

	gastoDeuda = GastoDeuda.objects.filter(deuda=deuda).delete()
	deuda.delete()
	messages.add_message(request, messages.SUCCESS, "Deuda cancelada.")
	return redirect(deud_index)


@group_required('administrativo', 'contable')
def deud_ver(request, pk):
	try:
		deuda = Deuda.objects.get(
				pk=pk,
				consorcio=consorcio(request),
				confirmado=True,
				)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error, debe seleccionar opciones validas en el menu')
		return redirect(deud_index)

	gastoDeuda = GastoDeuda.objects.filter(deuda=deuda)

	return render(request, 'deudas/ver.html', locals())


@group_required('administrativo', 'contable')
@transaction.atomic
def deud_vincular_pago(request, pk):
	try:
		deuda = Deuda.objects.get(
				pk=pk,
				consorcio=consorcio(request),
				confirmado=True,
				)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error, debe seleccionar opciones validas en el menu')
		return redirect(deud_index)

	adelantos = GastoOP.objects.filter(
				op__acreedor=deuda.acreedor,
				gasto__cuenta_contable=deuda.acreedor.cuenta_contable
			)
	for a in adelantos:
		if a.op.deudaop_set.filter(deuda=deuda):
			adelantos = adelantos.exclude(id=a.id)

	if not adelantos:
		messages.add_message(request, messages.ERROR, 'No hay pagos posibles a vincular.')
		return redirect('deud_ver', pk=deuda.pk)

	if request.method == "POST":
		seleccionados = adelantos.filter(id__in=request.POST.getlist('pagos'))
		suma_seleccionados = sum([a.valor for a in seleccionados])
		errores = []
		if suma_seleccionados > deuda.saldo:
			errores.append('El total de pagos seleccionados excede al saldo de la deuda.')
		if not errores:
			vinculaciones = []
			for s in seleccionados:
				vinculaciones.append(
						DeudaOP(
							op=s.op,
							deuda=deuda,
							valor=s.valor
						)
					)
				s.delete()
			guardar_vinculaciones = DeudaOP.objects.bulk_create(vinculaciones)
			deuda.chequear()
			messages.add_message(request, messages.SUCCESS, 'Pagos vinculados con exito.')
			return redirect('deud_ver', pk=deuda.pk)

	return render(request, 'deudas/vincular-pago.html', locals())

