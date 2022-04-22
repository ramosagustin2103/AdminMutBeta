from __future__ import unicode_literals
import calendar
import base64
from datetime import datetime, date, timedelta
from django.db.models import Max
from decimal import Decimal
from django.db import models
from django_afip.models import PointOfSales
from django.template.loader import render_to_string
from django.urls import reverse
from django_afip.models import *
from django_afip.pdf import ReceiptBarcodeGenerator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.mail import EmailMultiAlternatives
from weasyprint import HTML

from consorcios.models import *
from arquitectura.models import *
from contabilidad.models import *
from admincu.funciones import armar_link, emisor_mail

exposed_request = None

class Liquidacion(models.Model):
	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	punto = models.ForeignKey(PointOfSales, on_delete=models.CASCADE)
	numero = models.PositiveIntegerField(blank=True, null=True)
	fecha = models.DateField(blank=True, null=True)
	capital = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
	ESTADO_CHOICES = (
		('en_proceso', 'En proceso'),
		('errores', 'Errores'),
		('confirmado', 'Confirmado'),
	)
	estado = models.CharField(max_length=15, choices=ESTADO_CHOICES)
	pdf = models.FileField(upload_to="liquidaciones/pdf/", blank=True, null=True)
	asiento = models.ForeignKey(Asiento, on_delete=models.SET_NULL, blank=True, null=True)
	mails = models.BooleanField(default=False) # Si esta en True, el cron enviara los mails

	def puntof(self):
		agregado = "0"
		numero = str(self.punto.number)
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

	@property
	def suma_capitales(self):

		""" Suma los capitales de los creditos """

		return sum([c.capital for c in self.credito_set.filter(padre__isnull=True)])

	@property
	def suma_bonificaciones(self):

		""" Suma las bonificaciones de los creditos """

		return sum([c.bonificacion for c in self.credito_set.filter(padre__isnull=True)])

	@property
	def suma_brutos(self):

		""" Suma los brutos de los creditos """

		return sum([c.bruto for c in self.credito_set.filter(padre__isnull=True)])

	def confirmar(self):

		"""
			Chequea si al finalizar el procesamiento de una liquidacion
			existen facturas no validadas por AFIP
		"""

		errores = self.factura_set.filter(receipt__receipt_number__isnull=True)
		if errores:
			self.estado = "errores"
		else:
			self.estado = "confirmado"
			self.hacer_pdf()
			self.hacer_asiento()
			self.mails = True

		self.save()

	def hacer_pdf(self):
		if not self.pdf:
			liquidacion = self
			html_string_pdf = render_to_string('creditos/pdfs/liquidacion.html', locals())
			html = HTML(string=html_string_pdf, base_url='https://www.admincu.com/liquidaciones/')
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
			from contabilidad.models import Cuenta
			descripcion = 'Liquidacion {}'.format(self.formatoAfip())
			if self.factura_set.first():
				fecha_asiento = self.factura_set.first().receipt.issued_date
			else:
				fecha_asiento = self.fecha
			data_asiento = {
				'consorcio': self.consorcio,
				'fecha_asiento': fecha_asiento,
				'descripcion': descripcion
			}
			data_operaciones = [
				{
					'cuenta': Cuenta.objects.get(numero=112101),
					'debe': self.suma_brutos,
					'haber': 0,
					'descripcion': descripcion

				}
			]

			creditos = self.credito_set.filter(padre__isnull=True)
			bonificaciones = set([credito.acc_bonif for credito in creditos if credito.acc_bonif])
			if bonificaciones:
				for bonificacion in bonificaciones:
					creditos_bonificacion = creditos.filter(acc_bonif=bonificacion)
					debe = sum([credito.bonificacion for credito in creditos_bonificacion])
					operacion = {
						'cuenta': bonificacion.cuenta_contable,
						'debe': debe,
						'haber': 0,
						'descripcion': descripcion
					}
					data_operaciones.append(operacion)



			ingresos = set([credito.ingreso for credito in creditos])
			for ingreso in ingresos:
				creditos_ingreso = creditos.filter(ingreso=ingreso)
				haber = sum([credito.capital for credito in creditos_ingreso])
				operacion = {
					'cuenta': ingreso.cuenta_contable,
					'debe': 0,
					'haber': haber,
					'descripcion': descripcion
				}
				data_operaciones.append(operacion)


			crear_asiento = AsientoCreator(data_asiento, data_operaciones)
			asiento = crear_asiento.guardar()
			self.asiento = asiento
			self.save()

	@property
	def cobrado(self):

		""" Retorna brutos de cobrados y pendientes """

		creditos = self.credito_set.filter(padre__isnull=True)
		pendientes = 0
		cobrados = 0
		for c in creditos:
			if c.saldo:
				pendientes += c.bruto
			else:
				cobrados += c.bruto

		return cobrados, pendientes



	def save(self, *args, **kw):
		if not self.numero:
			numero_liq = 1
			try:
				ultima = Liquidacion.objects.filter(
						consorcio=self.consorcio,
						punto=self.punto,
						).order_by('-numero')[0].numero
			except:
				ultima = 0
			self.numero = ultima + numero_liq
		super().save(*args, **kw)


