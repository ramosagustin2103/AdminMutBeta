from datetime import date
from django.db import transaction
from .models import *
from arquitectura.models import Caja


class TransferenciaCreator:

	""" Creador y Listador de objetos pre-confirmacion y para guardar """

	def __init__(
			self,
			data_inicial, # Diccionario LIMPIO que contiene "punto", "fecha", "caja_destino"
			data_cajas, # Lista de Diccionarios LIMPIOS que contiene "caja", "subtotal"
		):
		self.punto = data_inicial['punto']
		self.fecha = data_inicial['fecha']
		self.destino = data_inicial['caja_destino']
		self.consorcio = self.punto.owner.consorcio_set.first()
		self.data_cajas = data_cajas


	def hacer_cajas(self):

		"""
			Realiza los objetos de tipo CajaTransferencia
		"""
		transferencias = []

		# Creacion del cobro, sin valores
		for data in self.data_cajas:
			transferencias.append(CajaTransferencia(
				consorcio=self.consorcio,
				fecha=self.fecha,
				origen=data['caja'],
				destino=self.destino,
				referencia=data['referencia'],
				valor=data['subtotal']
			))

		return transferencias

	def hacer_total(self):

		""" Realiza el total """

		cajas = self.hacer_cajas()
		total = sum([caja.valor for caja in cajas])

		return total

	@transaction.atomic
	def guardar(self):
		# Realizacion de la transferencia
		total = self.hacer_total()
		transferencia = Transferencia(
			consorcio=self.consorcio,
			fecha=self.fecha,
			punto=self.punto,
			total=total,
		)
		transferencia.save()

		cajas = []
		for caja in self.hacer_cajas():
			caja.transferencia = transferencia
			cajas.append(caja)

		CajaTransferencia.objects.bulk_create(cajas)

		transferencia.hacer_pdf()
		transferencia.hacer_asiento()
		return transferencia