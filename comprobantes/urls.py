from django.urls import path
from .views import *

urlpatterns = [
	# Indexs
	path('', Index.as_view(), name='cobranzas'),
	path('socio/', IndexSocio.as_view(), name='cobranzas-socio'), # Index para Socio

	# Creaciones
	path('RCX/', RCXWizard.as_view(), name='nuevo-rcx'),
	path('RCX/<int:pk>', RCXFacturaWizard.as_view(), name='nuevo-rcx-factura'), # pk de la factura a cobrar
	path('RCXMP/', RCXMPWizard.as_view(), name='nuevo-rcxmp'),
	path('RCXEXP/', RCXEXPWizard.as_view(), name='nuevo-rcxexp'),
	path('RCXEXP/masivo/', RCXEXPMWizard.as_view(), name='nuevo-rcxexp-masivo'),
	path('NCC/', NCCWizard.as_view(), name='nuevo-ncc'),
	#path('cobros/importacion/', CobrosImportacionWizard.as_view(), name='nuevo-cobros-importacion'),

	# Registros
	path('registro/', Registro.as_view(), name='registro'),

	# Vistas particulares
	path('pdf/<int:pk>/', PDF.as_view(), name='pdf-comprobante'),
	path('ver/<int:pk>/', Ver.as_view(), name='ver-comprobante'),
	path('anular/<int:pk>/', Anular.as_view(), name='anular-comprobante'),

]
