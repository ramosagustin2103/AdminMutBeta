from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django_afip.models import *
from django.db import transaction
from django.template.loader import render_to_string
from weasyprint import HTML
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import modelformset_factory
from django.views import generic
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy

from admincu.funciones import *
from admincu.generic import OrderQS
from contabilidad.asientos.funciones import asiento_op, asiento_op_anulacion
from consorcios.models import *
from arquitectura.models import *
from .models import *
from .forms import *
from reportes.models import Cierre
from .funciones import *
from .filters import *


@method_decorator(group_required('administrativo', 'contable'), name='dispatch')
class Registro(OrderQS):

	""" Registro de comprobantes """

	model = OP
	filterset_class = OPFilter
	template_name = 'op/registros/ops.html'
	paginate_by = 50



@group_required('administrativo', 'contable')
def op_index(request):

	ops = OP.objects.filter(consorcio=consorcio(request), confirmado=True).order_by('-id')

	borrar_op_no_confirmadas(request.user)

	try:
		ultima = ops.first()
	except:
		ultima = None

	ops = ops[:5]

	return render(request, 'op/index.html', locals())


@group_required('administrativo', 'contable')
def op_registro(request):

	ops = OP.objects.filter(consorcio=consorcio(request), confirmado=True).order_by('-id')

	if request.POST.get('fechas'):
		rango = request.POST.get('fechas').split(" / ")
		ops = ops.filter(fecha__range=rango)
	else:
		ops = ops[:20]

	return render(request, 'op/registro.html', locals())


@group_required('administrativo')
@transaction.atomic
def op_d_parcial(request, pk):
	try:
		deuda = Deuda.objects.get(
				pk=pk,
				consorcio=consorcio(request),
				confirmado=True,
				pagado=False,
			)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error al buscar la deuda. O la misma ya se encontraba pagada.')
		return redirect('op')

	borrar_op_no_confirmadas(request.user)

	form = PagoParcialForm(
			data=request.POST or None,
			consorcio=consorcio(request),
		)

	if form.is_valid():
		errores = []
		total = form.cleaned_data['total']
		if not total:
			errores.append('Debe colocar un valor')
		else:
			if total > deuda.saldo:
				errores.append('El valor debe ser menor al saldo de la deuda')

		if not errores:
			op = form.save(commit=False)
			op.consorcio = consorcio(request)
			op.usuario = request.user
			op.acreedor = deuda.acreedor
			op.save()

			deudaOP = DeudaOP(
				deuda=deuda,
				op=op,
				valor=op.total
				)
			deudaOP.save()
			return redirect('op_caja', pk=op.pk)
	else:
		messages.add_message(request, messages.ERROR, 'Debes rellenar todos los campos para poder continuar') if request.method == "POST" else None

	return render(request, 'op/pago-parcial.html', locals())



@group_required('administrativo')
@transaction.atomic
def op_nuevo(request):
	if valid_demo(request.user):
		return redirect('op')

	borrar_op_no_confirmadas(request.user)

	pregunta = "Seleccione las siguientes opciones"
	form = encabezadoForm(
			data=request.POST or None,
			consorcio=consorcio(request),
		)
	if form.is_valid():
		op = form.save(commit=False)
		op.consorcio = consorcio(request)
		op.usuario = request.user
		op.save()
		return redirect('op_vinculaciones', pk=op.pk)
	else:
		messages.add_message(request, messages.ERROR, 'Debes rellenar todos los campos para poder continuar') if request.method == "POST" else None

	return render(request, 'op/nuevo.html', locals())


@group_required('administrativo')
@transaction.atomic
def op_vinculaciones(request, pk):
	try:
		op = OP.objects.get(pk=pk, consorcio=consorcio(request), confirmado=False)
	except:
		return redirect('op')

	# Por si ya se habian creado
	gastoOP = GastoOP.objects.filter(op=op)
	deudaOP = DeudaOP.objects.filter(op=op)
	if deudaOP or gastoOP:
		op.delete()
		return redirect('op')

	deudas = Deuda.objects.filter(consorcio=consorcio(request), acreedor=op.acreedor, pagado=False)

	if request.method == "POST":
		errores = []
		deudas_seleccionadas = deudas.filter(id__in=request.POST.getlist('vinculo[]'), pagado=False)
		gastos = [
		{
			"nombre": gasto.split("_")[1],
			"valor": float(valor)
		} for gasto, valor in request.POST.items() if "gasto_" in gasto and valor != 0 and valor != ""
		]
		errores.append("Debes cargar valores en los gastos vinculados al acreedor") if not gastos and not deudas_seleccionadas else None

		if not errores:
			total_gastos = sum([val for gasto in gastos for g,val in gasto.items() if g == "valor"]) if gastos else 0
			total_deudas = sum([d.saldo for d in deudas_seleccionadas]) if deudas_seleccionadas else 0
			total = float(total_deudas) + float(total_gastos)
			op.total = total
			op.save()

			# Construccion de vinculaciones

			## Gastos
			if gastos:
				listado_gastos = []
				for gasto in gastos:
					gastoOP = GastoOP(
						op=op,
						gasto=Gasto.objects.get(id=gasto['nombre']),
						valor=gasto["valor"],
						)
					listado_gastos.append(gastoOP)

				# Guardado de gastos en base de datos
				try:
					guardar_gastos = GastoOP.objects.bulk_create(listado_gastos)
				except:
					op.delete()
					messages.add_message(request, messages.ERROR, 'Hubo un error, debe realizar el proceso de generacion de la orden de pago')
					return redirect('op')

			## Deudas
			if deudas_seleccionadas:
				listado_deudas = []
				for deuda in deudas_seleccionadas:
					deudaOP = DeudaOP(
						op=op,
						deuda=deuda,
						valor=deuda.saldo,
						)
					listado_deudas.append(deudaOP)

				# Guardado de gastos en base de datos
				try:
					guardar_deudas = DeudaOP.objects.bulk_create(listado_deudas)
				except:
					op.delete()
					messages.add_message(request, messages.ERROR, 'Hubo un error, debe realizar el proceso de generacion de la orden de pago')
					return redirect('op')


			return redirect('op_caja', pk=op.pk)

	return render(request, 'op/vinculaciones.html', locals())


