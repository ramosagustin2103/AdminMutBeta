from rest_framework import viewsets

from django.http import Http404
from rest_framework.response import Response
from django.shortcuts import get_object_or_404 

from .permissions import IsSSUser

from arquitectura.models import (
	Socio
)

class EstadoCuentaViewSet(viewsets.ModelViewSet):
	"""
		Estado de cuenta para Cliente (Consulta hoy unicamente SimpleSolutions)
	"""
	http_method_names = ['get']



	def get_object(self):
		obj = get_object_or_404(
				Socio.objects.all(),
				pk=self.kwargs["pk"]
			)
		self.check_object_permissions(self.request, obj)
		return obj
			

	def retrieve(self, request, pk=None, **kwargs):
		socio = self.get_object()
		operaciones = []
		for fecha, datas in socio.cuenta_corriente().items():
			for numero, operacion in datas.items():
				operacion = {
					'numero': numero,
					'fecha': fecha,
					'concepto': str(operacion[0]),
					'comprobante': str(operacion[1]),
					'debito': operacion[2],
					'credito': operacion[3],
					'saldo': operacion[4]
				}
				operaciones.append(operacion)

		return Response(operaciones)



	def get_queryset(self, **kwargs):
		return []

	def get_permissions(self):
		'''Manejo de permisos'''
		permissions = [IsSSUser]
		return [p() for p in permissions]

