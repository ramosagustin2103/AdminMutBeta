from django.urls import path
from .views import *

urlpatterns = [
	path('', pc_index, name='cuentas'),
	path('nuevo/', pc_nuevo, name='cuentas_nuevo'),
	path('desvincular/<str:cuenta>/', pc_desvincular, name='cuentas_desvincular'),
	path('<str:cuenta>/', pc_set, name='cuentas_set'),
]
