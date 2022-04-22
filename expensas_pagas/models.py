import base64
from django.db import models
from consorcios.models import Consorcio
from creditos.models import Factura
from io import BytesIO
from barcode import ITF
from barcode.writer import ImageWriter
from django_afip.pdf import ImageWitoutTextWriter
from django.template.loader import render_to_string
from weasyprint import HTML
from django.core.files.uploadedfile import SimpleUploadedFile


from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from admincu.funciones import emisor_mail



class DocumentoExp(models.Model):

	""" Agrega datos de exp necesarios al dcocumento."""

	documento = models.ForeignKey(Factura, related_name='exp', on_delete=models.CASCADE)
	barcode = models.CharField(max_length=90)
	cpe = models.CharField(max_length=6516)
	inf_deuda = models.BooleanField(default=False)
	pdf = models.FileField(upload_to="expensas_pagas/pdf/", blank=True, null=True)

	@property
	def socio(self):
		return self.documento.socio

	def hacer_pdf(self):

		if not self.pdf:
			archivo = []
			enteros = []
			factura = self.documento

			codigo_barra = self.barcode
			cpe = self.cpe

			rv = BytesIO()

			ITF(codigo_barra, writer=ImageWitoutTextWriter()).write(rv)
			barcode_cupon = base64.b64encode(rv.getvalue()).decode("utf-8")
			
			fecha1 = factura.expensas_pagas(0)
			fecha2 = factura.expensas_pagas(1)
			if not fecha2:
				fecha2 = fecha1			
			saldo1 = factura.saldo(fecha1)
			saldo2 = factura.saldo(fecha2)

			barcode_text = self.barcode

			html_string_cupon = render_to_string('expensas_pagas/cupon.html', locals())
			html_cupon = HTML(string=html_string_cupon, base_url='https://www.admincu.com/comprobantes/')
			pdfCupon = html_cupon.render()
			enteros.append(pdfCupon)
			for p in pdfCupon.pages:
				archivo.append(p)

			pdf = enteros[0].copy(archivo).write_pdf()
			ruta = "exp_{}_{}_{}.pdf".format(
					str(factura.consorcio.abreviatura),
					str(factura.receipt.receipt_type.code),
					str(factura.formatoAfip())
			)

			self.pdf = SimpleUploadedFile(ruta, pdf, content_type='application/pdf')
			self.save()



	def enviar_mail(self):
		if self.documento.consorcio.mails:
			if self.documento.consorcio.superficie:
				socio = self.documento.socio
				html_string = render_to_string('expensas_pagas/mail.html', locals())

				lista_mails = []
				usuarios = socio.usuarios.all()
				if usuarios:
					for usuario in usuarios:
						lista_mails.append(usuario.email)
				else:
					lista_mails.append(socio.mail)
				for receptor in lista_mails:
					if receptor:
						msg = EmailMultiAlternatives(
							subject="Nuevo Cupon de Pago",
							body="",
							from_email=emisor_mail(self.consorcio),
							to=[receptor],
						)

						msg.attach_alternative(html_string, "text/html")
						msg.attach_file(self.pdf.path)
						msg.send()
				



class ClienteExp(models.Model):

	""" Vincula el consorcio con datos enviados por exp para el mismo."""

	consorcio = models.ForeignKey(Consorcio, related_name='exp', on_delete=models.CASCADE)
	codigo_exp = models.PositiveIntegerField(blank=True, null=True)
	di_exp = models.PositiveIntegerField(blank=True, null=True)



class CobroExp(models.Model):

	""" Cobros Expensas Pagas Model."""

	codigo_consorcio = models.PositiveIntegerField(blank=True, null=True)
	unidad_funcional = models.PositiveIntegerField(blank=True, null=True)
	fecha_cobro = models.DateField(blank=True, null=True)
	importe_cobrado = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
	comision_plataforma = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
	neto_a_depositar = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
	canal_de_pago = models.CharField(max_length=15)
	documentado = models.DateField(blank=True, null=True)





