from django.urls import path
from .views import *

urlpatterns = [
	path('', Index.as_view(), name='herramientas'),
	path('rg3369/', Rg3369.as_view(), name='rg3369'),

	# Transferencia entre cajas
	path('transferencias/', TransferenciasIndex.as_view(), name='transferencias'),
	path('transferencias/nueva/', TransferenciaWizard.as_view(), name='nueva-transferencia'),
	path('transferencias/registros/', RegistroTransferencias.as_view(), name='registro de transferencias'),
	path('transferencias/pdf/<int:pk>/', PDFTransferencia.as_view(), name='pdf-transferencia'),
]
