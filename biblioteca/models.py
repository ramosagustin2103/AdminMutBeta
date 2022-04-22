# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
from django.utils.text import slugify
from consorcios.models import *


class Categoria(models.Model):
	consorcio = models.ForeignKey(Consorcio, blank=True,null=True, on_delete=models.CASCADE)
	icono = models.CharField(max_length=30, blank=False, null=False)
	nombre = models.CharField(max_length=70)
	slug = models.SlugField(max_length=70)
	descripcion = models.TextField(blank=False, null=False)
	galeria = models.BooleanField(default=False)
	compartido = models.ManyToManyField(Group)

	def __str__(self):
		nombre = '{}'.format(self.nombre)
		return nombre

	def save(self, *args, **kw):
		self.slug = slugify(self.nombre)
		super(Categoria, self).save(*args, **kw)


class Libro(models.Model):
	consorcio = models.ForeignKey(Consorcio, blank=True,null=True, on_delete=models.CASCADE)
	nombre = models.CharField(max_length=70, blank=False, null=False)
	slug = models.SlugField(max_length=70)
	ubicacion = models.FileField(upload_to="biblioteca/")
	categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
	compartido = models.ManyToManyField(Group)

	def __str__(self):
		nombre = '{}'.format(self.nombre)
		return nombre

	def imagen(self):
		try:
			imagen = 'assets/images/file_icons/{}.svg'.format(str(self.ubicacion)[::-1].split('.', 1)[0][::-1])
		except:
			imagen = 'assets/images/file_icons/txt.svg'
		return imagen

	def formato(self):
		return '{}'.format(str(self.ubicacion)[::-1].split('.', 1)[0][::-1])


	def save(self, *args, **kw):
		self.slug = '{}.{}'.format(slugify(self.nombre), self.formato())
		super(Libro, self).save(*args, **kw)

@receiver(pre_delete, sender=Libro)
def Libro_delete(sender, instance, **kwargs):
    instance.ubicacion.delete(False)