class Factura(models.Model):
	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	receipt = models.ForeignKey(Receipt, blank=True, null=True ,on_delete=models.CASCADE)
	liquidacion = models.ForeignKey(Liquidacion, blank=True, null=True, on_delete=models.CASCADE)
	socio = models.ForeignKey(Socio,blank=True, null=True, on_delete=models.PROTECT)
	pdf = models.FileField(upload_to="facturas/pdf/", blank=True, null=True)
	observacion = models.TextField(blank=True, null=True) # Observacion devuelta por AFIP

	def __str__(self):
		nombre = 'Socio: {}. '.format(self.socio)
		if self.receipt.receipt_number:
			nombre += self.formatoAfip()
		else:
			nombre += 'No validada'
		return nombre

	def puntof(self):
		agregado = "0"
		numero = str(self.receipt.point_of_sales)
		largo = len(numero)
		ceros = 4 - largo
		ceros = agregado * ceros
		numero = ceros + numero
		return numero

	def numerof(self):
		agregado = "0"
		numero = str(self.receipt.receipt_number)
		largo = len(numero)
		ceros = 8 - largo
		ceros = agregado * ceros
		numero = ceros + numero
		return numero

	def formatoAfip(self):
		data = "%s-%s" % (self.puntof(), self.numerof())
		return data

	def incorporar_creditos(self):

		"""
			No es lookup inverso.
			Se utiliza esta funcion para obtener los creditos
			(Los creditos aun no tienen "factura", entonces esta funcion es necesaria).
			Y retorna los creditos
		"""	

		creditos = Credito.objects.filter(liquidacion=self.liquidacion, socio=self.socio)
		creditos.update(factura=self)
		return creditos

	def hacer_pdf(self):

		if not self.pdf:
			archivo = []
			enteros = []
			factura = self
			if self.consorcio.id in [2, 4, 8, 17, 7, 3]: # 2 Demo, 4 Prado, 8 Praderas, 17 Terrazas, 7 Chacras, 3 jardines
				dominios = self.socio.socio.all()
				if dominios:
					creditos = Credito.objects.filter(
							dominio__in=dominios,
							fin__isnull=True,
							liquidacion__estado="confirmado",
							)
				else:
					creditos = Credito.objects.filter(
							socio=self.socio,
							liquidacion__estado="confirmado",
							dominio__isnull=True,
							fin__isnull=True,
							)

				total_deudas = sum([c.saldo for c in creditos])
				total_deudas += sum([c.saldo for c in factura.credito_set.all()])

				saldos = self.socio.get_saldos(fecha=date.today())
				total_saldos = sum([s.saldo() for s in saldos])

				total_adeudado = total_deudas - total_saldos

				if total_adeudado:
					texto_saldo = "Tu saldo total "
					texto_saldo += "adeudado" if total_adeudado >= 0 else "a favor"
					texto_saldo += " a la fecha, incluyendo capital, intereses y descuentos y el monto de la presente factura es de: ${}".format(abs(total_adeudado))
					
			if self.consorcio.id in [2, 8]: # 2 Demo, 8 Praderas
				fecha1 = self.expensas_pagas(0) # Se utiliza expensas_pagas porque se creo esa funcion antes con ese nombre pero hace lo mismo
				fecha2 = self.expensas_pagas(1) # Se utiliza expensas_pagas porque se creo esa funcion antes con ese nombre pero hace lo mismo
				if not fecha2:
					fecha2 = fecha1
				saldo1 = self.saldo(fecha1)
				saldo2 = self.saldo(fecha2)

				tablas_vencimientos = {
					'fecha1': fecha1,
					'saldo1': saldo1,
					'fecha2': fecha2,
					'saldo2': saldo2
				}
			if self.receipt.receipt_type.code == "11":
				generator = ReceiptBarcodeGenerator(self.receipt)
				barcode = base64.b64encode(generator.generate_barcode()).decode("utf-8")
			html_string = render_to_string('creditos/pdfs/{}.html'.format(self.receipt.receipt_type.code), locals())
			html = HTML(string=html_string, base_url='https://www.admincu.com/comprobantes/')
			pdfFactura = html.render()
			enteros.append(pdfFactura)
			for p in pdfFactura.pages:
				archivo.append(p)



			pdf = enteros[0].copy(archivo).write_pdf()
			ruta = "{}_{}_{}.pdf".format(
					str(self.consorcio.abreviatura),
					str(self.receipt.receipt_type.code),
					str(self.formatoAfip())
			)

			self.pdf = SimpleUploadedFile(ruta, pdf, content_type='application/pdf')
			self.save()


	def validar_factura(self):

		"""
			Si es "101" (Factura X) no valida, pone el numero y hace el PDF
			Si es "11" (Factura C) valida la factura y hace el PDF
			o le agrega el error de AFIP en observacion
		"""
		if self.receipt.receipt_type.code == "101":
			if not self.receipt.receipt_number:
				last = Receipt.objects.filter(
					receipt_type=self.receipt.receipt_type,
					point_of_sales=self.receipt.point_of_sales,
				).aggregate(Max('receipt_number'))['receipt_number__max'] or 0
				self.receipt.receipt_number = last + 1
				self.receipt.save()	
				self.hacer_pdf()
		else:
			error = self.receipt.validate()
			if error:
				self.observacion = error
				self.save()
			else:
				self.hacer_pdf()

	@property
	def suma_capitales(self):

		""" Suma los capitales de los creditos """

		return sum([c.capital for c in self.credito_set.filter(padre__isnull=True)])

	@property
	def suma_bonificaciones(self):

		""" Suma las bonificaciones de los creditos """

		return sum([c.bonificacion for c in self.credito_set.filter(padre__isnull=True)])

	def enviar_mail(self):
		if self.consorcio.mails:

			if self.receipt.is_validated or self.consorcio.superficie:
				socio = self.socio
				numero = self.formatoAfip()
				valor = self.receipt.total_amount
				# Expensas pagas
				expensas_pagas = True if self.exp.first() else False
				link_facturacion = armar_link(reverse('facturacion-socio'))
				html_string = render_to_string('creditos/mail.html', locals())

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
							subject="Nueva Factura",
							body="",
							from_email=emisor_mail(self.consorcio),
							to=[receptor],
						)

						msg.attach_alternative(html_string, "text/html")
						msg.attach_file(self.pdf.path)
						if expensas_pagas:
							expensas_pagas_pdf = self.exp.first().pdf.path
							msg.attach_file(expensas_pagas_pdf)
						msg.send()


	def descuentos(self):

		""" Retorna una lista de strings """

		accesorios = []
		for credito in self.credito_set.all():
			if credito.acc_desc:
				leyenda = "Descuento por pronto pago de {} hasta la fecha {} ".format(credito.ingreso, credito.gracia)
				if credito.acc_desc.tipo == "tasa":
					leyenda += "del {}%.".format(credito.acc_desc.monto)
				elif credito.acc_desc.tipo == "fijo":
					leyenda += "de ${}.".format(credito.acc_desc.monto)
				accesorios.append(leyenda)

		return set(accesorios)


	def detalles(self):

		""" Retorna una lista de strings """

		detalles = []
		for credito in self.credito_set.all():
			if credito.detalle_limpio:
				detalles.append(credito.detalle_limpio)

		return detalles


	def fechas_exp(self):
		"""logica de fechas de vencimiento y gracia, retorna una lista con una o dos fechas."""

		l = []

		l.extend(list((self.credito_set.filter(vencimiento__isnull=False)).values_list('vencimiento', flat=True)))
		l.extend(list((self.credito_set.filter(gracia__isnull=False)).values_list('gracia', flat=True)))
		l.append(self.receipt.issued_date + timedelta(days=30))
		l = list(set(l))
		l.sort()
		if len(l)>1:
			l = l[:2]
		else:
			l.append(None)
		return l



	def expensas_pagas(self, indicacion):
		'''Retorna la fecha para expensas pagas, recibe 0 o 1 segun se busque la primera o la segunda fecha'''
		fechas = self.fechas_exp()
		if indicacion == 1 and len(fechas) == 1:
			return None
		return fechas[indicacion]


	def saldo(self, fecha):
		valor = 0
		for c in self.credito_set.filter(padre__isnull=True):
			valor = valor + c.subtotal(fecha_operacion=fecha)
		return float(valor)





