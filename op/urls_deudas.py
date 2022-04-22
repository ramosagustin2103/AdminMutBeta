from django.urls import path
from .views_deud import *


urlpatterns = [
    path('', deud_index, name='deudas'),

    path('registro/', Registro.as_view(), name='registro de deudas'),

    path('nuevo/', deud_nuevo, name='deud_nuevo'),
    path('vinculaciones/', deud_vinculaciones, name='deud_vinculaciones'),
    path('confirm/<int:pk>/', deud_confirm, name='deud_confirm'),
    path('cancelar/<int:pk>/', deud_eliminar, name='deud_eliminar'),
    path('vincular-pago/<int:pk>/', deud_vincular_pago, name='deud_vincular_pago'),
    path('<int:pk>/', deud_ver, name='deud_ver'),

]
