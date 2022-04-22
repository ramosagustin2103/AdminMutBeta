from django.urls import path
from .views_op import *

urlpatterns = [

    path('', op_index, name='op'),

    path('registro/', Registro.as_view(), name='registro de pagos'),

    path('parcial-deuda/<int:pk>', op_d_parcial, name='op_d_parcial'),
    path('nuevo/', op_nuevo, name='op_nuevo'),
    path('vinculaciones/<int:pk>', op_vinculaciones, name='op_vinculaciones'),
    path('caja/<int:pk>', op_caja, name='op_caja'),
    path('confirm/<int:pk>/', op_confirm, name='op_confirm'),
    path('cancelar/<int:pk>/', op_eliminar, name='op_eliminar'),
    path('anular/<int:pk>/', OPAnular.as_view(), name='op_anular'),
    path('pdf/<int:pk>/', op_pdf, name='op_pdf'),
    path('<int:pk>/', op_ver, name='op_ver'),

]
