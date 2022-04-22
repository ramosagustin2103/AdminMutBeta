from django.urls import path
from .views import *

urlpatterns = [
	path('', ejercicios_index, name='ejercicios'),
	path('nuevo/', ejercicio_nuevo, name='ejercicio_nuevo'),
	path('<str:ejercicio>/', ejercicio_set, name='ejercicio_set'),
	path('<str:ejercicio>/diario/', ejercicio_diario, name='ejercicio_diario'),
]
