from django.urls import path
from .views import *
from expensas_pagas.manager import *
from .views_mp import *

urlpatterns = [
	# Indexs
	path('', Index.as_view(), name='facturacion'), # Index para Administrativo y Contable
	path('socio/', IndexSocio.as_view(), name='facturacion-socio'), # Index para Socio
	path('conceptos/', IndexConceptos.as_view(), name='conceptos'), # Index para Administrativo y Contable


	# Creaciones
	path('nuevo/individuales/', IndividualesWizard.as_view(), name='nuevo-individuales'),
	path('nuevo/masivo/', MasivoWizard.as_view(), name='nuevo-masivo'),
	path('nuevo/grupos/', GrupoWizard.as_view(), name='nuevo-grupo'),
	path('nuevo/conceptos/', ConceptoWizard.as_view(), name='nuevo-conceptos'),
	path('nuevo/conceptos/importacion/', ConceptoImportacionWizard.as_view(), name='nuevo-conceptos-importacion'),

	# Registros
	path('registro/liquidaciones/', RegistroLiquidaciones.as_view(), name='registro de liquidaciones'),
	path('registro/creditos/', RegistroCreditos.as_view(), name='registro de creditos'),

	# Vistas particulares
	path('liquidacion/pdf/<int:pk>/', PDFLiquidacion.as_view(), name='pdf-liquidacion'),
	path('comprobante/pdf/<int:pk>/', PDFFactura.as_view(), name='pdf-factura'),
	path('liquidacion/<int:pk>/', Ver.as_view(), name='ver-liquidacion'),
	path('errores/<int:pk>/', VerErrores.as_view(), name='ver-errores'),
	path('editar/concepto/<int:pk>/', EditarConcepto.as_view(), name='editar-concepto'),
	path('eliminar/conceptos/', EliminarConcepto.as_view(), name='eliminar-conceptos'),
	path('liquidar/conceptos/', LiquidarConcepto.as_view(), name='liquidar-conceptos'),

	# MercadoPago
	path('MercadoPago/', PreferenceNew.as_view(), name='preference-new'),
	path('MercadoPago/Eliminar/<int:pk>/', PreferenceDelete.as_view(), name='preference-delete'),
	path('MercadoPago/Success/<int:pk>/', MPSuccess.as_view(), name='mp-success'),
	path('MercadoPago/Failed/<int:pk>/', MPFailed.as_view(), name='mp-failed'),
	path('MercadoPago/Pending/<int:pk>/', MPPending.as_view(), name='mp-pending'),

]
