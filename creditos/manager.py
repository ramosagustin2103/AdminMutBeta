from datetime import date
from creditos.models import *
from django_afip.models import *
from django.db import transaction


class LiquidacionCreator:

	""" Creador y Listador de objetos pre-confirmacion y para guardar """

	def __init__(
			self,
			data_inicial, # Diccionario LIMPIO que contiene "punto", "fecha_operacion", "concepto", "fecha_factura"
			data_creditos, # Lista de Diccionarios LIMPIOS que contiene "campos basicos para crear objetos de credito". Ver en views.py
			data_plazos=None, # Lista de Diccionarios LIMPIOS que contienen "accesorio" y "plazo"
			preconceptos=None # QUERYSET con Objetos de tipo Credito para incorporar a la liquidacion
		):
		self.punto = data_inicial['punto']
		self.consorcio = self.punto.owner.consorcio_set.first()
		self.receipt_type = ReceiptType.objects.get(code="11") if not self.consorcio.superficie else ReceiptType.objects.get(code="101") 
		self.periodo = data_inicial['fecha_operacion']
		self.fecha_factura = data_inicial['fecha_factura']
		self.concepto = data_inicial['concepto']
		self.creditos = data_creditos
		self.data_plazos = data_plazos
		self.preconceptos = preconceptos or Credito.objects.none()

	def reagrupar_creditos(self):

		""" Reagrupacion de creditos por destinatario de factura """

		socios = set([credito['socio'] for credito in self.creditos])
		grupos_de_creditos = [[credito for credito in self.creditos if credito['socio'] == socio] for socio in socios]
		return grupos_de_creditos

	def colocar_accesorios(self, credito):

		""" Le agrega los accesorios al credito """

		accesorios = credito.ingreso.accesorio_set.filter(finalizacion__isnull=True)
		if accesorios:
			for a in accesorios:
				if a.clase == "descuento":
					credito.acc_desc = a
				elif a.clase == "interes":
					credito.acc_int = a
				elif a.clase == "bonificacion" and credito.dominio.grupo_set.all():
					credito.acc_bonif = a

		return credito

	def hacer_total(self, socio, grupo_creditos=None, grupo_preconceptos=None):

		"""
		Calcula el total por factura.
		"""

		suma = 0
		if grupo_creditos:
			for credito in grupo_creditos:
				suma += credito.bruto
		preconceptos_socio = self.preconceptos.filter(socio=socio)
		if grupo_preconceptos:
			for credito in grupo_preconceptos:
				suma += credito.bruto

		return suma

	def colocar_plazos(self, credito):

		""" Recibe objeto de tipo credito y le coloca fecha de vencimiento y fecha de gracia si es que encuentra """

		for a in self.data_plazos:
			if credito.ingreso in a['accesorio'].ingreso.all():
				if a['accesorio'].clase == "interes":
					credito.vencimiento = a['plazo']
				elif a['accesorio'].clase == "descuento":
					credito.gracia = a['plazo']

	def hacer_credito(self, c):

		""" Crea los objetos de tipo Credito """

		# Creacion de los creditos
		data = c.copy()
		data['fecha'] = self.fecha_factura
		credito = Credito(**data)
		# Colocacion de vencimiento y gracia
		self.colocar_plazos(credito)
		self.colocar_accesorios(credito)
		if credito.bruto == 0.00:
			credito.fin = self.fecha_factura or credito.periodo

		return credito

	def hacer_documento(self, socio, grupo_creditos=None, grupo_preconceptos=None):

		""" Crea diccionario con receipt, factura y creditos por la cabeza """

		# Creacion del receipt sin totales ni finalizacion de conceptos
		receipt = Receipt(
			point_of_sales=self.punto,
			receipt_type=self.receipt_type,
			concept=self.concepto,
			document_type=socio.tipo_documento,
			document_number=socio.numero_documento,
			issued_date=self.fecha_factura,
			net_untaxed=0,
			exempt_amount=0,
			expiration_date=self.fecha_factura,
			currency=CurrencyType.objects.get(code="PES"),
		)
		# Agregar finalizacion de conceptos en el receipt recien creado
		if not self.concepto.code == "1":
			receipt.service_start = self.fecha_factura
			receipt.service_end = self.fecha_factura

		# Creacion de la factura. Nada tiene que ver con el receipt. Por ahora
		factura = Factura(
			consorcio=self.consorcio,
			socio=socio,
		)

		# Creacion de los creditos
		creditos = []
		if grupo_creditos:
			for c in grupo_creditos:
				creditos.append(self.hacer_credito(c))

		total_factura = self.hacer_total(socio=socio, grupo_creditos=creditos, grupo_preconceptos=grupo_preconceptos)
		receipt.total_amount = total_factura
		receipt.net_taxed = total_factura

		documento = {
			'receipt': receipt,
			'factura': factura,
			'creditos': creditos,
			'preconceptos': grupo_preconceptos
		}
		return documento


	def socios_preconceptos(self):

		socios = []
		if self.preconceptos:
			for credito in self.preconceptos:
				socios.append(credito.socio)

		return set(socios)

	def listar_documentos(self):

		""" Lista todos los documentos que se pueden realizar una vez recibidos los creditos """

		grupos_de_creditos = self.reagrupar_creditos()
		documentos = []
		for grupo in grupos_de_creditos:
			socio = grupo[0]['socio']
			preconceptos_socio = self.preconceptos.filter(socio=socio)
			documentos.append(self.hacer_documento(socio=socio, grupo_creditos=grupo, grupo_preconceptos=preconceptos_socio))
		if not grupos_de_creditos:
			socios = self.socios_preconceptos()
			for socio in socios:
				preconceptos_socio = self.preconceptos.filter(socio=socio)
				documentos.append(self.hacer_documento(socio=socio, grupo_preconceptos=preconceptos_socio))



		return documentos

	def guardar_preconceptos(self, liquidacion):

		self.preconceptos.update(liquidacion=liquidacion)
		self.preconceptos.update(fecha=self.fecha_factura)

	@transaction.atomic
	def guardar(self):

		""" Incorpora los objetos procesados en esta clase en la base de datos """

		# Guardado de liquidacion
		liquidacion = Liquidacion(
			consorcio=self.consorcio,
			punto=self.punto,
			fecha=date.today(),
			estado="errores",
		)
		liquidacion.save()

		facturas = []
		creditos = []
		for documento in self.listar_documentos():
			# Guardado de receipt
			receipt = documento['receipt']
			receipt.save()


			# Incorporacion de atributos necesarios a la factura. Sin guardar, Para ahorrar consultas se hara con bulk_create
			documento['factura'].receipt = receipt
			documento['factura'].liquidacion = liquidacion
			facturas.append(documento['factura'])
			for credito in documento['creditos']:
				credito.liquidacion = liquidacion
				creditos.append(credito)

		Factura.objects.bulk_create(facturas)
		Credito.objects.bulk_create(creditos) # Se crean sin la vinculacion con su factura.
		self.guardar_preconceptos(liquidacion)

		liquidacion.estado = "en_proceso"
		liquidacion.save()

		return liquidacion