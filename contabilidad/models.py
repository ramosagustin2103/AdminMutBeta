from __future__ import unicode_literals
from datetime import date
from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
from consorcios.models import *


class Cuenta(models.Model):
	consorcio = models.ForeignKey(Consorcio, blank=True, null=True, on_delete=models.CASCADE) # Para cuentas especificas
	nivel = models.IntegerField()
	dependencia = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE)
	numero = models.CharField(max_length=6)
	nombre = models.CharField(max_length=50)

	def __str__(self):
		nombre = '%s | %s' % (self.numero, self.nombre)
		return nombre


	def operaciones(self, ejercicio, fecha_inicio=None, fecha_fin=None):

		""" Recoje las operaciones """

		if not fecha_inicio:
			fecha_inicio = ejercicio.inicio

		if not fecha_fin:
			fecha_fin = ejercicio.cierre

		return self.operacion_set.filter(
				asiento__fecha_asiento__range=[fecha_inicio, fecha_fin],
				asiento__consorcio=ejercicio.consorcio
			)


	def saldo_debe(self, operaciones):

		""" Saldo del debe, tiene que recibir las operaciones """

		return sum([o.debe for o in operaciones])

	def saldo_haber(self, operaciones):

		""" Saldo del haber, tiene que recibir las operaciones """

		return sum([o.haber for o in operaciones])

	def saldo(self, ejercicio, fecha_inicio=None, fecha_fin=None):

		operaciones = self.operaciones(ejercicio, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
		debe = self.saldo_debe(operaciones)
		haber = self.saldo_haber(operaciones)
		numero = int(self.numero) # Numero de la cuenta expresado en int
		if numero in range(100000,199999) or numero > 500000:
			saldo = debe - haber
		else:
			saldo = haber - debe
		return saldo

	class Meta:
		ordering = ['numero']



class Plan(models.Model):
	consorcio = models.ForeignKey(Consorcio, blank=True, null=True, on_delete=models.CASCADE)
	cuentas = models.ManyToManyField(Cuenta)

	def __str__(self):
		nombre = '%s' % (self.consorcio)
		return nombre



class Operacion(models.Model):
	numero_aleatorio = models.CharField(max_length=30, blank=True, null=True)
	cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
	debe = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
	haber = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
	descripcion = models.CharField(max_length=150, blank=True, null=True)

	def __str__(self):
		nombre = '%s' % (self.cuenta)
		return nombre


class Asiento(models.Model):
	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	fecha_asiento = models.DateField()
	descripcion = models.CharField(max_length=150, blank=True, null=True)
	fecha_creacion = models.DateField(auto_now_add=True, auto_now=False)
	fecha_ultima_modificacion = models.DateField(auto_now_add=False, auto_now=True)
	operaciones = models.ManyToManyField(Operacion)
	principal = models.IntegerField(blank=True, null=True) # 1 para apertura, 2 para cierre de resultados, 3 para cierre patrimonial

	def __str__(self):
		nombre = '%s' % (self.fecha_asiento)
		return nombre


class Ejercicio(models.Model):
	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	numero_aleatorio = models.CharField(max_length=30)
	nombre = models.CharField(max_length=15)
	inicio = models.DateField()
	cierre = models.DateField()
	activo = models.BooleanField(default=False)

	def __str__(self):
		nombre = '%s' % (self.nombre)
		return nombre

	def save(self, *args, **kw):
		if self.activo == True:
			otros_ejercicios = Ejercicio.objects.filter(consorcio=self.consorcio).exclude(id=self.id)
			if otros_ejercicios:
				otros_ejercicios.update(activo=False)
		super(Ejercicio, self).save(*args, **kw)


	def delete(self, *args, **kw):
		otros_ejercicios = Ejercicio.objects.filter(consorcio=self.consorcio).exclude(id=self.id).order_by('-cierre')
		if otros_ejercicios:
			otros_ejercicios[0].activo = True
			otros_ejercicios[0].save()
		super(Ejercicio, self).delete(*args, **kw)