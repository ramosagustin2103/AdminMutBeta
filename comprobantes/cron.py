from django.db import transaction
from consorcios.models import Consorcio
from datetime import date, timedelta
from .models import *
from .funciones import asiento_diario

@transaction.atomic
def hacer_asiento():

	""" Realizacion de asiento diario de comprobantes """

	hoy = date.today()
	for consorcio in Consorcio.objects.all():
		comprobantes = consorcio.comprobante_set.filter(asiento__isnull=True, fecha=hoy)
		asiento_diario(hoy, consorcio, comprobantes)


def chequear_mp():

	"""
		Chequea si se cobro.
		Si no se cobro y ademas es viejo por 60 dias lo borra
	"""

	for cobro in Cobro.objects.filter(comprobante__isnull=True, preference__paid=False, credito__fin__isnull=True):
		try:
			cobro.preference.poll_status()
		except:
			pass

def procesar_recibos_masivos():
	for comprobante in Comprobante.objects.filter(anulado__isnull=True, pdf="", fecha__gt=date(2020,11,1)):
		error = None
		if comprobante.nota_credito:
			validacion_nc = comprobante.validar_receipt(comprobante.nota_credito)
			if validacion_nc:
				error = validacion_nc
		if comprobante.nota_debito:
			validacion_nd = comprobante.validar_receipt(comprobante.nota_debito)
			if validacion_nd:
				error = validacion_nd
		
		print(error)
		
		if not error:
			try:
				comprobante.hacer_pdfs()
				comprobante.enviar_mail()
			except:
				pass
