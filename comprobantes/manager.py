from datetime import date
from django_afip.models import *
from django.db import transaction
from .models import *
from arquitectura.models import Caja


class ComprobanteCreator:

	""" Creador y Listador de objetos pre-confirmacion y para guardar """

	def __init__(
			self,
			data_inicial, # Diccionario LIMPIO que contiene "punto", "socio", "fecha_operacion", "condonacion", "tipo" ("Recibo X" o "Nota de Credito C")
			data_descripcion, # String de la descripcion
			data_cobros=None, # Lista de Diccionarios LIMPIOS que contiene "credito", "subtotal"
			data_utilizacion_saldos=None, # Lista de Diccionarios LIMPIOS que contiene "saldo", "subtotal"
			data_nuevo_saldo=None, # Valor del nuevo saldo
			data_cajas=None, # Lista de Diccionarios LIMPIOS que contiene "caja", "subtotal"
			data_mp=None, # Lista de objetos Guardados en la base de dato tipo Cobro
			data_exp=None # Lista de objetos Guardados en la base de dato tipo Cobro
		):
		self.punto = data_inicial['punto']
		self.socio = data_inicial['socio']
		self.tipo = data_inicial['tipo']
		self.fecha_operacion = data_inicial['fecha_operacion'] if data_inicial['fecha_operacion'] else date.today()
		self.condonacion = data_inicial['condonacion']
		self.consorcio = self.punto.owner.consorcio_set.first()
		self.data_cobros = data_cobros
		self.data_utilizacion_saldos = data_utilizacion_saldos
		self.data_cajas = data_cajas
		self.descripcion = data_descripcion
		self.data_nuevo_saldo = data_nuevo_saldo
		self.data_mp = data_mp
		self.receipt_type_nd = ReceiptType.objects.get(code="12") if not self.consorcio.superficie else ReceiptType.objects.get(code="102") 
		self.receipt_type_nc = ReceiptType.objects.get(code="13") if not self.consorcio.superficie else ReceiptType.objects.get(code="103") 


	def hacer_cobros_y_creditos(self):

		"""
			Realiza los objetos de tipo cobros y los objetos de tipo credito si es que no pone el mismo monto (El que debe)
		"""
		cobros = []
		creditos = []

		# Si existe data de cobro a traves de MercadoPago
		if self.data_mp:
			for data in self.data_mp:
				data.fecha = date.today()
				cobros.append(data)

		# Creacion del cobro, sin valores
		elif self.data_cobros:
			for data in self.data_cobros:
				credito = data['credito']
				subtotal = data['subtotal'] # Lo que escribio la persona
				cobro = Cobro(
					consorcio=self.consorcio,
					socio=self.socio,
					credito=credito,
					fecha=date.today(),
					subtotal=subtotal,
				)

				bruto = credito.bruto
				int_desc = credito.int_desc(fecha_operacion=self.fecha_operacion, condonacion=self.condonacion)
				total = credito.subtotal(fecha_operacion=self.fecha_operacion, condonacion=self.condonacion) # Lo que deberia colocar el usuario para saldar
				if subtotal == total:
					# Si se coloca el mismo valor que lo que se debe:
					# el cobro pasa derecho
					cobro.capital = bruto
					cobro.int_desc = int_desc
				else:
					# Creacion del credito que surge por el cobro, sin valores
					padre = credito.padre if credito.padre else credito
					credito_nuevo = Credito(
							consorcio=self.consorcio,
							liquidacion=credito.liquidacion,
							factura=credito.factura,
							fecha=date.today(),
							periodo=credito.periodo,
							ingreso=credito.ingreso,
							dominio=credito.dominio,
							socio=credito.socio,
							acc_int=credito.acc_int,
							detalle=credito.detalle,
							padre=padre
						)
					# Si paga algo con intereses, debe abonar los intereses y si sobra va a capital
					if int_desc > 0:
						diferencia = subtotal - int_desc
						if diferencia < 0:
							cobro.int_desc = subtotal
							cobro.capital = 0
						else:
							cobro.int_desc = int_desc
							cobro.capital = diferencia

						credito_nuevo.capital = credito.bruto - diferencia
						credito_nuevo.vencimiento = date.today()
					else:
						cobro.capital = subtotal
						cobro.int_desc = 0

						credito_nuevo.acc_desc = padre.acc_desc
						credito_nuevo.gracia = padre.gracia
						credito_nuevo.capital = credito.bruto - subtotal
						credito_nuevo.vencimiento = padre.vencimiento

					if credito_nuevo.capital > 0.00:
						creditos.append(credito_nuevo)
				cobros.append(cobro)

		return cobros, creditos

	def hacer_utilizaciones_de_saldos(self):

		""" Realiza los objetos de tipo saldo (Utilizados) """

		saldos = []
		if self.data_utilizacion_saldos:
			for data in self.data_utilizacion_saldos:
				saldo = data['saldo']
				# Creacion del saldo
				saldos.append(Saldo(
					consorcio=self.consorcio,
					socio=self.socio,
					fecha=date.today(),
					comprobante_origen=saldo.comprobante_origen,
					subtotal=-data['subtotal'],
					padre=saldo
				))


		return saldos

	def hacer_cajas(self):

		""" Realiza los objetos de tipo caja """

		cajas = []
		if self.data_mp:
			caja = Caja.objects.get(consorcio=self.consorcio, primario=True)
			suma = 0
			for data in self.data_mp:
				suma += data.subtotal
			cajas.append(CajaComprobante(
					consorcio=self.consorcio,
					socio=self.socio,
					fecha=date.today(),
					caja=caja,
					valor=suma
				))
		elif self.data_cajas:
			for data in self.data_cajas:
				cajas.append(CajaComprobante(
						consorcio=self.consorcio,
						socio=self.socio,
						fecha=date.today(),
						caja=data['caja'],
						referencia=data['referencia'],
						valor=data['subtotal']
					))
		return cajas

	def hacer_nuevo_saldo(self):

		""" Realiza el objeto de tipo saldo (El nuevo) """

		saldo = None

		if self.data_nuevo_saldo:
			saldo = Saldo(
			consorcio=self.consorcio,
			socio=self.socio,
			fecha=date.today(),
			subtotal=self.data_nuevo_saldo,
			)
		return saldo

	def hacer_nota_debito(self):

		"""
			Realiza la nota de debito por intereses SIEMPRE que haya intereses
			Por el TOTAL independientemente de si se abonaron los mismos
		"""

		cobros, creditos = self.hacer_cobros_y_creditos()
		intereses = 0
		if cobros and not self.condonacion:
			for cobro in cobros:
				int_desc = cobro.credito.int_desc(fecha_operacion=self.fecha_operacion)
				if int_desc > 0:
					intereses += int_desc

		if intereses:
			return Receipt(
				point_of_sales=self.punto,
				receipt_type=self.receipt_type_nd,
				concept=ConceptType.objects.get(code=2),
				document_type=self.socio.tipo_documento,
				document_number=self.socio.numero_documento,
				issued_date=date.today(),
				total_amount=intereses,
				net_untaxed=0,
				net_taxed=intereses,
				exempt_amount=0,
				service_start=date.today(),
				service_end=date.today(),
				expiration_date=date.today(),
				currency=CurrencyType.objects.get(code="PES"),
				)
		return

	def hacer_nota_credito(self):

		"""
			Realiza la nota de credito AUTOMATICA por descuentos.
			Solo se realizara si la persona paga el total de un credito con descuento.
			Si abona parcialmente un credito que tenga decuento entonces no se realiza la nota de credito
		"""

		cobros, creditos = self.hacer_cobros_y_creditos()
		descuentos = 0
		if cobros:
			for cobro in cobros:
				if (cobro.subtotal == cobro.credito.subtotal(fecha_operacion=self.fecha_operacion, condonacion=self.condonacion) and cobro.int_desc < 0):
					descuentos += cobro.int_desc

		if descuentos:
			descuentos *= -1
			return Receipt(
				point_of_sales=self.punto,
				receipt_type=self.receipt_type_nc,
				concept=ConceptType.objects.get(code=2),
				document_type=self.socio.tipo_documento,
				document_number=self.socio.numero_documento,
				issued_date=date.today(),
				total_amount=descuentos,
				net_untaxed=0,
				net_taxed=descuentos,
				exempt_amount=0,
				service_start=date.today(),
				service_end=date.today(),
				expiration_date=date.today(),
				currency=CurrencyType.objects.get(code="PES"),
				)
		return

	def hacer_total(self):

		""" Realiza el total """

		if self.tipo == "Recibo X" or self.tipo == "Recibo X exp":
			cajas = self.hacer_cajas()
			if cajas:
				total = sum([caja.valor for caja in cajas])
			else:
				total = 0
		else:
			cobros, creditos = self.hacer_cobros_y_creditos()
			total = sum([cobro.subtotal for cobro in cobros])

		return total

	def guardar_vinculaciones(self, comprobante):

		""" Agrega el comprobante a los objetos y los guarda """

		cobros, creditos = self.hacer_cobros_y_creditos()
		if cobros:

			for c in cobros:
				c.credito.fin = c.fecha
				c.credito.save()
				c.comprobante = comprobante
				if self.data_mp:
					c.save()

			if not self.data_mp:
				Cobro.objects.bulk_create(cobros)
				Credito.objects.bulk_create(creditos)

		utilizaciones_saldos = self.hacer_utilizaciones_de_saldos()
		if utilizaciones_saldos:
			for s in utilizaciones_saldos:
				s.comprobante_destino = comprobante

			Saldo.objects.bulk_create(utilizaciones_saldos)

		cajas = self.hacer_cajas()
		if cajas:
			for c in cajas:
				c.comprobante = comprobante
			CajaComprobante.objects.bulk_create(cajas)

		nuevo_saldo = self.hacer_nuevo_saldo()
		if nuevo_saldo:
			nuevo_saldo.comprobante_origen = comprobante
			nuevo_saldo.save()

	@transaction.atomic
	def guardar(self, masivo=False):
		# Realizacion del comprobante
		if self.tipo == "Recibo X" or self.tipo == "Recibo X exp" or self.tipo == "Recibo X exp masivo":
			punto = self.punto
		else:
			punto = None
		total = self.hacer_total()
		comprobante = Comprobante(
			consorcio=self.consorcio,
			socio=self.socio,
			punto=punto,
			fecha=date.today(),
			descripcion=self.descripcion,
			total=total,
		)
		# Realizacion de la nota de credito
		if self.tipo == "Nota de Credito C":
			# Por realizacion manual de la nota de credito
			nota_credito = Receipt(
				point_of_sales=self.punto,
				receipt_type=self.receipt_type_nc,
				concept=ConceptType.objects.get(code=2),
				document_type=self.socio.tipo_documento,
				document_number=self.socio.numero_documento,
				issued_date=date.today(),
				total_amount=total,
				net_untaxed=0,
				net_taxed=total,
				exempt_amount=0,
				service_start=date.today(),
				service_end=date.today(),
				expiration_date=date.today(),
				currency=CurrencyType.objects.get(code="PES"),
				)
		else:
			# Por realizacion de Recibo X
			nota_credito = self.hacer_nota_credito()

		if nota_credito:
			nota_credito.save()
			factura = self.data_cobros[-1]['credito'].factura
			if not factura:
				factura = self.socio.factura_set.first()
			related_receipt = factura.receipt
			nota_credito.related_receipts.add(related_receipt)
			if not masivo:
				validacion = comprobante.validar_receipt(nota_credito)
				if validacion:
					return validacion
			comprobante.nota_credito = nota_credito
		# Fin de la realizacion de la nota de credito

		# Realizacion de la nota de debito por intereses
		nota_debito = self.hacer_nota_debito()
		if nota_debito:
			nota_debito.save()
			factura = self.data_cobros[-1]['credito'].factura
			if not factura:
				factura = self.socio.factura_set.first()
			related_receipt = factura.receipt
			nota_debito.related_receipts.add(related_receipt)
			if not masivo:
				validacion = comprobante.validar_receipt(nota_debito)
				if validacion:
					return validacion
			comprobante.nota_debito = nota_debito
		# Fin de la realizacion de la nota de debito


		# Guardado del comprobante si se validan los receipts en AFIP
		comprobante.save()
		self.guardar_vinculaciones(comprobante)
		if not masivo:
			comprobante.hacer_pdfs()
			comprobante.enviar_mail()
		return comprobante