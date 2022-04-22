from datetime import datetime, date
from pytz import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from decimal import Decimal
from admincu.funciones import *
from consorcios.models import *
from arquitectura.models import *
from arquitectura.forms import *
from weasyprint import HTML
from django.db import transaction
from comprobantes.models import *
from django_mercadopago.models import *
from .models import *
from .funciones import *
from comprobantes.funciones import bloqueador


@group_required('socio')
@transaction.atomic
def exp_index(request):
	try:
		socio = Socio.objects.get(usuarios=request.user)
	except:
		return redirect('home')

	expensas = Credito.objects.filter(socio=socio).order_by('-liquidacion')
	bloqueo = bloqueador(expensas)

	if request.method == "POST":
		# messages.add_message(request, messages.ERROR, 'Por el momento no se permite realizar pagos con MercadoPago.')
		# return redirect('socio:expensas')
		if valid_demo(request.user):
			return redirect('socio:expensas')
		creditos_seleccionados = expensas.filter(id__in=request.POST.getlist('vinculo[]'))
		# Para ver si se intenta pagar un credito que ya tiene un pago en estado activo
		errores = [c.id for c in creditos_seleccionados for p in c.pago_set.filter(estado=True)]
		if errores:
			messages.add_message(request, messages.ERROR, 'Esta intentando abonar un concepto que tiene un pago en estado pendiente. Para volver a generarlo debe desechar los pagos pendientes.')
		else:
			try:
				totales = Decimal("%s" % 1.0569093) # Credito mas costo de mercadopago
				price = sum([(c.subtotal * totales) for c in creditos_seleccionados])
				price = Decimal("%.2f" % price)
				hoy = datetime.today()
				ultimo_minuto = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)
				vencimiento = ultimo_minuto.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
				vencimiento = vencimiento + "-03:00"
				extra_fields = {
					"expires": True,
					"expiration_date_from": vencimiento,
					"expiration_date_to": vencimiento,
				}
				preference = Preference.objects.create(
					title='Cobro de expensas',
					price=price,
					reference=randomNumber(Preference, 'reference'),
					description='',
					account=consorcio(request).mercado_pago,
					extra_fields=extra_fields,
				)
				pagados = [Pago(
						socio=socio,
						credito=c,
						capital=c.capital,
						int_desc=-c.descuento if c.descuento else c.intereses,
						subtotal=c.subtotal,
						preference=preference,
					) for c in creditos_seleccionados]
				Pago.objects.bulk_create(pagados)
				return HttpResponseRedirect(preference.url)
			except:
				messages.add_message(request, messages.ERROR, 'Hubo un error, MercadoPago no esta disponible en este momento.')
				return redirect('socio:expensas')

	return render(request, 'socio/expensas/index.html', locals())


@require_http_methods(["POST"])
@group_required('socio')
@transaction.atomic
def eliminar_pagos(request):
	try:
		socio = Socio.objects.get(usuarios=request.user)
	except:
		return redirect('home')

	pagos = Pago.objects.filter(socio=socio).update(estado=False)


	messages.add_message(request, messages.SUCCESS, 'Pagos descartados con exito')
	return redirect('socio:expensas')


@group_required('socio')
def pagos_index(request):
	try:
		socio = Socio.objects.get(usuarios=request.user)
	except:
		return redirect('home')

	comprobantes = Comprobante.objects.filter(socio=socio).order_by('-id')
	pagos = Payment.objects.filter(
				cobro__socio=socio,
				cobro__comprobante__isnull=True,
			).distinct()

	return render(request, 'socio/pagos/index.html', locals())


@transaction.atomic
def mp_success(request, pk):
	try:
		notification = Notification.objects.get(id=pk)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error al buscar el pago.')
		return redirect('socio:expensas')

	pago = notification.process()
	generar_cobro(pago)

	messages.add_message(request, messages.SUCCESS, 'Pago realizado con exito.')
	return redirect('socio:pagos')


@transaction.atomic
def mp_failure(request, pk):
	try:
		preference = Preference.objects.get(id=pk)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error al buscar el pago.')
		return redirect('socio:expensas')

	pagos = Pago.objects.filter(preference=preference).update(estado=False)

	messages.add_message(request, messages.ERROR, 'Pago cancelado.')
	return redirect('socio:expensas')

def mp_pending(request, pk):
	try:
		preference = Preference.objects.get(id=pk)
	except:
		messages.add_message(request, messages.ERROR, 'Hubo un error al buscar el pago.')
		return redirect('socio:expensas')

	messages.add_message(request, messages.SUCCESS, 'Pago en estado pendiente.')
	return redirect('socio:expensas')