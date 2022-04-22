from django.urls import path
from .views import *

urlpatterns = [
	path('', bib_index, name='biblioteca'),
	path('eliminar/<str:tipo>/<str:instance>', bib_eliminar, name='bib_eliminar'),
	path('descargar/<str:slug>/', bib_descargar, name='bib_descargar'),
	path('<str:tipo>/', bib_nuevo, name='bib_nuevo'),
	path('<str:tipo>/<str:instance>/', bib_nuevo, name='bib_nuevo'),
]
