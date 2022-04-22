from django.urls import include, path
from .views import *
from .libros import views as vl

urlpatterns = [
	path('', cont_index, name='contabilidad'),
	# Asientos
	path('asientos/', include('contabilidad.asientos.urls')),
	# Mayores
	path('mayores/', vl.mayores_index, name='mayores'),
	# Mayores
	path('sys/', vl.sys_index, name='sys'),
	# Ejercicios
	path('ejercicios/', include('contabilidad.ejercicios.urls')),
	# Plan de cuentas
	path('cuentas/', include('contabilidad.cuentas.urls')),
]
