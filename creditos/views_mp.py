from datetime import datetime, date
from decimal import Decimal
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.views import generic
from django.db import transaction
from django_mercadopago.models import *
from django.contrib import messages

from admincu.funciones import *
from .models import Credito
from comprobantes.models import Cobro
from comprobantes.funciones import *

@method_decorator(group_required('socio'), name='dispatch')
class PreferenceNew(generic.View):

	""" Para crear preferencia de pago a traves de MP """

	def get(self, request, *args, **kwargs):
		return redirect('facturacion-socio')

	@transaction.atomic
	def post(self, request):

		creditos_seleccionados = Credito.objects.filter(id__in=request.POST.getlist('vinculo[]'))
		todos_creditos = Credito.objects.filter(
				padre__isnull=True,
				liquidacion__estado="confirmado",
				socio=self.request.user.socio_set.first()
		)
		socio = request.user.socio_set.first()

		try:
			costo_mp = 1.0440909 if not consorcio(request).costo_mp else 1
			totales = Decimal("%s" % costo_mp) # Credito mas costo de mercadopago
			bloqueo_descuento = bloqueador_descuentos(todos_creditos)
			price = 0
			for c in creditos_seleccionados:
				if bloqueo_descuento:
					price += c.saldo_socio * totales
				else:
					price += c.saldo * totales

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
				title='Cobro',
				price=price,
				reference=randomNumber(Preference, 'reference'),
				description='',
				account=consorcio(request).mercado_pago,
				extra_fields=extra_fields,
			)
			cobros = []
			for c in creditos_seleccionados:
				if bloqueo_descuento:
					if c.int_desc() > 0:
						int_desc = c.int_desc()
						subtotal = c.subtotal()
					else:
						int_desc = 0
						subtotal = c.bruto
				else:
					int_desc = c.int_desc()
					subtotal = c.subtotal()
				cobros.append(Cobro(
						consorcio=consorcio(request),
						fecha=date.today(),
						socio=socio,
						credito=c,
						capital=c.bruto,
						int_desc=int_desc,
						subtotal=subtotal,
						preference=preference,
					))
			Cobro.objects.bulk_create(cobros)
			direccionamiento = "https://www.mercadopago.com/mla/checkout/start?pref_id={}".format(preference.mp_id)
			return HttpResponseRedirect(direccionamiento)
		except:
			messages.error(request, "No se pudo generar la peticion a MercadoPago")
			return redirect('facturacion-socio')



@method_decorator(group_required('socio'), name='dispatch')
class PreferenceDelete(generic.DeleteView):

	""" Eliminar preferencia de MercadoPago """

	model = Preference
	template_name = "creditos/socio/eliminar-preference.html"
	success_url = "/facturacion/socio/"

	@transaction.atomic
	def delete(self, request, *args, **kwargs):
		preference = self.get_object()
		cobros = preference.cobro_set.all()
		cobros.delete()
		return redirect('facturacion-socio')

	def dispatch(self, request, *args, **kwargs):
		preference = self.get_object()
		error = False
		if preference.paid: # Redireccionar si ya esta pagada
			error = True
		socio = request.user.socio_set.first()
		cobros = preference.cobro_set.first() # Solo traer el primero, para consultar el socio
		if cobros.socio != socio:
			error = True
		if error:
			messages.error(request, "No se pudo encontrar la peticion a MercadoPago")
			return redirect('facturacion-socio')
		return super().dispatch(request, *args, **kwargs)



class MPSuccess(generic.View):

	""" Al recibir una notificacion por cobro satisfactorio realizado desde mercadopago """

	@transaction.atomic
	def get(self, request, pk):
		notification = Notification.objects.get(id=pk)
		messages.success(request, "Pago realizado con exito")
		return redirect('cobranzas-socio')


class MPFailed(generic.View):

	""" Al recibir una preferencia que fallo desde mercadopago """

	@transaction.atomic
	def get(self, request, pk):
		preference = Preference.objects.get(id=pk)
		preference.delete()
		messages.error(self.request, 'No se pudo registrar su pago.')
		return redirect('facturacion-socio')


class MPPending(generic.View):

	""" Al recibir una preferencia que esta pendiente desde mercadopago """

	def get(self, request, pk):

		preference = Preference.objects.get(id=pk)
		messages.success(self.request, 'Tu pago se encuentra pendiente. Tienes hasta las 23 hs para abonar')
		return redirect('facturacion-socio')