@group_required('administrativo')
@transaction.atomic
def op_caja(request, pk):
	try:
		op = OP.objects.get(pk=pk, consorcio=consorcio(request), confirmado=False)
	except:
		return redirect('op')

	deudas = Deuda.objects.filter(consorcio=consorcio(request), acreedor=op.acreedor, pagado=False)

	retencionOP = RetencionOP.objects.filter(op=op)
	cajaOP = CajaOP.objects.filter(op=op)
	if retencionOP or cajaOP:
		op.delete()
		return redirect('op')

	formset = modelformset_factory(
			CajaOP,
			form=cajaForm,
			extra=4,
			can_delete=True,

		)

	queryset = CajaOP.objects.none()

	formSetCaja = formset(
			form_kwargs={
				'consorcio': consorcio(request),
				'data': request.POST or None,
			},
			prefix="op",
			queryset=queryset
			)

	if request.method == "POST":
		formSetCaja.extra = int(request.POST.get('op-TOTAL_FORMS'))
		# Validaciones
		errores = []
		retenciones = [
		{
			"tipo": ret.split("_")[1],
			"valor": float(valor)
		} for ret, valor in request.POST.items() if "ret_" in ret and valor != 0 and valor != ""
		]
		cajas = []
		for f in formSetCaja:
			if f.is_valid():
				try:
					caja = f.cleaned_data['caja']
					valor = f.cleaned_data['valor']
				except:
					caja = None
					valor = None
				if caja and valor:
					cajas.append({
						'caja': caja,
						'referencia': f.cleaned_data['referencia'] or "",
						'valor': float(valor),
						})
		total_retenciones = sum([val for ret in retenciones for r,val in ret.items() if r == "valor"]) if retenciones else 0
		if cajas:
			total_cajas = sum([val for caja in cajas for c,val in caja.items() if c == "valor"])
			total_pagado = round(total_retenciones + total_cajas, 2)
			if float(op.total) != total_pagado:
				errores.append("Los montos ingresados no coinciden con la suma de gastos y deudas.")
		else:
			errores.append("Debes colocar por lo menos un medio de pago.")

		# Fin de validaciones
		if not errores:

			listado_cajas = []
			for caja in cajas:
				listado_cajas.append(CajaOP(
					op=op,
					caja=caja['caja'],
					referencia=caja['referencia'],
					valor=caja['valor']
					))

			# Guardado de gastos en base de datos
			try:
				guardar_cajas = CajaOP.objects.bulk_create(listado_cajas)
			except:
				op.delete()
				messages.add_message(request, messages.ERROR, 'Hubo un error, debe realizar el proceso de generacion de la orden de pago')
				return redirect('op')


			## Retenciones
			if retenciones:
				listado_retenciones = []
				deudas_retenciones = []
				for ret in retenciones:
					# Construccion de la deuda
					tipo_retencion = Relacion.objects.get(id=ret['tipo'])
					ret_deuda = Deuda(
						consorcio=consorcio(request),
						retencion=tipo_retencion,
						fecha=op.fecha,
						acreedor=Acreedor.objects.get(consorcio=consorcio(request), recibe=tipo_retencion),
						total=ret['valor'],
						)
					ret_deuda.save()
					deudas_retenciones.append(ret_deuda)
					# Vinculacion con la OP
					ret_vinculacion = RetencionOP(
						op=op,
						deuda=ret_deuda,
						valor=ret_deuda.total,
						)
					listado_retenciones.append(ret_vinculacion)

				# Guardado de gastos en base de datos
				try:
					guardar_retenciones = RetencionOP.objects.bulk_create(listado_retenciones)
				except:
					for d in deudas_retenciones:
						d.delete()
					op.delete()
					messages.add_message(request, messages.ERROR, 'Hubo un error, debe realizar el proceso de generacion de la orden de pago')
					return redirect('op')

			op.descripcion = request.POST.get('descripcion') or ''
			op.save()

			return redirect('op_confirm', pk=op.pk)

	return render(request, 'op/caja.html', locals())


