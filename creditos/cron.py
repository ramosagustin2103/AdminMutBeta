from consorcios.models import Consorcio
from django.db import transaction
from .models import Liquidacion, Factura
from expensas_pagas.models import ClienteExp, DocumentoExp
from expensas_pagas.manager import *

def procesar_liquidaciones():

	"""
		Procesamiento de liquidaciones .
		Envia la informacion a AFIP.
		Una vez terminado el recorrido por las facturas de la liquidacion, cambia su estado por "confimado" o "errores"
	"""

	for consorcio in Consorcio.objects.all():
		for liquidacion in consorcio.liquidacion_set.filter(estado="en_proceso"):
			for factura in liquidacion.factura_set.filter(receipt__receipt_number__isnull=True):
				creditos = factura.incorporar_creditos()

				factura.validar_factura()

			liquidacion.confirmar()



def enviar_mails_facturas():

	""" Envia los mails de las liquidaciones donde mails=True """

	for liquidacion in Liquidacion.objects.filter(mails=True):
		for factura in liquidacion.factura_set.all():
			if factura.pdf:
				if liquidacion.consorcio.exp.first():
					if len(liquidacion.factura_set.all()) >= (0.7*len(liquidacion.consorcio.socio_set.filter(baja__isnull=True))):

						if factura.receipt.total_amount < 100000:
							if factura.socio.socio.first(): # Si es socio
								if not factura.exp.first():	# Si no existe aun cupon de esta factura
									NewExp().cupon_creator(c=factura) # Hacer el cupon
									factura.exp.first().hacer_pdf() # Hacer el pdf




				factura.enviar_mail()
		liquidacion.mails = False
		liquidacion.save()
