from django.urls import path
from .views import *


urlpatterns = [
	path('', asiento_index, name='asiento'),
	path('eliminar/', asiento_eliminar, name='asiento_eliminar'),
	path('generador/', asiento_generador_principales, name='asiento_generador'),
	path('<int:numero>', asiento_index, name='asiento_mod'),
	path('redireccion/<int:id_asiento>', asiento_redireccion, name='asiento_redireccion'),
]


