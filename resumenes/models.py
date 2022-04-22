from __future__ import unicode_literals
from django.db import models
from django.utils.text import slugify


class Resumen(models.Model):
	nombre = models.CharField(max_length=70)
	slug = models.SlugField(max_length=70, blank=True, null=True)
	descripcion = models.TextField(blank=True, null=True)

	def __str__(self):
		return self.nombre

	def save(self, *args, **kw):
		self.slug = slugify(self.nombre)
		super(Resumen, self).save(*args, **kw)