class Credito(models.Model):
	consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
	liquidacion = models.ForeignKey(Liquidacion, blank=True, null=True, on_delete=models.CASCADE)
	factura = models.ForeignKey(Factura, blank=True, null=True, on_delete=models.CASCADE)
	fecha = models.DateField(blank=True, null=True)
	periodo = models.DateField(blank=True, null=True)
	ingreso = models.ForeignKey(Ingreso, blank=True, null=True, on_delete=models.CASCADE)
	dominio = models.ForeignKey(Dominio, blank=True, null=True, on_delete=models.CASCADE)
	socio = models.ForeignKey(Socio, blank=True, null=True, on_delete=models.CASCADE)
	acc_int = models.ForeignKey(Accesorio, blank=True, null=True, on_delete=models.PROTECT, related_name='acc_int')
	acc_desc = models.ForeignKey(Accesorio, blank=True, null=True, on_delete=models.PROTECT, related_name='acc_desc')
	acc_bonif = models.ForeignKey(Accesorio, blank=True, null=True, on_delete=models.PROTECT, related_name='acc_bonif')
	vencimiento = models.DateField(blank=True, null=True)
	gracia = models.DateField(blank=True, null=True)
	capital = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
	padre = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL, related_name='hijos')
	detalle = models.CharField(max_length=100, blank=True, null=True)
	fin = models.DateField(blank=True, null=True)


	@property
	def nombre(self):

		""" Retorna el nombre. No utilizo __str__ porque nose donde la estoy mostrando """

		nombre = "Liquidacion {}. ".format(self.liquidacion)
		if self.factura:
			nombre += "Factura C {}.".format(self.factura.formatoAfip())
		return nombre



	def calcular_accesorio(self, accesorio, fecha_operacion=None):

		""" Realiza el calculo de algun accesorio """

		calculo = 0

		if accesorio:
			if accesorio.tipo == "fijo":
				calculo = round(accesorio.monto, 2)
			else:
				if accesorio.clase == "bonificacion":
					calculo = round(self.capital * accesorio.monto / 100, 2)
				elif accesorio.clase == "descuento":
					if self.padre:
						capital = self.padre.bruto
					else:
						capital = self.bruto
					calculo = round(capital * accesorio.monto / 100, 2)
				elif accesorio.clase == "interes":
					bruto = self.bruto
					tasa = accesorio.monto
					reconocimiento = accesorio.reconocimiento
					base_calculo = accesorio.base_calculo
					periodos = ((fecha_operacion - self.vencimiento).days // reconocimiento)
					if not reconocimiento == 1: # por si se elije un reconocimiento distinto de 1, para agararse el interes aun no generado
						periodos += 1
					calculo = round((bruto*tasa*periodos)/(100*base_calculo//reconocimiento), 2)
		return calculo

	@property
	def bonificacion(self):
		return self.calcular_accesorio(self.acc_bonif)

	@property
	def bruto(self):
		return self.capital - self.bonificacion

	@property
	def ultimo_hijo(self):
		if self.hijos.all():
			return self.hijos.last()
		return

	@property
	def actual(self):
		if self.ultimo_hijo:
			return self.ultimo_hijo
		return self

	@property
	def saldo(self, fecha_operacion=date.today(), condonacion=False):
		if self.ultimo_hijo:
			return self.ultimo_hijo.saldo
		else:
			if self.fin:
				return Decimal("%.2f" % 0.00)
			else:
				return self.subtotal(fecha_operacion=fecha_operacion, condonacion=condonacion)

	@property
	def saldo_socio(self):

		""" Devuelve el saldo del socio sumado el descuento, porque tenia deudas anteriores y no pago """

		if self.ultimo_hijo:
			ultimo_saldo = Decimal("%.2f" % self.ultimo_hijo.saldo)
			return ultimo_saldo + self.descuento()
		else:
			if self.fin:
				return 0.00
			else:
				return self.subtotal() + self.descuento()

	@property
	def prioritario(self):
		return self.ingreso.prioritario

	def intereses(self, fecha_operacion=date.today()):
		intereses = 0
		# Si existe accesorio de interes
		if self.acc_int:
			## Si el credito esta vencido
			if self.vencimiento < fecha_operacion:

				intereses = self.calcular_accesorio(self.acc_int, fecha_operacion)

		return Decimal("%.2f" % intereses)

	def descuento(self, fecha_operacion=date.today()):
		descuento = 0
		# Si existe accesorio de descuento
		if self.acc_desc:
			## Si el credito todavia no llego a la fecha del fin de la gracia
			if self.gracia > fecha_operacion or self.gracia == fecha_operacion:

				descuento = self.calcular_accesorio(self.acc_desc, fecha_operacion)

		return Decimal("%.2f" % descuento)

	def int_desc(self, fecha_operacion=date.today(), condonacion=False):
		valor = -self.descuento(fecha_operacion=fecha_operacion)
		if not condonacion:
			valor += self.intereses(fecha_operacion=fecha_operacion)
		return valor

	def subtotal(self, fecha_operacion=date.today(), condonacion=False):
		valor = self.bruto - self.descuento(fecha_operacion=fecha_operacion)
		if not condonacion:
			valor += self.intereses(fecha_operacion=fecha_operacion)
		return valor

	def detalle_acc(self, fecha_operacion=date.today(), condonacion=False):
		texto = ""
		if self.descuento(fecha_operacion=fecha_operacion):
			texto = "Descuento por pronto pago. Hasta el dia {}".format(self.gracia)
		elif self.intereses(fecha_operacion=fecha_operacion) and not condonacion:
			texto = "Intereses generados desde el dia {}".format(self.vencimiento)
		return texto

	@property
	def detalle_limpio(self):
		if self.detalle in ['cat', 'soc', 'gru'] or not self.detalle:
			return
		if self.dominio:
			leyenda = "{} {}. {}-{}: {}".format(
					self.dominio.nombre,
					self.ingreso,
					self.periodo.year,
					self.periodo.month,
					self.detalle
				)
		else:
			leyenda = "{} {}. {}-{}: {}".format(
					self.socio,
					self.ingreso,
					self.periodo.year,
					self.periodo.month,
					self.detalle
				)
		return leyenda


	def __str__(self):
		if self.dominio:
			nombre = '{} {} {}-{}'.format(self.dominio.nombre, self.ingreso, self.periodo.year, self.periodo.month)
		else:
			nombre = '{} {} {}-{}'.format(self.socio, self.ingreso, self.periodo.year, self.periodo.month)
		return nombre



class PdfSocio(models.Model):
	socio = models.ForeignKey(Socio, blank=True, null=True, on_delete=models.CASCADE)
	liquidacion = models.ForeignKey(Liquidacion, on_delete=models.CASCADE)
	pdf = models.FileField(upload_to="liquidaciones/pdf/")