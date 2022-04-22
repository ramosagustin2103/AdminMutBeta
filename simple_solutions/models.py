from django.db import models
from consorcios.models import Consorcio

class ClienteSS(models.Model):

	""" Vincula el consorcio con el nombre asignado por SimpleSolutions y si tiene o no Expensas Pagas ."""

	consorcio = models.ForeignKey(Consorcio, related_name='ss', on_delete=models.CASCADE)
	nombre = models.CharField(max_length=100)
	expensas_pagas = models.BooleanField(default=False)


class Enviado(models.Model):

	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	modelo = models.CharField(max_length=20)
	id_modelo = models.PositiveIntegerField()
	fecha_envio = models.DateField(blank=True, null=True)


	def __str__(self):
		return "{} - {}".format(self.modelo, self.id_modelo)