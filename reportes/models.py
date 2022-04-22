from __future__ import unicode_literals
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives

from admincu.funciones import armar_link, emisor_mail
from consorcios.models import *
from arquitectura.models import *
from creditos.models import *

class Cierre(models.Model):
	consorcio = models.ForeignKey(Consorcio, blank=True, null=True, on_delete=models.CASCADE)
	periodo = models.DateField()
	auditor = models.CharField(max_length=25, blank=True, null=True)
	logo_auditor = models.ImageField(upload_to="reportes/logos/", blank=True, null=True)
	confirmado = models.BooleanField(default=False)
	total = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
	mails = models.BooleanField(default=False)

	per_cap = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True) # En desuso
	referencia = models.DecimalField(max_digits=20, decimal_places=3, blank=True, null=True) # En desuso
	reservado = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True) # En desuso
	liquidacion = models.ForeignKey(Liquidacion, blank=True, null=True, on_delete=models.CASCADE) # En desuso

	def __str__(self):
		nombre = '%s' % (self.periodo)
		return nombre

	@property
	def extension_logo(self):
		return '{}'.format(str(self.logo_auditor)[::-1].split('.', 1)[0][::-1])

	@property
	def admission(self):
		extension_container = ['jpg', 'JPG', 'png', 'PNG']
		return self.extension_logo in extension_container

	def enviar_mails(self):
		if self.consorcio.mails:

			socios = self.consorcio.socio_set.filter(baja__isnull=True)
			for socio in socios:
				link_reportes = armar_link(reverse('reportes'))
				html_string = render_to_string('reportes/mail.html', locals())

				for usuario in socio.usuarios.all():
					if usuario.email:
						msg = EmailMultiAlternatives(
							subject="Nuevos reportes de tu consorcio",
							body="",
							from_email=emisor_mail(self.consorcio),
							to=[usuario.email],
						)

						msg.attach_alternative(html_string, "text/html")
						for reporte in self.reportes.all():
							msg.attach_file(reporte.ubicacion.path)
						msg.send()


class Subtotal(models.Model):
	cierre = models.ForeignKey(Cierre, blank=True, null=True, on_delete=models.CASCADE, related_name="subtotales")
	cuenta = models.ForeignKey(Cuenta, blank=True, null=True, on_delete=models.CASCADE)
	total = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)


class Reporte(models.Model):
	consorcio = models.ForeignKey(Consorcio, blank=True, null=True, on_delete=models.CASCADE)
	cierre = models.ForeignKey(Cierre, blank=True, null=True, on_delete=models.CASCADE, related_name="reportes")
	ubicacion = models.FileField(upload_to="reportes/")
	nombre = models.CharField(max_length=100, blank=True, null=True)
	automatico = models.BooleanField(default=False)

	def imagen(self):
		try:
			imagen = 'assets/images/file_icons/{}.svg'.format(self.extension)
		except:
			imagen = 'assets/images/file_icons/txt.svg'
		return imagen

	@property
	def extension(self):
		return '{}'.format(str(self.nombre)[::-1].split('.', 1)[0][::-1])

	@property
	def admission(self):
		extension_container = ['pdf', 'PDF', 'doc', 'DOC', 'docx', 'DOCX', 'xls', 'XLS', 'xlsx', 'XLSX']
		return self.extension in extension_container


	def __str__(self):
		nombre = '%s' % (self.nombre)
		return nombre


@receiver(pre_delete, sender=Reporte)
def rep_archivo_delete(sender, instance, **kwargs):
    instance.ubicacion.delete(False)