from django.dispatch import receiver
from django_mercadopago.signals import *
from .funciones import *

@receiver(payment_received)
def prcesar_notif(sender, **kwargs):
	pago = kwargs['payment']
	generar_cobro(pago)
