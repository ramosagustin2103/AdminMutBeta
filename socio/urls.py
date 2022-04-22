from django.urls import path
from .views import *

urlpatterns = [
	path('estado-cuenta/', exp_index, name='expensas'),
	path('eliminar-pagos/', eliminar_pagos, name='eliminar_pagos'),
	path('pagos/', pagos_index, name='pagos'),
    path('pago-exitoso/<str:pk>', mp_success, name='mp_success'),
    path('pago-fallido/<str:pk>', mp_failure, name='mp_failure'),
    path('pago-pendiente/<str:pk>', mp_pending, name='mp_pending'),
]