@group_required('administrativo')
@transaction.atomic
def op_confirm(request, pk):
	try:
		op = OP.objects.get(
				consorcio=consorcio(request),
				pk=pk,
				confirmado=False
				)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error, debe realizar el proceso de generacion de OP')
		return redirect(op_index)

	gastoOP = GastoOP.objects.filter(op=op)
	deudaOP = DeudaOP.objects.filter(op=op)
	retencionOP = RetencionOP.objects.filter(op=op)
	cajaOP = CajaOP.objects.filter(op=op)

	if request.method == "POST":
		if request.POST.get('accion') =='confirm':
			op.confirmado = True
			# Para que tenga el numero
			op.save()
			pdf = op.hacer_pdf()
			if deudaOP:
				for vinc in deudaOP:
					vinc.deuda.chequear()
			if retencionOP:
				for r in retencionOP:
					r.deuda.confirmado = True
					r.deuda.save()
			op.save()

			fecha_operacion = op.fecha_operacion or op.fecha
			gastoOP.update(fecha=fecha_operacion)
			deudaOP.update(fecha=fecha_operacion)
			retencionOP.update(fecha=fecha_operacion)
			cajaOP.update(fecha=fecha_operacion)

			asiento = asiento_op(op, gastoOP, deudaOP, retencionOP, cajaOP)

			if asiento == True:
				messages.add_message(request, messages.SUCCESS, "OP generada con exito.")
			else:
				messages.add_message(request, messages.ERROR, asiento)
			return redirect(op_index)

	return render(request, 'op/confirmacion.html', locals())


@group_required('administrativo')
@transaction.atomic
def op_eliminar(request, pk):
	try:
		op = OP.objects.get(
				consorcio=consorcio(request),
				pk=pk,
				confirmado=False
				)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error, debe realizar el proceso de generacion de OP')
		return redirect(op_index)

	op.delete()
	messages.add_message(request, messages.SUCCESS, "Orden de pago cancelada.")
	return redirect(op_index)


@group_required('administrativo', 'contable')
def op_ver(request, pk):
	try:
		op = OP.objects.get(
				pk=pk,
				consorcio=consorcio(request)
				)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error, debe seleccionar opciones validas en el menu')
		return redirect(op_index)

	gastos = GastoOP.objects.filter(op=op)
	deudas = DeudaOP.objects.filter(op=op)
	retenciones = RetencionOP.objects.filter(op=op)
	cajas = CajaOP.objects.filter(op=op)

	return render(request, 'op/ver.html', locals())


@group_required('administrativo', 'contable')
def op_pdf(request, pk):
	try:
		op = OP.objects.get(
				pk=pk,
				consorcio=consorcio(request),
				confirmado=True,
				)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error, debe seleccionar opciones validas en el menu')
		return redirect(op_index)

	pdf = op.hacer_pdf()

	response = HttpResponse(pdf, content_type='application/pdf')
	nombre = "OP_%s.pdf" % (op.formatoAfip())
	content = "inline; filename=%s" % nombre
	response['Content-Disposition'] = content
	return response

class HeaderExemptMixin:

	def get_object(self, queryset=None):
		return OP.objects.get(
				consorcio=consorcio(self.request),
				pk=self.kwargs['pk']
			)
	def get_cierre(self):
		try:
			return Cierre.objects.filter(consorcio=consorcio(self.request), confirmado=True).order_by('-periodo')[0]
		except:
			return None

class OPManager(HeaderExemptMixin):

	def cajas(self, *args, **kwargs):
		pass

	def anular(self, *args, **kwargs):
		op = self.get_object()
		if not op.anulado:
			op.reversar_operaciones()
			op.anulado = date.today()
			asiento_anulacion = asiento_op_anulacion(op)
			for d in op.deudaop_set.all():
				d.deuda.chequear()
			for r in op.retencionop_set.all():
				r.deuda.anulado = date.today()
				r.deuda.save()

@method_decorator(group_required('administrativo'), name='dispatch')
class OPAnular(OPManager, generic.DeleteView):

	""" Para anular una OP """

	template_name = 'op/anular.html'
	model = OP

	def delete(self, request, *args, **kwargs):
		cierre = self.get_cierre()
		op = self.get_object()
		if cierre:
			if op.fecha <= cierre.periodo:
				messages.error(self.request, 'No se puede anular una OP anterior a un cierre.')
				return redirect(self.get_success_url())



		self.anular()
		messages.success(self.request, 'OP anulada con exito.')

		return redirect(self.get_success_url())

	def get_success_url(self, **kwargs):
		return reverse_lazy('op_ver', args=(self.get_object().pk,))