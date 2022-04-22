from consorcios.models import Consorcio
from .models import Cierre


def enviar_mails_cierres():

	""" Envia los mails de los cierres donde mails=True """

	for cierre in Cierre.objects.filter(mails=True):
		cierre.enviar_mails()
		cierre.mails = False
		cierre.save()

