from __future__ import unicode_literals
from django.contrib.auth.models import User, Group
from django.db import models
from django_afip.models import TaxPayer
from django_mercadopago.models import Account


class Tipo_CU(models.Model):
	nombre = models.CharField(max_length=40)
	codigo_afip = models.CharField(max_length=4)

	def __str__(self):
		nombre = '%s' % (self.nombre)
		return nombre


class Codigo_Provincia(models.Model):
	nombre = models.CharField(max_length=40)
	codigo_afip = models.CharField(max_length=4)

	def __str__(self):
		nombre = '%s' % (self.nombre)
		return nombre


class Consorcio(models.Model):
	contribuyente = models.ForeignKey(TaxPayer, on_delete=models.CASCADE)
	mercado_pago = models.ForeignKey(Account, blank=True, null=True, on_delete=models.CASCADE)
	nombre = models.CharField(max_length=20, blank=False, null=False)
	nombre_completo = models.CharField(max_length=70, blank=False, null=False)
	tipo = models.ForeignKey(Tipo_CU, blank=True, null=True, on_delete=models.CASCADE)
	abreviatura = models.CharField(max_length=7, blank=False, null=False)
	domicilio = models.CharField(max_length=70, blank=True, null=True)
	provincia = models.ForeignKey(Codigo_Provincia, blank=True, null=True, on_delete=models.CASCADE)
	superficie = models.DecimalField(max_digits=9, decimal_places=3, blank=True, null=True)
	fecha_reg = models.DateTimeField(auto_now_add=True, auto_now=False)
	usuarios = models.ManyToManyField(User, blank=True)
	mails = models.BooleanField(default=False)
	dominioweb = models.CharField(max_length=70, blank=True, null=True)
	costo_mp = models.BooleanField(default=False) # Si es True el club se hace cargo

	def __str__(self):
		nombre = '%s' % (self.nombre)
		return nombre

	def lista(self):
		return self.nombre.split(' ')

	@property
	def nombre_raiz(self):
		return self.lista()[0]

	@property
	def referencia(self):
		if self.superficie:
			return self.superficie
		else:
			return self.dominio_set.all().count()

	def cuit(self):
	    numero = str(self.contribuyente.cuit)
	    if len(numero) != 11:
	        return numero
	    return '{}-{}-{}'.format(
	        numero[0:2],
	        numero[2:10],
	        numero[10:11]
	    )


class Tipo_Ocupante(models.Model):
	nombre = models.CharField(max_length=40)
	codigo_afip = models.CharField(max_length=4)

	def __str__(self):
		nombre = '%s' % (self.nombre)
		return nombre