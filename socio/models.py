from __future__ import unicode_literals
from django.db import models
from arquitectura.models import *
from creditos.models import *
from django_mercadopago.models import Preference

class Pago(models.Model):
	socio = models.ForeignKey(Socio, on_delete=models.CASCADE)
	credito = models.ForeignKey(Credito, blank=True, null=True, on_delete=models.CASCADE)
	capital = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
	int_desc = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
	subtotal = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
	preference = models.ForeignKey(Preference, blank=True, null=True, on_delete=models.CASCADE)
	estado = models.BooleanField(default=True)

	def __str__(self):
		return str(self.socio)

