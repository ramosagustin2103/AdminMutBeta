from django.urls import include, path
from .views import *

urlpatterns = [
	path('', perfil_index, name='perfil'),
	path('pass/', perfil_pass, name='perfil_pass'),
	path('edicion/', perfil_edicion, name='perfil_edicion'),
]
