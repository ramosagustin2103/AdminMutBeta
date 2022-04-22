from django.db import models
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from datetime import date
from django.template.loader import render_to_string
from django.core.files.uploadedfile import SimpleUploadedFile
from weasyprint import HTML

from arquitectura.models import *
from admincu.funciones import armar_link, emisor_mail
from biblioteca.models import Libro

class Bienvenida(models.Model):

	""" Mail de bienvenida al socio """

	socio = models.ForeignKey(Socio, on_delete=models.CASCADE)
	mail = models.EmailField(max_length=254)
	saludo = models.TextField(blank=True, null=True)
	fecha_envio = models.DateField(blank=True, null=True)

	def __str__(self):
		return str(self.socio)

	def enviar(self):
		if self.socio.consorcio.mails and not self.fecha_envio:
			socio = self.socio
			if not socio.codigo:
				socio.generar_codigo()

			saludo = self.saludo
			link_facturacion = armar_link(reverse('signup'))
			html_string = render_to_string('herramientas/bienvenida/mail.html', locals())

			msg = EmailMultiAlternatives(
				subject="Bienvenido a AdminCU - Crea tu usuario",
				body="",
				from_email=emisor_mail(self.socio.consorcio),
				to=[self.mail],
			)
			instructivo = Libro.objects.get(consorcio__isnull=True, slug='instructivo-basico-del-socio.pdf')
			msg.attach_alternative(html_string, "text/html")
			msg.attach_file(instructivo.ubicacion.path)
			msg.send()
			self.fecha_envio = date.today()
			self.save()


class Transferencia(models.Model):

	""" Mail de bienvenida al socio """

	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	fecha = models.DateField(blank=True, null=True)
	punto = models.ForeignKey(PointOfSales, blank=True, null=True, on_delete=models.CASCADE)
	numero = models.PositiveIntegerField(blank=True, null=True)
	total = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
	asiento = models.ForeignKey(Asiento, on_delete=models.SET_NULL, blank=True, null=True)
	pdf = models.FileField(upload_to="transferencias/pdf/", blank=True, null=True)

	def puntof(self):
		agregado = "0"
		numero = str(self.punto)
		largo = len(numero)
		ceros = 4 - largo
		ceros = agregado * ceros
		numero = ceros + numero
		return numero

	def numerof(self):
		agregado = "0"
		numero = str(self.numero)
		largo = len(numero)
		ceros = 8 - largo
		ceros = agregado * ceros
		numero = ceros + numero
		return numero

	def formatoAfip(self):
		data = "%s-%s" % (self.puntof(), self.numerof())
		return data

	def __str__(self):
		nombre = self.formatoAfip()
		return nombre


	def save(self, *args, **kw):
		if not self.numero:
			numero_transferencia = 1
			try:
				ultima = Transferencia.objects.filter(
						consorcio=self.consorcio,
						punto=self.punto,
						numero__isnull=False
					).order_by('-numero')[0].numero
			except:
				ultima = 0
			self.numero = ultima + numero_transferencia
		super().save(*args, **kw)


	def hacer_pdf(self):
		if not self.pdf:
			transferencia = self
			html_string_pdf = render_to_string('herramientas/transferencias/pdf/transferencia.html', locals())
			html = HTML(string=html_string_pdf, base_url='https://www.admincu.com/herramientas/')
			pdf = html.write_pdf()
			ruta = "{}_{}.pdf".format(
					str(self.consorcio.abreviatura),
					str(self.formatoAfip())
				)
			self.pdf = SimpleUploadedFile(ruta, pdf, content_type='application/pdf')
			self.save()

	def hacer_asiento(self):

		""" Crea el asiento de la liquidacion """

		if not self.asiento:
			from contabilidad.asientos.manager import AsientoCreator

			descripcion = 'Transferencia {}'.format(self.formatoAfip())
			data_asiento = {
				'consorcio': self.consorcio,
				'fecha_asiento': self.fecha,
				'descripcion': descripcion
			}

			cajas_origen = self.cajatransferencia_set.all()
			caja_destino = cajas_origen.first().destino

			operaciones = [
				{
					'cuenta': caja_destino.cuenta_contable,
					'debe': self.total,
					'haber': 0,
					'descripcion': descripcion
				}
			]
			for caja in cajas_origen:
				operaciones.append({
					'cuenta': caja.origen.cuenta_contable,
					'debe': 0,
					'haber': caja.valor,
					'descripcion': descripcion
				})

			crear_asiento = AsientoCreator(data_asiento, operaciones)
			asiento = crear_asiento.guardar()
			self.asiento = asiento
			self.save()



class CajaTransferencia(models.Model):

	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	fecha = models.DateField(blank=True, null=True)
	transferencia = models.ForeignKey(Transferencia, blank=True, null=True, on_delete=models.CASCADE)
	origen = models.ForeignKey(Caja, blank=True, null=True, on_delete=models.CASCADE, related_name='transferencia_origen')
	destino = models.ForeignKey(Caja, blank=True, null=True, on_delete=models.CASCADE, related_name='transferencia_destino')
	referencia = models.CharField(max_length=10, blank=True, null=True)
	valor = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

	def __str__(self):
		return "{}. {} a {}".format(self.transferencia, self.origen, self.destino)


	@property
	def nombre(self):

		""" Retorna el nombre. No utilizo __str__ porque nose donde la estoy mostrando """

		nombre = "Transferencia entre Cajas {}. ".format(self.transferencia.formatoAfip())

		return nombre