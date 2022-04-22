from django.db import transaction
from contabilidad.models import *
from admincu.funciones import randomNumber

class AsientoCreator:

	""" Creador de asientos """

	def __init__(
			self,
			data_asiento, # Diccionario LIMPIO que contiene "consorcio", "fecha_asiento", "descripcion",
			data_operaciones, # Lista de Diccionarios LIMPIOS que contiene "cuenta", "debe", "haber", "descripcion"
		):
		self.data_asiento = data_asiento
		self.operaciones = data_operaciones
		self.numero_aleatorio = randomNumber(Operacion, 'numero_aleatorio')

	def hacer_asiento(self):

		""" Crea el objeto Asiento """

		return Asiento(**self.data_asiento)

	def hacer_operaciones(self):

		""" Crea los objetos Operacion """

		operaciones = []
		for data in self.operaciones:
			operacion = Operacion(**data)
			operacion.numero_aleatorio = self.numero_aleatorio
			operaciones.append(operacion)
		return operaciones


	@transaction.atomic
	def guardar(self):

		""" Guardado en la base de datos """

		Operacion.objects.bulk_create(self.hacer_operaciones())
		operaciones = Operacion.objects.filter(numero_aleatorio=self.numero_aleatorio)

		asiento = self.hacer_asiento()
		asiento.save()
		asiento.operaciones.add(*operaciones)
		return asiento