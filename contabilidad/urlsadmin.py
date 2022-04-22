from django.urls import path
from .views import *

urlpatterns = [
	path('', adm_index, name='administracion'),
]
